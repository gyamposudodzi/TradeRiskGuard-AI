"""
API endpoints for Deriv/MT5 integration (Async Optimized)
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc, and_, or_, func, update, delete
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import asyncio

from api import schemas
from api.database import get_async_db, AsyncSessionLocal
from api.auth import get_current_active_user
from api.models import User, Analysis
from api.models.integration_models import DerivConnection, DerivTrade, SyncLog, WebhookEvent
from api.utils.encryption import encryption_service
from api.utils.deriv_client import DerivAPIClient
from api.schemas.integrations import (
    DerivConnectRequest, ConnectionStatusResponse, SyncResultResponse,
    ConnectionResponse, SyncTradesRequest, UpdateConnectionRequest,
    WebhookEventRequest, WebhookResponse, ConnectionStats
)
from core.metrics_calculator import TradeMetricsCalculator
from core.risk_rules import RiskRuleEngine
from core.risk_scorer import RiskScorer
from core.ai_explainer import AIRiskExplainer
from core.pattern_recognition import PatternDetector
from core.news_service import NewsService

router = APIRouter()

# Helper functions
async def get_deriv_connection(db: AsyncSession, connection_id: str, user_id: str) -> DerivConnection:
    """Get Deriv connection with authorization check"""
    query = select(DerivConnection).where(
        DerivConnection.id == connection_id,
        DerivConnection.user_id == user_id
    )
    result = await db.execute(query)
    connection = result.scalars().first()
    
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    return connection

async def create_sync_log(db: AsyncSession, connection_id: str, sync_type: str, status: str = "started") -> SyncLog:
    """Create a new sync log entry"""
    sync_log = SyncLog(
        connection_id=connection_id,
        sync_type=sync_type,
        status=status
    )
    db.add(sync_log)
    await db.commit()
    await db.refresh(sync_log)
    return sync_log

async def update_sync_log(db: AsyncSession, sync_log_id: str, status: str, stats: Dict[str, Any] = None):
    """Update sync log with results"""
    # We fetch it again to ensure it's attached to the current session if needed, 
    # or simple update. Since this is often called in a different scope, let's just update by ID.
    
    values = {
        "status": status,
        "completed_at": datetime.utcnow()
    }
    
    if stats:
        for key, value in stats.items():
            values[key] = value

    # We need to calculate duration. Complex to do in one update if we need to read start_time.
    # Let's fetch, update, commit.
    query = select(SyncLog).where(SyncLog.id == sync_log_id)
    result = await db.execute(query)
    sync_log = result.scalars().first()
    
    if sync_log:
        sync_log.status = status
        sync_log.completed_at = datetime.utcnow()
        if stats:
             for key, value in stats.items():
                if hasattr(sync_log, key):
                    setattr(sync_log, key, value)
        
        if sync_log.started_at:
            sync_log.duration_seconds = (sync_log.completed_at - sync_log.started_at).total_seconds()
        
        await db.commit()

async def analyze_synced_trades(db: AsyncSession, connection: DerivConnection, sync_log: SyncLog) -> Optional[Dict[str, Any]]:
    """Analyze synced trades and create analysis"""
    try:
        # Get recent trades from this connection
        query = select(DerivTrade).where(
            DerivTrade.connection_id == connection.id
        ).order_by(DerivTrade.purchase_time)
        
        result = await db.execute(query)
        trades = result.scalars().all()
        
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
        
        # Import pandas locally
        import pandas as pd
        df = pd.DataFrame(trades_data)
        
        # Calculate metrics
        calculator = TradeMetricsCalculator(df)
        metrics = calculator.compute_all_metrics()
        
        # Detect risks
        risk_engine = RiskRuleEngine(metrics, df)
        risk_results = risk_engine.detect_all_risks()
        
        # Detect Event Trading Risks (Phase 3)
        try:
            news_service = NewsService()
            event_risks = []
            if 'entry_time' in df.columns:
                # Ensure safe datetime conversion
                times = pd.to_datetime(df['entry_time'], errors='coerce').dropna()
                for t in times:
                    risk = news_service.check_event_trading_risk(t)
                    if risk:
                        event_risks.append(risk)
            
            if event_risks:
                if "risk_details" not in risk_results:
                    risk_results["risk_details"] = {}
                    
                risk_results["risk_details"]["event_trading"] = {
                    "name": "News Event Trading",
                    "severity": 85,
                    "description": f"Detected {len(event_risks)} trades executed during high-impact news events.",
                    "occurrences": len(event_risks)
                }
        except Exception as e:
            print(f"News risk detection failed for sync: {e}")

        # Detect patterns (Phase 2)
        try:
            pattern_detector = PatternDetector(df)
            patterns = pattern_detector.detect_all_patterns()
            risk_results["patterns"] = patterns
        except Exception as e:
            print(f"Pattern detection failed for sync: {e}")
            risk_results["patterns"] = []
        
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
        await db.commit()
        await db.refresh(analysis)
        
        # Link trades to analysis (Bulk Update would be better but simple loop is fine for <1000 items)
        for trade in trades:
            trade.analysis_id = analysis.id
        
        # Link sync log to analysis
        sync_log.analysis_id = analysis.id
        
        await db.commit()
        
        return {
            "analysis_id": analysis.id,
            "score": score_result.get("score"),
            "grade": score_result.get("grade"),
            "trade_count": len(trades)
        }
        
    except Exception as e:
        print(f"Error analyzing synced trades: {e}")
        return None

async def sync_trades_background_task(
    connection_id: str,
    days_back: int,
    force_full_sync: bool,
    analyze_after_sync: bool
):
    """Background task to sync trades (Manages its own session)"""
    
    async with AsyncSessionLocal() as db:
        # Fetch connection again inside this session
        query = select(DerivConnection).where(DerivConnection.id == connection_id)
        result = await db.execute(query)
        connection = result.scalars().first()
        
        if not connection:
            print(f"Connection {connection_id} not found in background task")
            return

        sync_log = await create_sync_log(db, connection.id, "manual" if force_full_sync else "incremental")
        
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
            
            # Test connection first (Async)
            test_result = await client.test_connection() 
            if not test_result.get("success"):
                raise Exception(f"Connection test failed: {test_result.get('error')}")
            
            # Get account info
            account_info = test_result.get("account_info", {})
            connection.account_info = account_info
            connection.connection_status = "connected"
            
            # Get trades from Deriv (Async)
            trades = await client.get_trades(days_back)
            
            # Process trades
            new_trades = 0
            updated_trades = 0
            skipped_trades = 0
            
            for trade_data in trades:
                # Check if trade already exists
                existing_query = select(DerivTrade).where(
                    DerivTrade.deriv_trade_id == trade_data["deriv_trade_id"],
                    DerivTrade.connection_id == connection.id
                )
                existing_result = await db.execute(existing_query)
                existing_trade = existing_result.scalars().first()
                
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
            
            await db.commit()
            
            # Update connection stats
            connection.last_sync_at = datetime.utcnow()
            connection.last_successful_sync = datetime.utcnow()
            connection.last_sync_status = "success"
            connection.total_syncs += 1
            connection.total_trades_synced += new_trades
            connection.error_count = 0
            connection.last_error = None
            
            await db.commit()
            
            # Run analysis if requested and we have new trades
            analysis_id = None
            
            if analyze_after_sync and (new_trades > 0 or updated_trades > 0):
                analysis_result = await analyze_synced_trades(db, connection, sync_log)
                if analysis_result:
                    analysis_id = analysis_result.get("analysis_id")
            
            # Update sync log with success
            await update_sync_log(
                db=db,
                sync_log_id=sync_log.id,
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
            await update_sync_log(
                db=db,
                sync_log_id=sync_log.id,
                status="failed",
                stats={
                    "error_message": str(e)
                }
            )
            
            await db.commit()

# API Endpoints
@router.post("/deriv/connect", response_model=schemas.APIResponse)
async def connect_deriv_account(
    request: DerivConnectRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Connect a Deriv account using API credentials
    """
    if current_user is None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated"
        )
    try:
        # Check if connection already exists for this account
        query = select(DerivConnection).where(
            DerivConnection.user_id == current_user.id,
            DerivConnection.app_id == request.app_id,
            DerivConnection.account_id == request.account_id
        )
        result = await db.execute(query)
        existing = result.scalars().first()
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail="Account already connected"
            )
        
        # Test the connection first (Async)
        client = DerivAPIClient(
            api_token=request.api_token,
            app_id=request.app_id,
            account_id=request.account_id
        )
        
        test_result = await client.test_connection()
        if not test_result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=f"Connection test failed: {test_result.get('error')}"
            )
        
        # Encrypt API token for storage
        encrypted_token = encryption_service.encrypt(request.api_token)
        
        # Prepare account info (merging standard info + mt5 accounts)
        full_account_info = test_result.get("account_info", {})
        if "mt5_accounts" in test_result:
            full_account_info["mt5_accounts"] = test_result["mt5_accounts"]

        # Create connection record
        connection = DerivConnection(
            user_id=current_user.id,
            api_token_encrypted=encrypted_token,
            app_id=request.app_id,
            account_id=request.account_id,
            connection_name=request.connection_name,
            connection_status="connected",
            account_info=full_account_info,
            auto_sync=request.auto_sync,
            sync_frequency=request.sync_frequency,
            sync_days_back=request.sync_days_back,
            connected_at=datetime.utcnow()
        )
        
        db.add(connection)
        await db.commit()
        await db.refresh(connection)
        
        # Start initial sync in background
        if request.auto_sync:
            background_tasks.add_task(
                sync_trades_background_task,
                connection_id=connection.id,
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
    db: AsyncSession = Depends(get_async_db)
):
    """
    Manually sync trades from Deriv account
    """
    if current_user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        if connection_id:
            # Sync specific connection
            connection = await get_deriv_connection(db, connection_id, current_user.id)
            connections = [connection]
        else:
            # Sync all user's connections
            query = select(DerivConnection).where(
                DerivConnection.user_id == current_user.id,
                DerivConnection.connection_status == "connected"
            )
            result = await db.execute(query)
            connections = result.scalars().all()
        
        if not connections:
            raise HTTPException(
                status_code=404,
                detail="No connected Deriv accounts found"
            )
        
        # Start background sync for each connection
        for connection in connections:
            days_back = request.days_back or connection.sync_days_back
            
            background_tasks.add_task(
                sync_trades_background_task,
                connection_id=connection.id,
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
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get status of Deriv connection(s)
    """
    if current_user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        if connection_id:
            connection = await get_deriv_connection(db, connection_id, current_user.id)
            connections = [connection]
        else:
            query = select(DerivConnection).where(DerivConnection.user_id == current_user.id)
            result = await db.execute(query)
            connections = result.scalars().all()
        
        status_data = []
        for connection in connections:
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
                "is_syncing": False, 
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
    db: AsyncSession = Depends(get_async_db)
):
    """
    List all Deriv connections for current user
    """
    if current_user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        query = select(DerivConnection).where(
            DerivConnection.user_id == current_user.id
        ).order_by(desc(DerivConnection.created_at))
        
        result = await db.execute(query)
        connections = result.scalars().all()
        
        print(f"DEBUG: User {current_user.id} has {len(connections)} Deriv connections")

        connections_data = []
        for connection in connections:
            data = connection.to_dict()
            # Decrypt token for owner (requested by user for persistence)
            if connection.api_token_encrypted:
                try:
                    decrypted_token = encryption_service.decrypt(connection.api_token_encrypted)
                    data["api_token"] = decrypted_token
                    print(f"DEBUG: Decrypted token for connection {connection.id}")
                except Exception as e:
                    print(f"Failed to decrypt token for connection {connection.id}: {e}")
            connections_data.append(data)

        return schemas.APIResponse.success_response(
            data={
                "connections": connections_data,
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
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get trades for a specific Deriv connection
    """
    if current_user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        connection = await get_deriv_connection(db, connection_id, current_user.id)
        
        # Build query
        query = select(DerivTrade).where(DerivTrade.connection_id == connection.id)
        
        if status and status != "all":
            query = query.where(DerivTrade.status == status)
        
        # Get count (simplified)
        count_result = await db.execute(query)
        total_count = len(count_result.scalars().all())
        
        # Get paginated
        query = query.order_by(desc(DerivTrade.purchase_time)).offset(offset).limit(limit)
        result = await db.execute(query)
        trades = result.scalars().all()
        
        # Calculate statistics
        stats = {
            "total_trades": total_count,
            "total_profit": sum(t.profit for t in trades), # only for paginated set, typically should be total
            "win_count": sum(1 for t in trades if t.profit > 0),
            "loss_count": sum(1 for t in trades if t.profit < 0),
            "open_count": sum(1 for t in trades if t.status == "open"),
            "most_traded_symbol": None
        }
        
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
    db: AsyncSession = Depends(get_async_db)
):
    """
    Update Deriv connection settings
    """
    if current_user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        connection = await get_deriv_connection(db, connection_id, current_user.id)
        
        update_data = request.dict(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(connection, field):
                setattr(connection, field, value)
        
        connection.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(connection)
        
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
    db: AsyncSession = Depends(get_async_db)
):
    """
    Disconnect Deriv account
    """
    if current_user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        connection = await get_deriv_connection(db, connection_id, current_user.id)
        
        await db.delete(connection)
        await db.commit()
        
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
    db: AsyncSession = Depends(get_async_db)
):
    """
    Webhook endpoint for Deriv real-time updates
    """
    try:
        webhook_event = WebhookEvent(
            event_type=request.event,
            event_source="deriv",
            raw_payload=request.dict(),
            signature=request.signature,
            received_at=datetime.utcnow()
        )
        
        db.add(webhook_event)
        await db.commit()
        await db.refresh(webhook_event)
        
        if request.event == "transaction" and request.transaction:
            # Handle new trade (placeholder)
            webhook_event.processed = True
            webhook_event.processed_at = datetime.utcnow()
            webhook_event.trade_id = request.transaction.get("transaction_id")
            await db.commit()
        
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
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get statistics for Deriv integrations
    """
    if current_user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        query = select(DerivConnection).where(DerivConnection.user_id == current_user.id)
        result = await db.execute(query)
        connections = result.scalars().all()
        
        query_syncs = select(SyncLog).join(DerivConnection).where(
            DerivConnection.user_id == current_user.id
        ).order_by(desc(SyncLog.started_at)).limit(10)
        
        result_syncs = await db.execute(query_syncs)
        recent_syncs = result_syncs.scalars().all()
        
        total_trades = sum(c.total_trades_synced for c in connections)
        
        # Simple stats counting
        # For complex counts in async, we might want raw SQL or count() queries,
        # but for typical user loads, python-side counting on fetched lists is acceptable if lists are small
        # or separate count queries. Here we'll stick to simple connection-based stats.
        
        stats = {
            "total_connections": len(connections),
            "active_connections": sum(1 for c in connections if c.connection_status == "connected"),
            "total_trades_synced": total_trades,
            "recent_syncs": [sync.to_dict() for sync in recent_syncs]
        }
        
        return schemas.APIResponse.success_response(data=stats)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error getting stats: {str(e)}"
        )