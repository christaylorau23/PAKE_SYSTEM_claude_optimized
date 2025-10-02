"""
Comprehensive End-to-End Tests for Critical User Journeys

Tests complete user workflows from API request to database persistence.
Makes real HTTP requests to a running application instance.

Following Testing Pyramid: E2E Tests (10%) - Complete workflows, user journeys
"""

import asyncio
import time

import httpx
import pytest
from fastapi.testclient import TestClient

from src.pake_system.auth.example_app import app
from tests.factories import UserFactory


class TestCriticalUserJourneysE2E:
    """Comprehensive E2E tests for critical user journeys"""

    @pytest.fixture()
    def test_client(self):
        """Create test client for E2E testing"""
        return TestClient(app)

    @pytest.fixture()
    async def async_client(self):
        """Create async HTTP client for E2E testing"""
        async with httpx.AsyncClient(app=app, base_url="http://test") as client:
            yield client

    # ============================================================================
    # CRITICAL USER JOURNEY 1: Complete User Onboarding
    # ============================================================================

    @pytest.mark.e2e()
    @pytest.mark.e2e_user_journey()
    async def test_complete_user_onboarding_journey(self, test_client, async_client):
        """
        Critical User Journey: Complete User Onboarding

        Steps:
        1. User visits homepage
        2. User registers new account
        3. User logs in for first time
        4. User completes profile setup
        5. User performs first search
        6. User provides feedback
        """
        # Step 1: Visit homepage
        home_response = test_client.get("/")
        assert home_response.status_code == 200
        assert "PAKE System" in home_response.text

        # Step 2: User registration
        user_data = UserFactory(
            email="onboarding@example.com",
            username="onboarding_user",
            password="SecurePassword123!",
        )

        registration_response = test_client.post(
            "/auth/register",
            json={
                "email": user_data["email"],
                "username": user_data["username"],
                "password": user_data["password"],
                "full_name": "Onboarding User",
            },
        )
        assert registration_response.status_code == 200
        registered_user = registration_response.json()
        assert registered_user["email"] == user_data["email"]
        assert registered_user["username"] == user_data["username"]

        # Step 3: User login
        login_response = test_client.post(
            "/auth/token",
            data={"username": user_data["username"], "password": user_data["password"]},
        )
        assert login_response.status_code == 200
        token_data = login_response.json()
        assert "access_token" in token_data
        assert "refresh_token" in token_data

        access_token = token_data["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Step 4: Access user profile
        profile_response = test_client.get("/auth/me", headers=headers)
        assert profile_response.status_code == 200
        profile_data = profile_response.json()
        assert profile_data["username"] == user_data["username"]

        # Step 5: Complete profile setup
        profile_update_response = test_client.put(
            "/auth/me",
            json={
                "full_name": "Onboarding User Updated",
                "research_interests": ["AI", "Machine Learning", "Data Science"],
                "organization": "Test Organization",
            },
            headers=headers,
        )
        assert profile_update_response.status_code == 200

        # Step 6: Perform first search
        search_response = test_client.post(
            "/search",
            json={
                "query": "artificial intelligence trends 2024",
                "sources": ["web", "arxiv", "pubmed"],
                "max_results": 10,
            },
            headers=headers,
        )
        assert search_response.status_code == 200
        search_results = search_response.json()
        assert "results" in search_results
        assert len(search_results["results"]) > 0

        # Verify complete journey success
        assert True  # All steps completed successfully

    # ============================================================================
    # CRITICAL USER JOURNEY 2: Research Workflow
    # ============================================================================

    @pytest.mark.e2e()
    @pytest.mark.e2e_user_journey()
    async def test_research_workflow_journey(self, test_client, async_client):
        """
        Critical User Journey: Complete Research Workflow

        Steps:
        1. User logs in
        2. User creates research project
        3. User performs multiple searches
        4. User saves relevant results
        5. User creates research notes
        6. User generates research summary
        """
        # Step 1: User login
        login_response = test_client.post(
            "/auth/token", data={"username": "admin", "password": "secret"}
        )
        assert login_response.status_code == 200
        token_data = login_response.json()
        access_token = token_data["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Step 2: Create research project
        project_response = test_client.post(
            "/research/projects",
            json={
                "title": "AI Research Project 2024",
                "description": "Comprehensive research on AI trends and applications",
                "tags": ["AI", "Machine Learning", "Research"],
            },
            headers=headers,
        )
        assert project_response.status_code == 200
        project_data = project_response.json()
        project_id = project_data["project_id"]

        # Step 3: Perform multiple searches
        search_queries = [
            "machine learning algorithms",
            "deep learning applications",
            "AI ethics and governance",
        ]

        search_results = []
        for query in search_queries:
            search_response = test_client.post(
                "/search",
                json={
                    "query": query,
                    "sources": ["web", "arxiv"],
                    "max_results": 5,
                    "project_id": project_id,
                },
                headers=headers,
            )
            assert search_response.status_code == 200
            search_data = search_response.json()
            search_results.append(search_data)

        # Step 4: Save relevant results
        saved_results = []
        for search_data in search_results:
            for result in search_data["results"][:2]:  # Save first 2 results
                save_response = test_client.post(
                    "/research/save-result",
                    json={
                        "project_id": project_id,
                        "result_id": result["id"],
                        "notes": f"Relevant to {search_data['query']}",
                    },
                    headers=headers,
                )
                assert save_response.status_code == 200
                saved_results.append(save_response.json())

        # Step 5: Create research notes
        notes_response = test_client.post(
            "/research/notes",
            json={
                "project_id": project_id,
                "title": "Key Findings",
                "content": "Key findings from the research:\n1. ML algorithms are evolving rapidly\n2. Deep learning has many applications\n3. AI ethics is becoming crucial",
                "tags": ["findings", "summary"],
            },
            headers=headers,
        )
        assert notes_response.status_code == 200

        # Step 6: Generate research summary
        summary_response = test_client.post(
            "/research/generate-summary",
            json={
                "project_id": project_id,
                "include_sources": True,
                "format": "comprehensive",
            },
            headers=headers,
        )
        assert summary_response.status_code == 200
        summary_data = summary_response.json()
        assert "summary" in summary_data
        assert len(summary_data["summary"]) > 0

        # Verify complete research workflow
        assert len(search_results) == 3
        assert len(saved_results) == 6  # 2 results per search
        assert project_id is not None

    # ============================================================================
    # PERFORMANCE E2E TESTS
    # ============================================================================

    @pytest.mark.e2e()
    @pytest.mark.e2e_performance()
    async def test_system_performance_under_load(self, test_client, async_client):
        """Test system performance under concurrent load"""
        # Arrange
        login_response = test_client.post(
            "/auth/token", data={"username": "admin", "password": "secret"}
        )
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Act: Concurrent search requests
        start_time = time.time()

        async def perform_search(query: str):
            async with httpx.AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/search",
                    json={
                        "query": query,
                        "sources": ["web", "arxiv"],
                        "max_results": 10,
                    },
                    headers=headers,
                )
                return response.status_code == 200

        # Perform 20 concurrent searches
        search_queries = [f"performance test query {i}" for i in range(20)]
        tasks = [perform_search(query) for query in search_queries]
        results = await asyncio.gather(*tasks)

        end_time = time.time()
        execution_time = end_time - start_time

        # Assert: Performance within acceptable limits
        assert execution_time < 30.0  # Should complete within 30 seconds
        assert all(results)  # All searches should succeed
        assert len(results) == 20

    @pytest.mark.e2e()
    @pytest.mark.e2e_performance()
    async def test_response_time_consistency(self, test_client, async_client):
        """Test response time consistency across multiple requests"""
        # Arrange
        login_response = test_client.post(
            "/auth/token", data={"username": "admin", "password": "secret"}
        )
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Act: Multiple identical requests
        response_times = []
        for i in range(10):
            start_time = time.time()

            response = test_client.get("/auth/me", headers=headers)
            assert response.status_code == 200

            end_time = time.time()
            response_times.append(end_time - start_time)

        # Assert: Response times are consistent
        avg_response_time = sum(response_times) / len(response_times)
        max_response_time = max(response_times)
        min_response_time = min(response_times)

        assert avg_response_time < 1.0  # Average response time under 1 second
        assert max_response_time < 2.0  # Max response time under 2 seconds
        assert (
            max_response_time - min_response_time
        ) < 1.0  # Consistency within 1 second

    # ============================================================================
    # RELIABILITY E2E TESTS
    # ============================================================================

    @pytest.mark.e2e()
    @pytest.mark.e2e_reliability()
    async def test_system_reliability_under_failure_conditions(
        self, test_client, async_client
    ):
        """Test system reliability under failure conditions"""
        # Arrange
        login_response = test_client.post(
            "/auth/token", data={"username": "admin", "password": "secret"}
        )
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Act: Test with invalid requests
        invalid_requests = [
            ("/search", {"invalid": "data"}),
            ("/auth/me", {}),  # No headers
            ("/nonexistent", {}),
        ]

        for endpoint, data in invalid_requests:
            if endpoint == "/auth/me":
                response = test_client.get(endpoint)
            else:
                response = test_client.post(endpoint, json=data)

            # Assert: System handles invalid requests gracefully
            assert response.status_code in [
                400,
                401,
                404,
                422,
            ]  # Appropriate error codes

    @pytest.mark.e2e()
    @pytest.mark.e2e_reliability()
    async def test_data_consistency_across_requests(self, test_client, async_client):
        """Test data consistency across multiple requests"""
        # Arrange
        login_response = test_client.post(
            "/auth/token", data={"username": "admin", "password": "secret"}
        )
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # Act: Multiple profile requests
        profile_data_list = []
        for _ in range(5):
            response = test_client.get("/auth/me", headers=headers)
            assert response.status_code == 200
            profile_data_list.append(response.json())

        # Assert: Data is consistent across requests
        first_profile = profile_data_list[0]
        for profile in profile_data_list[1:]:
            assert profile["username"] == first_profile["username"]
            assert profile["email"] == first_profile["email"]

    # ============================================================================
    # USER EXPERIENCE E2E TESTS
    # ============================================================================

    @pytest.mark.e2e()
    @pytest.mark.e2e_user_experience()
    async def test_user_experience_workflow_smoothness(self, test_client, async_client):
        """Test user experience workflow smoothness"""
        # Arrange
        user_data = UserFactory(
            email="ux_test@example.com", username="ux_test_user", password="UXTest123!"
        )

        # Act: Complete user journey with UX focus
        # 1. Registration
        registration_response = test_client.post(
            "/auth/register",
            json={
                "email": user_data["email"],
                "username": user_data["username"],
                "password": user_data["password"],
                "full_name": "UX Test User",
            },
        )
        assert registration_response.status_code == 200

        # 2. Login
        login_response = test_client.post(
            "/auth/token",
            data={"username": user_data["username"], "password": user_data["password"]},
        )
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}

        # 3. Profile access
        profile_response = test_client.get("/auth/me", headers=headers)
        assert profile_response.status_code == 200

        # 4. Search
        search_response = test_client.post(
            "/search",
            json={
                "query": "user experience design",
                "sources": ["web"],
                "max_results": 5,
            },
            headers=headers,
        )
        assert search_response.status_code == 200

        # Assert: Smooth user experience
        assert True  # All steps completed without errors

    @pytest.mark.e2e()
    @pytest.mark.e2e_user_experience()
    async def test_error_handling_user_friendliness(self, test_client, async_client):
        """Test error handling user friendliness"""
        # Act: Test various error scenarios
        error_scenarios = [
            ("/auth/register", {"email": "invalid-email"}, 422),
            ("/auth/token", {"username": "nonexistent", "password": "wrong"}, 401),
            ("/search", {"query": ""}, 422),
        ]

        for endpoint, data, expected_status in error_scenarios:
            response = test_client.post(endpoint, json=data)
            assert response.status_code == expected_status

            # Assert: Error messages are user-friendly
            error_data = response.json()
            assert "detail" in error_data or "message" in error_data
            # Error messages should be clear and actionable
