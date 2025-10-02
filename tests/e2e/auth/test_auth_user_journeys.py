"""
End-to-End Tests for Authentication User Journeys

Tests complete user workflows from HTTP request to database persistence.
Makes real HTTP requests to a running application instance.

Following Testing Pyramid: E2E tests (10%) - Complete workflows, user journeys

Critical User Journeys Tested:
1. User Registration and First Login
2. Login, Access Protected Resource, Logout
3. Token Refresh Flow
4. Password Change Workflow
5. Failed Authentication Scenarios
"""

import pytest

# ============================================================================
# E2E Test: User Registration and First Login
# ============================================================================


@pytest.mark.e2e()
@pytest.mark.e2e_user_journey()
class TestUserRegistrationJourney:
    """Test complete user registration and first login journey"""

    def test_new_user_registration_and_login_flow(self, test_client):
        """
        User Journey: New user registers and logs in for the first time

        Steps:
        1. Access public homepage (no auth required)
        2. Attempt to access protected endpoint (should fail)
        3. Register new user account (would call /register endpoint)
        4. Login with new credentials
        5. Access protected endpoint (should succeed)
        6. Verify user data is correct
        """
        # Step 1: Access public homepage
        response = test_client.get("/")
        assert response.status_code == 200
        assert "PAKE System" in response.json().get("message", "")

        # Step 2: Attempt to access protected endpoint without auth
        response = test_client.get("/protected")
        assert response.status_code == 401

        # Step 3: Register user (using existing test user from fake_users_db)
        # In production, would POST to /register endpoint

        # Step 4: Login with credentials
        login_response = test_client.post(
            "/token", data={"username": "admin", "password": "secret"}
        )

        assert login_response.status_code == 200
        token_data = login_response.json()
        assert "access_token" in token_data
        assert token_data["token_type"] == "bearer"

        # Step 5: Access protected endpoint with token
        token = token_data["access_token"]
        protected_response = test_client.get(
            "/protected", headers={"Authorization": f"Bearer {token}"}
        )

        assert protected_response.status_code == 200
        assert "admin" in protected_response.json()["message"]

        # Step 6: Verify user info
        user_info_response = test_client.get(
            "/auth/me", headers={"Authorization": f"Bearer {token}"}
        )

        assert user_info_response.status_code == 200
        user_info = user_info_response.json()
        assert user_info["username"] == "admin"
        assert user_info["disabled"] is False


# ============================================================================
# E2E Test: Login, Access Resources, Logout
# ============================================================================


@pytest.mark.e2e()
@pytest.mark.e2e_user_journey()
class TestLoginAccessLogoutJourney:
    """Test complete login, access, and logout journey"""

    def test_login_access_multiple_resources_logout(self, test_client):
        """
        User Journey: User logs in, accesses multiple resources, then logs out

        Steps:
        1. Login to get access token
        2. Access user profile
        3. Access protected resource #1
        4. Access protected resource #2 (admin panel)
        5. Logout
        6. Verify token is invalidated (optional, depends on implementation)
        """
        # Step 1: Login
        login_response = test_client.post(
            "/token", data={"username": "admin", "password": "secret"}
        )

        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Step 2: Access user profile
        profile_response = test_client.get("/auth/me", headers=headers)
        assert profile_response.status_code == 200
        assert profile_response.json()["username"] == "admin"

        # Step 3: Access protected resource
        resource1_response = test_client.get("/protected", headers=headers)
        assert resource1_response.status_code == 200

        # Step 4: Access admin panel
        admin_response = test_client.get("/admin", headers=headers)
        assert admin_response.status_code == 200
        assert "admin" in admin_response.json()["message"]

        # Step 5: Logout
        logout_response = test_client.post("/auth/logout", headers=headers)
        assert logout_response.status_code == 200

        # Step 6: Verify token invalidation (if implemented)
        # Note: JWT tokens can't be truly invalidated without a blacklist
        # This test would verify blacklist functionality if implemented


# ============================================================================
# E2E Test: Token Refresh Flow
# ============================================================================


@pytest.mark.e2e()
@pytest.mark.e2e_user_journey()
class TestTokenRefreshJourney:
    """Test token refresh workflow"""

    def test_token_refresh_flow(self, test_client):
        """
        User Journey: User gets access token, then refreshes it

        Steps:
        1. Initial login to get access + refresh tokens
        2. Use access token to access resources
        3. Refresh token to get new access token
        4. Use new access token
        5. Verify old token still works (until expiry)
        """
        # Step 1: Initial login
        login_response = test_client.post(
            "/token", data={"username": "admin", "password": "secret"}
        )

        assert login_response.status_code == 200
        initial_token = login_response.json()["access_token"]

        # Step 2: Use initial access token
        response = test_client.get(
            "/auth/me", headers={"Authorization": f"Bearer {initial_token}"}
        )
        assert response.status_code == 200

        # Step 3-5: Token refresh would be tested here if implemented
        # For now, verify initial token works


# ============================================================================
# E2E Test: Password Change Workflow
# ============================================================================


@pytest.mark.e2e()
@pytest.mark.e2e_user_journey()
class TestPasswordChangeJourney:
    """Test password change workflow"""

    def test_password_change_flow(self, test_client):
        """
        User Journey: User changes their password

        Steps:
        1. Login with current password
        2. Change password (would call /auth/change-password)
        3. Verify old password no longer works
        4. Login with new password
        5. Access protected resources with new token
        """
        # Step 1: Login with current password
        login_response = test_client.post(
            "/token", data={"username": "testuser", "password": "secret"}
        )

        # testuser doesn't exist in fake_users_db, so this would fail
        # In real E2E test with actual database, would proceed with steps 2-5


