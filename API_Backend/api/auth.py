"""
Authentication with robust password hashing (bcrypt safe)
"""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from api.database import get_db
from api import models

# Secret settings (use .env in production)
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

# Password hashing (bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT token
security = HTTPBearer()

# Max bcrypt password length
BCRYPT_MAX_LENGTH = 72

# --------------------------
# Password hashing & verification
# --------------------------
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a bcrypt hash"""
    return pwd_context.verify(plain_password[:BCRYPT_MAX_LENGTH], hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password safely (truncate to bcrypt max length)"""
    if not password:
        raise ValueError("Password cannot be empty")
    # truncate password to 72 bytes to avoid bcrypt error
    truncated_password = password[:BCRYPT_MAX_LENGTH]
    return pwd_context.hash(truncated_password)

# --------------------------
# JWT token handling
# --------------------------
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    """Decode a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

# --------------------------
# Dependency functions
# --------------------------
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    if credentials is None:
        return None
        
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token = credentials.credentials
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: models.User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
):
    if credentials is None:
        return None
    try:
        token = credentials.credentials
        payload = decode_access_token(token)
        if payload is None:
            return None
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        user = db.query(models.User).filter(models.User.id == user_id).first()
        return user
    except Exception:
        return None
