"""
Comprehensive Unit Tests for PAKE System Authentication
Tests all authentication components in complete isolation using mocks
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone
from jose import JWTError

from src.pake_system.auth.security import (
    create_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    validate_password_strength,
    generate_secure_password,
    verify_token_type,
    generate_csrf_token,
    hash_sensitive_data
)
from src.pake_system.auth.models import User, UserInDB, Token, TokenData, UserCreate
from src.pake_system.auth.dependencies import get_current_user, get_current_active_user
from src.pake_system.auth.database import get_user, authenticate_user, create_user


class TestPasswordSecurity:
    """Test password hashing and validation security functions"""

    def test_create_password_hash_returns_bcrypt_hash(self):
        """Test that password hashing creates a proper bcrypt hash"""
        # Arrange
        password = "SecurePassword123!"
        
        # Act
        hashed = create_password_hash(password)
        
        # Assert
        assert hashed.startswith("$2b$")
        assert len(hashed) > 50  # Bcrypt hashes are typically 60+ characters
        assert hashed != password  # Ensure password is not stored in plaintext

    def test_verify_password_correct_password_returns_true(self):
        """Test that correct password verification returns True"""
        # Arrange
        password = "SecurePassword123!"
        hashed = create_password_hash(password)
        
        # Act
        result = verify_password(password, hashed)
        
        # Assert
        assert result is True

    def test_verify_password_incorrect_password_returns_false(self):
        """Test that incorrect password verification returns False"""
        # Arrange
        correct_password = "SecurePassword123!"
        wrong_password = "WrongPassword456!"
        hashed = create_password_hash(correct_password)
        
        # Act
        result = verify_password(wrong_password, hashed)
        
        # Assert
        assert result is False

    def test_password_hashing_is_deterministic(self):
        """Test that same password produces different hashes (due to salt)"""
        # Arrange
        password = "SecurePassword123!"
        
        # Act
        hash1 = create_password_hash(password)
        hash2 = create_password_hash(password)
        
        # Assert
        assert hash1 != hash2  # Different salts should produce different hashes
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True

    def test_verify_password_timing_attack_resistance(self):
        """Test that password verification is resistant to timing attacks"""
        import time
        
        # Arrange
        password = "SecurePassword123!"
        hashed = create_password_hash(password)
        wrong_password = "WrongPassword456!"
        
        # Act & Assert
        # Both operations should take similar time (within reasonable bounds)
        start_time = time.time()
        verify_password(password, hashed)
        correct_time = time.time() - start_time
        
        start_time = time.time()
        verify_password(wrong_password, hashed)
        wrong_time = time.time() - start_time
        
        # Times should be similar (within 10ms tolerance)
        assert abs(correct_time - wrong_time) < 0.01


class TestPasswordStrengthValidation:
    """Test password strength validation functionality"""

    def test_validate_password_strength_strong_password_passes(self):
        """Test that a strong password passes validation"""
        # Arrange
        strong_password = "MySecurePassword123!"
        
        # Act
        is_valid, errors = validate_password_strength(strong_password)
        
        # Assert
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_password_strength_weak_password_fails(self):
        """Test that a weak password fails validation"""
        # Arrange
        weak_password = "weak"
        
        # Act
        is_valid, errors = validate_password_strength(weak_password)
        
        # Assert
        assert is_valid is False
        assert len(errors) > 0
        assert any("at least 12 characters" in error for error in errors)

    def test_validate_password_strength_missing_requirements(self):
        """Test validation catches missing character requirements"""
        # Arrange
        password_no_upper = "mypassword123!"
        password_no_lower = "MYPASSWORD123!"
        password_no_number = "MyPassword!"
        password_no_special = "MyPassword123"
        
        # Act & Assert
        for password in [password_no_upper, password_no_lower, password_no_number, password_no_special]:
            is_valid, errors = validate_password_strength(password)
            assert is_valid is False
            assert len(errors) > 0

    def test_validate_password_strength_common_patterns_rejected(self):
        """Test that common weak patterns are rejected"""
        # Arrange
        common_passwords = [
            "password123",
            "admin123",
            "qwerty123",
            "abc123456"
        ]
        
        # Act & Assert
        for password in common_passwords:
            is_valid, errors = validate_password_strength(password)
            assert is_valid is False
            assert any("common pattern" in error for error in errors)

    def test_validate_password_strength_sequential_characters_rejected(self):
        """Test that sequential characters are rejected"""
        # Arrange
        sequential_password = "abc123def456"
        
        # Act
        is_valid, errors = validate_password_strength(sequential_password)
        
        # Assert
        assert is_valid is False
        assert any("sequential characters" in error for error in errors)


class TestSecurePasswordGeneration:
    """Test secure password generation functionality"""

    def test_generate_secure_password_default_length(self):
        """Test that generated password meets default length requirement"""
        # Act
        password = generate_secure_password()
        
        # Assert
        assert len(password) >= 12
        assert len(password) <= 16  # Default length

    def test_generate_secure_password_custom_length(self):
        """Test that generated password meets custom length requirement"""
        # Arrange
        custom_length = 20
        
        # Act
        password = generate_secure_password(custom_length)
        
        # Assert
        assert len(password) == custom_length

    def test_generate_secure_password_minimum_length_enforced(self):
        """Test that minimum length is enforced even if requested shorter"""
        # Act
        password = generate_secure_password(8)  # Request shorter than minimum
        
        # Assert
        assert len(password) >= 12  # Minimum enforced

    def test_generate_secure_password_meets_strength_requirements(self):
        """Test that generated password meets all strength requirements"""
        # Act
        password = generate_secure_password()
        
        # Assert
        is_valid, errors = validate_password_strength(password)
        assert is_valid is True
        assert len(errors) == 0

    def test_generate_secure_password_uniqueness(self):
        """Test that generated passwords are unique"""
        # Act
        passwords = [generate_secure_password() for _ in range(10)]
        
        # Assert
        assert len(set(passwords)) == len(passwords)  # All unique


class TestJWTTokenSecurity:
    """Test JWT token creation and validation"""

    @patch('src.pake_system.auth.security.settings')
    def test_create_access_token_success(self, mock_settings):
        """Test successful access token creation"""
        # Arrange
        mock_settings.SECRET_KEY = "test-secret-key"
        mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
        mock_settings.ALGORITHM = "HS256"
        data = {"sub": "testuser"}
        
        # Act
        token = create_access_token(data)
        
        # Assert
        assert isinstance(token, str)
        assert len(token) > 100  # JWT tokens are typically long
        assert "." in token  # JWT format has dots

    @patch('src.pake_system.auth.security.settings')
    def test_create_access_token_with_expiration(self, mock_settings):
        """Test access token creation with custom expiration"""
        # Arrange
        mock_settings.SECRET_KEY = "test-secret-key"
        mock_settings.ALGORITHM = "HS256"
        data = {"sub": "testuser"}
        expires_delta = timedelta(minutes=60)
        
        # Act
        token = create_access_token(data, expires_delta)
        
        # Assert
        assert isinstance(token, str)
        assert len(token) > 100

    @patch('src.pake_system.auth.security.settings')
    def test_create_access_token_no_secret_key_raises_error(self, mock_settings):
        """Test that missing secret key raises error"""
        # Arrange
        mock_settings.SECRET_KEY = None
        data = {"sub": "testuser"}
        
        # Act & Assert
        with pytest.raises(ValueError, match="SECRET_KEY must be configured"):
            create_access_token(data)

    @patch('src.pake_system.auth.security.settings')
    def test_create_refresh_token_success(self, mock_settings):
        """Test successful refresh token creation"""
        # Arrange
        mock_settings.SECRET_KEY = "test-secret-key"
        mock_settings.REFRESH_TOKEN_EXPIRE_DAYS = 7
        mock_settings.ALGORITHM = "HS256"
        data = {"sub": "testuser"}
        
        # Act
        token = create_refresh_token(data)
        
        # Assert
        assert isinstance(token, str)
        assert len(token) > 100

    @patch('src.pake_system.auth.security.settings')
    def test_decode_token_success(self, mock_settings):
        """Test successful token decoding"""
        # Arrange
        mock_settings.SECRET_KEY = "test-secret-key"
        mock_settings.ALGORITHM = "HS256"
        data = {"sub": "testuser"}
        token = create_access_token(data)
        
        # Act
        payload = decode_token(token)
        
        # Assert
        assert payload["sub"] == "testuser"
        assert "exp" in payload
        assert "iat" in payload

    @patch('src.pake_system.auth.security.settings')
    def test_decode_token_invalid_token_raises_error(self, mock_settings):
        """Test that invalid token raises JWTError"""
        # Arrange
        mock_settings.SECRET_KEY = "test-secret-key"
        mock_settings.ALGORITHM = "HS256"
        invalid_token = "invalid.token.here"
        
        # Act & Assert
        with pytest.raises(JWTError):
            decode_token(invalid_token)

    @patch('src.pake_system.auth.security.settings')
    def test_decode_token_no_secret_key_raises_error(self, mock_settings):
        """Test that missing secret key raises error"""
        # Arrange
        mock_settings.SECRET_KEY = None
        token = "some.token.here"
        
        # Act & Assert
        with pytest.raises(ValueError, match="SECRET_KEY must be configured"):
            decode_token(token)

    @patch('src.pake_system.auth.security.settings')
    def test_verify_token_type_access_token(self, mock_settings):
        """Test token type verification for access token"""
        # Arrange
        mock_settings.SECRET_KEY = "test-secret-key"
        mock_settings.ALGORITHM = "HS256"
        data = {"sub": "testuser"}
        token = create_access_token(data)
        
        # Act
        is_access = verify_token_type(token, "access")
        is_refresh = verify_token_type(token, "refresh")
        
        # Assert
        assert is_access is True
        assert is_refresh is False

    @patch('src.pake_system.auth.security.settings')
    def test_verify_token_type_refresh_token(self, mock_settings):
        """Test token type verification for refresh token"""
        # Arrange
        mock_settings.SECRET_KEY = "test-secret-key"
        mock_settings.ALGORITHM = "HS256"
        data = {"sub": "testuser"}
        token = create_refresh_token(data)
        
        # Act
        is_access = verify_token_type(token, "access")
        is_refresh = verify_token_type(token, "refresh")
        
        # Assert
        assert is_access is False
        assert is_refresh is True

    def test_verify_token_type_invalid_token_returns_false(self):
        """Test that invalid token returns False"""
        # Arrange
        invalid_token = "invalid.token.here"
        
        # Act
        result = verify_token_type(invalid_token, "access")
        
        # Assert
        assert result is False


class TestCSRFTokenGeneration:
    """Test CSRF token generation"""

    def test_generate_csrf_token_returns_string(self):
        """Test that CSRF token generation returns a string"""
        # Act
        token = generate_csrf_token()
        
        # Assert
        assert isinstance(token, str)
        assert len(token) > 0

    def test_generate_csrf_token_uniqueness(self):
        """Test that generated CSRF tokens are unique"""
        # Act
        tokens = [generate_csrf_token() for _ in range(10)]
        
        # Assert
        assert len(set(tokens)) == len(tokens)  # All unique

    def test_generate_csrf_token_length(self):
        """Test that CSRF token has expected length"""
        # Act
        token = generate_csrf_token()
        
        # Assert
        assert len(token) == 43  # Base64 encoded 32 bytes = 43 characters


class TestSensitiveDataHashing:
    """Test sensitive data hashing functionality"""

    def test_hash_sensitive_data_returns_hash(self):
        """Test that sensitive data hashing returns a hash"""
        # Arrange
        sensitive_data = "sensitive-information"
        
        # Act
        hashed = hash_sensitive_data(sensitive_data)
        
        # Assert
        assert isinstance(hashed, str)
        assert hashed.startswith("$2b$")
        assert hashed != sensitive_data

    def test_hash_sensitive_data_deterministic(self):
        """Test that same data produces different hashes (due to salt)"""
        # Arrange
        data = "sensitive-information"
        
        # Act
        hash1 = hash_sensitive_data(data)
        hash2 = hash_sensitive_data(data)
        
        # Assert
        assert hash1 != hash2  # Different salts should produce different hashes


class TestAuthenticationDependencies:
    """Test FastAPI authentication dependencies"""

    @pytest.mark.asyncio
    async def test_get_current_user_valid_token(self, mocker):
        """Test get_current_user with valid token"""
        # Arrange
        mock_decode_token = mocker.patch('src.pake_system.auth.dependencies.decode_token')
        mock_get_user = mocker.patch('src.pake_system.auth.dependencies.get_user')
        
        mock_decode_token.return_value = {"sub": "testuser"}
        mock_get_user.return_value = User(username="testuser", email="test@example.com")
        
        # Act
        user = await get_current_user("valid.token.here")
        
        # Assert
        assert user.username == "testuser"
        mock_decode_token.assert_called_once_with("valid.token.here")
        mock_get_user.assert_called_once_with(username="testuser")

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token_raises_exception(self, mocker):
        """Test get_current_user with invalid token raises HTTPException"""
        # Arrange
        mock_decode_token = mocker.patch('src.pake_system.auth.dependencies.decode_token')
        mock_decode_token.side_effect = JWTError("Invalid token")
        
        # Act & Assert
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user("invalid.token.here")
        
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_no_subject_raises_exception(self, mocker):
        """Test get_current_user with token missing subject raises HTTPException"""
        # Arrange
        mock_decode_token = mocker.patch('src.pake_system.auth.dependencies.decode_token')
        mock_decode_token.return_value = {}  # No 'sub' key
        
        # Act & Assert
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user("token.without.subject")
        
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_not_found_raises_exception(self, mocker):
        """Test get_current_user with user not found raises HTTPException"""
        # Arrange
        mock_decode_token = mocker.patch('src.pake_system.auth.dependencies.decode_token')
        mock_get_user = mocker.patch('src.pake_system.auth.dependencies.get_user')
        
        mock_decode_token.return_value = {"sub": "nonexistent"}
        mock_get_user.return_value = None
        
        # Act & Assert
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user("valid.token.here")
        
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_active_user_active_user(self, mocker):
        """Test get_current_active_user with active user"""
        # Arrange
        active_user = User(username="testuser", email="test@example.com", disabled=False)
        mock_get_current_user = mocker.patch('src.pake_system.auth.dependencies.get_current_user')
        mock_get_current_user.return_value = active_user
        
        # Act
        user = await get_current_active_user(active_user)
        
        # Assert
        assert user.username == "testuser"
        assert user.disabled is False

    @pytest.mark.asyncio
    async def test_get_current_active_user_disabled_user_raises_exception(self, mocker):
        """Test get_current_active_user with disabled user raises HTTPException"""
        # Arrange
        disabled_user = User(username="testuser", email="test@example.com", disabled=True)
        
        # Act & Assert
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await get_current_active_user(disabled_user)
        
        assert exc_info.value.status_code == 400


class TestDatabaseOperations:
    """Test database operations with mocked dependencies"""

    @pytest.mark.asyncio
    async def test_get_user_existing_user(self, mocker):
        """Test get_user with existing user"""
        # Arrange
        mock_fake_users_db = mocker.patch('src.pake_system.auth.database.fake_users_db')
        mock_fake_users_db.__contains__.return_value = True
        mock_fake_users_db.__getitem__.return_value = {
            "username": "testuser",
            "email": "test@example.com",
            "full_name": "Test User",
            "hashed_password": "$2b$12$...",
            "disabled": False
        }
        
        # Act
        user = await get_user("testuser")
        
        # Assert
        assert user is not None
        assert user.username == "testuser"

    @pytest.mark.asyncio
    async def test_get_user_nonexistent_user(self, mocker):
        """Test get_user with nonexistent user"""
        # Arrange
        mock_fake_users_db = mocker.patch('src.pake_system.auth.database.fake_users_db')
        mock_fake_users_db.__contains__.return_value = False
        
        # Act
        user = await get_user("nonexistent")
        
        # Assert
        assert user is None

    @pytest.mark.asyncio
    async def test_authenticate_user_valid_credentials(self, mocker):
        """Test authenticate_user with valid credentials"""
        # Arrange
        mock_get_user = mocker.patch('src.pake_system.auth.database.get_user')
        mock_verify_password = mocker.patch('src.pake_system.auth.database.verify_password')
        
        mock_user = UserInDB(
            username="testuser",
            email="test@example.com",
            hashed_password="$2b$12$...",
            disabled=False
        )
        mock_get_user.return_value = mock_user
        mock_verify_password.return_value = True
        
        # Act
        user = await authenticate_user("testuser", "password123")
        
        # Assert
        assert user is not None
        assert user.username == "testuser"
        mock_verify_password.assert_called_once_with("password123", "$2b$12$...")

    @pytest.mark.asyncio
    async def test_authenticate_user_invalid_password(self, mocker):
        """Test authenticate_user with invalid password"""
        # Arrange
        mock_get_user = mocker.patch('src.pake_system.auth.database.get_user')
        mock_verify_password = mocker.patch('src.pake_system.auth.database.verify_password')
        
        mock_user = UserInDB(
            username="testuser",
            email="test@example.com",
            hashed_password="$2b$12$...",
            disabled=False
        )
        mock_get_user.return_value = mock_user
        mock_verify_password.return_value = False
        
        # Act
        user = await authenticate_user("testuser", "wrongpassword")
        
        # Assert
        assert user is None

    @pytest.mark.asyncio
    async def test_authenticate_user_nonexistent_user(self, mocker):
        """Test authenticate_user with nonexistent user"""
        # Arrange
        mock_get_user = mocker.patch('src.pake_system.auth.database.get_user')
        mock_get_user.return_value = None
        
        # Act
        user = await authenticate_user("nonexistent", "password123")
        
        # Assert
        assert user is None

    @pytest.mark.asyncio
    async def test_create_user_success(self, mocker):
        """Test create_user with valid data"""
        # Arrange
        mock_fake_users_db = mocker.patch('src.pake_system.auth.database.fake_users_db')
        
        # Act
        user = await create_user(
            username="newuser",
            email="new@example.com",
            hashed_password="$2b$12$...",
            full_name="New User"
        )
        
        # Assert
        assert user.username == "newuser"
        assert user.email == "new@example.com"
        assert user.disabled is False
        mock_fake_users_db.__setitem__.assert_called_once()


class TestModelValidation:
    """Test Pydantic model validation"""

    def test_user_model_validation(self):
        """Test User model validation"""
        # Arrange & Act
        user = User(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            disabled=False
        )
        
        # Assert
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.disabled is False

    def test_user_model_minimum_length_validation(self):
        """Test User model minimum length validation"""
        # Act & Assert
        with pytest.raises(ValueError):
            User(username="ab")  # Too short

    def test_user_create_model_validation(self):
        """Test UserCreate model validation"""
        # Arrange & Act
        user_create = UserCreate(
            username="newuser",
            email="new@example.com",
            password="SecurePassword123!",
            full_name="New User"
        )
        
        # Assert
        assert user_create.username == "newuser"
        assert user_create.email == "new@example.com"
        assert user_create.password == "SecurePassword123!"
        assert user_create.full_name == "New User"

    def test_token_model_validation(self):
        """Test Token model validation"""
        # Arrange & Act
        token = Token(
            access_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            token_type="bearer",
            refresh_token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        )
        
        # Assert
        assert token.access_token == "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
        assert token.token_type == "bearer"
        assert token.refresh_token == "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

    def test_token_data_model_validation(self):
        """Test TokenData model validation"""
        # Arrange & Act
        token_data = TokenData(username="testuser")
        
        # Assert
        assert token_data.username == "testuser"


# Performance Tests
class TestPerformance:
    """Test performance characteristics of authentication functions"""

    def test_password_hashing_performance(self):
        """Test that password hashing completes within reasonable time"""
        import time
        
        # Arrange
        password = "SecurePassword123!"
        
        # Act
        start_time = time.time()
        hashed = create_password_hash(password)
        end_time = time.time()
        
        # Assert
        assert end_time - start_time < 1.0  # Should complete within 1 second
        assert verify_password(password, hashed) is True

    def test_token_generation_performance(self):
        """Test that token generation completes within reasonable time"""
        import time
        
        # Arrange
        data = {"sub": "testuser"}
        
        # Act
        start_time = time.time()
        with patch('src.pake_system.auth.security.settings') as mock_settings:
            mock_settings.SECRET_KEY = "test-secret-key"
            mock_settings.ALGORITHM = "HS256"
            mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30
            
            token = create_access_token(data)
            payload = decode_token(token)
        
        end_time = time.time()
        
        # Assert
        assert end_time - start_time < 0.1  # Should complete within 100ms
        assert payload["sub"] == "testuser"
