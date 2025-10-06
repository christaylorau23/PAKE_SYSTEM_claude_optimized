"""
Unit Tests for Authentication Security Module

Tests password hashing and JWT token generation in complete isolation.
All external dependencies are mocked using pytest-mock.

Following Testing Pyramid: Unit tests (70%) - Fast, isolated, comprehensive
"""

from datetime import timedelta
from unittest.mock import patch

from jose import JWTError, jwt
import pytest

from src.pake_system.auth.security import (
    create_access_token,
    create_password_hash,
    decode_token,
    verify_password,
)

# ============================================================================
# Unit Tests - Password Hashing
# ============================================================================


@pytest.mark.unit
@pytest.mark.unit_functional
class TestPasswordHashing:
    """Test password hashing functionality in isolation"""

    def test_create_password_hash_generates_valid_hash(self) -> None:
        """Test that password hashing creates a valid bcrypt hash"""
        # Arrange
        password = "SecurePassword123!"

        # Act
        hashed = create_password_hash(password)

        # Assert
        assert isinstance(hashed, str)
        assert hashed.startswith("$2b$")  # Bcrypt identifier
        assert len(hashed) > 50  # Bcrypt hashes are ~60 chars

    def test_create_password_hash_uses_salt(self) -> None:
        """Test that each hash is unique due to salting"""
        # Arrange
        password = "SamePassword123"

        # Act
        hash1 = create_password_hash(password)
        hash2 = create_password_hash(password)

        # Assert - hashes should be different due to random salt
        assert hash1 != hash2

    def test_verify_password_accepts_correct_password(self) -> None:
        """Test password verification with correct password"""
        # Arrange
        password = "CorrectPassword123"
        hashed = create_password_hash(password)

        # Act
        result = verify_password(password, hashed)

        # Assert
        assert result is True

    def test_verify_password_rejects_incorrect_password(self) -> None:
        """Test password verification with wrong password"""
        # Arrange
        correct_password = "CorrectPassword123"
        wrong_password = "WrongPassword456"
        hashed = create_password_hash(correct_password)

        # Act
        result = verify_password(wrong_password, hashed)

        # Assert
        assert result is False

    @pytest.mark.unit_edge_case
    def test_verify_password_rejects_empty_password(self) -> None:
        """Test password verification with empty string"""
        # Arrange
        hashed = create_password_hash("password")

        # Act
        result = verify_password("", hashed)

        # Assert
        assert result is False

    @pytest.mark.unit_edge_case
    def test_verify_password_handles_special_characters(self) -> None:
        """Test password hashing with special characters"""
        # Arrange
        password = "P@ssw0rd!#$%^&*()"
        hashed = create_password_hash(password)

        # Act
        result = verify_password(password, hashed)

        # Assert
        assert result is True

    @pytest.mark.unit_error_handling
    def test_create_password_hash_handles_unicode(self) -> None:
        """Test password hashing with unicode characters"""
        # Arrange
        password = "密码🔒测试"

        # Act
        hashed = create_password_hash(password)

        # Assert
        assert verify_password(password, hashed) is True


# ============================================================================
# Unit Tests - JWT Token Generation (with mocked settings)
# ============================================================================


