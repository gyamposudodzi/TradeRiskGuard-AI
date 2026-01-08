"""
API endpoints for trade analysis
"""
import pandas as pd
import io
import json
import numpy as np
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from api import schemas, models, auth
from api.database import get_db
from core.metrics_calculator import TradeMetricsCalculator
from core.risk_rules import RiskRuleEngine
from core.risk_scorer import RiskScorer
from core.ai_explainer import AIRiskExplainer

router = APIRouter()

# =====================================================
# JSON SAFETY HELPER (FIX)
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


# =====================================================
# CORE PROCESSING
# =====================================================

def process_trade_data(df: pd.DataFrame):
    """Process trade data and return analysis results"""

    # Calculate metrics
    calculator = TradeMetricsCalculator(df)
    metrics = calculator.compute_all_metrics()

    # Detect risks
    risk_engine = RiskRuleEngine(metrics, df)
    risk_results = risk_engine.detect_all_risks()

    # Calculate score
    scorer = RiskScorer()
    score_result = scorer.calculate_score(risk_results["risk_details"])

    # Generate AI explanations
    ai_explainer = AIRiskExplainer()
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


def save_analysis_to_db(
    db: Session,
    user: Optional[models.User],
    filename: str,
    original_filename: str,
    file_size: int,
    trade_count: int,
    results: dict
):
    """Save analysis results to database"""

    # 🔑 CRITICAL FIX
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
    db.commit()
    db.refresh(analysis)
    return analysis


# =====================================================
# ANALYZE CSV OR SAMPLE
# =====================================================

@router.post("/trades", response_model=schemas.APIResponse)
async def analyze_trades(
    file: Optional[UploadFile] = File(None),
    use_sample: bool = False,
    background_tasks: BackgroundTasks = None,
    current_user: Optional[schemas.UserResponse] = Depends(auth.get_optional_user),
    db: Session = Depends(get_db)
):
    """
    Analyze trading data from uploaded CSV file or use sample data
    """
    try:
        if use_sample:
            sample_data = {
                "trade_id": [1, 2, 3, 4],
                "profit_loss": [50, -30, 75, -20],
                "lot_size": [0.1, 0.2, 0.15, 0.1],
                "account_balance_before": [10000, 10050, 10020, 10095],
                "stop_loss": [1.1, 1.2, 1.15, 1.3],
                "entry_time": [
                    "2024-01-01 10:00:00",
                    "2024-01-01 11:00:00",
                    "2024-01-01 12:00:00",
                    "2024-01-01 12:15:00"
                ],
                "exit_time": [
                    "2024-01-01 11:00:00",
                    "2024-01-01 11:30:00",
                    "2024-01-01 13:00:00",
                    "2024-01-01 12:45:00"
                ]
            }
            df = pd.DataFrame(sample_data)
            filename = "sample_data.csv"
            original_filename = "sample_data.csv"
            file_size = 1024
            trade_count = len(df)

        else:
            if not file:
                raise HTTPException(
                    status_code=400,
                    detail="No file uploaded. Either upload a file or set use_sample=true"
                )

            if not file.filename.endswith(".csv"):
                raise HTTPException(
                    status_code=400,
                    detail="Only CSV files are supported"
                )

            contents = await file.read()
            df = pd.read_csv(io.StringIO(contents.decode("utf-8")))

            filename = file.filename
            original_filename = file.filename
            file_size = len(contents)
            trade_count = len(df)

        results = process_trade_data(df)

        analysis = save_analysis_to_db(
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
    db: Session = Depends(get_db)
):
    analysis = db.query(models.Analysis).filter(models.Analysis.id == analysis_id).first()

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
    current_user: Optional[schemas.UserResponse] = Depends(auth.get_optional_user),
    db: Session = Depends(get_db)
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    analyses = (
        db.query(models.Analysis)
        .filter(models.Analysis.user_id == current_user.id)
        .order_by(models.Analysis.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    total = (
        db.query(models.Analysis)
        .filter(models.Analysis.user_id == current_user.id)
        .count()
    )

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
            for a in analyses
        ],
        "total": total,
        "skip": skip,
        "limit": limit
    })

    return schemas.APIResponse.success_response(data=response_data)


# =====================================================
# QUICK ANALYSIS (JSON INPUT)
# =====================================================

@router.post("/quick", response_model=schemas.APIResponse)
async def quick_analyze(
    request: dict,
    current_user: Optional[schemas.UserResponse] = Depends(auth.get_optional_user),
    db: Session = Depends(get_db)
):
    """
    Quick analysis from JSON data
    """
    try:
        df = pd.DataFrame(request.get("trades", []))

        if df.empty:
            raise HTTPException(
                status_code=400,
                detail="No trade data provided"
            )

        results = process_trade_data(df)

        analysis = save_analysis_to_db(
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
