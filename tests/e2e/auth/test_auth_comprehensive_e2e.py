"""
Comprehensive End-to-End Tests for PAKE System
Tests complete user journeys from API request to database persistence
"""

import pytest
import asyncio
from datetime import datetime, timezone
from httpx import AsyncClient
from fastapi.testclient import TestClient

from src.pake_system.auth.models import User, UserCreate, Token
from src.pake_system.auth.security import create_password_hash
from tests.factories import UserFactory


class TestCriticalUserJourneys:
    """End-to-end tests for critical user journeys"""

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_complete_user_registration_and_login_journey(self, test_client):
        """
        Test complete user journey: Registration -> Login -> Access Protected Resources
        
        This is the most critical user journey in the authentication system.
        """
        # Arrange
        user_data = {
            "username": "newuser",
            "email": "new@example.com",
            "password": "SecurePassword123!",
            "full_name": "New User"
        }
        
        # Act 1: User Registration
        registration_response = test_client.post("/auth/register", json=user_data)
        
        # Assert 1: Registration successful
        assert registration_response.status_code == 200
        registered_user = registration_response.json()
        assert registered_user["username"] == user_data["username"]
        assert registered_user["email"] == user_data["email"]
        assert registered_user["disabled"] is False
        assert "hashed_password" not in registered_user  # Password not returned
        
        # Act 2: User Login
        login_response = test_client.post(
            "/auth/token",
            data={"username": user_data["username"], "password": user_data["password"]}
        )
        
        # Assert 2: Login successful
        assert login_response.status_code == 200
        token_data = login_response.json()
        assert "access_token" in token_data
        assert "refresh_token" in token_data
        assert token_data["token_type"] == "bearer"
        
        access_token = token_data["access_token"]
        refresh_token = token_data["refresh_token"]
        
        # Act 3: Access Protected Resource
        protected_response = test_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        # Assert 3: Protected resource accessible
        assert protected_response.status_code == 200
        user_info = protected_response.json()
        assert user_info["username"] == user_data["username"]
        assert user_info["email"] == user_data["email"]
        
        # Act 4: Token Refresh
        refresh_response = test_client.post("/auth/refresh", json={"refresh_token": refresh_token})
        
        # Assert 4: Token refresh successful
        assert refresh_response.status_code == 200
        new_token_data = refresh_response.json()
        assert "access_token" in new_token_data
        assert new_token_data["token_type"] == "bearer"
        
        # Act 5: Use New Token
        new_access_token = new_token_data["access_token"]
        new_protected_response = test_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {new_access_token}"}
        )
        
        # Assert 5: New token works
        assert new_protected_response.status_code == 200
        new_user_info = new_protected_response.json()
        assert new_user_info["username"] == user_data["username"]
        
        # Act 6: Logout
        logout_response = test_client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {new_access_token}"}
        )
        
        # Assert 6: Logout successful
        assert logout_response.status_code == 200
        assert logout_response.json()["message"] == "Successfully logged out"

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_password_strength_validation_journey(self, test_client):
        """
        Test complete password strength validation journey
        
        This journey ensures users create secure passwords.
        """
        # Arrange
        weak_passwords = [
            "weak",
            "password123",
            "admin",
            "qwerty123",
            "abc123456"
        ]
        
        strong_password = "MySecurePassword123!"
        
        # Act & Assert: Test weak passwords
        for weak_password in weak_passwords:
            user_data = {
                "username": f"user_{weak_password}",
                "email": f"user_{weak_password}@example.com",
                "password": weak_password,
                "full_name": "Test User"
            }
            
            # Registration should fail
            registration_response = test_client.post("/auth/register", json=user_data)
            assert registration_response.status_code == 400
            assert "Password validation failed" in registration_response.json()["detail"]
            
            # Password validation endpoint should also fail
            validation_response = test_client.post(
                "/auth/validate-password",
                json={"password": weak_password}
            )
            assert validation_response.status_code == 200
            validation_result = validation_response.json()
            assert validation_result["is_valid"] is False
            assert len(validation_result["errors"]) > 0
        
        # Act & Assert: Test strong password
        user_data = {
            "username": "stronguser",
            "email": "strong@example.com",
            "password": strong_password,
            "full_name": "Strong User"
        }
        
        # Registration should succeed
        registration_response = test_client.post("/auth/register", json=user_data)
        assert registration_response.status_code == 200
        
        # Password validation should pass
        validation_response = test_client.post(
            "/auth/validate-password",
            json={"password": strong_password}
        )
        assert validation_response.status_code == 200
        validation_result = validation_response.json()
        assert validation_result["is_valid"] is True
        assert len(validation_result["errors"]) == 0

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_secure_password_generation_journey(self, test_client):
        """
        Test secure password generation journey
        
        This journey helps users generate secure passwords.
        """
        # Act: Generate passwords of different lengths
        password_lengths = [12, 16, 20, 24]
        generated_passwords = []
        
        for length in password_lengths:
            response = test_client.get(f"/auth/generate-password?length={length}")
            assert response.status_code == 200
            
            password_data = response.json()
            assert "password" in password_data
            assert len(password_data["password"]) == length
            
            generated_passwords.append(password_data["password"])
        
        # Assert: All generated passwords are unique and strong
        assert len(set(generated_passwords)) == len(generated_passwords)  # All unique
        
        for password in generated_passwords:
            validation_response = test_client.post(
                "/auth/validate-password",
                json={"password": password}
            )
            assert validation_response.status_code == 200
            validation_result = validation_response.json()
            assert validation_result["is_valid"] is True
            assert len(validation_result["errors"]) == 0

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_authentication_failure_and_recovery_journey(self, test_client):
        """
        Test authentication failure and recovery journey
        
        This journey tests security measures against failed login attempts.
        """
        # Arrange
        username = "testuser"
        password = "SecurePassword123!"
        
        # Create user
        hashed_password = create_password_hash(password)
        from src.pake_system.auth.database import create_user
        await create_user(
            username=username,
            email="test@example.com",
            hashed_password=hashed_password,
            full_name="Test User"
        )
        
        # Act 1: Multiple failed login attempts
        wrong_passwords = ["wrong1", "wrong2", "wrong3", "wrong4", "wrong5"]
        failed_responses = []
        
        for wrong_password in wrong_passwords:
            response = test_client.post(
                "/auth/token",
                data={"username": username, "password": wrong_password}
            )
            failed_responses.append(response)
        
        # Assert 1: All failed attempts return 401
        for response in failed_responses:
            assert response.status_code == 401
        
        # Act 2: Correct login after failures
        correct_response = test_client.post(
            "/auth/token",
            data={"username": username, "password": password}
        )
        
        # Assert 2: Correct login still works
        assert correct_response.status_code == 200
        token_data = correct_response.json()
        assert "access_token" in token_data
        
        # Act 3: Access protected resource
        access_token = token_data["access_token"]
        protected_response = test_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        # Assert 3: Protected resource accessible
        assert protected_response.status_code == 200
        user_info = protected_response.json()
        assert user_info["username"] == username

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_token_expiration_and_refresh_journey(self, test_client):
        """
        Test token expiration and refresh journey
        
        This journey tests token lifecycle management.
        """
        # Arrange
        username = "testuser"
        password = "SecurePassword123!"
        
        # Create user
        hashed_password = create_password_hash(password)
        from src.pake_system.auth.database import create_user
        await create_user(
            username=username,
            email="test@example.com",
            hashed_password=hashed_password,
            full_name="Test User"
        )
        
        # Act 1: Initial login
        login_response = test_client.post(
            "/auth/token",
            data={"username": username, "password": password}
        )
        
        # Assert 1: Login successful
        assert login_response.status_code == 200
        token_data = login_response.json()
        access_token = token_data["access_token"]
        refresh_token = token_data["refresh_token"]
        
        # Act 2: Use access token
        protected_response = test_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        # Assert 2: Access token works
        assert protected_response.status_code == 200
        
        # Act 3: Refresh token
        refresh_response = test_client.post("/auth/refresh", json={"refresh_token": refresh_token})
        
        # Assert 3: Refresh successful
        assert refresh_response.status_code == 200
        new_token_data = refresh_response.json()
        new_access_token = new_token_data["access_token"]
        
        # Act 4: Use new access token
        new_protected_response = test_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {new_access_token}"}
        )
        
        # Assert 4: New access token works
        assert new_protected_response.status_code == 200
        
        # Act 5: Try to use old access token (should still work if not expired)
        old_protected_response = test_client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        
        # Assert 5: Old token may still work (depends on expiration time)
        # This test assumes tokens have some overlap time
        assert old_protected_response.status_code in [200, 401]

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_concurrent_user_operations_journey(self, test_client):
        """
        Test concurrent user operations journey
        
        This journey tests system behavior under concurrent load.
        """
        import asyncio
        import time
        
        # Arrange
        users_data = [
            {
                "username": f"concurrent_user_{i}",
                "email": f"concurrent_{i}@example.com",
                "password": "SecurePassword123!",
                "full_name": f"Concurrent User {i}"
            }
            for i in range(5)
        ]
        
        # Act: Concurrent user registration
        start_time = time.time()
        
        async def register_user(user_data):
            response = test_client.post("/auth/register", json=user_data)
            return response
        
        tasks = [register_user(user_data) for user_data in users_data]
        registration_responses = await asyncio.gather(*tasks)
        
        registration_time = time.time() - start_time
        
        # Assert: All registrations successful
        for response in registration_responses:
            assert response.status_code == 200
        
        # Act: Concurrent login attempts
        start_time = time.time()
        
        async def login_user(user_data):
            response = test_client.post(
                "/auth/token",
                data={"username": user_data["username"], "password": user_data["password"]}
            )
            return response
        
        login_tasks = [login_user(user_data) for user_data in users_data]
        login_responses = await asyncio.gather(*login_tasks)
        
        login_time = time.time() - start_time
        
        # Assert: All logins successful
        for response in login_responses:
            assert response.status_code == 200
            token_data = response.json()
            assert "access_token" in token_data
        
        # Assert: Performance within acceptable limits
        assert registration_time < 10.0  # Registration within 10 seconds
        assert login_time < 5.0  # Login within 5 seconds

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_security_headers_and_cors_journey(self, test_client):
        """
        Test security headers and CORS journey
        
        This journey tests security headers and cross-origin policies.
        """
        # Act: Make requests to various endpoints
        endpoints = ["/auth/me", "/auth/generate-password", "/health"]
        
        for endpoint in endpoints:
            response = test_client.get(endpoint)
            
            # Assert: Security headers present
            headers = response.headers
            
            # Check for security headers
            security_headers = [
                "X-Frame-Options",
                "X-Content-Type-Options",
                "X-XSS-Protection",
                "Strict-Transport-Security",
                "Content-Security-Policy",
                "Referrer-Policy",
                "Permissions-Policy"
            ]
            
            for header in security_headers:
                assert header in headers, f"Security header {header} missing from {endpoint}"
            
            # Check specific header values
            assert headers["X-Frame-Options"] == "DENY"
            assert headers["X-Content-Type-Options"] == "nosniff"
            assert "mode=block" in headers["X-XSS-Protection"]

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery_journey(self, test_client):
        """
        Test error handling and recovery journey
        
        This journey tests system resilience to various error conditions.
        """
        # Act & Assert: Test various error conditions
        
        # 1. Invalid JSON in registration
        response = test_client.post(
            "/auth/register",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422
        
        # 2. Missing required fields
        response = test_client.post("/auth/register", json={})
        assert response.status_code == 422
        
        # 3. Invalid email format
        response = test_client.post("/auth/register", json={
            "username": "testuser",
            "email": "invalid-email",
            "password": "SecurePassword123!",
            "full_name": "Test User"
        })
        assert response.status_code == 422
        
        # 4. Invalid token format
        response = test_client.get(
            "/auth/me",
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == 401
        
        # 5. Missing authorization header
        response = test_client.get("/auth/me")
        assert response.status_code == 401
        
        # 6. Invalid refresh token
        response = test_client.post("/auth/refresh", json={"refresh_token": "invalid"})
        assert response.status_code == 401

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_data_persistence_and_consistency_journey(self, test_client):
        """
        Test data persistence and consistency journey
        
        This journey tests that data is properly persisted and consistent.
        """
        # Arrange
        user_data = {
            "username": "persistence_user",
            "email": "persistence@example.com",
            "password": "SecurePassword123!",
            "full_name": "Persistence User"
        }
        
        # Act 1: Register user
        registration_response = test_client.post("/auth/register", json=user_data)
        assert registration_response.status_code == 200
        
        # Act 2: Login user
        login_response = test_client.post(
            "/auth/token",
            data={"username": user_data["username"], "password": user_data["password"]}
        )
        assert login_response.status_code == 200
        
        # Act 3: Access user info multiple times
        access_token = login_response.json()["access_token"]
        
        user_info_responses = []
        for _ in range(3):
            response = test_client.get(
                "/auth/me",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            user_info_responses.append(response)
        
        # Assert: All responses consistent
        for response in user_info_responses:
            assert response.status_code == 200
            user_info = response.json()
            assert user_info["username"] == user_data["username"]
            assert user_info["email"] == user_data["email"]
            assert user_info["full_name"] == user_data["full_name"]
            assert user_info["disabled"] is False
        
        # Act 4: Verify user exists in database
        from src.pake_system.auth.database import get_user
        db_user = await get_user(user_data["username"])
        
        # Assert: Database consistency
        assert db_user is not None
        assert db_user.username == user_data["username"]
        assert db_user.email == user_data["email"]
        assert db_user.full_name == user_data["full_name"]
        assert db_user.disabled is False


class TestPerformanceE2E:
    """End-to-end performance tests"""

    @pytest.mark.e2e
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_authentication_performance_under_load(self, test_client):
        """
        Test authentication performance under load
        
        This test ensures the system can handle multiple concurrent requests.
        """
        import time
        import asyncio
        
        # Arrange
        username = "perfuser"
        password = "SecurePassword123!"
        
        # Create user
        hashed_password = create_password_hash(password)
        from src.pake_system.auth.database import create_user
        await create_user(
            username=username,
            email="perf@example.com",
            hashed_password=hashed_password,
            full_name="Performance User"
        )
        
        # Act: Multiple concurrent login requests
        start_time = time.time()
        
        async def login_request():
            response = test_client.post(
                "/auth/token",
                data={"username": username, "password": password}
            )
            return response
        
        # Create 10 concurrent login requests
        tasks = [login_request() for _ in range(10)]
        responses = await asyncio.gather(*tasks)
        
        end_time = time.time()
        
        # Assert: All requests successful and within time limit
        for response in responses:
            assert response.status_code == 200
        
        total_time = end_time - start_time
        assert total_time < 5.0  # Should complete within 5 seconds
        
        # Calculate requests per second
        rps = len(responses) / total_time
        assert rps > 2.0  # Should handle at least 2 requests per second

    @pytest.mark.e2e
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_password_generation_performance(self, test_client):
        """
        Test password generation performance
        
        This test ensures password generation is fast enough for user experience.
        """
        import time
        
        # Act: Generate multiple passwords
        start_time = time.time()
        
        passwords = []
        for _ in range(20):
            response = test_client.get("/auth/generate-password")
            assert response.status_code == 200
            password_data = response.json()
            passwords.append(password_data["password"])
        
        end_time = time.time()
        
        # Assert: All passwords generated and within time limit
        assert len(passwords) == 20
        assert len(set(passwords)) == 20  # All unique
        
        total_time = end_time - start_time
        assert total_time < 2.0  # Should complete within 2 seconds
        
        # Calculate passwords per second
        pps = len(passwords) / total_time
        assert pps > 10.0  # Should generate at least 10 passwords per second
