# core/metrics_calculator.py
import pandas as pd
import numpy as np
from datetime import datetime

class TradeMetricsCalculator:
    """Calculate trading metrics from trade data"""
    
    def __init__(self, df):
        self.df = df.copy()
        self.metrics = {}
        
    def compute_all_metrics(self):
        """Compute all trading metrics"""
        self.compute_basic_metrics()
        self.compute_risk_metrics()
        self.compute_performance_metrics()
        self.compute_pattern_metrics()
        return self.metrics
    
    def compute_basic_metrics(self):
        """Compute basic trading statistics"""
        df = self.df
        
        self.metrics['total_trades'] = len(df)
        self.metrics['winning_trades'] = len(df[df['profit_loss'] > 0])
        self.metrics['losing_trades'] = len(df[df['profit_loss'] < 0])
        self.metrics['win_rate'] = (self.metrics['winning_trades'] / self.metrics['total_trades'] * 100 
                                   if self.metrics['total_trades'] > 0 else 0)
        
        # Profit metrics
        self.metrics['total_profit'] = df[df['profit_loss'] > 0]['profit_loss'].sum()
        self.metrics['total_loss'] = abs(df[df['profit_loss'] < 0]['profit_loss'].sum())
        self.metrics['net_profit'] = df['profit_loss'].sum()
        self.metrics['avg_win'] = (df[df['profit_loss'] > 0]['profit_loss'].mean() 
                                  if self.metrics['winning_trades'] > 0 else 0)
        self.metrics['avg_loss'] = (abs(df[df['profit_loss'] < 0]['profit_loss'].mean()) 
                                   if self.metrics['losing_trades'] > 0 else 0)
        
        # Profit factor
        if self.metrics['total_loss'] != 0:
            self.metrics['profit_factor'] = self.metrics['total_profit'] / self.metrics['total_loss']
        else:
            self.metrics['profit_factor'] = float('inf') if self.metrics['total_profit'] > 0 else 0
    
    def compute_risk_metrics(self):
        """Compute risk-related metrics"""
        df = self.df
        
        # Position sizing
        if 'lot_size' in df.columns and 'account_balance_before' in df.columns:
            df['position_size_pct'] = (df['lot_size'] * 100000) / df['account_balance_before'] * 100
            self.metrics['avg_position_size_pct'] = df['position_size_pct'].mean()
            self.metrics['max_position_size_pct'] = df['position_size_pct'].max()
        
        # Stop loss usage
        if 'stop_loss' in df.columns:
            sl_missing = df['stop_loss'].isna() | (df['stop_loss'] == 0)
            self.metrics['sl_usage_rate'] = (1 - sl_missing.sum() / len(df)) * 100
        
        # Risk-reward ratio
        winning_trades = df[df['profit_loss'] > 0]
        losing_trades = df[df['profit_loss'] < 0]
        
        if len(losing_trades) > 0 and len(winning_trades) > 0:
            avg_risk = abs(losing_trades['profit_loss']).mean()
            avg_reward = winning_trades['profit_loss'].mean()
            self.metrics['risk_reward_ratio'] = avg_reward / avg_risk if avg_risk != 0 else 0
        else:
            self.metrics['risk_reward_ratio'] = 0
    
    def compute_performance_metrics(self):
        """Compute performance metrics"""
        df = self.df
        
        # Drawdown calculation
        if 'account_balance_before' in df.columns:
            # Simple drawdown calculation
            balances = df['account_balance_before'].tolist()
            running_max = balances[0]
            max_drawdown_pct = 0
            
            for balance in balances:
                if balance > running_max:
                    running_max = balance
                drawdown_pct = (running_max - balance) / running_max * 100
                if drawdown_pct > max_drawdown_pct:
                    max_drawdown_pct = drawdown_pct
            
            self.metrics['max_drawdown_pct'] = max_drawdown_pct
    
    def compute_pattern_metrics(self):
        """Detect trading patterns"""
        df = self.df
        
        # Convert to datetime if not already
        if 'entry_time' in df.columns:
            df['entry_time_dt'] = pd.to_datetime(df['entry_time'])
            df['exit_time_dt'] = pd.to_datetime(df['exit_time'])
            
            # Trading frequency
            df['trade_duration'] = (df['exit_time_dt'] - df['entry_time_dt']).dt.total_seconds() / 3600  # hours
            self.metrics['avg_trade_duration_hours'] = df['trade_duration'].mean()
            
            # Sort by time and check for revenge trading
            df_sorted = df.sort_values('entry_time_dt')
            df_sorted['prev_result'] = df_sorted['profit_loss'].shift(1)
            df_sorted['time_since_last'] = df_sorted['entry_time_dt'].diff().dt.total_seconds() / 60  # minutes
            
            # Revenge trading: trade within 30 minutes of a loss
            revenge_trades = df_sorted[
                (df_sorted['prev_result'] < 0) & 
                (df_sorted['time_since_last'] < 30)
            ]
            
            self.metrics['revenge_trades_count'] = len(revenge_trades)
            self.metrics['revenge_trading_pct'] = (len(revenge_trades) / len(df) * 100 
                                                  if len(df) > 0 else 0)
            
            # Time of day analysis
            df_sorted['entry_hour'] = df_sorted['entry_time_dt'].dt.hour
            self.metrics['most_active_hour'] = df_sorted['entry_hour'].mode()[0] if len(df_sorted) > 0 else None

# Test function
def test_metrics():
    """Test the metrics calculator"""
    # Create sample data
    data = {
        'trade_id': [1, 2, 3, 4],
        'profit_loss': [50, -30, 75, -20],
        'lot_size': [0.1, 0.2, 0.15, 0.1],
        'account_balance_before': [10000, 10050, 10020, 10095],
        'stop_loss': [1.1, 1.2, 1.15, 1.3],
        'entry_time': ['2024-01-01 10:00:00', '2024-01-01 11:00:00', 
                      '2024-01-01 12:00:00', '2024-01-01 12:15:00'],
        'exit_time': ['2024-01-01 11:00:00', '2024-01-01 11:30:00',
                     '2024-01-01 13:00:00', '2024-01-01 12:45:00']
    }
    
    df = pd.DataFrame(data)
    calculator = TradeMetricsCalculator(df)
    metrics = calculator.compute_all_metrics()
    
    print("Metrics calculated:")
    for key, value in metrics.items():
        print(f"{key}: {value}")
    
    return metrics

if __name__ == "__main__":
    test_metrics()