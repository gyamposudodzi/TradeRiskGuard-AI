"""
Database models for Deriv/MT5 integration
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from api.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class DerivConnection(Base):
    __tablename__ = "deriv_connections"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Deriv API credentials (encrypted)
    api_token_encrypted = Column(Text, nullable=False)  # Encrypted API token
    app_id = Column(String, nullable=False)
    account_id = Column(String, nullable=True)  # Specific account if multiple
    
    # Connection metadata
    connection_name = Column(String, default="Deriv Account")
    connection_status = Column(String, default="disconnected")  # "connected", "disconnected", "error"
    last_sync_status = Column(String, nullable=True)  # "success", "failed", "partial"
    
    # Account info (cached from Deriv)
    account_info = Column(JSON, nullable=True)  # Balance, currency, etc.
    account_type = Column(String, nullable=True)  # "demo", "real"
    
    # Sync settings
    auto_sync = Column(Boolean, default=True)
    sync_frequency = Column(String, default="daily")  # "hourly", "daily", "weekly"
    sync_days_back = Column(Integer, default=90)  # How many days back to sync
    
    # Sync history
    last_sync_at = Column(DateTime, nullable=True)
    last_successful_sync = Column(DateTime, nullable=True)
    total_syncs = Column(Integer, default=0)
    total_trades_synced = Column(Integer, default=0)
    
    # Error tracking
    last_error = Column(Text, nullable=True)
    error_count = Column(Integer, default=0)
    disabled_until = Column(DateTime, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    connected_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", backref="deriv_connections")
    synced_trades = relationship("DerivTrade", back_populates="connection")
    sync_logs = relationship("SyncLog", back_populates="connection")
    
    def to_dict(self, include_sensitive=False):
        """Convert to dictionary, optionally including sensitive info"""
        data = {
            "id": self.id,
            "connection_name": self.connection_name,
            "connection_status": self.connection_status,
            "account_id": self.account_id,
            "account_type": self.account_type,
            "auto_sync": self.auto_sync,
            "sync_frequency": self.sync_frequency,
            "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
            "last_successful_sync": self.last_successful_sync.isoformat() if self.last_successful_sync else None,
            "total_trades_synced": self.total_trades_synced,
            "total_syncs": self.total_syncs,
            "account_info": self.account_info or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "connected_at": self.connected_at.isoformat() if self.connected_at else None,
            "last_error": self.last_error
        }
        
        if include_sensitive:
            data["app_id"] = self.app_id
            # Note: Never expose encrypted token
        
        return data

class DerivTrade(Base):
    __tablename__ = "deriv_trades"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    connection_id = Column(String, ForeignKey("deriv_connections.id"), nullable=False)
    analysis_id = Column(String, ForeignKey("analyses.id"), nullable=True)
    
    # Deriv trade data
    deriv_trade_id = Column(String, nullable=False, index=True)  # Original Deriv trade ID
    transaction_id = Column(String, nullable=True, index=True)
    contract_id = Column(String, nullable=True)
    
    # Trade details
    symbol = Column(String, nullable=False)
    contract_type = Column(String, nullable=False)  # "MULTUP", "MULTDOWN", "RISE", "FALL", etc.
    currency = Column(String, nullable=False, default="USD")
    
    # Prices and amounts
    buy_price = Column(Float, nullable=False)
    sell_price = Column(Float, nullable=True)
    barrier = Column(Float, nullable=True)
    barrier2 = Column(Float, nullable=True)
    
    # Financials
    stake = Column(Float, nullable=False)  # Amount bet
    payout = Column(Float, nullable=True)
    profit = Column(Float, nullable=False)  # Calculated profit/loss
    commission = Column(Float, nullable=True, default=0)
    
    # Timing
    purchase_time = Column(DateTime, nullable=False)
    expiry_time = Column(DateTime, nullable=True)
    sell_time = Column(DateTime, nullable=True)
    duration = Column(Integer, nullable=True)  # Duration in seconds
    
    # Status
    status = Column(String, nullable=False)  # "open", "won", "lost", "sold", "cancelled"
    exit_spot = Column(Float, nullable=True)
    
    # Raw data for reference
    raw_data = Column(JSON, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    connection = relationship("DerivConnection", back_populates="synced_trades")
    analysis = relationship("Analysis", backref="deriv_trades")
    
    def to_dict(self):
        return {
            "id": self.id,
            "deriv_trade_id": self.deriv_trade_id,
            "symbol": self.symbol,
            "contract_type": self.contract_type,
            "status": self.status,
            "stake": self.stake,
            "profit": self.profit,
            "purchase_time": self.purchase_time.isoformat() if self.purchase_time else None,
            "expiry_time": self.expiry_time.isoformat() if self.expiry_time else None,
            "duration": self.duration,
            "buy_price": self.buy_price,
            "sell_price": self.sell_price,
            "barrier": self.barrier,
            "payout": self.payout
        }

class SyncLog(Base):
    __tablename__ = "sync_logs"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    connection_id = Column(String, ForeignKey("deriv_connections.id"), nullable=False)
    
    # Sync details
    sync_type = Column(String, nullable=False)  # "initial", "incremental", "manual", "scheduled"
    status = Column(String, nullable=False)  # "started", "success", "failed", "partial"
    
    # Statistics
    trades_fetched = Column(Integer, default=0)
    trades_new = Column(Integer, default=0)
    trades_updated = Column(Integer, default=0)
    trades_skipped = Column(Integer, default=0)
    
    # Time range
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    
    # Timing
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    
    # Results
    analysis_id = Column(String, ForeignKey("analyses.id"), nullable=True)
    error_message = Column(Text, nullable=True)
    logs = Column(JSON, nullable=True)  # Detailed sync logs
    
    # Relationships
    connection = relationship("DerivConnection", back_populates="sync_logs")
    analysis = relationship("Analysis", backref="sync_logs")
    
    def to_dict(self):
        return {
            "id": self.id,
            "sync_type": self.sync_type,
            "status": self.status,
            "trades_fetched": self.trades_fetched,
            "trades_new": self.trades_new,
            "trades_updated": self.trades_updated,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "error_message": self.error_message
        }

class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    connection_id = Column(String, ForeignKey("deriv_connections.id"), nullable=True)
    
    # Webhook data
    event_type = Column(String, nullable=False)  # "trade_update", "balance_update", "login"
    event_source = Column(String, default="deriv")  # "deriv", "mt5", "manual"
    
    # Payload
    raw_payload = Column(JSON, nullable=False)
    signature = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    
    # Processing
    processed = Column(Boolean, default=False)
    processed_at = Column(DateTime, nullable=True)
    processing_error = Column(Text, nullable=True)
    
    # Result
    trade_id = Column(String, nullable=True)
    analysis_triggered = Column(Boolean, default=False)
    analysis_id = Column(String, ForeignKey("analyses.id"), nullable=True)
    
    # Metadata
    received_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    connection = relationship("DerivConnection")
    analysis = relationship("Analysis", backref="webhook_events")
    
    def to_dict(self):
        return {
            "id": self.id,
            "event_type": self.event_type,
            "event_source": self.event_source,
            "processed": self.processed,
            "received_at": self.received_at.isoformat() if self.received_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "analysis_triggered": self.analysis_triggered,
            "trade_id": self.trade_id
        }