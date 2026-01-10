"""
API endpoints for Deriv/MT5 integration
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_, func
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import asyncio

from api import schemas
from api.database import get_db
from api.auth import get_current_active_user
from api.models import User, Analysis
from api.modelss.integration_models import DerivConnection, DerivTrade, SyncLog, WebhookEvent
from api.utils.encryption import encryption_service
from api.utils.deriv_client import DerivAPIClient
from api.schemass.integrations import (
    DerivConnectRequest, ConnectionStatusResponse, SyncResultResponse,
    ConnectionResponse, SyncTradesRequest, UpdateConnectionRequest,
    WebhookEventRequest, WebhookResponse, ConnectionStats
)
from core.metrics_calculator import TradeMetricsCalculator
from core.risk_rules import RiskRuleEngine
from core.risk_scorer import RiskScorer
from core.ai_explainer import AIRiskExplainer

router = APIRouter()

# Helper functions
def get_deriv_connection(db: Session, connection_id: str, user_id: str) -> DerivConnection:
    """Get Deriv connection with authorization check"""
    connection = db.query(DerivConnection).filter(
        DerivConnection.id == connection_id,
        DerivConnection.user_id == user_id
    ).first()
    
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    return connection

def create_sync_log(db: Session, connection_id: str, sync_type: str, status: str = "started") -> SyncLog:
    """Create a new sync log entry"""
    sync_log = SyncLog(
        connection_id=connection_id,
        sync_type=sync_type,
        status=status
    )
    db.add(sync_log)
    db.commit()
    db.refresh(sync_log)
    return sync_log

def update_sync_log(db: Session, sync_log: SyncLog, status: str, stats: Dict[str, Any] = None):
    """Update sync log with results"""
    sync_log.status = status
    sync_log.completed_at = datetime.utcnow()
    
    if stats:
        for key, value in stats.items():
            if hasattr(sync_log, key):
                setattr(sync_log, key, value)
    
    # Calculate duration
    if sync_log.started_at:
        sync_log.duration_seconds = (sync_log.completed_at - sync_log.started_at).total_seconds()
    
    db.commit()

def sync_trades_background(
    db: Session,
    connection: DerivConnection,
    days_back: int,
    force_full_sync: bool,
    analyze_after_sync: bool
):
    """Background task to sync trades"""
    sync_log = create_sync_log(db, connection.id, "manual" if force_full_sync else "incremental")
    
    try:
        # Decrypt API token
        api_token = encryption_service.decrypt(connection.api_token_encrypted)
        if not api_token:
            raise Exception("Failed to decrypt API token")
        
        # Create Deriv client
        client = DerivAPIClient(
            api_token=api_token,
            app_id=connection.app_id,
            account_id=connection.account_id
        )
        
        # Test connection first
        test_result = client.test_connection()
        if not test_result.get("success"):
            raise Exception(f"Connection test failed: {test_result.get('error')}")
        
        # Get account info
        account_info = test_result.get("account_info", {})
        connection.account_info = account_info
        connection.connection_status = "connected"
        
        # Get trades from Deriv
        trades = client.get_trades(days_back)
        
        # Process trades
        new_trades = 0
        updated_trades = 0
        skipped_trades = 0
        
        for trade_data in trades:
            # Check if trade already exists
            existing_trade = db.query(DerivTrade).filter(
                DerivTrade.deriv_trade_id == trade_data["deriv_trade_id"],
                DerivTrade.connection_id == connection.id
            ).first()
            
            if existing_trade:
                # Update existing trade
                for key, value in trade_data.items():
                    if hasattr(existing_trade, key) and key not in ["id", "created_at"]:
                        setattr(existing_trade, key, value)
                updated_trades += 1
            else:
                # Create new trade
                trade = DerivTrade(
                    connection_id=connection.id,
                    deriv_trade_id=trade_data["deriv_trade_id"],
                    transaction_id=trade_data.get("transaction_id"),
                    contract_id=trade_data.get("contract_id"),
                    symbol=trade_data.get("symbol", ""),
                    contract_type=trade_data.get("contract_type", ""),
                    currency=trade_data.get("currency", "USD"),
                    buy_price=trade_data.get("buy_price", 0),
                    sell_price=trade_data.get("sell_price"),
                    barrier=trade_data.get("barrier"),
                    barrier2=trade_data.get("barrier2"),
                    stake=trade_data.get("stake", 0),
                    payout=trade_data.get("payout"),
                    profit=trade_data.get("profit", 0),
                    purchase_time=trade_data.get("purchase_time"),
                    expiry_time=trade_data.get("expiry_time"),
                    sell_time=trade_data.get("sell_time"),
                    duration=trade_data.get("duration"),
                    status=trade_data.get("status", "unknown"),
                    exit_spot=trade_data.get("exit_spot"),
                    raw_data=trade_data.get("raw_data")
                )
                db.add(trade)
                new_trades += 1
        
        db.commit()
        
        # Update connection stats
        connection.last_sync_at = datetime.utcnow()
        connection.last_successful_sync = datetime.utcnow()
        connection.last_sync_status = "success"
        connection.total_syncs += 1
        connection.total_trades_synced += new_trades
        connection.error_count = 0
        connection.last_error = None
        
        db.commit()
        
        # Run analysis if requested and we have new trades
        analysis_id = None
        analysis_score = None
        
        if analyze_after_sync and (new_trades > 0 or updated_trades > 0):
            analysis_result = analyze_synced_trades(db, connection, sync_log)
            if analysis_result:
                analysis_id = analysis_result.get("analysis_id")
                analysis_score = analysis_result.get("score")
        
        # Update sync log with success
        update_sync_log(
            db=db,
            sync_log=sync_log,
            status="success",
            stats={
                "trades_fetched": len(trades),
                "trades_new": new_trades,
                "trades_updated": updated_trades,
                "trades_skipped": skipped_trades,
                "analysis_id": analysis_id
            }
        )
        
    except Exception as e:
        # Update connection with error
        connection.connection_status = "error"
        connection.last_sync_status = "failed"
        connection.last_error = str(e)
        connection.error_count += 1
        
        # Update sync log with failure
        update_sync_log(
            db=db,
            sync_log=sync_log,
            status="failed",
            stats={
                "error_message": str(e)
            }
        )
        
        db.commit()

def analyze_synced_trades(db: Session, connection: DerivConnection, sync_log: SyncLog) -> Optional[Dict[str, Any]]:
    """Analyze synced trades and create analysis"""
    try:
        # Get recent trades from this connection
        trades = db.query(DerivTrade).filter(
            DerivTrade.connection_id == connection.id
        ).order_by(DerivTrade.purchase_time).all()
        
        if not trades:
            return None
        
        # Convert to DataFrame-like format for analysis
        trades_data = []
        for trade in trades:
            trades_data.append({
                "trade_id": trade.id,
                "symbol": trade.symbol,
                "profit_loss": trade.profit,
                "lot_size": trade.stake / 100,  # Approximate lot size
                "account_balance_before": 10000,  # Default, should be calculated
                "stop_loss": None,  # Deriv doesn't have stop loss in same way
                "entry_time": trade.purchase_time,
                "exit_time": trade.sell_time or trade.expiry_time or trade.purchase_time,
                "trade_type": "BUY" if trade.profit >= 0 else "SELL"  # Simplified
            })
        
        # Import pandas locally to avoid dependency if not needed
        import pandas as pd
        df = pd.DataFrame(trades_data)
        
        # Calculate metrics
        calculator = TradeMetricsCalculator(df)
        metrics = calculator.compute_all_metrics()
        
        # Detect risks
        risk_engine = RiskRuleEngine(metrics, df)
        risk_results = risk_engine.detect_all_risks()
        
        # Calculate score
        scorer = RiskScorer()
        score_result = scorer.calculate_score(risk_results['risk_details'])
        
        # Generate AI explanations
        ai_explainer = AIRiskExplainer()
        ai_explanations = ai_explainer.generate_explanation(
            metrics, 
            risk_results, 
            score_result
        )
        
        # Create analysis record
        analysis = Analysis(
            user_id=connection.user_id,
            filename=f"deriv_sync_{connection.id}",
            original_filename=f"Deriv Account {connection.account_id}",
            file_size=len(trades_data) * 100,  # Approximate
            trade_count=len(trades),
            metrics=metrics,
            risk_results=risk_results,
            score_result=score_result,
            ai_explanations=ai_explanations,
            status="completed",
            completed_at=datetime.utcnow()
        )
        
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        
        # Link trades to analysis
        for trade in trades:
            trade.analysis_id = analysis.id
        
        # Link sync log to analysis
        sync_log.analysis_id = analysis.id
        
        db.commit()
        
        return {
            "analysis_id": analysis.id,
            "score": score_result.get("score"),
            "grade": score_result.get("grade"),
            "trade_count": len(trades)
        }
        
    except Exception as e:
        print(f"Error analyzing synced trades: {e}")
        return None

# API Endpoints
@router.post("/deriv/connect", response_model=schemas.APIResponse)
async def connect_deriv_account(
    request: DerivConnectRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Connect a Deriv account using API credentials
    """
    try:
        # Check if connection already exists for this account
        existing = db.query(DerivConnection).filter(
            DerivConnection.user_id == current_user.id,
            DerivConnection.app_id == request.app_id,
            DerivConnection.account_id == request.account_id
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Account already connected"
            )
        
        # Test the connection first
        client = DerivAPIClient(
            api_token=request.api_token,
            app_id=request.app_id,
            account_id=request.account_id
        )
        
        test_result = client.test_connection()
        if not test_result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=f"Connection test failed: {test_result.get('error')}"
            )
        
        # Encrypt API token for storage
        encrypted_token = encryption_service.encrypt(request.api_token)
        
        # Create connection record
        connection = DerivConnection(
            user_id=current_user.id,
            api_token_encrypted=encrypted_token,
            app_id=request.app_id,
            account_id=request.account_id,
            connection_name=request.connection_name,
            connection_status="connected",
            account_info=test_result.get("account_info", {}),
            auto_sync=request.auto_sync,
            sync_frequency=request.sync_frequency,
            sync_days_back=request.sync_days_back,
            connected_at=datetime.utcnow()
        )
        
        db.add(connection)
        db.commit()
        db.refresh(connection)
        
        # Start initial sync in background
        if request.auto_sync:
            background_tasks.add_task(
                sync_trades_background,
                db=db,
                connection=connection,
                days_back=request.sync_days_back,
                force_full_sync=True,
                analyze_after_sync=True
            )
        
        return schemas.APIResponse.success_response(
            data={
                "connection": connection.to_dict(),
                "test_result": test_result
            },
            message="Deriv account connected successfully. Initial sync started in background."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error connecting Deriv account: {str(e)}"
        )

