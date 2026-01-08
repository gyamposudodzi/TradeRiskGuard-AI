"""
API endpoints for dashboard data
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from typing import Optional
import statistics

from api import schemas, models, auth
from api.database import get_db

router = APIRouter()

@router.get("/summary", response_model=schemas.APIResponse)
async def get_dashboard_summary(
    current_user: schemas.UserResponse = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get dashboard summary data
    """
    # Get user's analyses
    analyses = db.query(models.Analysis)\
        .filter(models.Analysis.user_id == current_user.id)\
        .order_by(desc(models.Analysis.created_at))\
        .all()
    
    if not analyses:
        response_data = schemas.DashboardSummary(
            total_analyses=0,
            average_score=0,
            recent_analyses=[],
            risk_distribution={},
            improvement_trend=[]
        )
        return schemas.APIResponse.success_response(data=response_data)
    
    # Calculate statistics
    total_analyses = len(analyses)
    
    # Average score (only from completed analyses with scores)
    completed_analyses = [a for a in analyses if a.score_result and a.score_result.get("score")]
    if completed_analyses:
        average_score = statistics.mean([a.score_result["score"] for a in completed_analyses])
    else:
        average_score = 0
    
    # Recent analyses (last 5)
    recent_analyses = [
        schemas.AnalysisResponse(
            id=a.id,
            status=a.status,
            metrics=a.metrics,
            risk_results=a.risk_results,
            score_result=a.score_result,
            ai_explanations=a.ai_explanations,
            created_at=a.created_at,
            completed_at=a.completed_at
        )
        for a in analyses[:5]
    ]
    
    # Risk distribution
    risk_distribution = {"low": 0, "medium": 0, "high": 0}
    for a in completed_analyses:
        breakdown = a.score_result.get("risk_breakdown", {})
        for risk_level, count in breakdown.items():
            if risk_level in risk_distribution:
                risk_distribution[risk_level] += count
    
    # Improvement trend (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_analyses_30d = [
        a for a in completed_analyses 
        if a.created_at >= thirty_days_ago
    ]
    
    improvement_trend = []
    if len(recent_analyses_30d) > 1:
        # Group by week
        weekly_scores = {}
        for a in recent_analyses_30d:
            week = a.created_at.isocalendar()[1]  # Week number
            if week not in weekly_scores:
                weekly_scores[week] = []
            weekly_scores[week].append(a.score_result["score"])
        
        for week, scores in sorted(weekly_scores.items()):
            avg_score = statistics.mean(scores)
            improvement_trend.append({
                "week": week,
                "average_score": avg_score,
                "analysis_count": len(scores)
            })
    
    response_data = schemas.DashboardSummary(
        total_analyses=total_analyses,
        average_score=round(average_score, 2),
        recent_analyses=recent_analyses,
        risk_distribution=risk_distribution,
        improvement_trend=improvement_trend
    )
    
    return schemas.APIResponse.success_response(data=response_data)

