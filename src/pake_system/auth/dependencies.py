"""
FastAPI authentication dependencies
Provides reusable dependency functions for protecting endpoints
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError

from .models import TokenData, User
from .security import decode_token
from .database import get_user

# OAuth2 scheme for token extraction
# This tells FastAPI to extract the token from the Authorization header
# Format: Authorization: Bearer <token>
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    """
    FastAPI dependency to get the current authenticated user.

    This function:
    1. Extracts the JWT token from the Authorization header
    2. Decodes and validates the token
    3. Extracts the username from the token payload
    4. Fetches the user from the database
    5. Returns the User object

    Usage in endpoints:
        @app.get("/protected")
        async def protected_route(current_user: User = Depends(get_current_user)):
            return {"message": f"Hello {current_user.username}"}

    Args:
        token: JWT token extracted from Authorization header

    Returns:
        User: The authenticated user

    Raises:
        HTTPException: 401 Unauthorized if token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # Decode and validate the JWT token
        payload = decode_token(token)

        # Extract username from token subject (sub) claim
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception

        token_data = TokenData(username=username)

    except JWTError:
        raise credentials_exception

    # Fetch user from database (token_data.username is guaranteed not None here)
    if token_data.username is None:
        raise credentials_exception

    user = await get_user(username=token_data.username)
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    FastAPI dependency to get the current active (non-disabled) user.

    This is a stricter version of get_current_user that also checks
    if the user account is disabled.

    Usage in endpoints:
        @app.get("/protected")
        async def protected_route(user: User = Depends(get_current_active_user)):
            return {"message": f"Hello {user.username}"}

    Args:
        current_user: User obtained from get_current_user dependency

    Returns:
        User: The authenticated and active user

    Raises:
        HTTPException: 400 Bad Request if user account is disabled
    """
    if current_user.disabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    return current_user
