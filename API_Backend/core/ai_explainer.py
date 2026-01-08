# core/ai_explainer.py
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate
)
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

# Local imports
from core.risk_rules import RiskRuleEngine
from core.risk_scorer import RiskScorer


@dataclass
class RiskExplanation:
    risk_name: str
    severity: str
    explanation: str
    educational_context: str
    non_advice_suggestions: List[str]
    trader_psychology_insight: Optional[str] = None


class AIRiskAIOutput(BaseModel):
    risk_summary: str
    key_strengths: List[str]
    key_risks: List[str]
    educational_insights: str
    improvement_focus: str
    deriv_context: str


class AIRiskExplainer:
    """AI-powered explanation engine for trading risks"""

    def __init__(self, openai_api_key: Optional[str] = None):
        self.api_key = openai_api_key or os.getenv("OPENAI_API_KEY")

        if not self.api_key:
            self.mock_mode = True
            print("⚠️ OpenAI API key not found. Running in demo mode.")
        else:
            self.mock_mode = False
            os.environ["OPENAI_API_KEY"] = self.api_key
            self.llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.3,
                max_tokens=1000
            )

        self.output_parser = PydanticOutputParser(
            pydantic_object=AIRiskAIOutput
        )
        self.format_instructions = self.output_parser.get_format_instructions()

        self.system_prompt = SystemMessagePromptTemplate.from_template("""
        You are a risk education assistant for retail traders.
        Explain risks clearly and educationally.
        Never give trading advice, predictions, or signals.
        """)

        self.human_prompt_template = HumanMessagePromptTemplate.from_template("""
        ### Trading Metrics:
        {metrics_summary}

        ### Detected Risks:
        {risk_summary}

        ### Risk Score:
        Score: {risk_score}/100
        Grade: {risk_grade}
        Total Risks: {total_risks}

        {format_instructions}
        """)

    def generate_explanation(
        self,
        metrics: Dict[str, Any],
        risk_results: Dict[str, Any],
        score_result: Dict[str, Any]
    ) -> Dict[str, Any]:

        if self.mock_mode:
            return self._generate_mock_explanation(metrics, risk_results, score_result)

        prompt = ChatPromptTemplate.from_messages([
            self.system_prompt,
            self.human_prompt_template
        ])

        messages = prompt.format_prompt(
            metrics_summary=self._format_metrics_for_ai(metrics),
            risk_summary=self._format_risks_for_ai(risk_results),
            risk_score=score_result["score"],
            risk_grade=score_result["grade"],
            total_risks=score_result["total_risks"],
            format_instructions=self.format_instructions
        ).to_messages()

        response = self.llm.invoke(messages)

        parsed = self.output_parser.parse(response.content)
        parsed = parsed.model_dump()

        parsed["ai_model"] = "gpt-4o-mini"
        parsed["timestamp"] = self._get_timestamp()

        return parsed

    # --- helper methods unchanged ---

    
    def _generate_risk_specific_explanations(self, 
                                           risk_results: Dict[str, Any],
                                           metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate detailed explanations for each detected risk"""
        explanations = []
        
        for risk_name, details in risk_results.get('risk_details', {}).items():
            explanation = self._explain_single_risk(risk_name, details, metrics)
            explanations.append(explanation)
        
        return explanations
    
    def _explain_single_risk(self, 
                            risk_name: str, 
                            details: Dict[str, Any],
                            metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Generate explanation for a single risk"""
        
        # Risk templates for different risk types
        risk_templates = {
            'over_leverage': {
                'title': 'Position Sizing & Leverage',
                'concept': 'Risk per trade relative to account size',
                'why_matters': 'Large positions increase potential losses and margin call risk',
                'principle': 'The 1-2% rule: Risk only 1-2% of account per trade',
                'analogy': 'Like driving a car - higher speed (leverage) means faster results but harder to control'
            },
            'no_stop_loss': {
                'title': 'Stop-Loss Usage',
                'concept': 'Pre-defined exit points for losing trades',
                'why_matters': 'Without stop-loss, losses can accumulate without limit',
                'principle': 'Always have an exit plan before entering a trade',
                'analogy': 'Like wearing a seatbelt - you hope not to need it, but it prevents catastrophic outcomes'
            },
            'revenge_trading': {
                'title': 'Emotional Trading Patterns',
                'concept': 'Trading decisions driven by emotions rather than strategy',
                'why_matters': 'Emotional decisions often lead to impulsive, poorly-planned trades',
                'principle': 'Stick to your trading plan regardless of recent outcomes',
                'analogy': 'Like gambling - chasing losses rarely ends well'
            },
            'poor_rr_ratio': {
                'title': 'Risk-Reward Management',
                'concept': 'Ratio of potential profit to potential loss',
                'why_matters': 'Unfavorable ratios require higher win rates to be profitable',
                'principle': 'Aim for at least 1:1.5 risk:reward ratio',
                'analogy': 'Like a business - would you risk $100 to make $50?'
            },
            'high_drawdown': {
                'title': 'Capital Preservation',
                'concept': 'Maximum peak-to-trough decline in account value',
                'why_matters': 'Large drawdowns require even larger gains to recover',
                'principle': 'Protect your capital to stay in the game',
                'analogy': 'Like a ship taking on water - easier to bail early than when half-sunk'
            }
        }
        
        # Get template for this risk
        template = risk_templates.get(risk_name, {
            'title': risk_name.replace('_', ' ').title(),
            'concept': 'Risk management principle',
            'why_matters': 'Important for long-term trading success',
            'principle': 'General trading best practice',
            'analogy': 'Common trading concept'
        })
        
        # Generate non-advisory suggestions
        suggestions = self._generate_suggestions(risk_name, details)
        
        # Determine severity level
        severity_score = details.get('severity', 0)
        if severity_score >= 70:
            severity = 'high'
        elif severity_score >= 40:
            severity = 'medium'
        else:
            severity = 'low'
        
        return {
            'risk_name': risk_name,
            'display_name': template['title'],
            'severity': severity,
            'severity_score': severity_score,
            'concept': template['concept'],
            'why_matters': template['why_matters'],
            'principle': template['principle'],
            'analogy': template['analogy'],
            'non_advice_suggestions': suggestions,
            'specific_observation': details.get('message', ''),
            'psychology_insight': self._get_psychology_insight(risk_name)
        }
    
    def _generate_suggestions(self, risk_name: str, details: Dict[str, Any]) -> List[str]:
        """Generate non-advisory suggestions for risk improvement"""
        
        suggestion_templates = {
            'over_leverage': [
                "Consider reviewing position sizing relative to account balance",
                "Some traders use the 1-2% rule as a guideline for risk per trade",
                "Trading platforms often have risk calculators that can help with position sizing"
            ],
            'no_stop_loss': [
                "Setting stop-loss orders is a common risk management practice",
                "Many traders include stop-loss placement in their trading plan",
                "Consider where you would exit if the trade moves against you"
            ],
            'revenge_trading': [
                "Some traders take breaks after losses to avoid emotional decisions",
                "Having a trading journal can help identify emotional patterns",
                "Sticking to a pre-defined trading plan can reduce emotional trading"
            ],
            'poor_rr_ratio': [
                "Evaluating risk-reward before entering trades is a common practice",
                "Many successful traders aim for favorable risk-reward ratios",
                "Consider whether potential reward justifies potential risk"
            ],
            'high_drawdown': [
                "Monitoring account drawdown is a key risk management activity",
                "Some traders set maximum drawdown limits for themselves",
                "Capital preservation is often emphasized in trading education"
            ],
            'low_win_rate': [
                "Reviewing trade outcomes can provide insights for improvement",
                "Many traders focus on consistency rather than just win rate",
                "Consider whether losses are part of your trading strategy"
            ],
            'concentration_risk': [
                "Diversification is a common principle in financial markets",
                "Some traders spread risk across different instruments",
                "Consider whether overexposure to one asset aligns with your risk tolerance"
            ]
        }
        
        return suggestion_templates.get(risk_name, [
            "Review this aspect of your trading approach",
            "Consider general risk management principles in this area",
            "Many trading educational resources cover this topic"
        ])
    
    def _get_psychology_insight(self, risk_name: str) -> str:
        """Provide psychological insight for the risk"""
        insights = {
            'over_leverage': "The desire for larger profits can lead to excessive risk-taking. Patience with smaller, consistent gains often leads to better long-term results.",
            'no_stop_loss': "Hope can be a dangerous emotion in trading. Accepting small losses is psychologically difficult but necessary for survival.",
            'revenge_trading': "Losses trigger emotional responses. The best traders acknowledge emotions but don't let them dictate actions.",
            'poor_rr_ratio': "Focusing on being 'right' rather than profitable. Good traders care more about risk management than being right on direction.",
            'high_drawdown': "The sunk cost fallacy - holding losing positions hoping they'll recover. Sometimes cutting losses is the smartest move."
        }
        return insights.get(risk_name, "Trading psychology plays a role in many risk management decisions.")
    
    def _format_metrics_for_ai(self, metrics: Dict[str, Any]) -> str:
        """Format metrics for AI consumption"""
        important_metrics = {
            'total_trades': metrics.get('total_trades', 0),
            'win_rate': metrics.get('win_rate', 0),
            'profit_factor': metrics.get('profit_factor', 0),
            'net_profit': metrics.get('net_profit', 0),
            'avg_position_size_pct': metrics.get('avg_position_size_pct', 0),
            'max_drawdown_pct': metrics.get('max_drawdown_pct', 0),
            'risk_reward_ratio': metrics.get('risk_reward_ratio', 0),
            'sl_usage_rate': metrics.get('sl_usage_rate', 0),
            'revenge_trading_pct': metrics.get('revenge_trading_pct', 0)
        }
        
        formatted = []
        for key, value in important_metrics.items():
            if isinstance(value, float):
                formatted.append(f"- {key}: {value:.2f}")
            else:
                formatted.append(f"- {key}: {value}")
        
        return "\n".join(formatted)
    
    def _format_risks_for_ai(self, risk_results: Dict[str, Any]) -> str:
        """Format risks for AI consumption"""
        if not risk_results.get('detected_risks'):
            return "No significant risks detected"
        
        formatted = []
        for risk in risk_results['detected_risks']:
            details = risk_results['risk_details'].get(risk, {})
            severity = details.get('severity', 0)
            message = details.get('message', '')
            formatted.append(f"- {risk} (Severity: {severity}%): {message}")
        
        return "\n".join(formatted)
    
    def _parse_fallback_response(self, response: str) -> Dict[str, Any]:
        """Fallback parser if structured parsing fails"""
        # Simple parsing logic
        return {
            'risk_summary': "AI analysis generated successfully.",
            'key_strengths': ["Analysis completed"],
            'key_risks': ["See detailed risk explanations"],
            'educational_insights': "Review the risk-specific explanations below",
            'improvement_focus': "Focus on the highest severity risks first",
            'deriv_context': "Responsible trading involves understanding your risk profile"
        }
    
    def _generate_mock_explanation(self, 
                                 metrics: Dict[str, Any], 
                                 risk_results: Dict[str, Any],
                                 score_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate mock explanations when API key is not available"""
        
        # Generate risk-specific explanations even in mock mode
        risk_explanations = []
        for risk_name, details in risk_results.get('risk_details', {}).items():
            risk_explanations.append(self._explain_single_risk(risk_name, details, metrics))
        
        grade = score_result.get('grade', 'B')
        
        mock_responses = {
            'A': {
                'risk_summary': "Your trading shows excellent risk management discipline with consistent application of sound principles.",
                'key_strengths': ["Strong position sizing control", "Consistent stop-loss usage", "Emotional discipline in trading"],
                'key_risks': ["Minor areas for refinement"],
                'educational_insights': "Even experienced traders periodically review their risk management approaches to maintain consistency.",
                'improvement_focus': "Consider whether your current approach scales effectively as your account grows.",
                'deriv_context': "Deriv provides tools that can help maintain disciplined trading practices."
            },
            'B': {
                'risk_summary': "Good overall risk management with some areas that could be strengthened for better consistency.",
                'key_strengths': ["Reasonable win rate", "Generally good trade timing"],
                'key_risks': ["Position sizing could be more conservative", "Stop-loss discipline needs improvement"],
                'educational_insights': "Small improvements in risk management often have disproportionate benefits to long-term results.",
                'improvement_focus': "Focus on the highest impact risks first, such as position sizing and stop-loss discipline.",
                'deriv_context': "Using Deriv's risk management tools consistently can help improve trading discipline."
            },
            'C': {
                'risk_summary': "Several risk management areas need attention to improve trading consistency and protect capital.",
                'key_strengths': ["Active trading engagement", "Market participation"],
                'key_risks': ["Over-leverage detected", "Inconsistent stop-loss usage", "Unfavorable risk-reward ratios"],
                'educational_insights': "Risk management is not about avoiding losses but about controlling them to survive and profit long-term.",
                'improvement_focus': "Prioritize position sizing and stop-loss discipline as these have the biggest impact on risk reduction.",
                'deriv_context': "Deriv emphasizes responsible trading practices that focus on risk awareness and management."
            },
            'D': {
                'risk_summary': "Significant risk management improvements are needed to protect your trading capital and improve consistency.",
                'key_strengths': ["Trading activity and engagement"],
                'key_risks': ["Excessive position sizes", "Frequent trading without stop-loss", "Emotional trading patterns"],
                'educational_insights': "The first rule of trading is to preserve capital. Without this, long-term success is difficult.",
                'improvement_focus': "Immediate focus on reducing position sizes and implementing consistent stop-loss usage.",
                'deriv_context': "Deriv offers educational resources that can help traders understand and manage their risks better."
            }
        }
        
        response = mock_responses.get(grade, mock_responses['B'])
        
        return {
            **response,
            'risk_explanations': risk_explanations,
            'full_response': "Mock explanation generated - add OpenAI API key for AI-powered insights",
            'ai_model': 'demo_mode',
            'timestamp': self._get_timestamp()
        }
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def format_for_display(self, explanation: Dict[str, Any]) -> str:
        """Format explanation for display in UI"""
        
        output = f"""
# 🤖 AI Risk Analysis

**Overall Assessment:** {explanation.get('risk_summary', '')}

## 📈 Key Strengths
"""
        
        for strength in explanation.get('key_strengths', []):
            output += f"- {strength}\n"
        
        output += f"""
## 🚨 Key Risks to Understand
"""
        
        for risk in explanation.get('key_risks', []):
            output += f"- {risk}\n"
        
        output += f"""
## 🎓 Educational Insights
{explanation.get('educational_insights', '')}

## 🎯 Improvement Focus (Non-Advisory)
{explanation.get('improvement_focus', '')}

## 🔗 Platform Context
{explanation.get('deriv_context', '')}

---
*Analysis generated: {explanation.get('timestamp', '')} | Model: {explanation.get('ai_model', 'N/A')}*
"""
        
        return output

# Test function
def test_ai_explainer():
    """Test the AI explainer functionality"""
    print("🧠 Testing AI Explanation Engine")
    print("="*60)
    
    # Create sample data
    sample_metrics = {
        'total_trades': 45,
        'win_rate': 42.2,
        'profit_factor': 1.35,
        'net_profit': 1250.50,
        'avg_position_size_pct': 3.2,
        'max_drawdown_pct': 22.5,
        'risk_reward_ratio': 0.85,
        'sl_usage_rate': 68.0,
        'revenge_trading_pct': 18.5
    }
    
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
        }
    }
    
    sample_risk_results = {
        'detected_risks': ['over_leverage', 'no_stop_loss'],
        'risk_details': sample_risk_details,
        'total_risks': 2
    }
    
    sample_score_result = {
        'score': 65.5,
        'grade': 'C',
        'total_risks': 2,
        'improvement_potential': 34.5
    }
    
    # Initialize explainer (will use mock mode if no API key)
    explainer = AIRiskExplainer()
    
    print("Generating AI explanations...")
    explanations = explainer.generate_explanation(
        sample_metrics, 
        sample_risk_results, 
        sample_score_result
    )
    
    print("\n" + "="*60)
    print("AI EXPLANATION RESULTS:")
    print("="*60)
    
    print(f"\n📊 Overall Summary:")
    print(f"{explanations.get('risk_summary', '')}")
    
    print(f"\n✅ Key Strengths:")
    for strength in explanations.get('key_strengths', []):
        print(f"  • {strength}")
    
    print(f"\n⚠️ Key Risks:")
    for risk in explanations.get('key_risks', []):
        print(f"  • {risk}")
    
    print(f"\n🎓 Educational Insights:")
    print(f"{explanations.get('educational_insights', '')}")
    
    print(f"\n🎯 Improvement Focus:")
    print(f"{explanations.get('improvement_focus', '')}")
    
    print(f"\n🔗 Deriv Context:")
    print(f"{explanations.get('deriv_context', '')}")
    
    print(f"\n📋 Risk-Specific Explanations:")
    print("-"*40)
    for risk_exp in explanations.get('risk_explanations', []):
        print(f"\n{risk_exp.get('display_name', 'Unknown Risk')} ({risk_exp.get('severity', 'N/A')}):")
        print(f"  Concept: {risk_exp.get('concept', '')}")
        print(f"  Why it matters: {risk_exp.get('why_matters', '')}")
        print(f"  Principle: {risk_exp.get('principle', '')}")
        print(f"  Psychology: {risk_exp.get('psychology_insight', '')}")
        
        print(f"  Suggestions:")
        for suggestion in risk_exp.get('non_advice_suggestions', []):
            print(f"    • {suggestion}")
    
    print(f"\n🕒 Generated: {explanations.get('timestamp', 'N/A')}")
    print(f"🤖 Model: {explanations.get('ai_model', 'N/A')}")
    
    print("\n" + "="*60)
    print("FORMATTED FOR DISPLAY:")
    print("="*60)
    print(explainer.format_for_display(explanations))
    
    return explanations

if __name__ == "__main__":
    test_ai_explainer()