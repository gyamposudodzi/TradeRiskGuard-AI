"""
API endpoints for trade analysis (Async Optimized)
"""
import pandas as pd
import io
import json
import numpy as np
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional
from datetime import datetime

from api import schemas, models, auth
from api.database import get_async_db  # Updated dependency
from core.metrics_calculator import TradeMetricsCalculator
from core.risk_rules import RiskRuleEngine
from core.risk_scorer import RiskScorer
from core.ai_explainer import AIRiskExplainer

router = APIRouter()

# =====================================================
# JSON SAFETY HELPER
# =====================================================

def make_json_safe(obj):
    """
    Recursively convert NumPy / Pandas types to native Python types
    so they can be safely serialized to JSON and stored in DB.
    """
    if isinstance(obj, dict):
        return {k: make_json_safe(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_safe(v) for v in obj]
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    else:
        return obj


from core.pattern_recognition import PatternDetector
from core.news_service import NewsService

# =====================================================
# CORE PROCESSING (CPU-BOUND)
# =====================================================

def process_trade_data(df: pd.DataFrame, openai_api_key: Optional[str] = None):
    """Process trade data and return analysis results (CPU Bound)"""

    # Calculate metrics
    calculator = TradeMetricsCalculator(df)
    metrics = calculator.compute_all_metrics()

    # Detect risks (Rules)
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
                # t might be Timestamp, convert to python datetime if needed, or use as is (NewsService handles properties)
                # Pandas Timestamp has .hour, .minute
                risk = news_service.check_event_trading_risk(t)
                if risk:
                    event_risks.append(risk)
        
        if event_risks:
            # Add to risk_details
            if "risk_details" not in risk_results:
                risk_results["risk_details"] = {}
                
            risk_results["risk_details"]["event_trading"] = {
                "name": "News Event Trading",
                "severity": 85,
                "description": f"Detected {len(event_risks)} trades executed during high-impact news events (e.g. FOMC, NFP).",
                "occurrences": len(event_risks)
            }
            # Also append to the main list if structure differs, but risk_details is consistent
            
    except Exception as e:
        print(f"News risk detection failed: {e}")
            
    # Detect patterns (ML + Heuristics)
    try:
        pattern_detector = PatternDetector(df)
        patterns = pattern_detector.detect_all_patterns()
        # Merge patterns into risk_results so they are persisted in the same JSON column
        risk_results["patterns"] = patterns
    except Exception as e:
        print(f"Pattern detection failed: {e}")
        risk_results["patterns"] = []

    # Calculate score
    scorer = RiskScorer()
    score_result = scorer.calculate_score(risk_results["risk_details"])

    # Generate AI explanations using User's Key if provided
    ai_explainer = AIRiskExplainer(openai_api_key=openai_api_key)
    ai_explanations = ai_explainer.generate_explanation(
        metrics,
        risk_results,
        score_result
    )

    return {
        "metrics": metrics,
        "risk_results": risk_results,
        "score_result": score_result,
        "ai_explanations": ai_explanations
    }


async def save_analysis_to_db(
    db: AsyncSession,
    user: Optional[models.User],
    filename: str,
    original_filename: str,
    file_size: int,
    trade_count: int,
    results: dict
):
    """Save analysis results to database (Async)"""

    safe_results = make_json_safe(results)

    analysis = models.Analysis(
        user_id=user.id if user else None,
        filename=filename,
        original_filename=original_filename,
        file_size=file_size,
        trade_count=trade_count,
        metrics=safe_results.get("metrics"),
        risk_results=safe_results.get("risk_results"),
        score_result=safe_results.get("score_result"),
        ai_explanations=safe_results.get("ai_explanations"),
        status="completed",
        completed_at=datetime.utcnow()
    )

    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)
    return analysis


# =====================================================
# ANALYZE CSV OR SAMPLE
# =====================================================

from api.utils.mt5_parser import parse_mt5_html

