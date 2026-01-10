"""
Pydantic schemas for Deriv/MT5 integration
"""
from pydantic import BaseModel, Field, validator, HttpUrl
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# Enums
class ConnectionStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    SYNCING = "syncing"

class SyncFrequency(str, Enum):
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MANUAL = "manual"

class SyncType(str, Enum):
    INITIAL = "initial"
    INCREMENTAL = "incremental"
    MANUAL = "manual"
    SCHEDULED = "scheduled"

# Request Schemas
class DerivConnectRequest(BaseModel):
    api_token: str = Field(..., min_length=10, description="Deriv API token")
    app_id: str = Field(..., min_length=3, description="Deriv App ID")
    account_id: Optional[str] = Field(None, description="Specific account ID (optional)")
    connection_name: Optional[str] = Field("Deriv Account", description="Custom name for this connection")
    auto_sync: bool = Field(True, description="Enable automatic sync")
    sync_frequency: SyncFrequency = Field(SyncFrequency.DAILY, description="Sync frequency")
    sync_days_back: int = Field(90, ge=1, le=365, description="Days of history to sync")

class SyncTradesRequest(BaseModel):
    days_back: Optional[int] = Field(None, ge=1, le=365, description="Override default days back")
    force_full_sync: bool = Field(False, description="Force full re-sync")
    analyze_after_sync: bool = Field(True, description="Run analysis after sync")

class UpdateConnectionRequest(BaseModel):
    connection_name: Optional[str] = None
    auto_sync: Optional[bool] = None
    sync_frequency: Optional[SyncFrequency] = None
    sync_days_back: Optional[int] = Field(None, ge=1, le=365)
    disabled: Optional[bool] = None

class WebhookEventRequest(BaseModel):
    event: str
    transaction: Optional[Dict[str, Any]] = None
    contract: Optional[Dict[str, Any]] = None
    account: Optional[Dict[str, Any]] = None
    signature: Optional[str] = None

# Response Schemas
class DerivAccountInfo(BaseModel):
    account_id: str
    currency: str
    balance: float
    country: Optional[str] = None
    created_at: Optional[datetime] = None
    is_virtual: Optional[bool] = None

class ConnectionStatusResponse(BaseModel):
    connected: bool
    connection_id: str
    connection_name: str
    connection_status: str
    account_info: Optional[DerivAccountInfo] = None
    last_sync: Optional[datetime] = None
    next_sync: Optional[datetime] = None
    total_trades: int
    sync_settings: Dict[str, Any]
    error_message: Optional[str] = None

class SyncResultResponse(BaseModel):
    success: bool
    connection_id: str
    sync_type: str
    trades_fetched: int
    trades_new: int
    trades_updated: int
    trades_skipped: int
    analysis_id: Optional[str] = None
    analysis_score: Optional[float] = None
    duration_seconds: float
    error_message: Optional[str] = None
    logs: Optional[List[str]] = None

class DerivTradeResponse(BaseModel):
    id: str
    deriv_trade_id: str
    symbol: str
    contract_type: str
    status: str
    stake: float
    profit: float
    purchase_time: datetime
    expiry_time: Optional[datetime] = None
    duration: Optional[int] = None
    buy_price: float
    sell_price: Optional[float] = None
    barrier: Optional[float] = None
    payout: Optional[float] = None
    
    class Config:
        from_attributes = True

class ConnectionResponse(BaseModel):
    id: str
    connection_name: str
    connection_status: str
    account_id: Optional[str] = None
    account_type: Optional[str] = None
    auto_sync: bool
    sync_frequency: str
    last_sync_at: Optional[datetime] = None
    last_successful_sync: Optional[datetime] = None
    total_trades_synced: int
    total_syncs: int
    account_info: Dict[str, Any]
    created_at: datetime
    connected_at: Optional[datetime] = None
    last_error: Optional[str] = None
    
    class Config:
        from_attributes = True

class SyncLogResponse(BaseModel):
    id: str
    sync_type: str
    status: str
    trades_fetched: int
    trades_new: int
    trades_updated: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True

class WebhookResponse(BaseModel):
    received: bool
    event_id: str
    processed: bool
    trade_updated: bool
    analysis_triggered: bool
    analysis_id: Optional[str] = None

# Statistics Schemas
class ConnectionStats(BaseModel):
    total_connections: int
    active_connections: int
    total_trades_synced: int
    sync_success_rate: float
    recent_syncs: List[SyncLogResponse]