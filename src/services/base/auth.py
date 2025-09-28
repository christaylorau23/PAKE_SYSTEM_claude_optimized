"""
Enterprise Authentication and Security
Task T039-T045 - Phase 18 Production System Integration

Production-grade JWT authentication, security middleware, and
enterprise security patterns.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from .database import get_db
from .models import Base
from sqlalchemy import String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID

# Security configuration with enterprise secrets management
from ..secrets_manager.enterprise_secrets_manager import get_jwt_secret, get_api_key

# Initialize secrets manager
import asyncio
try:
    SECRET_KEY = asyncio.run(get_jwt_secret())
except Exception as e:
    raise ValueError(
        f"Failed to initialize JWT secret: {e}. "
        "Please configure Azure Key Vault or SECRET_KEY environment variable."
    )
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token scheme
security = HTTPBearer()


class User(Base):
    """User model for authentication"""
    __tablename__ = "users"

    # Primary key
    user_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), 
        primary_key=True, 
        default=uuid4
    )
    
    # User information
    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_REDACTED_SECRET: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # User status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc)
    )
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Relationships
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")


class UserSession(Base):
    """User session tracking"""
    __tablename__ = "user_sessions"

    # Primary key
    session_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), 
        primary_key=True, 
        default=uuid4
    )
    
    # Foreign key to user
    user_id: Mapped[UUID] = mapped_column(
        PostgresUUID(as_uuid=True), 
        ForeignKey("users.user_id"),
        nullable=False
    )
    
    # Session information
    refresh_token: Mapped[str] = mapped_column(String(500), nullable=False)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500))
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    
    # Session status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc)
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # Relationships
    user = relationship("User", back_populates="sessions")


class AuthService:
    """Enterprise authentication service"""
    
    @staticmethod
    def verify_REDACTED_SECRET(plain_REDACTED_SECRET: str, hashed_REDACTED_SECRET: str) -> bool:
        """Verify a REDACTED_SECRET against its hash"""
        return pwd_context.verify(plain_REDACTED_SECRET, hashed_REDACTED_SECRET)
    
    @staticmethod
    def get_REDACTED_SECRET_hash(REDACTED_SECRET: str) -> str:
        """Hash a REDACTED_SECRET"""
        return pwd_context.hash(REDACTED_SECRET)
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(data: Dict[str, Any]) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    token = credentials.credentials
    payload = AuthService.verify_token(token)
    
    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


class SecurityMiddleware:
    """Enterprise security middleware"""
    
    @staticmethod
    async def validate_api_key(api_key: str) -> bool:
        """Validate API key with enterprise secrets management"""
        try:
            expected_api_key = await get_api_key()
            # In production, this would validate against a database of API keys
            # For now, we'll use a simple check with proper secrets management
            return api_key == expected_api_key
        except Exception as e:
            logger.error(f"Failed to validate API key: {e}")
            return False
    
    @staticmethod
    async def check_rate_limit(user_id: str, endpoint: str) -> bool:
        """Check rate limiting (placeholder for enterprise implementation)"""
        # In production, this would check against Redis or similar
        # For now, we'll allow all requests
        return True
    
    @staticmethod
    async def log_security_event(event_type: str, user_id: Optional[str], details: Dict[str, Any]):
        """Log security events"""
        # In production, this would log to a security monitoring system
        print(f"Security Event: {event_type} - User: {user_id} - Details: {details}")