@router.post("/trades", response_model=schemas.APIResponse)
async def analyze_trades(
    file: Optional[UploadFile] = File(None),
    use_sample: bool = False,
    background_tasks: BackgroundTasks = None,
    current_user: Optional[schemas.UserResponse] = Depends(auth.get_optional_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Analyze trading data from uploaded CSV or MT5 HTML Report
    """
    try:
        if use_sample:
            sample_data = {
                "trade_id": [1, 2, 3, 4],
                "profit_loss": [50, -30, 75, -20],
                "lot_size": [0.1, 0.2, 0.15, 0.1],
                "account_balance_before": [10000, 10050, 10020, 10095],
                "stop_loss": [1.1, 1.2, 1.15, 1.3],
                "entry_time": ["2024-01-01 10:00:00", "2024-01-01 11:00:00", "2024-01-01 12:00:00", "2024-01-01 12:15:00"],
                "exit_time": ["2024-01-01 11:00:00", "2024-01-01 11:30:00", "2024-01-01 13:00:00", "2024-01-01 12:45:00"]
            }
            df = pd.DataFrame(sample_data)
            filename = "sample_data.csv"
            original_filename = "sample_data.csv"
            file_size = 1024
            trade_count = len(df)

        else:
            if not file:
                raise HTTPException(status_code=400, detail="No file uploaded")

            filename = file.filename.lower()
            if not (filename.endswith(".csv") or filename.endswith(".html") or filename.endswith(".htm")):
                raise HTTPException(status_code=400, detail="Only CSV and MT5 HTML files are supported")

            # Async read
            contents = await file.read()
            
            # Determine processing method
            if filename.endswith(".csv"):
                # Offload CSV parsing to threadpool
                def parse_csv(content_bytes):
                    return pd.read_csv(io.StringIO(content_bytes.decode("utf-8")))
                
                df = await run_in_threadpool(parse_csv, contents)
            else:
                # MT5 HTML Parsing
                def parse_html_wrapper(content_bytes):
                    return parse_mt5_html(content_bytes)
                
                df = await run_in_threadpool(parse_html_wrapper, contents)
            
            filename = file.filename
            original_filename = file.filename
            file_size = len(contents)
            trade_count = len(df)

        # Prepare OpenAI key if available
        openai_api_key = None
        if current_user:
            # We need to fetch the full user settings + decrypted key
            # Since current_user is from a token dependency, it might not have the settings relation loaded or refreshed
            # Let's fetch settings explicitly
            query = select(models.UserSettings).where(models.UserSettings.user_id == current_user.id)
            settings_res = await db.execute(query)
            user_settings = settings_res.scalars().first()
            
            if user_settings and user_settings.openai_api_key_encrypted:
                try:
                    from api.utils.encryption import encryption_service
                    openai_api_key = encryption_service.decrypt(user_settings.openai_api_key_encrypted)
                except Exception as e:
                    print(f"Failed to decrypt user OpenAI key: {e}")

        # Offload heavy calculation to threadpool
        results = await run_in_threadpool(process_trade_data, df, openai_api_key)

        # Async save
        analysis = await save_analysis_to_db(
            db=db,
            user=current_user,
            filename=filename,
            original_filename=original_filename,
            file_size=file_size,
            trade_count=trade_count,
            results=results
        )

        response_data = make_json_safe({
            "analysis_id": analysis.id,
            **results
        })

        return schemas.APIResponse.success_response(
            data=response_data,
            message="Analysis completed successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing analysis: {str(e)}"
        )


# =====================================================
# GET SINGLE ANALYSIS
# =====================================================

@router.get("/{analysis_id}", response_model=schemas.APIResponse)
async def get_analysis(
    analysis_id: str,
    current_user: Optional[schemas.UserResponse] = Depends(auth.get_optional_user),
    db: AsyncSession = Depends(get_async_db)
):
    query = select(models.Analysis).where(models.Analysis.id == analysis_id)
    result = await db.execute(query)
    analysis = result.scalars().first()

    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    if current_user and analysis.user_id and analysis.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    response_data = make_json_safe({
        "id": analysis.id,
        "status": analysis.status,
        "metrics": analysis.metrics,
        "risk_results": analysis.risk_results,
        "score_result": analysis.score_result,
        "ai_explanations": analysis.ai_explanations,
        "created_at": analysis.created_at,
        "completed_at": analysis.completed_at,
        "filename": analysis.original_filename,
        "trade_count": analysis.trade_count
    })

    return schemas.APIResponse.success_response(data=response_data)


# =====================================================
# LIST ANALYSES
# =====================================================

@router.get("/", response_model=schemas.APIResponse)
async def list_analyses(
    skip: int = 0,
    limit: int = 20,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    min_score: Optional[float] = None,
    current_user: Optional[schemas.UserResponse] = Depends(auth.get_optional_user),
    db: AsyncSession = Depends(get_async_db)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Async Query with Filters
    query = select(models.Analysis).where(models.Analysis.user_id == current_user.id)

    if start_date:
        query = query.where(models.Analysis.created_at >= start_date)
    if end_date:
        query = query.where(models.Analysis.created_at <= end_date)
    # Check score within JSON column requires casting or simple python filtering.
    # SQL filtering on JSON is dialect specific (Postgres vs SQLite).
    # For SQLite, we might fetch and filter in Python if volume is low, or use specific JSON operators.
    # Given we are using SQLite + aiosqlite, let's filter in python for complex JSON fields if needed,
    # BUT `score_result` is JSON. Extraction is messy in generic SQLAlchemy.
    # Recommendation: Add a `score` float column to Analysis model for simpler indexing/querying.
    # For now, we will FILTER IN PYTHON for min_score or ignore it if efficient paging is needed.
    
    query = query.order_by(models.Analysis.created_at.desc())
    
    # Execution
    result = await db.execute(query)
    all_analyses = result.scalars().all()  # Fetch all for python filtering (warn: scaling issue)

    # In-memory filtering for JSON field score
    filtered_analyses = []
    for a in all_analyses:
        if min_score is not None:
             score = a.score_result.get("score", 0) if a.score_result else 0
             if score < min_score:
                 continue
        filtered_analyses.append(a)

    total = len(filtered_analyses)
    
    # Pagination in Python (post-filter)
    paginated = filtered_analyses[skip : skip + limit]

    response_data = make_json_safe({
        "analyses": [
            {
                "id": a.id,
                "filename": a.original_filename,
                "trade_count": a.trade_count,
                "score": a.score_result.get("score") if a.score_result else None,
                "grade": a.score_result.get("grade") if a.score_result else None,
                "created_at": a.created_at,
                "status": a.status
            }
            for a in paginated
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    })

    return schemas.APIResponse.success_response(data=response_data)


@router.get("/history/trends", response_model=schemas.APIResponse)
async def get_analysis_trends(
    days: int = 30,
    current_user: Optional[schemas.UserResponse] = Depends(auth.get_optional_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get aggregated trends of risk scores over time
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    query = select(models.Analysis).where(
        models.Analysis.user_id == current_user.id,
        models.Analysis.created_at >= cutoff_date,
        models.Analysis.status == "completed"
    ).order_by(models.Analysis.created_at.asc())
    
    result = await db.execute(query)
    analyses = result.scalars().all()
    
    # Aggregate data
    trend_data = []
    
    for a in analyses:
        if not a.score_result:
            continue
            
        trend_data.append({
            "date": a.created_at.isoformat(),
            "score": a.score_result.get("score"),
            "trade_count": a.trade_count,
            "win_rate": a.metrics.get("win_rate") if a.metrics else 0
        })
    
    return schemas.APIResponse.success_response(
        data={
            "trends": trend_data,
            "period_days": days,
            "analysis_count": len(trend_data)
        }
    )


# =====================================================
# QUICK ANALYSIS (JSON INPUT)
# =====================================================

@router.post("/quick", response_model=schemas.APIResponse)
async def quick_analyze(
    request: dict,
    current_user: Optional[schemas.UserResponse] = Depends(auth.get_optional_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Quick analysis from JSON data
    """
    try:
        df = pd.DataFrame(request.get("trades", []))

        if df.empty:
            raise HTTPException(status_code=400, detail="No trade data provided")

        # Offload calculation
        results = await run_in_threadpool(process_trade_data, df)

        # Async save
        analysis = await save_analysis_to_db(
            db=db,
            user=current_user,
            filename="quick_analysis.json",
            original_filename="quick_analysis.json",
            file_size=len(json.dumps(make_json_safe(request))),
            trade_count=len(df),
            results=results
        )

        response_data = make_json_safe({
            "analysis_id": analysis.id,
            **results
        })

        return schemas.APIResponse.success_response(
            data=response_data,
            message="Quick analysis completed successfully"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error in quick analysis: {str(e)}"
        )
