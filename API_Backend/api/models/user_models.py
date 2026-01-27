"""
Database models for storing analyses and user data
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Boolean, ForeignKey

from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from api.database import Base

"""
Update main models.py to import alert models
"""
# Add at the top
from .alert_models import PredictiveAlert, AlertSettings, AlertHistory

# Keep all existing models, just add these imports


def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    analyses = relationship("Analysis", back_populates="user")
    settings = relationship("UserSettings", back_populates="user", uselist=False)

class UserSettings(Base):
    __tablename__ = "user_settings"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), unique=True)
    
    # Risk thresholds
    max_position_size_pct = Column(Float, default=2.0)
    min_win_rate = Column(Float, default=40.0)
    max_drawdown_pct = Column(Float, default=20.0)
    min_rr_ratio = Column(Float, default=1.0)
    min_sl_usage_rate = Column(Float, default=80.0)
    
    # AI settings
    ai_enabled = Column(Boolean, default=True)
    preferred_model = Column(String, default="gpt-4o-mini")
    openai_api_key_encrypted = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="settings")

class Analysis(Base):
    __tablename__ = "analyses"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)  # Nullable for guest analyses
    
    # File info
    filename = Column(String)
    original_filename = Column(String)
    file_size = Column(Integer)  # in bytes
    trade_count = Column(Integer)
    
    # Analysis results (stored as JSON for flexibility)
    metrics = Column(JSON, nullable=True)
    risk_results = Column(JSON, nullable=True)
    score_result = Column(JSON, nullable=True)
    ai_explanations = Column(JSON, nullable=True)
    
    # Metadata
    status = Column(String, default="completed")  # pending, processing, completed, failed
    error_message = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="analyses")
    reports = relationship("Report", back_populates="analysis")

class Report(Base):
    __tablename__ = "reports"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    analysis_id = Column(String, ForeignKey("analyses.id"))
    
    # Report content
    report_type = Column(String)  # markdown, html, pdf
    content = Column(String)  # For markdown/html, store directly
    file_path = Column(String, nullable=True)  # For PDF/large files
    
    # Metadata
    generated_at = Column(DateTime, default=datetime.utcnow)
    download_count = Column(Integer, default=0)
    
    analysis = relationship("Analysis", back_populates="reports")