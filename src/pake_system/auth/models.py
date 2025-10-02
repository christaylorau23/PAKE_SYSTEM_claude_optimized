"""Pydantic models for authentication
Defines the data structures for users, tokens, and authentication
"""

from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    """OAuth2 token response model.

    Returned after successful authentication at the /token endpoint.
    """

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(
        default="bearer", description="Token type (always 'bearer')"
    )
    refresh_token: Optional[str] = Field(
        None, description="JWT refresh token for token renewal"
    )


class TokenData(BaseModel):
    """Decoded token payload.

    Contains the user identifier extracted from a validated JWT token.
    """

    username: Optional[str] = None


class User(BaseModel):
    """User model for API responses.

    This is the public-facing user model that excludes sensitive data.
    """

    username: str = Field(
        ..., description="Unique username", min_length=3, max_length=50
    )
    email: Optional[EmailStr] = Field(None, description="User email address")
    full_name: Optional[str] = Field(None, description="User's full name")
    disabled: Optional[bool] = Field(
        default=False, description="Whether the user account is disabled"
    )

    class Config:
        """Pydantic configuration"""

        json_schema_extra = {
            "example": {
                "username": "johndoe",
                "email": "johndoe@example.com",
                "full_name": "John Doe",
                "disabled": False,
            }
        }


class UserInDB(User):
    """User model with password hash for database storage.

    This model extends User with the hashed_password field.
    NEVER return this model in API responses - it contains sensitive data.
    """

    hashed_password: str = Field(..., description="Bcrypt hashed password")


class UserCreate(BaseModel):
    """User creation request model.

    Used when registering new users. The password is validated
    and hashed before storage.
    """

    username: str = Field(
        ..., description="Unique username", min_length=3, max_length=50
    )
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password", min_length=8)
    full_name: Optional[str] = Field(None, description="User's full name")

    class Config:
        """Pydantic configuration"""

        json_schema_extra = {
            "example": {
                "username": "johndoe",
                "email": "johndoe@example.com",
                "password": "SecurePassword123!",
                "full_name": "John Doe",
            }
        }
