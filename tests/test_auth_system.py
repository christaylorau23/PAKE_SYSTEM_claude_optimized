"""
Comprehensive tests for the PAKE System authentication module

Tests cover:
- Password hashing and verification
- JWT token generation and validation
- User authentication flow
- Protected endpoint access
- OAuth2 token endpoint
- Error handling

Run with: pytest tests/test_auth_system.py -v --cov=src/pake_system/auth
"""

import pytest
from datetime import timedelta
from fastapi.testclient import TestClient
from jose import jwt

from src.pake_system.auth.security import (
    create_access_token,
    create_password_hash,
    decode_token,
    verify_password,
)
from src.pake_system.auth.database import authenticate_user, get_user
from src.pake_system.auth.example_app import app
from src.pake_system.core.config import get_settings

settings = get_settings()


# Fixtures


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def test_password():
    """Test password"""
    return "TestPassword123!"


@pytest.fixture
def test_hashed_password(test_password):
    """Hashed test password"""
    return create_password_hash(test_password)


# Unit Tests - Password Hashing


@pytest.mark.unit
class TestPasswordHashing:
    """Test password hashing functionality"""

    def test_create_password_hash(self, test_password):
        """Test that password hashing generates a valid hash"""
        hashed = create_password_hash(test_password)

        # Hash should be a string
        assert isinstance(hashed, str)

        # Hash should start with bcrypt identifier
        assert hashed.startswith("$2b$")

        # Hash should be different each time (due to salt)
        hashed2 = create_password_hash(test_password)
        assert hashed != hashed2

    def test_verify_password_correct(self, test_password, test_hashed_password):
        """Test password verification with correct password"""
        assert verify_password(test_password, test_hashed_password) is True

    def test_verify_password_incorrect(self, test_hashed_password):
        """Test password verification with incorrect password"""
        assert verify_password("WrongPassword", test_hashed_password) is False

    def test_verify_password_empty_string(self, test_hashed_password):
        """Test password verification with empty password"""
        assert verify_password("", test_hashed_password) is False


# Unit Tests - JWT Tokens


@pytest.mark.unit
class TestJWTTokens:
    """Test JWT token generation and validation"""

    def test_create_access_token(self):
        """Test JWT token creation"""
        data = {"sub": "testuser"}
        token = create_access_token(data)

        # Token should be a string
        assert isinstance(token, str)

        # Token should have three parts (header.payload.signature)
        assert len(token.split(".")) == 3

    def test_create_access_token_with_expiration(self):
        """Test JWT token with custom expiration"""
        data = {"sub": "testuser"}
        expires = timedelta(minutes=15)
        token = create_access_token(data, expires_delta=expires)

        # Decode and check expiration
        payload = decode_token(token)
        assert "exp" in payload
        assert "iat" in payload
        assert payload["sub"] == "testuser"

    def test_decode_token_valid(self):
        """Test decoding a valid token"""
        data = {"sub": "testuser", "role": "admin"}
        token = create_access_token(data)

        # Decode token
        payload = decode_token(token)

        # Check payload contains expected data
        assert payload["sub"] == "testuser"
        assert payload["role"] == "admin"
        assert "exp" in payload
        assert "iat" in payload

    def test_decode_token_invalid(self):
        """Test decoding an invalid token"""
        from jose import JWTError

        with pytest.raises(JWTError):
            decode_token("invalid.token.here")

    def test_decode_token_wrong_signature(self):
        """Test decoding token with wrong signature"""
        from jose import JWTError

        # Create token with different secret
        token = jwt.encode(
            {"sub": "testuser"},
            "wrong-secret",
            algorithm=settings.ALGORITHM
        )

        with pytest.raises(JWTError):
            decode_token(token)


# Integration Tests - User Authentication


@pytest.mark.integration_auth
class TestUserAuthentication:
    """Test user authentication flow"""

    @pytest.mark.asyncio
    async def test_get_user_exists(self):
        """Test retrieving an existing user"""
        user = await get_user("admin")

        assert user is not None
        assert user.username == "admin"
        assert user.email == "admin@example.com"
        assert hasattr(user, "hashed_password")

    @pytest.mark.asyncio
    async def test_get_user_not_exists(self):
        """Test retrieving a non-existent user"""
        user = await get_user("nonexistent")
        assert user is None

    @pytest.mark.asyncio
    async def test_authenticate_user_success(self):
        """Test successful user authentication"""
        user = await authenticate_user("admin", "secret")

        assert user is not None
        assert user.username == "admin"
        assert user.disabled is False

    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self):
        """Test authentication with wrong password"""
        user = await authenticate_user("admin", "wrongpassword")
        assert user is None

    @pytest.mark.asyncio
    async def test_authenticate_user_not_exists(self):
        """Test authentication with non-existent user"""
        user = await authenticate_user("nonexistent", "password")
        assert user is None


