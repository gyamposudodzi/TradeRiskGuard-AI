# core/risk_scorer.py
import json
from typing import Dict, List, Any
import numpy as np

class RiskScorer:
    """Calculate overall risk score based on detected risks"""
    
    def __init__(self):
        # Risk weights (sum to 100)
        self.risk_weights = {
            'over_leverage': 30,      # Position sizing risk
            'no_stop_loss': 25,       # Stop loss discipline
            'high_drawdown': 20,      # Capital preservation
            'revenge_trading': 15,    # Emotional control
            'poor_rr_ratio': 10,      # Risk-reward management
            'low_win_rate': 5,        # Performance
            'concentration_risk': 5,  # Diversification
            'overtrading': 5          # Trading frequency
        }
        
        # Grade boundaries
        self.grade_boundaries = {
            'A': (80, 100),    # Low risk
            'B': (60, 79),     # Moderate risk
            'C': (40, 59),     # High risk
            'D': (0, 39)       # Critical risk
        }
        
        # Grade colors
        self.grade_colors = {
            'A': '#10b981',    # Green
            'B': '#f59e0b',    # Yellow
            'B': '#f59e0b',    # Orange
            'C': '#ef4444',    # Red
            'D': '#dc2626'     # Dark red
        }
    
    def calculate_score(self, risk_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate overall risk score and grade
        
        Args:
            risk_details: Dictionary from RiskRuleEngine.risk_details
            
        Returns:
            Dictionary containing score, grade, and breakdown
        """
        if not risk_details:
            return self._perfect_score()
        
        # Calculate weighted score for each risk
        weighted_scores = []
        score_breakdown = []
        
        total_weight_used = 0
        
        for risk_name, details in risk_details.items():
            if risk_name in self.risk_weights:
                severity = details.get('severity', 0)
                weight = self.risk_weights[risk_name]
                
                # Risk contributes negatively to score
                risk_contribution = (severity / 100) * weight
                weighted_scores.append(risk_contribution)
                
                score_breakdown.append({
                    'risk': risk_name,
                    'severity': severity,
                    'weight': weight,
                    'contribution': round(risk_contribution, 2),
                    'message': details.get('message', '')
                })
                
                total_weight_used += weight
        
        # Calculate base score (100 minus sum of risk contributions)
        total_risk_impact = sum(weighted_scores)
        raw_score = max(0, 100 - total_risk_impact)
        
        # Adjust for unused weights (if some risks weren't detected)
        if total_weight_used < 100:
            unused_weight = 100 - total_weight_used
            raw_score = (raw_score * total_weight_used + 100 * unused_weight) / 100
        
        final_score = round(raw_score, 2)
        
        # Determine grade
        grade = self._get_grade(final_score)
        
        # Calculate improvement potential
        improvement_potential = round(100 - final_score, 2)
        
        # Get top 3 risks to address
        top_risks = sorted(score_breakdown, 
                          key=lambda x: x['contribution'], 
                          reverse=True)[:3]
        
        return {
            'score': final_score,
            'grade': grade,
            'grade_color': self.grade_colors.get(grade, '#6b7280'),
            'improvement_potential': improvement_potential,
            'total_risks': len(risk_details),
            'breakdown': score_breakdown,
            'top_risks': [r['risk'] for r in top_risks],
            'risk_breakdown': self._create_risk_breakdown(score_breakdown),
            'recommendation': self._get_recommendation(grade, top_risks)
        }
    
    def _perfect_score(self) -> Dict[str, Any]:
        """Return perfect score when no risks detected"""
        return {
            'score': 95,  # Not 100 to leave room for improvement
            'grade': 'A',
            'grade_color': self.grade_colors['A'],
            'improvement_potential': 5,
            'total_risks': 0,
            'breakdown': [],
            'top_risks': [],
            'risk_breakdown': {'low': 100, 'medium': 0, 'high': 0},
            'recommendation': "Excellent risk management! Continue with your disciplined approach."
        }
    
    def _get_grade(self, score: float) -> str:
        """Determine grade based on score"""
        for grade, (lower, upper) in self.grade_boundaries.items():
            if lower <= score <= upper:
                return grade
        return 'D'  # Default to D if score is below 0
    
    def _create_risk_breakdown(self, breakdown: List[Dict]) -> Dict[str, float]:
        """Categorize risks by severity level"""
        risk_breakdown = {'low': 0, 'medium': 0, 'high': 0}
        
        for item in breakdown:
            severity = item['severity']
            if severity >= 70:
                risk_breakdown['high'] += 1
            elif severity >= 40:
                risk_breakdown['medium'] += 1
            else:
                risk_breakdown['low'] += 1
        
        return risk_breakdown
    
    def _get_recommendation(self, grade: str, top_risks: List[Dict]) -> str:
        """Generate recommendation based on grade and top risks"""
        recommendations = {
            'A': "Maintain your excellent risk management practices. Consider periodic reviews to stay consistent.",
            'B': "Good risk management overall. Focus on addressing the few areas of concern to improve your score.",
            'C': "Significant improvement needed in risk management. Prioritize addressing the high-risk areas identified.",
            'D': "Urgent attention required. Your current risk management practices expose you to high potential losses."
        }
        
        base_recommendation = recommendations.get(grade, "")
        
        if top_risks:
            risk_names = [r['risk'].replace('_', ' ').title() for r in top_risks]
            focus_areas = ", ".join(risk_names)
            base_recommendation += f" Focus on: {focus_areas}."
        
        return base_recommendation
    
    def generate_scorecard(self, score_data: Dict[str, Any]) -> str:
        """Generate a formatted scorecard"""
        score = score_data['score']
        grade = score_data['grade']
        
        scorecard = f"""
╔══════════════════════════════════════════╗
║           RISK HEALTH SCORECARD          ║
╠══════════════════════════════════════════╣
║  Overall Score: {score:>6.1f}/100              ║
║  Grade:           {grade:>6}                   ║
║  Total Risks:     {score_data['total_risks']:>6}                   ║
║  Improvement:     {score_data['improvement_potential']:>6.1f}%                ║
╠══════════════════════════════════════════╣
║            RISK BREAKDOWN                ║
╠══════════════════════════════════════════╣
"""
        
        # Add risk breakdown
        breakdown = score_data.get('risk_breakdown', {})
        scorecard += f"║  High Risks:       {breakdown.get('high', 0):>6}                   ║\n"
        scorecard += f"║  Medium Risks:     {breakdown.get('medium', 0):>6}                   ║\n"
        scorecard += f"║  Low Risks:        {breakdown.get('low', 0):>6}                   ║\n"
        
        scorecard += "╚══════════════════════════════════════════╝\n"
        
        return scorecard

# Test function
def test_risk_scorer():
    """Test the risk scoring system"""
    
    # Sample risk details (simulating output from RiskRuleEngine)
    sample_risk_details = {
        'over_leverage': {
            'severity': 75.0,
            'avg_position_size_pct': 3.5,
            'message': 'Average position size (3.5%) exceeds recommended limit'
        },
        'no_stop_loss': {
            'severity': 60.0,
            'sl_usage_rate': 65.0,
            'message': '35% of trades executed without stop-loss orders'
        },
        'poor_rr_ratio': {
            'severity': 40.0,
            'current_rr_ratio': 0.8,
            'message': 'Risk-reward ratio (0.8) below recommended minimum'
        }
    }
    
    scorer = RiskScorer()
    score_result = scorer.calculate_score(sample_risk_details)
    
    print("SCORE CALCULATION RESULTS:")
    print("="*50)
    print(f"Overall Score: {score_result['score']}/100")
    print(f"Grade: {score_result['grade']}")
    print(f"Improvement Potential: {score_result['improvement_potential']}%")
    print(f"Total Risks: {score_result['total_risks']}")
    
    print("\nSCORE BREAKDOWN:")
    print("-"*30)
    for item in score_result['breakdown']:
        print(f"{item['risk'].replace('_', ' ').title():20} "
              f"Severity: {item['severity']:5.1f}% "
              f"Weight: {item['weight']:3} "
              f"Impact: -{item['contribution']:5.1f}")
    
    print("\nTOP RISKS TO ADDRESS:")
    print("-"*30)
    for i, risk in enumerate(score_result['top_risks'], 1):
        print(f"{i}. {risk.replace('_', ' ').title()}")
    
    print("\n" + "="*50)
    print("SCORECARD:")
    print("="*50)
    print(scorer.generate_scorecard(score_result))
    
    print("\nRECOMMENDATION:")
    print("-"*30)
    print(score_result['recommendation'])
    
    return score_result

if __name__ == "__main__":
    test_risk_scorer()