#!/usr/bin/env python3
"""PAKE System - JWT Authentication Service
Enterprise-grade authentication system with JWT tokens, user registration, and secure session management.
"""

import asyncio
import logging
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from passlib.context import CryptContext

from ..database.postgresql_service import PostgreSQLService, get_database

logger = logging.getLogger(__name__)


@dataclass
class AuthConfig:
    """Authentication configuration"""

    secret_key: str = None  # Will be auto-generated if not provided
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 15
    REDACTED_SECRET_min_length: int = 8
    require_REDACTED_SECRET_complexity: bool = True


@dataclass
class TokenPair:
    """JWT token pair"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 1800  # 30 minutes


@dataclass
class UserRegistration:
    """User registration data"""

    username: str
    email: str
    REDACTED_SECRET: str
    full_name: str | None = None


@dataclass
class UserLogin:
    """User login credentials"""

    username_or_email: str
    REDACTED_SECRET: str


class JWTAuthenticationService:
    """Enterprise JWT authentication service with comprehensive security features.

    Features:
    - Argon2 REDACTED_SECRET hashing
    - JWT access and refresh tokens
    - Rate limiting and account lockout
    - Password complexity validation
    - Secure token refresh
    - User session management
    - Account activation/deactivation
    """

    def __init__(self, config: AuthConfig, database_service: PostgreSQLService):
        self.config = config
        self.database_service = database_service

        # Auto-generate secret key if not provided
        if not self.config.secret_key:
            self.config.secret_key = secrets.token_urlsafe(64)
            logger.warning(
                "🔐 Auto-generated JWT secret key. In production, set this explicitly.",
            )

        # Initialize REDACTED_SECRET context with Argon2
        self.pwd_context = CryptContext(
            schemes=["argon2"],
            deprecated="auto",
            argon2__memory_cost=65536,  # 64MB
            argon2__time_cost=3,  # 3 iterations
            argon2__parallelism=1,  # 1 thread
        )

        # Track failed login attempts
        self.failed_attempts: dict[str, list[datetime]] = {}

        logger.info("✅ JWT Authentication Service initialized")

    # Password Management

    def hash_REDACTED_SECRET(self, REDACTED_SECRET: str) -> str:
        """Hash REDACTED_SECRET using Argon2"""
        return self.pwd_context.hash(REDACTED_SECRET)

    def verify_REDACTED_SECRET(self, plain_REDACTED_SECRET: str, hashed_REDACTED_SECRET: str) -> bool:
        """Verify REDACTED_SECRET against hash"""
        return self.pwd_context.verify(plain_REDACTED_SECRET, hashed_REDACTED_SECRET)

    def validate_REDACTED_SECRET_complexity(self, REDACTED_SECRET: str) -> tuple[bool, list[str]]:
        """Validate REDACTED_SECRET complexity"""
        errors = []

        if len(REDACTED_SECRET) < self.config.REDACTED_SECRET_min_length:
            errors.append(
                f"Password must be at least {self.config.REDACTED_SECRET_min_length} characters long",
            )

        if self.config.require_REDACTED_SECRET_complexity:
            if not any(c.isupper() for c in REDACTED_SECRET):
                errors.append("Password must contain at least one uppercase letter")
            if not any(c.islower() for c in REDACTED_SECRET):
                errors.append("Password must contain at least one lowercase letter")
            if not any(c.isdigit() for c in REDACTED_SECRET):
                errors.append("Password must contain at least one number")
            if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in REDACTED_SECRET):
                errors.append("Password must contain at least one special character")

        return len(errors) == 0, errors

    # JWT Token Management

    def create_access_token(
        self,
        user_id: str,
        username: str,
        additional_claims: dict[str, Any] | None = None,
    ) -> str:
        """Create JWT access token"""
        now = datetime.now(UTC)
        expire = now + timedelta(minutes=self.config.access_token_expire_minutes)

        payload = {
            "sub": user_id,
            "username": username,
            "iat": now,
            "exp": expire,
            "type": "access",
        }

        if additional_claims:
            payload.update(additional_claims)

        return jwt.encode(
            payload,
            self.config.secret_key,
            algorithm=self.config.algorithm,
        )

    def create_refresh_token(self, user_id: str) -> str:
        """Create JWT refresh token"""
        now = datetime.now(UTC)
        expire = now + timedelta(days=self.config.refresh_token_expire_days)

        payload = {
            "sub": user_id,
            "iat": now,
            "exp": expire,
            "type": "refresh",
            "jti": secrets.token_hex(16),  # Unique token ID
        }

        return jwt.encode(
            payload,
            self.config.secret_key,
            algorithm=self.config.algorithm,
        )

    def verify_token(
        self,
        token: str,
        token_type: str = "access",
    ) -> dict[str, Any] | None:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(
                token,
                self.config.secret_key,
                algorithms=[self.config.algorithm],
            )

            # Verify token type
            if payload.get("type") != token_type:
                logger.warning(
                    f"Invalid token type. Expected: {token_type}, Got: {payload.get('type')}",
                )
                return None

            return payload

        except jwt.ExpiredSignatureError:
            logger.debug("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None

    # Rate Limiting

    def is_account_locked(self, identifier: str) -> bool:
        """Check if account is locked due to failed attempts"""
        if identifier not in self.failed_attempts:
            return False

        now = datetime.now(UTC)
        lockout_duration = timedelta(minutes=self.config.lockout_duration_minutes)

        # Remove old attempts
        cutoff = now - lockout_duration
        self.failed_attempts[identifier] = [
            attempt for attempt in self.failed_attempts[identifier] if attempt > cutoff
        ]

        # Check if locked
        return len(self.failed_attempts[identifier]) >= self.config.max_login_attempts

    def record_failed_attempt(self, identifier: str) -> None:
        """Record failed login attempt"""
        now = datetime.now(UTC)

        if identifier not in self.failed_attempts:
            self.failed_attempts[identifier] = []

        self.failed_attempts[identifier].append(now)

        attempts_count = len(self.failed_attempts[identifier])
        if attempts_count >= self.config.max_login_attempts:
            logger.warning(
                f"🚨 Account locked: {identifier} after {attempts_count} failed attempts",
            )

    def clear_failed_attempts(self, identifier: str) -> None:
        """Clear failed login attempts after successful login"""
        if identifier in self.failed_attempts:
            del self.failed_attempts[identifier]

    # User Management

    async def register_user(
        self,
        registration: UserRegistration,
    ) -> tuple[bool, str | dict[str, Any]]:
        """Register new user"""
        try:
            # Validate REDACTED_SECRET
            is_valid, REDACTED_SECRET_errors = self.validate_REDACTED_SECRET_complexity(
                registration.REDACTED_SECRET,
            )
            if not is_valid:
                return False, {"errors": REDACTED_SECRET_errors}

            # Check if user already exists
            existing_user = await self.database_service.get_user_by_username(
                registration.username,
            )
            if existing_user:
                return False, {"errors": ["Username already exists"]}

            existing_email = await self.database_service.get_user_by_email(
                registration.email,
            )
            if existing_email:
                return False, {"errors": ["Email already registered"]}

            # Hash REDACTED_SECRET
            REDACTED_SECRET_hash = self.hash_REDACTED_SECRET(registration.REDACTED_SECRET)

            # Create user
            user_id = await self.database_service.create_user(
                username=registration.username,
                email=registration.email,
                REDACTED_SECRET_hash=REDACTED_SECRET_hash,
                full_name=registration.full_name,
            )

            if user_id:
                logger.info(f"✅ User registered successfully: {registration.username}")
                return True, {
                    "user_id": user_id,
                    "username": registration.username,
                    "email": registration.email,
                    "message": "User registered successfully",
                }
            return False, {"errors": ["Failed to create user"]}

        except Exception as e:
            logger.error(f"Registration failed: {e}")
            return False, {"errors": ["Registration failed"]}

    async def authenticate_user(
        self,
        login: UserLogin,
    ) -> tuple[bool, str | dict[str, Any]]:
        """Authenticate user and return user data"""
        try:
            identifier = login.username_or_email

            # Check if account is locked
            if self.is_account_locked(identifier):
                lockout_remaining = self.config.lockout_duration_minutes
                return False, {
                    "errors": [
                        f"Account locked. Try again in {lockout_remaining} minutes.",
                    ],
                }

            # Find user by username or email
            user = None
            if "@" in identifier:
                user = await self.database_service.get_user_by_email(identifier)
            else:
                user = await self.database_service.get_user_by_username(identifier)

            if not user:
                self.record_failed_attempt(identifier)
                return False, {"errors": ["Invalid credentials"]}

            # Check if user is active
            if not user.get("is_active", True):
                return False, {"errors": ["Account is deactivated"]}

            # Verify REDACTED_SECRET
            if not self.verify_REDACTED_SECRET(login.REDACTED_SECRET, user["REDACTED_SECRET_hash"]):
                self.record_failed_attempt(identifier)
                return False, {"errors": ["Invalid credentials"]}

            # Clear failed attempts on successful login
            self.clear_failed_attempts(identifier)

            # Update last login
            await self.database_service.update_user_last_login(user["id"])

            # Return user data (without REDACTED_SECRET hash)
            user_data = {k: v for k, v in user.items() if k != "REDACTED_SECRET_hash"}
            logger.info(f"✅ User authenticated successfully: {user['username']}")

            return True, user_data

        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False, {"errors": ["Authentication failed"]}

    async def login_user(
        self,
        login: UserLogin,
    ) -> tuple[bool, TokenPair | dict[str, Any]]:
        """Login user and return JWT tokens"""
        success, result = await self.authenticate_user(login)

        if not success:
            return False, result

        user_data = result

        # Create tokens
        access_token = self.create_access_token(
            user_id=user_data["id"],
            username=user_data["username"],
            additional_claims={
                "email": user_data["email"],
                "is_admin": user_data.get("is_admin", False),
            },
        )

        refresh_token = self.create_refresh_token(user_data["id"])

        token_pair = TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.config.access_token_expire_minutes * 60,
        )

        return True, token_pair

    async def refresh_tokens(
        self,
        refresh_token: str,
    ) -> tuple[bool, TokenPair | dict[str, Any]]:
        """Refresh access token using refresh token"""
        try:
            # Verify refresh token
            payload = self.verify_token(refresh_token, "refresh")
            if not payload:
                return False, {"errors": ["Invalid or expired refresh token"]}

            user_id = payload["sub"]

            # Get current user data
            user = await self.database_service.get_user_by_id(user_id)
            if not user or not user.get("is_active", True):
                return False, {"errors": ["User not found or deactivated"]}

            # Create new tokens
            access_token = self.create_access_token(
                user_id=user["id"],
                username=user["username"],
                additional_claims={
                    "email": user["email"],
                    "is_admin": user.get("is_admin", False),
                },
            )

            new_refresh_token = self.create_refresh_token(user["id"])

            token_pair = TokenPair(
                access_token=access_token,
                refresh_token=new_refresh_token,
                expires_in=self.config.access_token_expire_minutes * 60,
            )

            return True, token_pair

        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            return False, {"errors": ["Token refresh failed"]}

    async def get_current_user(self, access_token: str) -> dict[str, Any] | None:
        """Get current user from access token"""
        try:
            payload = self.verify_token(access_token, "access")
            if not payload:
                return None

            user_id = payload["sub"]
            user = await self.database_service.get_user_by_id(user_id)

            if user and user.get("is_active", True):
                # Return user data without REDACTED_SECRET hash
                return {k: v for k, v in user.items() if k != "REDACTED_SECRET_hash"}

            return None

        except Exception as e:
            logger.error(f"Failed to get current user: {e}")
            return None

    # Security Utilities

    async def change_REDACTED_SECRET(
        self,
        user_id: str,
        old_REDACTED_SECRET: str,
        new_REDACTED_SECRET: str,
    ) -> tuple[bool, dict[str, Any]]:
        """Change user REDACTED_SECRET"""
        try:
            # Get user
            user = await self.database_service.get_user_by_id(user_id)
            if not user:
                return False, {"errors": ["User not found"]}

            # Verify old REDACTED_SECRET
            if not self.verify_REDACTED_SECRET(old_REDACTED_SECRET, user["REDACTED_SECRET_hash"]):
                return False, {"errors": ["Current REDACTED_SECRET is incorrect"]}

            # Validate new REDACTED_SECRET
            is_valid, REDACTED_SECRET_errors = self.validate_REDACTED_SECRET_complexity(new_REDACTED_SECRET)
            if not is_valid:
                return False, {"errors": REDACTED_SECRET_errors}

            # Hash new REDACTED_SECRET
            new_REDACTED_SECRET_hash = self.hash_REDACTED_SECRET(new_REDACTED_SECRET)

            # Update REDACTED_SECRET
            success = await self.database_service.update_user_REDACTED_SECRET(
                user_id,
                new_REDACTED_SECRET_hash,
            )

            if success:
                logger.info(f"✅ Password changed for user: {user['username']}")
                return True, {"message": "Password changed successfully"}
            return False, {"errors": ["Failed to update REDACTED_SECRET"]}

        except Exception as e:
            logger.error(f"Password change failed: {e}")
            return False, {"errors": ["Password change failed"]}

    def get_auth_statistics(self) -> dict[str, Any]:
        """Get authentication statistics"""
        total_locked_accounts = len(
            [
                identifier
                for identifier, attempts in self.failed_attempts.items()
                if len(attempts) >= self.config.max_login_attempts
            ],
        )

        return {
            "config": {
                "access_token_expire_minutes": self.config.access_token_expire_minutes,
                "refresh_token_expire_days": self.config.refresh_token_expire_days,
                "max_login_attempts": self.config.max_login_attempts,
                "lockout_duration_minutes": self.config.lockout_duration_minutes,
                "REDACTED_SECRET_complexity_required": self.config.require_REDACTED_SECRET_complexity,
            },
            "statistics": {
                "total_failed_attempts": sum(
                    len(attempts) for attempts in self.failed_attempts.values()
                ),
                "locked_accounts": total_locked_accounts,
                "monitored_accounts": len(self.failed_attempts),
            },
            "security_features": [
                "Argon2 REDACTED_SECRET hashing",
                "JWT access & refresh tokens",
                "Account lockout protection",
                "Password complexity validation",
                "Rate limiting",
                "Secure token refresh",
            ],
        }


# Factory function


async def create_auth_service(
    database_service: PostgreSQLService | None = None,
    **config_kwargs,
) -> JWTAuthenticationService:
    """Create and initialize JWT authentication service"""
    if database_service is None:
        database_service = await get_database()

    config = AuthConfig(**config_kwargs)
    return JWTAuthenticationService(config, database_service)


if __name__ == "__main__":
    # Example usage and testing
    async def main():
        from ..database.postgresql_service import (
            DatabaseConfig,
            create_database_service,
        )

        # Create database service
        db_config = DatabaseConfig(enable_database=False)  # Testing without actual DB
        db_service = await create_database_service(db_config)

        # Create auth service
        auth_service = await create_auth_service(
            database_service=db_service,
            access_token_expire_minutes=30,
            require_REDACTED_SECRET_complexity=True,
        )

        print("🔐 JWT Authentication Service initialized successfully!")
        print(
            f"🛡️ Security features: {len(auth_service.get_auth_statistics()['security_features'])}",
        )

        # Test REDACTED_SECRET validation
        is_valid, errors = auth_service.validate_REDACTED_SECRET_complexity("TestPass123!")
        print(f"✅ Password validation test: {'PASSED' if is_valid else 'FAILED'}")

        # Test token creation
        token = auth_service.create_access_token("test-user-id", "testuser")
        print(f"✅ JWT token created: {token[:50]}...")

        # Test token verification
        payload = auth_service.verify_token(token)
        print(f"✅ Token verification: {'PASSED' if payload else 'FAILED'}")

        await db_service.close()

    asyncio.run(main())