@router.get("/metrics", response_model=schemas.APIResponse)
async def get_performance_metrics(
    period: str = "month",  # day, week, month, year
    current_user: schemas.UserResponse = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get performance metrics over time
    """
    # Calculate date range
    now = datetime.utcnow()
    if period == "day":
        start_date = now - timedelta(days=1)
    elif period == "week":
        start_date = now - timedelta(days=7)
    elif period == "month":
        start_date = now - timedelta(days=30)
    else:  # year
        start_date = now - timedelta(days=365)
    
    # Get analyses in period
    analyses = db.query(models.Analysis)\
        .filter(
            models.Analysis.user_id == current_user.id,
            models.Analysis.created_at >= start_date,
            models.Analysis.score_result.isnot(None)
        )\
        .order_by(models.Analysis.created_at)\
        .all()
    
    # Format response
    metrics_data = []
    for analysis in analyses:
        if analysis.metrics and analysis.score_result:
            metrics_data.append({
                "date": analysis.created_at.isoformat(),
                "score": analysis.score_result.get("score"),
                "grade": analysis.score_result.get("grade"),
                "win_rate": analysis.metrics.get("win_rate"),
                "profit_factor": analysis.metrics.get("profit_factor"),
                "max_drawdown": analysis.metrics.get("max_drawdown_pct"),
                "risk_count": analysis.score_result.get("total_risks", 0)
            })
    
    # Calculate trends
    trends = {}
    if len(metrics_data) >= 2:
        first = metrics_data[0]
        last = metrics_data[-1]
        
        trends = {
            "score_change": round(last["score"] - first["score"], 2),
            "win_rate_change": round(last.get("win_rate", 0) - first.get("win_rate", 0), 2),
            "risk_count_change": last.get("risk_count", 0) - first.get("risk_count", 0)
        }
    
    response_data = {
        "period": period,
        "analyses_count": len(metrics_data),
        "metrics": metrics_data,
        "trends": trends,
        "summary": {
            "average_score": round(statistics.mean([m["score"] for m in metrics_data]), 2) if metrics_data else 0,
            "best_score": max([m["score"] for m in metrics_data]) if metrics_data else 0,
            "worst_score": min([m["score"] for m in metrics_data]) if metrics_data else 0
        }
    }
    
    return schemas.APIResponse.success_response(data=response_data)

@router.get("/insights", response_model=schemas.APIResponse)
async def get_insights(
    limit: int = 3,
    current_user: schemas.UserResponse = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get personalized insights based on user's trading history
    """
    # Get recent analyses
    analyses = db.query(models.Analysis)\
        .filter(
            models.Analysis.user_id == current_user.id,
            models.Analysis.score_result.isnot(None)
        )\
        .order_by(desc(models.Analysis.created_at))\
        .limit(10)\
        .all()
    
    if not analyses:
        return schemas.APIResponse.success_response(
            data={"insights": []},
            message="No analyses found for insights"
        )
    
    insights = []
    
    # Check for consistent issues
    all_risks = []
    for analysis in analyses:
        if analysis.risk_results and analysis.risk_results.get("detected_risks"):
            all_risks.extend(analysis.risk_results["detected_risks"])
    
    from collections import Counter
    risk_counts = Counter(all_risks)
    
    # Generate insights based on frequent risks
    for risk, count in risk_counts.most_common(limit):
        if count >= len(analyses) / 2:  # Appears in at least half of analyses
            risk_names = {
                "over_leverage": "position sizing",
                "no_stop_loss": "stop-loss usage",
                "revenge_trading": "emotional trading",
                "poor_rr_ratio": "risk-reward management",
                "high_drawdown": "capital preservation"
            }
            
            risk_name = risk_names.get(risk, risk.replace('_', ' '))
            insights.append(
                f"You frequently struggle with {risk_name}. This appears in {count} out of {len(analyses)} recent analyses."
            )
    
    # Check for improvement
    if len(analyses) >= 2:
        scores = [a.score_result["score"] for a in analyses if a.score_result]
        if len(scores) >= 2:
            first_score = scores[0]
            last_score = scores[-1]
            
            if last_score > first_score:
                improvement = last_score - first_score
                insights.append(
                    f"Your risk score has improved by {improvement:.1f} points since your last analysis. Keep it up!"
            )
            elif last_score < first_score:
                decline = first_score - last_score
                insights.append(
                    f"Your risk score has declined by {decline:.1f} points. Consider reviewing recent trading patterns."
                )
    
    # Check for best/worst areas
    if analyses[0].score_result and analyses[0].score_result.get("breakdown"):
        breakdown = analyses[0].score_result["breakdown"]
        if breakdown:
            best_area = min(breakdown, key=lambda x: x.get("contribution", 100))
            worst_area = max(breakdown, key=lambda x: x.get("contribution", 0))
            
            insights.append(
                f"Your strongest area is {best_area.get('risk', '').replace('_', ' ')} "
                f"with only {best_area.get('contribution', 0):.1f} risk contribution."
            )
            insights.append(
                f"Your weakest area is {worst_area.get('risk', '').replace('_', ' ')} "
                f"contributing {worst_area.get('contribution', 0):.1f} to your risk score."
            )
    
    # Limit insights
    insights = insights[:limit]
    
    response_data = {
        "insights": insights,
        "analysis_count": len(analyses),
        "timeframe": "recent analyses"
    }
    
    return schemas.APIResponse.success_response(data=response_data)