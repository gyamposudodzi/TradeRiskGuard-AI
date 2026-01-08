"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

# Enums
class ReportFormat(str, Enum):
    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

# User Schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str

class UserCreate(UserBase):
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# Analysis Schemas
class AnalysisRequest(BaseModel):
    filename: Optional[str] = None
    use_sample: bool = False

class AnalysisResponse(BaseModel):
    id: str
    status: str
    metrics: Optional[Dict[str, Any]] = None
    risk_results: Optional[Dict[str, Any]] = None
    score_result: Optional[Dict[str, Any]] = None
    ai_explanations: Optional[Dict[str, Any]] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

# Risk Assessment Schemas
class RiskSimulationRequest(BaseModel):
    current_score: float
    improvements: Dict[str, float]  # risk_name: improvement_percentage

class RiskSimulationResponse(BaseModel):
    original_score: float
    simulated_score: float
    improvement: float
    new_grade: str
    recommendations: List[str]

# Report Schemas
class ReportGenerateRequest(BaseModel):
    analysis_id: str
    format: ReportFormat = ReportFormat.MARKDOWN
    include_sections: List[str] = Field(default_factory=list)

class ReportResponse(BaseModel):
    id: str
    analysis_id: str
    report_type: str
    content: Optional[str] = None
    download_url: Optional[str] = None
    generated_at: datetime

# Settings Schemas
class UserSettingsUpdate(BaseModel):
    max_position_size_pct: Optional[float] = None
    min_win_rate: Optional[float] = None
    max_drawdown_pct: Optional[float] = None
    min_rr_ratio: Optional[float] = None
    min_sl_usage_rate: Optional[float] = None
    ai_enabled: Optional[bool] = None
    preferred_model: Optional[str] = None

class UserSettingsResponse(UserSettingsUpdate):
    user_id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# Dashboard Schemas
class DashboardSummary(BaseModel):
    total_analyses: int
    average_score: float
    recent_analyses: List[AnalysisResponse]
    risk_distribution: Dict[RiskLevel, int]
    improvement_trend: List[Dict[str, Any]]

# Generic Response Schema
class APIResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    message: Optional[str] = None
    error: Optional[str] = None
    
    @classmethod
    def success_response(cls, data: Any = None, message: str = "Success"):
        return cls(success=True, data=data, message=message)
    
    @classmethod
    def error_response(cls, message: str = "Error", error: str = None):
        return cls(success=False, message=message, error=error)