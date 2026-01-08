# core/risk_rules.py
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any

class RiskRuleEngine:
    """Rule-based engine to detect trading risks"""
    
    def __init__(self, metrics: Dict[str, Any], df: pd.DataFrame = None):
        self.metrics = metrics
        self.df = df
        self.detected_risks = []
        self.risk_details = {}
        
        # Risk thresholds (can be configured)
        self.thresholds = {
            'max_position_size_pct': 2.0,  # Max 2% of account per trade
            'min_win_rate': 40.0,  # Minimum win rate %
            'max_drawdown_pct': 20.0,  # Maximum drawdown %
            'min_rr_ratio': 1.0,  # Minimum risk:reward ratio
            'max_revenge_trading_pct': 10.0,  # Max % of revenge trades
            'min_sl_usage_rate': 80.0,  # Minimum % of trades with SL
            'max_trade_frequency_hours': 1.0,  # Minimum time between trades
            'max_consecutive_losses': 3,  # Max consecutive losses
        }
    
    def detect_all_risks(self) -> Dict[str, Any]:
        """Run all risk detection rules"""
        self.detect_position_size_risk()
        self.detect_stop_loss_risk()
        self.detect_drawdown_risk()
        self.detect_revenge_trading_risk()
        self.detect_rr_ratio_risk()
        self.detect_win_rate_risk()
        self.detect_concentration_risk()
        self.detect_overtrading_risk()
        
        return {
            'detected_risks': self.detected_risks,
            'risk_details': self.risk_details,
            'total_risks': len(self.detected_risks)
        }
    
    def detect_position_size_risk(self):
        """Check if position sizes are too large"""
        if 'avg_position_size_pct' in self.metrics:
            avg_size = self.metrics['avg_position_size_pct']
            max_size = self.metrics.get('max_position_size_pct', 0)
            threshold = self.thresholds['max_position_size_pct']
            
            if avg_size > threshold:
                self.detected_risks.append('over_leverage')
                self.risk_details['over_leverage'] = {
                    'severity': self._calculate_severity(avg_size, threshold, 5.0),
                    'avg_position_size_pct': round(avg_size, 2),
                    'max_position_size_pct': round(max_size, 2),
                    'threshold': threshold,
                    'message': f"Average position size ({avg_size:.1f}%) exceeds recommended limit ({threshold}% of account)"
                }
    
    def detect_stop_loss_risk(self):
        """Check stop loss usage"""
        if 'sl_usage_rate' in self.metrics:
            sl_rate = self.metrics['sl_usage_rate']
            threshold = self.thresholds['min_sl_usage_rate']
            
            if sl_rate < threshold:
                missing_pct = 100 - sl_rate
                self.detected_risks.append('no_stop_loss')
                self.risk_details['no_stop_loss'] = {
                    'severity': self._calculate_severity(threshold, sl_rate, threshold),
                    'sl_usage_rate': round(sl_rate, 2),
                    'trades_without_sl': round((100 - sl_rate) * self.metrics.get('total_trades', 0) / 100),
                    'threshold': threshold,
                    'message': f"{missing_pct:.1f}% of trades executed without stop-loss orders"
                }
    
    def detect_drawdown_risk(self):
        """Check maximum drawdown"""
        if 'max_drawdown_pct' in self.metrics:
            drawdown = self.metrics['max_drawdown_pct']
            threshold = self.thresholds['max_drawdown_pct']
            
            if drawdown > threshold:
                self.detected_risks.append('high_drawdown')
                self.risk_details['high_drawdown'] = {
                    'severity': self._calculate_severity(drawdown, threshold, 50.0),
                    'max_drawdown_pct': round(drawdown, 2),
                    'threshold': threshold,
                    'message': f"Maximum drawdown ({drawdown:.1f}%) exceeds safe limit ({threshold}%)"
                }
    
    def detect_revenge_trading_risk(self):
        """Detect revenge trading patterns"""
        if 'revenge_trading_pct' in self.metrics:
            revenge_pct = self.metrics['revenge_trading_pct']
            threshold = self.thresholds['max_revenge_trading_pct']
            
            if revenge_pct > threshold:
                self.detected_risks.append('revenge_trading')
                self.risk_details['revenge_trading'] = {
                    'severity': self._calculate_severity(revenge_pct, threshold, 30.0),
                    'revenge_trades_pct': round(revenge_pct, 2),
                    'revenge_trades_count': self.metrics.get('revenge_trades_count', 0),
                    'threshold': threshold,
                    'message': f"Revenge trading detected: {revenge_pct:.1f}% of trades entered shortly after a loss"
                }
    
    def detect_rr_ratio_risk(self):
        """Check risk-reward ratio"""
        if 'risk_reward_ratio' in self.metrics:
            rr_ratio = self.metrics['risk_reward_ratio']
            threshold = self.thresholds['min_rr_ratio']
            
            if rr_ratio < threshold:
                self.detected_risks.append('poor_rr_ratio')
                self.risk_details['poor_rr_ratio'] = {
                    'severity': self._calculate_severity(threshold, rr_ratio, threshold),
                    'current_rr_ratio': round(rr_ratio, 2),
                    'threshold': threshold,
                    'message': f"Risk-reward ratio ({rr_ratio:.2f}) below recommended minimum ({threshold})"
                }
    
    def detect_win_rate_risk(self):
        """Check win rate"""
        if 'win_rate' in self.metrics:
            win_rate = self.metrics['win_rate']
            threshold = self.thresholds['min_win_rate']
            
            if win_rate < threshold:
                self.detected_risks.append('low_win_rate')
                self.risk_details['low_win_rate'] = {
                    'severity': self._calculate_severity(threshold, win_rate, threshold),
                    'current_win_rate': round(win_rate, 2),
                    'threshold': threshold,
                    'message': f"Win rate ({win_rate:.1f}%) below acceptable level ({threshold}%)"
                }
    
    def detect_concentration_risk(self):
        """Check if trading is concentrated in few symbols"""
        if self.df is not None and 'symbol' in self.df.columns:
            symbol_counts = self.df['symbol'].value_counts()
            total_trades = len(self.df)
            
            if len(symbol_counts) > 0:
                top_symbol_pct = (symbol_counts.iloc[0] / total_trades) * 100
                
                if top_symbol_pct > 50:  # More than 50% in one symbol
                    self.detected_risks.append('concentration_risk')
                    self.risk_details['concentration_risk'] = {
                        'severity': self._calculate_severity(top_symbol_pct, 50.0, 80.0),
                        'top_symbol': symbol_counts.index[0],
                        'concentration_pct': round(top_symbol_pct, 2),
                        'unique_symbols': len(symbol_counts),
                        'message': f"High concentration: {top_symbol_pct:.1f}% of trades in {symbol_counts.index[0]}"
                    }
    
    def detect_overtrading_risk(self):
        """Check for overtrading patterns"""
        if 'avg_trade_duration_hours' in self.metrics:
            avg_duration = self.metrics['avg_trade_duration_hours']
            total_trades = self.metrics.get('total_trades', 0)
            
            # High frequency trading with short durations
            if avg_duration < 1.0 and total_trades > 20:  # Less than 1 hour avg, >20 trades
                trades_per_day = total_trades / 30  # Assuming 30 days
                
                if trades_per_day > 5:  # More than 5 trades per day
                    self.detected_risks.append('overtrading')
                    self.risk_details['overtrading'] = {
                        'severity': min(100, trades_per_day * 10),
                        'avg_trade_duration_hours': round(avg_duration, 2),
                        'trades_per_day': round(trades_per_day, 2),
                        'total_trades': total_trades,
                        'message': f"Potential overtrading: {trades_per_day:.1f} trades per day with average duration {avg_duration:.1f} hours"
                    }
    
    def _calculate_severity(self, value: float, threshold: float, max_value: float) -> float:
        """Calculate severity score from 0-100"""
        excess = max(0, value - threshold)
        range_excess = max(0, max_value - threshold)
        
        if range_excess == 0:
            return 100 if excess > 0 else 0
        
        severity = min(100, (excess / range_excess) * 100)
        return round(severity, 2)
    
    def get_risk_summary(self) -> str:
        """Generate a human-readable risk summary"""
        if not self.detected_risks:
            return "✅ No significant risks detected. Your trading shows good risk management practices."
        
        summary = "🚨 **Risk Summary:**\n\n"
        
        # Categorize by severity
        high_risks = []
        medium_risks = []
        low_risks = []
        
        for risk in self.detected_risks:
            details = self.risk_details.get(risk, {})
            severity = details.get('severity', 0)
            
            if severity >= 70:
                high_risks.append((risk, details))
            elif severity >= 40:
                medium_risks.append((risk, details))
            else:
                low_risks.append((risk, details))
        
        if high_risks:
            summary += "**🔴 High Risks:**\n"
            for risk, details in high_risks:
                summary += f"• {details.get('message', risk)}\n"
            summary += "\n"
        
        if medium_risks:
            summary += "**🟡 Medium Risks:**\n"
            for risk, details in medium_risks:
                summary += f"• {details.get('message', risk)}\n"
            summary += "\n"
        
        if low_risks:
            summary += "**🟢 Low Risks:**\n"
            for risk, details in low_risks:
                summary += f"• {details.get('message', risk)}\n"
        
        return summary

# Test function
def test_risk_rules():
    """Test the risk rule engine"""
    # Sample metrics
    metrics = {
        'total_trades': 45,
        'avg_position_size_pct': 3.5,
        'max_position_size_pct': 5.2,
        'sl_usage_rate': 65.0,
        'max_drawdown_pct': 25.5,
        'revenge_trading_pct': 15.2,
        'revenge_trades_count': 7,
        'risk_reward_ratio': 0.8,
        'win_rate': 35.0,
        'avg_trade_duration_hours': 0.8
    }
    
    # Create sample dataframe for concentration test
    df = pd.DataFrame({
        'symbol': ['EURUSD'] * 30 + ['GBPUSD'] * 10 + ['BTCUSD'] * 5
    })
    
    engine = RiskRuleEngine(metrics, df)
    results = engine.detect_all_risks()
    
    print("Detected Risks:", results['detected_risks'])
    print("\nRisk Details:")
    for risk, details in results['risk_details'].items():
        print(f"\n{risk.upper()}:")
        for key, value in details.items():
            print(f"  {key}: {value}")
    
    print("\n" + "="*50)
    print("RISK SUMMARY:")
    print("="*50)
    print(engine.get_risk_summary())
    
    return results

if __name__ == "__main__":
    test_risk_rules()