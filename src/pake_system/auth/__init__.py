"""Authentication module for PAKE System
Enterprise-grade authentication with FastAPI OAuth2 integration
"""

from .dependencies import get_current_active_user, get_current_user
from .models import Token, TokenData, User, UserInDB
from .security import (
    create_access_token,
    create_password_hash,
    verify_password,
)

__all__ = [
    "create_access_token",
    "create_password_hash",
    "verify_password",
    "get_current_user",
    "get_current_active_user",
    "User",
    "UserInDB",
    "Token",
    "TokenData",
]
