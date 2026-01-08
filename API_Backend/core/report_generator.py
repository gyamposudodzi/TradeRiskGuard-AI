# core/report_generator.py
import json
from datetime import datetime
from typing import Dict, Any
import pandas as pd

class ReportGenerator:
    """Generate trade risk analysis reports"""
    
    def __init__(self):
        pass
    
    def generate_markdown_report(self, 
                                metrics: Dict[str, Any],
                                risk_results: Dict[str, Any],
                                score_result: Dict[str, Any],
                                ai_explanations: Dict[str, Any]) -> str:
        """Generate a markdown format report"""
        
        report_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        report = f"""
# 📊 TradeGuard AI - Risk Health Report
**Generated:** {report_date}
**Report ID:** TG-{datetime.now().strftime('%Y%m%d%H%M%S')}

---

## 🎯 Executive Summary

**Overall Risk Score:** {score_result['score']}/100
**Risk Grade:** {score_result['grade']}
**Total Risks Detected:** {score_result['total_risks']}
**Improvement Potential:** {score_result['improvement_potential']}%

### AI Assessment:
{ai_explanations.get('risk_summary', 'No AI assessment available')}

---

## 📈 Trading Performance Metrics

| Metric | Value |
|--------|-------|
"""
        
        # Add key metrics to table
        key_metrics = [
            ('Total Trades', metrics.get('total_trades', 0)),
            ('Win Rate', f"{metrics.get('win_rate', 0):.1f}%"),
            ('Profit Factor', f"{metrics.get('profit_factor', 0):.2f}"),
            ('Net Profit', f"${metrics.get('net_profit', 0):.2f}"),
            ('Average Position Size', f"{metrics.get('avg_position_size_pct', 0):.1f}%"),
            ('Maximum Drawdown', f"{metrics.get('max_drawdown_pct', 0):.1f}%"),
            ('Risk-Reward Ratio', f"{metrics.get('risk_reward_ratio', 0):.2f}"),
            ('Stop-Loss Usage', f"{metrics.get('sl_usage_rate', 0):.1f}%"),
            ('Revenge Trading', f"{metrics.get('revenge_trading_pct', 0):.1f}%")
        ]
        
        for name, value in key_metrics:
            report += f"| {name} | {value} |\n"
        
        report += """
---

## 🚨 Risk Analysis

### Detected Risks:
"""
        
        if risk_results.get('detected_risks'):
            for risk in risk_results['detected_risks']:
                details = risk_results['risk_details'].get(risk, {})
                severity = details.get('severity', 0)
                message = details.get('message', '')
                report += f"- **{risk.replace('_', ' ').title()}** (Severity: {severity}%): {message}\n"
        else:
            report += "✅ No significant risks detected.\n"
        
        report += """
---

## 🎓 AI Insights & Educational Context

### Key Strengths:
"""
        
        for strength in ai_explanations.get('key_strengths', []):
            report += f"- {strength}\n"
        
        report += f"""
### Key Risks:
"""
        
        for risk in ai_explanations.get('key_risks', []):
            report += f"- {risk}\n"
        
        report += f"""
### Educational Insights:
{ai_explanations.get('educational_insights', '')}

### Improvement Focus:
{ai_explanations.get('improvement_focus', '')}

---

## 📋 Action Plan (Non-Advisory)

### Priority Areas:
"""
        
        for i, risk in enumerate(score_result.get('top_risks', []), 1):
            report += f"{i}. **{risk.replace('_', ' ').title()}**\n"
        
        report += """
### Next Steps:
1. Review each detected risk understanding
2. Consider general risk management principles
3. Implement consistent trading practices
4. Monitor improvements over time

---

## ⚠️ Important Disclaimers

1. **Educational Purpose Only**: This report is for educational purposes only.
2. **No Trading Advice**: This report does not provide trading advice, signals, or predictions.
3. **Past Performance**: Past performance is not indicative of future results.
4. **Risk of Loss**: Trading involves risk of loss.
5. **Platform Agnostic**: Analysis is based on trading patterns, not platform-specific features.

**Analysis generated using:** TradeGuard AI v1.0
**AI Model:** {ai_explanations.get('ai_model', 'N/A')}
**Report Version:** 1.0

---
*End of Report*
"""
        
        return report
    
    def generate_html_report(self, markdown_report: str) -> str:
        """Convert markdown report to HTML"""
        # Simple HTML conversion
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TradeGuard AI - Risk Health Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 1000px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #2563eb; border-bottom: 2px solid #2563eb; padding-bottom: 10px; }}
        h2 {{ color: #475569; margin-top: 30px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #f8fafc; }}
        .risk-high {{ color: #dc2626; font-weight: bold; }}
        .risk-medium {{ color: #f59e0b; }}
        .risk-low {{ color: #10b981; }}
        .disclaimer {{ background-color: #fef2f2; border-left: 4px solid #dc2626; padding: 15px; margin: 20px 0; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 10px; margin-bottom: 30px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🛡️ TradeGuard AI</h1>
        <h2>Risk Health Check Report</h2>
        <p>Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    </div>
"""
        
        # Convert markdown to simple HTML
        lines = markdown_report.split('\n')
        in_table = False
        table_html = ""
        
        for line in lines:
            if line.startswith('|'):
                if not in_table:
                    in_table = True
                    table_html = "<table>\n"
                table_html += "  <tr>\n"
                cells = line.split('|')[1:-1]
                for cell in cells:
                    table_html += f"    <td>{cell.strip()}</td>\n"
                table_html += "  </tr>\n"
            else:
                if in_table:
                    html += table_html + "</table>\n"
                    in_table = False
                    table_html = ""
                
                if line.startswith('# '):
                    html += f'<h1>{line[2:]}</h1>\n'
                elif line.startswith('## '):
                    html += f'<h2>{line[3:]}</h2>\n'
                elif line.startswith('### '):
                    html += f'<h3>{line[4:]}</h3>\n'
                elif line.startswith('- **'):
                    # Handle bold list items
                    text = line[2:]
                    if '(Severity:' in text:
                        parts = text.split('(Severity:')
                        risk_text = parts[0].replace('**', '<strong>', 1).replace('**', '</strong>', 1)
                        severity = parts[1].split(')')[0]
                        if 'high' in severity.lower() or int(severity.split('%')[0]) >= 70:
                            severity_class = 'risk-high'
                        elif 'medium' in severity.lower() or 40 <= int(severity.split('%')[0]) < 70:
                            severity_class = 'risk-medium'
                        else:
                            severity_class = 'risk-low'
                        html += f'<li>{risk_text} <span class="{severity_class}">(Severity: {severity})</span></li>\n'
                    else:
                        html += f'<li>{text.replace("**", "<strong>", 1).replace("**", "</strong>", 1)}</li>\n'
                elif line.startswith('- '):
                    html += f'<li>{line[2:]}</li>\n'
                elif line.strip() == '---':
                    html += '<hr>\n'
                elif line.strip():
                    html += f'<p>{line}</p>\n'
        
        # Add disclaimer section
        html += """
    <div class="disclaimer">
        <h3>⚠️ Important Disclaimers</h3>
        <ul>
            <li><strong>Educational Purpose Only:</strong> This report is for educational purposes only.</li>
            <li><strong>No Trading Advice:</strong> This report does not provide trading advice, signals, or predictions.</li>
            <li><strong>Past Performance:</strong> Past performance is not indicative of future results.</li>
            <li><strong>Risk of Loss:</strong> Trading involves risk of loss.</li>
            <li><strong>Platform Agnostic:</strong> Analysis is based on trading patterns, not platform-specific features.</li>
        </ul>
    </div>
</body>
</html>
"""
        
        return html

# Test function
def test_report_generator():
    """Test the report generator"""
    print("📋 Testing Report Generator")
    print("="*60)
    
    # Create sample data
    sample_metrics = {
        'total_trades': 45,
        'win_rate': 42.2,
        'profit_factor': 1.35,
        'net_profit': 1250.50
    }
    
    sample_risk_results = {
        'detected_risks': ['over_leverage', 'no_stop_loss'],
        'risk_details': {
            'over_leverage': {'severity': 75.0, 'message': 'Position sizing too large'},
            'no_stop_loss': {'severity': 60.0, 'message': 'Missing stop-loss orders'}
        }
    }
    
    sample_score_result = {
        'score': 65.5,
        'grade': 'C',
        'total_risks': 2,
        'improvement_potential': 34.5,
        'top_risks': ['over_leverage', 'no_stop_loss']
    }
    
    sample_ai_explanations = {
        'risk_summary': 'Good overall but needs improvement in risk management.',
        'key_strengths': ['Consistent trading', 'Good market timing'],
        'key_risks': ['Over-leverage', 'Missing stop-loss'],
        'educational_insights': 'Risk management is crucial for long-term success.',
        'improvement_focus': 'Focus on position sizing and stop-loss discipline.',
        'ai_model': 'demo_mode'
    }
    
    # Generate report
    generator = ReportGenerator()
    markdown_report = generator.generate_markdown_report(
        sample_metrics,
        sample_risk_results,
        sample_score_result,
        sample_ai_explanations
    )
    
    print("Generated Markdown Report Preview:")
    print("-"*60)
    print(markdown_report[:1000] + "...\n")
    
    # Generate HTML report
    html_report = generator.generate_html_report(markdown_report)
    
    print("Generated HTML Report (first 500 chars):")
    print("-"*60)
    print(html_report[:500] + "...\n")
    
    # Save sample reports
    with open('sample_report.md', 'w') as f:
        f.write(markdown_report)
    
    with open('sample_report.html', 'w') as f:
        f.write(html_report)
    
    print(f"✅ Reports saved: sample_report.md, sample_report.html")
    print(f"📄 Markdown length: {len(markdown_report)} chars")
    print(f"🌐 HTML length: {len(html_report)} chars")
    
    return markdown_report, html_report

if __name__ == "__main__":
    test_report_generator()