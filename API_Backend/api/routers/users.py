"""
API endpoints for user management
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import timedelta
from typing import Optional

from api import schemas, models, auth
from api.config import settings
from api.database import get_db

router = APIRouter()

@router.post("/register", response_model=schemas.APIResponse)
async def register_user(
    user_data: schemas.UserCreate,
    db: Session = Depends(get_db)
):
    """
    Register a new user
    """
    # Check if user already exists
    existing_user = db.query(models.User)\
        .filter(
            (models.User.email == user_data.email) | 
            (models.User.username == user_data.username)
        )\
        .first()
    
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="User with this email or username already exists"
        )
    
    # Create new user
    hashed_password = auth.get_password_hash(user_data.password)
    
    user = models.User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Create default settings for user (avoid overwriting 'settings')
    user_settings = models.UserSettings(user_id=user.id)
    db.add(user_settings)
    db.commit()
    
    # Create access token using constant from auth.py
    access_token = auth.create_access_token(
        data={"sub": user.id},
        expires_delta=timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    response_data = {
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "created_at": user.created_at
        },
        "access_token": access_token,
        "token_type": "bearer"
    }
    
    return schemas.APIResponse.success_response(
        data=response_data,
        message="User registered successfully"
    )

@router.post("/login", response_model=schemas.APIResponse)
async def login_user(
    login_data: schemas.UserLogin,
    db: Session = Depends(get_db)
):
    """
    Login user and return access token
    """
    user = db.query(models.User)\
        .filter(models.User.email == login_data.email)\
        .first()
    
    if not user or not auth.verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=400,
            detail="Inactive user"
        )
    
    # Create access token
    access_token = auth.create_access_token(
        data={"sub": user.id},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    response_data = {
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "created_at": user.created_at
        },
        "access_token": access_token,
        "token_type": "bearer"
    }
    
    return schemas.APIResponse.success_response(
        data=response_data,
        message="Login successful"
    )

@router.get("/profile", response_model=schemas.APIResponse)
async def get_user_profile(
    current_user: schemas.UserResponse = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get current user's profile
    """
    response_data = {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at,
        "updated_at": current_user.updated_at
    }
    
    return schemas.APIResponse.success_response(data=response_data)

@router.get("/settings", response_model=schemas.APIResponse)
async def get_user_settings(
    current_user: schemas.UserResponse = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Get user settings
    """
    settings = db.query(models.UserSettings)\
        .filter(models.UserSettings.user_id == current_user.id)\
        .first()
    
    if not settings:
        # Create default settings if not exists
        settings = models.UserSettings(user_id=current_user.id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    
    response_data = schemas.UserSettingsResponse(
        user_id=settings.user_id,
        max_position_size_pct=settings.max_position_size_pct,
        min_win_rate=settings.min_win_rate,
        max_drawdown_pct=settings.max_drawdown_pct,
        min_rr_ratio=settings.min_rr_ratio,
        min_sl_usage_rate=settings.min_sl_usage_rate,
        ai_enabled=settings.ai_enabled,
        preferred_model=settings.preferred_model,
        created_at=settings.created_at,
        updated_at=settings.updated_at
    )
    
    return schemas.APIResponse.success_response(data=response_data)

@router.put("/settings", response_model=schemas.APIResponse)
async def update_user_settings(
    settings_update: schemas.UserSettingsUpdate,
    current_user: schemas.UserResponse = Depends(auth.get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Update user settings
    """
    settings = db.query(models.UserSettings)\
        .filter(models.UserSettings.user_id == current_user.id)\
        .first()
    
    if not settings:
        settings = models.UserSettings(user_id=current_user.id)
        db.add(settings)
    
    # Update only provided fields
    update_data = settings_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)
    
    db.commit()
    db.refresh(settings)
    
    response_data = schemas.UserSettingsResponse(
        user_id=settings.user_id,
        max_position_size_pct=settings.max_position_size_pct,
        min_win_rate=settings.min_win_rate,
        max_drawdown_pct=settings.max_drawdown_pct,
        min_rr_ratio=settings.min_rr_ratio,
        min_sl_usage_rate=settings.min_sl_usage_rate,
        ai_enabled=settings.ai_enabled,
        preferred_model=settings.preferred_model,
        created_at=settings.created_at,
        updated_at=settings.updated_at
    )
    
    return schemas.APIResponse.success_response(
        data=response_data,
        message="Settings updated successfully"
    )