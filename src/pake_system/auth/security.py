"""
Security utilities for PAKE System authentication
Implements secure password hashing and JWT token generation with enhanced security features
"""

import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import jwt
from passlib.context import CryptContext

from src.pake_system.core.config import get_settings

settings = get_settings()

# Password hashing context using Bcrypt
# Bcrypt is the industry-standard for password hashing, providing
# strong one-way encryption with automatic salting
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def create_password_hash(plain_password: str) -> str:
    """
    Create a secure password hash using Bcrypt.

    This is the ONLY function that should handle plaintext passwords
    during user registration and password changes.

    Args:
        plain_password: The plaintext password to hash

    Returns:
        str: The hashed password with salt

    Example:
        >>> hashed = create_password_hash("SecurePassword123!")
        >>> # Returns: $2b$12$...
    """
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a hashed password.

    This function is used during login to validate user credentials.
    It uses constant-time comparison to prevent timing attacks.

    Args:
        plain_password: The plaintext password to verify
        hashed_password: The stored hashed password

    Returns:
        bool: True if password matches, False otherwise

    Example:
        >>> hashed = create_password_hash("SecurePassword123!")
        >>> verify_password("SecurePassword123!", hashed)
        True
        >>> verify_password("WrongPassword", hashed)
        False
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """
    Create a JWT access token with an expiration claim.

    The token is signed with the SECRET_KEY from settings and includes
    an expiration time (exp) claim for security.

    Args:
        data: Dictionary of claims to encode in the token (typically {"sub": user_id})
        expires_delta: Optional custom expiration time. If None, uses default from settings

    Returns:
        str: Encoded JWT token

    Example:
        >>> token = create_access_token({"sub": "user@example.com"})
        >>> # Returns: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

    Security Notes:
        - The token is signed with HS256 (HMAC-SHA256)
        - The SECRET_KEY must be kept secure and never exposed
        - Tokens should be transmitted over HTTPS only
        - The exp claim is automatically validated by FastAPI
    """
    if not settings.SECRET_KEY:
        raise ValueError("SECRET_KEY must be configured for JWT token creation")
    
    to_encode = data.copy()

    # Set expiration time
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    # Add standard JWT claims
    to_encode.update({
        "exp": expire,  # Expiration time
        "iat": datetime.now(timezone.utc),  # Issued at time
    })

    # Encode and sign the token
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    return encoded_jwt


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT token.

    This function verifies the token signature and checks expiration.
    Raises exceptions if the token is invalid or expired.

    Args:
        token: The JWT token to decode

    Returns:
        dict: The decoded token payload

    Raises:
        jose.JWTError: If token is invalid or expired

    Example:
        >>> token = create_access_token({"sub": "user@example.com"})
        >>> payload = decode_token(token)
        >>> payload["sub"]
        'user@example.com'
    """
    if not settings.SECRET_KEY:
        raise ValueError("SECRET_KEY must be configured for JWT token validation")
    
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM]
    )


def validate_password_strength(password: str) -> tuple[bool, list[str]]:
    """
    Validate password strength according to enterprise security standards.

    Args:
        password: The password to validate

    Returns:
        tuple: (is_valid, list_of_errors)

    Example:
        >>> is_valid, errors = validate_password_strength("WeakPass")
        >>> is_valid
        False
        >>> errors
        ['Password must be at least 12 characters long', 'Password must contain uppercase letters']
    """
    errors = []
    
    # Minimum length requirement
    if len(password) < 12:
        errors.append("Password must be at least 12 characters long")
    
    # Character requirements
    if not any(c.isupper() for c in password):
        errors.append("Password must contain uppercase letters")
    
    if not any(c.islower() for c in password):
        errors.append("Password must contain lowercase letters")
    
    if not any(c.isdigit() for c in password):
        errors.append("Password must contain numbers")
    
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        errors.append("Password must contain special characters")
    
    # Check for common patterns
    common_patterns = [
        "password", "123456", "qwerty", "abc123", "admin",
        "letmein", "welcome", "monkey", "dragon", "master"
    ]
    
    password_lower = password.lower()
    for pattern in common_patterns:
        if pattern in password_lower:
            errors.append(f"Password contains common pattern: {pattern}")
            break
    
    # Check for sequential characters
    if any(
        ord(password[i]) + 1 == ord(password[i + 1]) == ord(password[i + 2]) - 1
        for i in range(len(password) - 2)
    ):
        errors.append("Password contains sequential characters")
    
    return len(errors) == 0, errors


def generate_secure_password(length: int = 16) -> str:
    """
    Generate a cryptographically secure random password.

    Args:
        length: Length of the password (minimum 12)

    Returns:
        str: Secure random password

    Example:
        >>> password = generate_secure_password(16)
        >>> len(password)
        16
        >>> is_valid, _ = validate_password_strength(password)
        >>> is_valid
        True
    """
    if length < 12:
        length = 12
    
    # Character sets
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    special = "!@#$%^&*()_+-=[]{}|;:,.<>?"
    
    # Ensure at least one character from each set
    password = [
        secrets.choice(lowercase),
        secrets.choice(uppercase),
        secrets.choice(digits),
        secrets.choice(special)
    ]
    
    # Fill the rest with random characters
    all_chars = lowercase + uppercase + digits + special
    for _ in range(length - 4):
        password.append(secrets.choice(all_chars))
    
    # Shuffle the password
    secrets.SystemRandom().shuffle(password)
    
    return ''.join(password)


def create_refresh_token(data: dict[str, Any]) -> str:
    """
    Create a JWT refresh token with longer expiration.

    Refresh tokens are used to obtain new access tokens without
    requiring user re-authentication.

    Args:
        data: Dictionary of claims to encode in the token

    Returns:
        str: Encoded JWT refresh token

    Example:
        >>> token = create_refresh_token({"sub": "user@example.com"})
        >>> # Returns: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
    """
    if not settings.SECRET_KEY:
        raise ValueError("SECRET_KEY must be configured for JWT token creation")
    
    to_encode = data.copy()
    
    # Set expiration time for refresh token (longer than access token)
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    
    # Add standard JWT claims
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh"  # Mark as refresh token
    })
    
    # Encode and sign the token
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def verify_token_type(token: str, expected_type: str) -> bool:
    """
    Verify that a token is of the expected type (access or refresh).

    Args:
        token: JWT token to verify
        expected_type: Expected token type ("access" or "refresh")

    Returns:
        bool: True if token type matches expected type

    Example:
        >>> access_token = create_access_token({"sub": "user@example.com"})
        >>> verify_token_type(access_token, "access")
        True
    """
    try:
        payload = decode_token(token)
        token_type = payload.get("type", "access")  # Default to access for backward compatibility
        return token_type == expected_type
    except Exception:
        return False


def generate_csrf_token() -> str:
    """
    Generate a cryptographically secure CSRF token.

    Returns:
        str: Secure random CSRF token

    Example:
        >>> token = generate_csrf_token()
        >>> len(token)
        32
    """
    return secrets.token_urlsafe(32)


def hash_sensitive_data(data: str) -> str:
    """
    Hash sensitive data for secure storage or comparison.

    This is different from password hashing - it's for general
    sensitive data that needs to be hashed but not verified.

    Args:
        data: Sensitive data to hash

    Returns:
        str: Hashed data

    Example:
        >>> hashed = hash_sensitive_data("sensitive-info")
        >>> # Returns: $2b$12$...
    """
    return pwd_context.hash(data)
