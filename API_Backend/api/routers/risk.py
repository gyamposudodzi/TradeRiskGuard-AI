"""
API endpoints for risk assessment
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
import numpy as np

from api import schemas, models, auth
from api.database import get_db
from core.risk_scorer import RiskScorer
from core.ai_explainer import AIRiskExplainer

router = APIRouter()

@router.post("/calculate", response_model=schemas.APIResponse)
async def calculate_risk_score(
    risk_details: dict,
    current_user: Optional[schemas.UserResponse] = Depends(auth.get_optional_user),
    db: Session = Depends(get_db)
):
    """
    Calculate risk score from risk details
    """
    try:
        scorer = RiskScorer()
        score_result = scorer.calculate_score(risk_details)
        
        response_data = {
            "score_result": score_result,
            "scorecard": scorer.generate_scorecard(score_result)
        }
        
        return schemas.APIResponse.success_response(data=response_data)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating risk score: {str(e)}"
        )

@router.post("/explanations", response_model=schemas.APIResponse)
async def get_risk_explanations(
    request: dict,
    current_user: Optional[schemas.UserResponse] = Depends(auth.get_optional_user),
    db: Session = Depends(get_db)
):
    """
    Get AI explanations for specific risks
    """
    try:
        metrics = request.get("metrics", {})
        risk_results = request.get("risk_results", {})
        score_result = request.get("score_result", {})
        
        ai_explainer = AIRiskExplainer()
        explanations = ai_explainer.generate_explanation(
            metrics,
            risk_results,
            score_result
        )
        
        # Format for display if requested
        formatted = None
        if request.get("format_for_display", False):
            formatted = ai_explainer.format_for_display(explanations)
        
        response_data = {
            "explanations": explanations,
            "formatted": formatted,
            "ai_model": explanations.get("ai_model", "unknown")
        }
        
        return schemas.APIResponse.success_response(data=response_data)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating explanations: {str(e)}"
        )

@router.post("/simulate", response_model=schemas.APIResponse)
async def simulate_risk_improvement(
    simulation: schemas.RiskSimulationRequest,
    current_user: Optional[schemas.UserResponse] = Depends(auth.get_optional_user),
    db: Session = Depends(get_db)
):
    """
    Simulate what-if scenarios for risk improvement
    """
    try:
        current_score = simulation.current_score
        improvements = simulation.improvements
        
        # Simple simulation: each percentage improvement adds to score
        # More sophisticated logic can be added here
        improvement_total = sum(improvements.values())
        simulated_score = min(100, current_score + (improvement_total * 0.5))
        
        # Determine new grade
        scorer = RiskScorer()
        simulated_grade = None
        for grade, (lower, upper) in scorer.grade_boundaries.items():
            if lower <= simulated_score <= upper:
                simulated_grade = grade
                break
        
        # Generate recommendations
        recommendations = []
        if simulated_score > current_score:
            improvement = simulated_score - current_score
            recommendations.append(
                f"Implementing these improvements could increase your score by {improvement:.1f} points"
            )
            
            if simulated_grade and simulated_grade != scorer._get_grade(current_score):
                recommendations.append(
                    f"This could improve your grade from {scorer._get_grade(current_score)} to {simulated_grade}"
                )
        
        response_data = schemas.RiskSimulationResponse(
            original_score=current_score,
            simulated_score=simulated_score,
            improvement=simulated_score - current_score,
            new_grade=simulated_grade or scorer._get_grade(current_score),
            recommendations=recommendations
        )
        
        return schemas.APIResponse.success_response(data=response_data)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error running simulation: {str(e)}"
        )

@router.get("/types", response_model=schemas.APIResponse)
async def get_risk_types():
    """
    Get all risk types and their descriptions
    """
    risk_types = {
        "over_leverage": {
            "name": "Over Leverage",
            "description": "Position size too large relative to account balance",
            "threshold": "2% of account per trade",
            "weight": 30
        },
        "no_stop_loss": {
            "name": "No Stop Loss",
            "description": "Trading without stop-loss orders",
            "threshold": "80% minimum usage rate",
            "weight": 25
        },
        "high_drawdown": {
            "name": "High Drawdown",
            "description": "Excessive peak-to-trough decline in account value",
            "threshold": "20% maximum drawdown",
            "weight": 20
        },
        "revenge_trading": {
            "name": "Revenge Trading",
            "description": "Trading shortly after losses, often emotionally driven",
            "threshold": "10% maximum revenge trades",
            "weight": 15
        },
        "poor_rr_ratio": {
            "name": "Poor Risk-Reward Ratio",
            "description": "Unfavorable ratio of potential profit to potential loss",
            "threshold": "1:1 minimum ratio",
            "weight": 10
        }
    }
    
    return schemas.APIResponse.success_response(data=risk_types)