@pytest.mark.unit
@pytest.mark.unit_functional
class TestJWTTokenGeneration:
    """Test JWT token creation and validation with mocked dependencies"""

    @patch("src.pake_system.auth.security.settings")
    def test_create_access_token_generates_valid_token(self) -> None:
        """Test that token generation creates valid JWT"""
        # Arrange
        self.mock_settings.SECRET_KEY = "test-secret-key"
        self.mock_settings.ALGORITHM = "HS256"
        self.mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30

        data = {"sub": "testuser"}

        # Act
        token = create_access_token(data)

        # Assert
        assert isinstance(token, str)
        assert len(token.split(".")) == 3  # JWT has 3 parts

    @patch("src.pake_system.auth.security.settings")
    def test_create_access_token_includes_subject(self) -> None:
        """Test that token includes the subject claim"""
        # Arrange
        self.mock_settings.SECRET_KEY = "test-secret-key"
        self.mock_settings.ALGORITHM = "HS256"
        self.mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30

        data = {"sub": "testuser", "role": "admin"}

        # Act
        token = create_access_token(data)
        payload = jwt.decode(
            token, self.self.mock_settings.SECRET_KEY, algorithms=[self.self.mock_settings.ALGORITHM]
        )

        # Assert
        assert payload["sub"] == "testuser"
        assert payload["role"] == "admin"

    @patch("src.pake_system.auth.security.settings")
    def test_create_access_token_includes_expiration(self) -> None:
        """Test that token includes expiration claim"""
        # Arrange
        self.mock_settings.SECRET_KEY = "test-secret-key"
        self.mock_settings.ALGORITHM = "HS256"
        self.mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30

        data = {"sub": "testuser"}

        # Act
        token = create_access_token(data)
        payload = jwt.decode(
            token, self.self.mock_settings.SECRET_KEY, algorithms=[self.self.mock_settings.ALGORITHM]
        )

        # Assert
        assert "exp" in payload
        assert "iat" in payload
        assert payload["exp"] > payload["iat"]

    @patch("src.pake_system.auth.security.settings")
    def test_create_access_token_with_custom_expiration(self) -> None:
        """Test token generation with custom expiration"""
        # Arrange
        self.mock_settings.SECRET_KEY = "test-secret-key"
        self.mock_settings.ALGORITHM = "HS256"

        data = {"sub": "testuser"}
        custom_expires = timedelta(minutes=15)

        # Act
        token = create_access_token(data, expires_delta=custom_expires)
        payload = jwt.decode(
            token, self.self.mock_settings.SECRET_KEY, algorithms=[self.self.mock_settings.ALGORITHM]
        )

        # Assert
        assert "exp" in payload
        # Custom expiration should be roughly 15 minutes from now

    @patch("src.pake_system.auth.security.settings")
    def test_decode_token_validates_signature(self) -> None:
        """Test that token decoding validates signature"""
        # Arrange
        self.mock_settings.SECRET_KEY = "test-secret-key"
        self.mock_settings.ALGORITHM = "HS256"
        self.mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30

        data = {"sub": "testuser"}
        token = create_access_token(data)

        # Act
        payload = decode_token(token)

        # Assert
        assert payload["sub"] == "testuser"

    @pytest.mark.unit_error_handling
    @patch("src.pake_system.auth.security.settings")
    def test_decode_token_rejects_invalid_signature(self) -> None:
        """Test that invalid signature is rejected"""
        # Arrange
        self.mock_settings.SECRET_KEY = "test-secret-key"
        self.mock_settings.ALGORITHM = "HS256"

        # Create token with one key, try to decode with another
        token = jwt.encode({"sub": "testuser"}, "wrong-key", algorithm="HS256")

        # Act & Assert
        with pytest.raises(JWTError):
            decode_token(token)

    @pytest.mark.unit_error_handling
    @patch("src.pake_system.auth.security.settings")
    def test_decode_token_rejects_malformed_token(self) -> None:
        """Test that malformed tokens are rejected"""
        # Arrange
        self.mock_settings.SECRET_KEY = "test-secret-key"
        self.mock_settings.ALGORITHM = "HS256"

        malformed_token = "not.a.valid.jwt.token"

        # Act & Assert
        with pytest.raises(JWTError):
            decode_token(malformed_token)

    @pytest.mark.unit_edge_case
    @patch("src.pake_system.auth.security.settings")
    def test_create_access_token_with_empty_data(self) -> None:
        """Test token creation with minimal data"""
        # Arrange
        self.mock_settings.SECRET_KEY = "test-secret-key"
        self.mock_settings.ALGORITHM = "HS256"
        self.mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30

        data = {}

        # Act
        token = create_access_token(data)
        payload = decode_token(token)

        # Assert
        assert "exp" in payload
        assert "iat" in payload


# ============================================================================
# Unit Tests - Security Edge Cases
# ============================================================================


@pytest.mark.unit
@pytest.mark.unit_edge_case
class TestSecurityEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_password_hash_extremely_long_password(self) -> None:
        """Test hashing of very long password"""
        # Arrange
        long_password = "a" * 1000

        # Act
        hashed = create_password_hash(long_password)

        # Assert
        assert verify_password(long_password, hashed) is True

    def test_password_hash_single_character(self) -> None:
        """Test hashing of single character password"""
        # Arrange
        password = "a"

        # Act
        hashed = create_password_hash(password)

        # Assert
        assert verify_password(password, hashed) is True

    @patch("src.pake_system.auth.security.settings")
    def test_token_with_large_payload(self) -> None:
        """Test token creation with large payload"""
        # Arrange
        self.mock_settings.SECRET_KEY = "test-secret-key"
        self.mock_settings.ALGORITHM = "HS256"
        self.mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30

        # Large payload
        data = {
            "sub": "testuser",
            "permissions": [f"perm_{i}" for i in range(100)],
            "metadata": {"key": "value" * 100},
        }

        # Act
        token = create_access_token(data)
        payload = decode_token(token)

        # Assert
        assert payload["sub"] == "testuser"
        assert len(payload["permissions"]) == 100


# ============================================================================
# Unit Tests - Performance (using pytest-benchmark if available)
# ============================================================================


@pytest.mark.unit
@pytest.mark.unit_performance
class TestSecurityPerformance:
    """Test performance characteristics of security functions"""

    def test_password_hashing_performance(self) -> None:
        """Benchmark password hashing speed"""
        # Act
        result = benchmark(create_password_hash, "password123")

        # Assert
        assert result.startswith("$2b$")

    def test_password_verification_performance(self) -> None:
        """Benchmark password verification speed"""
        # Arrange
        hashed = create_password_hash("password123")

        # Act
        result = benchmark(verify_password, "password123", hashed)

        # Assert
        assert result is True

    @patch("src.pake_system.auth.security.settings")
    def test_token_generation_performance(self) -> None:
        """Benchmark token generation speed"""
        # Arrange
        self.mock_settings.SECRET_KEY = "test-secret-key"
        self.mock_settings.ALGORITHM = "HS256"
        self.mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30

        # Act
        result = benchmark(create_access_token, {"sub": "testuser"})

        # Assert
        assert isinstance(result, str)

    @patch("src.pake_system.auth.security.settings")
    def test_token_decoding_performance(self) -> None:
        """Benchmark token decoding speed"""
        # Arrange
        self.mock_settings.SECRET_KEY = "test-secret-key"
        self.mock_settings.ALGORITHM = "HS256"
        self.mock_settings.ACCESS_TOKEN_EXPIRE_MINUTES = 30

        token = create_access_token({"sub": "testuser"})

        # Act
        result = benchmark(decode_token, token)

        # Assert
        assert result["sub"] == "testuser"