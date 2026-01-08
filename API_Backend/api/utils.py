"""
Utility functions for the API
"""
import pandas as pd
import io
from typing import Dict, Any
from fastapi import UploadFile
import json

def validate_csv_columns(df: pd.DataFrame) -> bool:
    """
    Validate that CSV has required columns for analysis
    """
    required_columns = ['profit_loss']
    recommended_columns = ['entry_time', 'exit_time', 'lot_size']
    
    # Check required columns
    for col in required_columns:
        if col not in df.columns:
            return False
    
    return True

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal attacks
    """
    # Remove directory paths
    filename = filename.split('/')[-1].split('\\')[-1]
    
    # Remove potentially dangerous characters
    dangerous_chars = ['<', '>', ':', '"', '|', '?', '*']
    for char in dangerous_chars:
        filename = filename.replace(char, '_')
    
    return filename

def format_error_response(error: Exception) -> Dict[str, Any]:
    """
    Format error response for API
    """
    return {
        "success": False,
        "error": str(error),
        "error_type": error.__class__.__name__,
        "timestamp": pd.Timestamp.now().isoformat()
    }

def create_sample_data() -> pd.DataFrame:
    """
    Create sample trade data for testing
    """
    sample_data = {
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
    return pd.DataFrame(sample_data)