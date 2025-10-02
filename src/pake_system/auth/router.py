"""
Authentication API router
Implements OAuth2 password flow endpoints
"""

from datetime import timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from src.pake_system.core.config import get_settings

from .database import authenticate_user
from .dependencies import get_current_active_user
from .models import Token, User, UserCreate
from .security import create_access_token, create_refresh_token, validate_password_strength, generate_secure_password

settings = get_settings()

# Create router for authentication endpoints
router = APIRouter(
    prefix="/auth",
    tags=["authentication"],
    responses={401: {"description": "Unauthorized"}},
)


@router.post("/token", response_model=Token)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
) -> Token:
    """
    OAuth2 compatible token login endpoint.

    This endpoint implements the OAuth2 "Password" flow, which is the
    standard way to authenticate users in FastAPI applications.

    **Authentication Flow:**
    1. Client sends username and password via form data
    2. Server validates credentials against the database
    3. Server generates a signed JWT access token
    4. Client stores token and includes it in subsequent requests

    **Request Format (application/x-www-form-urlencoded):**
    ```
    username=admin&password=secret
    ```

    **Response Format (JSON):**
    ```json
    {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type": "bearer"
    }
    ```

    **Security Notes:**
    - This endpoint must be accessed over HTTPS in production
    - Passwords are never stored in plaintext
    - Tokens expire after ACCESS_TOKEN_EXPIRE_MINUTES (configurable)
    - Failed login attempts should be rate-limited (implement separately)

    Args:
        form_data: OAuth2 form containing username and password

    Returns:
        Token: Object containing access_token and token_type

    Raises:
        HTTPException: 401 Unauthorized if credentials are invalid
    """
    # Authenticate the user
    user = await authenticate_user(form_data.username, form_data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user account is disabled
    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account"
        )

    # Create JWT access token
    # The "sub" (subject) claim contains the user identifier
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )

    # Create refresh token for token renewal
    refresh_token = create_refresh_token(data={"sub": user.username})

    # Return tokens in OAuth2 format
    return Token(access_token=access_token, token_type="bearer", refresh_token=refresh_token)


@router.get("/me", response_model=User)
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> User:
    """
    Get current authenticated user information.

    This is a protected endpoint that demonstrates how to use the
    authentication dependency to secure routes.

    **Usage:**
    ```
    GET /auth/me
    Headers:
        Authorization: Bearer <access_token>
    ```

    **Response:**
    ```json
    {
        "username": "admin",
        "email": "admin@example.com",
        "full_name": "Admin User",
        "disabled": false
    }
    ```

    Args:
        current_user: Automatically injected by FastAPI dependency

    Returns:
        User: The current authenticated user's information
    """
    return current_user


@router.post("/logout")
async def logout(
    current_user: Annotated[User, Depends(get_current_active_user)]
) -> dict[str, str]:
    """
    Logout endpoint (for completeness).

    Since JWT tokens are stateless, logout is typically handled client-side
    by removing the token from storage. However, this endpoint can be used
    for logging or triggering other cleanup actions.

    For true token revocation, you would need to:
    1. Maintain a blacklist of revoked tokens in Redis
    2. Check the blacklist in the get_current_user dependency
    3. Add tokens to the blacklist when this endpoint is called

    Args:
        current_user: Automatically injected by FastAPI dependency

    Returns:
        dict: Success message
    """
    return {"message": "Successfully logged out"}


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str
) -> Token:
    """
    Refresh access token using refresh token.

    This endpoint allows clients to obtain new access tokens without
    requiring user re-authentication.

    Args:
        refresh_token: Valid refresh token

    Returns:
        Token: New access token

    Raises:
        HTTPException: 401 Unauthorized if refresh token is invalid
    """
    from .security import decode_token, verify_token_type
    
    try:
        # Decode and validate refresh token
        payload = decode_token(refresh_token)
        
        # Verify it's a refresh token
        if not verify_token_type(refresh_token, "refresh"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        # Extract username from token
        username = payload.get("sub")
        if not username:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload"
            )
        
        # Create new access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": username},
            expires_delta=access_token_expires
        )
        
        return Token(access_token=access_token, token_type="bearer")
        
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.post("/register", response_model=User)
async def register_user(user_data: UserCreate) -> User:
    """
    Register a new user account.

    This endpoint validates password strength and creates a new user
    with secure password hashing.

    Args:
        user_data: User registration data

    Returns:
        User: Created user information (without password)

    Raises:
        HTTPException: 400 Bad Request if validation fails
    """
    from .database import create_user
    from .security import create_password_hash
    
    # Validate password strength
    is_valid, errors = validate_password_strength(user_data.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password validation failed: {', '.join(errors)}"
        )
    
    # Hash the password
    hashed_password = create_password_hash(user_data.password)
    
    # Create user
    user = await create_user(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name
    )
    
    return user


@router.get("/generate-password")
async def generate_password(length: int = 16) -> dict[str, str]:
    """
    Generate a secure random password.

    This endpoint generates cryptographically secure passwords
    that meet enterprise security standards.

    Args:
        length: Password length (minimum 12, maximum 64)

    Returns:
        dict: Generated password

    Example:
        >>> response = await generate_password(16)
        >>> response["password"]
        'K9#mP2$vL8@nQ4!'
    """
    if length < 12:
        length = 12
    elif length > 64:
        length = 64
    
    password = generate_secure_password(length)
    
    return {"password": password}


@router.post("/validate-password")
async def validate_password(password: str) -> dict[str, Any]:
    """
    Validate password strength.

    This endpoint checks if a password meets enterprise security
    requirements without storing or processing it further.

    Args:
        password: Password to validate

    Returns:
        dict: Validation result with errors if any

    Example:
        >>> response = await validate_password("WeakPass")
        >>> response["is_valid"]
        False
        >>> response["errors"]
        ['Password must be at least 12 characters long', ...]
    """
    is_valid, errors = validate_password_strength(password)
    
    return {
        "is_valid": is_valid,
        "errors": errors,
        "strength_score": max(0, 100 - len(errors) * 20)  # Simple strength scoring
    }