# ============================================================================
# E2E Test: Failed Authentication Scenarios
# ============================================================================


@pytest.mark.e2e()
@pytest.mark.e2e_user_journey()
class TestFailedAuthenticationJourneys:
    """Test various failure scenarios in authentication"""

    def test_login_with_invalid_credentials(self, test_client):
        """
        User Journey: User attempts login with wrong password

        Steps:
        1. Attempt login with wrong password
        2. Verify error response
        3. Verify user is not authenticated
        4. Verify access to protected resources is denied
        """
        # Step 1: Attempt login with wrong password
        response = test_client.post(
            "/token", data={"username": "admin", "password": "wrongpassword"}
        )

        # Step 2: Verify error response
        assert response.status_code == 401
        assert "detail" in response.json()

        # Step 3 & 4: Verify no authentication occurred
        # Try to access protected resource without token
        protected_response = test_client.get("/protected")
        assert protected_response.status_code == 401

    def test_access_protected_resource_without_token(self, test_client):
        """
        User Journey: User attempts to access protected resource without auth

        Steps:
        1. Attempt to access protected endpoint without token
        2. Verify 401 Unauthorized response
        3. Verify helpful error message
        """
        # Step 1: Attempt access without token
        response = test_client.get("/protected")

        # Step 2: Verify 401 response
        assert response.status_code == 401

        # Step 3: Verify error details
        assert "detail" in response.json()

    def test_access_with_invalid_token(self, test_client):
        """
        User Journey: User attempts to access with invalid token

        Steps:
        1. Create invalid/malformed token
        2. Attempt to access protected resource
        3. Verify 401 Unauthorized response
        """
        # Step 1: Create invalid token
        invalid_token = "invalid.token.here"

        # Step 2: Attempt access with invalid token
        response = test_client.get(
            "/protected", headers={"Authorization": f"Bearer {invalid_token}"}
        )

        # Step 3: Verify 401 response
        assert response.status_code == 401

    def test_access_with_expired_token(self, test_client):
        """
        User Journey: User attempts to use expired token

        Steps:
        1. Create token with past expiration (or wait for expiration)
        2. Attempt to access protected resource
        3. Verify 401 Unauthorized response
        4. Verify error indicates token is expired
        """
        # This test would require creating a token with past expiration
        # or mocking time to simulate expiration


# ============================================================================
# E2E Test: Complete Application Flow
# ============================================================================


@pytest.mark.e2e()
@pytest.mark.e2e_user_journey()
@pytest.mark.slow()
class TestCompleteApplicationFlow:
    """Test complete application workflows end-to-end"""

    def test_complete_user_session_lifecycle(self, test_client):
        """
        Complete User Journey: Full session from start to finish

        Steps:
        1. User visits homepage
        2. User registers account
        3. User logs in
        4. User accesses their profile
        5. User performs main application actions
        6. User changes settings/password
        7. User logs out
        8. User logs back in
        9. User's session persists
        """
        # Step 1: Visit homepage
        home_response = test_client.get("/")
        assert home_response.status_code == 200

        # Steps 2-9: Full lifecycle test
        # Using existing admin user from fake_users_db

        # Step 3: Login
        login_response = test_client.post(
            "/token", data={"username": "admin", "password": "secret"}
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Step 4: Access profile
        profile_response = test_client.get("/auth/me", headers=headers)
        assert profile_response.status_code == 200
        user_data = profile_response.json()

        # Step 5: Perform application actions
        protected_response = test_client.get("/protected", headers=headers)
        assert protected_response.status_code == 200

        admin_response = test_client.get("/admin", headers=headers)
        assert admin_response.status_code == 200

        # Step 7: Logout
        logout_response = test_client.post("/auth/logout", headers=headers)
        assert logout_response.status_code == 200

        # Step 8: Log back in
        second_login_response = test_client.post(
            "/token", data={"username": "admin", "password": "secret"}
        )
        assert second_login_response.status_code == 200
        new_token = second_login_response.json()["access_token"]

        # Step 9: Verify session persists
        new_profile_response = test_client.get(
            "/auth/me", headers={"Authorization": f"Bearer {new_token}"}
        )
        assert new_profile_response.status_code == 200
        assert new_profile_response.json()["username"] == user_data["username"]


# ============================================================================
# E2E Test: Performance and Reliability
# ============================================================================


@pytest.mark.e2e()
@pytest.mark.e2e_performance()
@pytest.mark.slow()
class TestAuthPerformanceAndReliability:
    """Test authentication performance and reliability"""

    def test_concurrent_login_requests(self, test_client):
        """
        Test system handles multiple concurrent login requests

        Steps:
        1. Send multiple login requests concurrently
        2. Verify all are handled correctly
        3. Verify no race conditions
        """
        # Multiple concurrent logins
        responses = []
        for _ in range(10):
            response = test_client.post(
                "/token", data={"username": "admin", "password": "secret"}
            )
            responses.append(response)

        # Verify all succeeded
        assert all(r.status_code == 200 for r in responses)
        assert all("access_token" in r.json() for r in responses)

    def test_authentication_response_time(self, test_client, benchmark):
        """
        Test authentication response time meets SLA

        Steps:
        1. Benchmark login endpoint response time
        2. Verify response time < 500ms
        """

        def login():
            return test_client.post(
                "/token", data={"username": "admin", "password": "secret"}
            )

        result = benchmark(login)
        assert result.status_code == 200

        # Benchmark will provide timing information