@router.post("/deriv/sync", response_model=schemas.APIResponse)
async def sync_deriv_trades(
    request: SyncTradesRequest,
    background_tasks: BackgroundTasks,
    connection_id: Optional[str] = Query(None, description="Specific connection ID (optional)"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Manually sync trades from Deriv account
    """
    try:
        if connection_id:
            # Sync specific connection
            connection = get_deriv_connection(db, connection_id, current_user.id)
            connections = [connection]
        else:
            # Sync all user's connections
            connections = db.query(DerivConnection).filter(
                DerivConnection.user_id == current_user.id,
                DerivConnection.connection_status == "connected"
            ).all()
        
        if not connections:
            raise HTTPException(
                status_code=404,
                detail="No connected Deriv accounts found"
            )
        
        # Start background sync for each connection
        for connection in connections:
            days_back = request.days_back or connection.sync_days_back
            
            background_tasks.add_task(
                sync_trades_background,
                db=db,
                connection=connection,
                days_back=days_back,
                force_full_sync=request.force_full_sync,
                analyze_after_sync=request.analyze_after_sync
            )
        
        return schemas.APIResponse.success_response(
            data={
                "connections_syncing": [c.id for c in connections],
                "total_connections": len(connections)
            },
            message=f"Started sync for {len(connections)} connection(s)"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error starting sync: {str(e)}"
        )

@router.get("/deriv/status", response_model=schemas.APIResponse)
async def get_deriv_status(
    connection_id: Optional[str] = Query(None, description="Specific connection ID (optional)"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get status of Deriv connection(s)
    """
    try:
        if connection_id:
            # Get specific connection
            connection = get_deriv_connection(db, connection_id, current_user.id)
            connections = [connection]
        else:
            # Get all user's connections
            connections = db.query(DerivConnection).filter(
                DerivConnection.user_id == current_user.id
            ).all()
        
        status_data = []
        for connection in connections:
            # Calculate next sync time
            next_sync = None
            if connection.auto_sync and connection.last_sync_at:
                if connection.sync_frequency == "hourly":
                    next_sync = connection.last_sync_at + timedelta(hours=1)
                elif connection.sync_frequency == "daily":
                    next_sync = connection.last_sync_at + timedelta(days=1)
                elif connection.sync_frequency == "weekly":
                    next_sync = connection.last_sync_at + timedelta(weeks=1)
            
            status_data.append({
                "connection": connection.to_dict(),
                "next_sync": next_sync.isoformat() if next_sync else None,
                "is_syncing": False,  # Would need to track in-progress syncs
                "can_sync": connection.connection_status == "connected"
            })
        
        return schemas.APIResponse.success_response(
            data={
                "connections": status_data,
                "total_connections": len(connections),
                "active_connections": sum(1 for c in connections if c.connection_status == "connected")
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting status: {str(e)}"
        )

@router.get("/deriv/connections", response_model=schemas.APIResponse)
async def list_deriv_connections(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List all Deriv connections for current user
    """
    try:
        connections = db.query(DerivConnection).filter(
            DerivConnection.user_id == current_user.id
        ).order_by(desc(DerivConnection.created_at)).all()
        
        return schemas.APIResponse.success_response(
            data={
                "connections": [connection.to_dict() for connection in connections],
                "total": len(connections)
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error listing connections: {str(e)}"
        )

@router.get("/deriv/trades", response_model=schemas.APIResponse)
async def get_deriv_trades(
    connection_id: str = Query(..., description="Connection ID"),
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    status: Optional[str] = Query(None, regex="^(open|won|lost|sold|expired|all)$"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get trades for a specific Deriv connection
    """
    try:
        connection = get_deriv_connection(db, connection_id, current_user.id)
        
        # Build query
        query = db.query(DerivTrade).filter(
            DerivTrade.connection_id == connection.id
        )
        
        # Apply status filter
        if status and status != "all":
            query = query.filter(DerivTrade.status == status)
        
        # Get total count
        total_count = query.count()
        
        # Get paginated results
        trades = query.order_by(desc(DerivTrade.purchase_time)).offset(offset).limit(limit).all()
        
        # Calculate statistics
        stats = {
            "total_trades": total_count,
            "total_profit": sum(t.profit for t in trades),
            "win_count": sum(1 for t in trades if t.profit > 0),
            "loss_count": sum(1 for t in trades if t.profit < 0),
            "open_count": sum(1 for t in trades if t.status == "open"),
            "most_traded_symbol": None
        }
        
        # Find most traded symbol
        if trades:
            symbol_counts = {}
            for trade in trades:
                symbol_counts[trade.symbol] = symbol_counts.get(trade.symbol, 0) + 1
            
            if symbol_counts:
                stats["most_traded_symbol"] = max(symbol_counts, key=symbol_counts.get)
        
        return schemas.APIResponse.success_response(
            data={
                "trades": [trade.to_dict() for trade in trades],
                "stats": stats,
                "pagination": {
                    "total": total_count,
                    "limit": limit,
                    "offset": offset,
                    "has_more": (offset + limit) < total_count
                }
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting trades: {str(e)}"
        )

@router.put("/deriv/connections/{connection_id}", response_model=schemas.APIResponse)
async def update_deriv_connection(
    connection_id: str,
    request: UpdateConnectionRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update Deriv connection settings
    """
    try:
        connection = get_deriv_connection(db, connection_id, current_user.id)
        
        # Update provided fields
        update_data = request.dict(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(connection, field):
                setattr(connection, field, value)
        
        connection.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(connection)
        
        return schemas.APIResponse.success_response(
            data=connection.to_dict(),
            message="Connection updated successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error updating connection: {str(e)}"
        )

@router.delete("/deriv/connections/{connection_id}", response_model=schemas.APIResponse)
async def disconnect_deriv_account(
    connection_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Disconnect Deriv account
    """
    try:
        connection = get_deriv_connection(db, connection_id, current_user.id)
        
        # Delete associated trades (optional - might want to keep for history)
        # db.query(DerivTrade).filter(DerivTrade.connection_id == connection_id).delete()
        
        # Delete the connection
        db.delete(connection)
        db.commit()
        
        return schemas.APIResponse.success_response(
            message="Deriv account disconnected successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error disconnecting account: {str(e)}"
        )

@router.post("/deriv/webhook", response_model=schemas.APIResponse)
async def deriv_webhook(
    request: WebhookEventRequest,
    db: Session = Depends(get_db)
):
    """
    Webhook endpoint for Deriv real-time updates
    Note: This should be publicly accessible and have proper authentication
    """
    try:
        # Create webhook event record
        webhook_event = WebhookEvent(
            event_type=request.event,
            event_source="deriv",
            raw_payload=request.dict(),
            signature=request.signature,
            received_at=datetime.utcnow()
        )
        
        db.add(webhook_event)
        db.commit()
        db.refresh(webhook_event)
        
        # Process based on event type
        if request.event == "transaction" and request.transaction:
            # Handle new trade
            transaction = request.transaction
            
            # Find connection by account ID (would need mapping)
            # For now, we'll just log it
            webhook_event.processed = True
            webhook_event.processed_at = datetime.utcnow()
            webhook_event.trade_id = transaction.get("transaction_id")
            
            db.commit()
        
        return schemas.APIResponse.success_response(
            data={
                "event_id": webhook_event.id,
                "received": True,
                "processed": webhook_event.processed
            },
            message="Webhook received"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing webhook: {str(e)}"
        )

@router.get("/deriv/stats", response_model=schemas.APIResponse)
async def get_deriv_statistics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get statistics for Deriv integrations
    """
    try:
        # Get connections
        connections = db.query(DerivConnection).filter(
            DerivConnection.user_id == current_user.id
        ).all()
        
        # Get recent syncs
        recent_syncs = db.query(SyncLog).join(DerivConnection).filter(
            DerivConnection.user_id == current_user.id
        ).order_by(desc(SyncLog.started_at)).limit(10).all()
        
        # Calculate statistics
        total_trades = sum(c.total_trades_synced for c in connections)
        
        # Calculate sync success rate
        successful_syncs = db.query(SyncLog).join(DerivConnection).filter(
            DerivConnection.user_id == current_user.id,
            SyncLog.status == "success"
        ).count()
        
        total_syncs = db.query(SyncLog).join(DerivConnection).filter(
            DerivConnection.user_id == current_user.id
        ).count()
        
        sync_success_rate = (successful_syncs / total_syncs * 100) if total_syncs > 0 else 0
        
        stats = {
            "total_connections": len(connections),
            "active_connections": sum(1 for c in connections if c.connection_status == "connected"),
            "total_trades_synced": total_trades,
            "sync_success_rate": round(sync_success_rate, 1),
            "recent_syncs": [sync.to_dict() for sync in recent_syncs]
        }
        
        return schemas.APIResponse.success_response(data=stats)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting statistics: {str(e)}"
        )