# Integration Tests - API Endpoints


@pytest.mark.integration_api
class TestAuthenticationEndpoints:
    """Test authentication API endpoints"""

    def test_root_endpoint(self, client):
        """Test public root endpoint"""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "authentication" in data

    def test_login_success(self, client):
        """Test successful login via /token endpoint"""
        response = client.post(
            "/token",
            data={
                "username": "admin",
                "password": "secret"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Check response format
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"

        # Token should be valid
        token = data["access_token"]
        payload = decode_token(token)
        assert payload["sub"] == "admin"

    def test_login_wrong_password(self, client):
        """Test login with wrong password"""
        response = client.post(
            "/token",
            data={
                "username": "admin",
                "password": "wrongpassword"
            }
        )

        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    def test_login_nonexistent_user(self, client):
        """Test login with non-existent user"""
        response = client.post(
            "/token",
            data={
                "username": "nonexistent",
                "password": "password"
            }
        )

        assert response.status_code == 401

    def test_get_current_user_authenticated(self, client):
        """Test /auth/me endpoint with valid token"""
        # First, login to get token
        login_response = client.post(
            "/token",
            data={"username": "admin", "password": "secret"}
        )
        token = login_response.json()["access_token"]

        # Access protected endpoint
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()

        # Check user data
        assert data["username"] == "admin"
        assert data["email"] == "admin@example.com"
        assert data["disabled"] is False

    def test_get_current_user_no_token(self, client):
        """Test /auth/me endpoint without token"""
        response = client.get("/auth/me")

        assert response.status_code == 401

    def test_get_current_user_invalid_token(self, client):
        """Test /auth/me endpoint with invalid token"""
        response = client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid.token.here"}
        )

        assert response.status_code == 401

    def test_protected_endpoint_authenticated(self, client):
        """Test protected endpoint with valid token"""
        # Login
        login_response = client.post(
            "/token",
            data={"username": "admin", "password": "secret"}
        )
        token = login_response.json()["access_token"]

        # Access protected endpoint
        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "admin" in data["message"]

    def test_protected_endpoint_unauthenticated(self, client):
        """Test protected endpoint without authentication"""
        response = client.get("/protected")

        assert response.status_code == 401

    def test_logout_endpoint(self, client):
        """Test logout endpoint"""
        # Login
        login_response = client.post(
            "/token",
            data={"username": "admin", "password": "secret"}
        )
        token = login_response.json()["access_token"]

        # Logout
        response = client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data


# End-to-End Tests


@pytest.mark.e2e
class TestAuthenticationE2E:
    """End-to-end authentication flow tests"""

    def test_complete_authentication_flow(self, client):
        """Test complete authentication workflow"""
        # Step 1: Access public endpoint (no auth required)
        response = client.get("/")
        assert response.status_code == 200

        # Step 2: Try to access protected endpoint (should fail)
        response = client.get("/protected")
        assert response.status_code == 401

        # Step 3: Login to get token
        response = client.post(
            "/token",
            data={"username": "admin", "password": "secret"}
        )
        assert response.status_code == 200
        token = response.json()["access_token"]

        # Step 4: Access protected endpoint with token (should succeed)
        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200

        # Step 5: Get user info
        response = client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["username"] == "admin"

        # Step 6: Logout
        response = client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200


# Performance Tests


@pytest.mark.performance
class TestAuthenticationPerformance:
    """Test authentication performance"""

    def test_password_hashing_performance(self, benchmark):
        """Benchmark password hashing"""
        result = benchmark(create_password_hash, "password123")
        assert result.startswith("$2b$")

    def test_password_verification_performance(self, benchmark, test_password, test_hashed_password):
        """Benchmark password verification"""
        result = benchmark(verify_password, test_password, test_hashed_password)
        assert result is True

    def test_token_generation_performance(self, benchmark):
        """Benchmark token generation"""
        result = benchmark(create_access_token, {"sub": "testuser"})
        assert isinstance(result, str)

    def test_token_decoding_performance(self, benchmark):
        """Benchmark token decoding"""
        token = create_access_token({"sub": "testuser"})
        result = benchmark(decode_token, token)
        assert result["sub"] == "testuser"
