"""
Deriv API client for fetching trade data
"""
import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import time
import hashlib

class DerivAPIClient:
    """Client for interacting with Deriv API"""
    
    def __init__(self, api_token: str, app_id: str, account_id: Optional[str] = None):
        self.api_token = api_token
        self.app_id = app_id
        self.account_id = account_id
        
        # API endpoints
        self.base_url = "https://deriv-api.crypto.com"
        self.websocket_url = "wss://deriv-api.crypto.com/websockets/v3"
        
        # Headers
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Token {self.api_token}"
        }
    
    def test_connection(self) -> Dict[str, Any]:
        """Test API connection and get account info"""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/user",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "account_info": data.get("user", {}),
                    "message": "Connection successful"
                }
            else:
                return {
                    "success": False,
                    "error": f"API returned {response.status_code}",
                    "details": response.text[:200]
                }
                
        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "error": "Connection failed",
                "details": "Cannot connect to Deriv API"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "details": "Unexpected error"
            }
    
    def get_account_balance(self) -> Optional[float]:
        """Get account balance"""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/balance",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                return float(data.get("balance", 0))
            return None
        except:
            return None
    
    def get_transactions(self, days_back: int = 90) -> List[Dict[str, Any]]:
        """Get transaction history"""
        try:
            end_time = int(time.time())
            start_time = end_time - (days_back * 24 * 60 * 60)
            
            params = {
                "limit": 1000,  # Max per request
                "offset": 0,
                "start_time": start_time,
                "end_time": end_time,
                "action": "buy"  # Get buy transactions (trades)
            }
            
            all_transactions = []
            has_more = True
            
            while has_more:
                response = requests.get(
                    f"{self.base_url}/api/v1/transactions",
                    headers=self.headers,
                    params=params,
                    timeout=30
                )
                
                if response.status_code != 200:
                    break
                
                data = response.json()
                transactions = data.get("transactions", [])
                all_transactions.extend(transactions)
                
                # Check if there are more transactions
                has_more = data.get("has_more", False)
                if has_more:
                    params["offset"] += params["limit"]
                    time.sleep(0.5)  # Rate limiting
            
            return all_transactions
            
        except Exception as e:
            print(f"Error fetching transactions: {e}")
            return []
    
    def get_contract_info(self, contract_id: str) -> Optional[Dict[str, Any]]:
        """Get details for a specific contract"""
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/contract/{contract_id}",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            return None
        except:
            return None
    
    def transform_transaction_to_trade(self, transaction: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Transform Deriv transaction to standardized trade format"""
        try:
            # Only process buy transactions (trades)
            if transaction.get("action") != "buy":
                return None
            
            contract_id = transaction.get("contract_id")
            contract_info = self.get_contract_info(contract_id) if contract_id else None
            
            # Extract basic info
            trade_data = {
                "deriv_trade_id": str(transaction.get("transaction_id", "")),
                "transaction_id": str(transaction.get("transaction_id", "")),
                "contract_id": contract_id,
                "symbol": transaction.get("symbol", ""),
                "contract_type": transaction.get("contract_type", ""),
                "currency": transaction.get("currency", "USD"),
                "buy_price": float(transaction.get("buy_price", 0)),
                "stake": float(abs(transaction.get("amount", 0))),  # Stake is absolute amount
                "purchase_time": datetime.fromtimestamp(transaction.get("transaction_time", 0)),
                "status": "open",  # Default, will be updated
                "profit": 0,  # Will be calculated
                "raw_data": transaction
            }
            
            # Add contract info if available
            if contract_info:
                trade_data.update({
                    "sell_price": float(contract_info.get("sell_price", 0)),
                    "expiry_time": datetime.fromtimestamp(contract_info.get("expiry_time", 0)) if contract_info.get("expiry_time") else None,
                    "sell_time": datetime.fromtimestamp(contract_info.get("sell_time", 0)) if contract_info.get("sell_time") else None,
                    "barrier": float(contract_info.get("barrier", 0)) if contract_info.get("barrier") else None,
                    "barrier2": float(contract_info.get("barrier2", 0)) if contract_info.get("barrier2") else None,
                    "payout": float(contract_info.get("payout", 0)),
                    "duration": contract_info.get("duration"),
                    "exit_spot": float(contract_info.get("exit_spot", 0)) if contract_info.get("exit_spot") else None
                })
                
                # Determine status
                if contract_info.get("status") == "sold":
                    trade_data["status"] = "sold"
                    trade_data["profit"] = float(contract_info.get("profit", 0))
                elif contract_info.get("is_expired", False):
                    trade_data["status"] = "expired"
                    trade_data["profit"] = -trade_data["stake"]  # Lost stake
                elif contract_info.get("is_valid_to_sell", False):
                    trade_data["status"] = "open"
                else:
                    trade_data["status"] = "unknown"
            
            return trade_data
            
        except Exception as e:
            print(f"Error transforming transaction: {e}")
            return None
    
    def get_trades(self, days_back: int = 90) -> List[Dict[str, Any]]:
        """Get all trades for the specified period"""
        transactions = self.get_transactions(days_back)
        
        trades = []
        for transaction in transactions:
            trade = self.transform_transaction_to_trade(transaction)
            if trade:
                trades.append(trade)
        
        return trades
    
    def get_recent_trades(self, hours_back: int = 24) -> List[Dict[str, Any]]:
        """Get recent trades (for real-time updates)"""
        # Convert hours to approximate days
        days_back = max(1, (hours_back // 24) + 1)
        return self.get_trades(days_back)