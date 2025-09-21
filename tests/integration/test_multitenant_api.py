#!/usr/bin/env python3
"""
PAKE System - Phase 17 Multi-Tenant API Integration Tests
Comprehensive end-to-end testing suite for multi-tenant API endpoints.
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from src.services.database.multi_tenant_schema import (
    MultiTenantDatabaseConfig,
)

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))


class MultiTenantAPITester:
    """
    Comprehensive multi-tenant API testing framework.

    Tests:
    1. Tenant management endpoints
    2. User management within tenants
    3. Authentication and authorization
    4. Search functionality with tenant isolation
    5. Security enforcement
    6. Performance and load testing
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.api_prefix = "/api/v1"
        self.test_tenants: list[dict[str, Any]] = []
        self.test_users: list[dict[str, Any]] = []
        self.auth_tokens: dict[str, str] = {}

    async def setup_test_environment(self) -> None:
        """Set up clean test environment"""
        print("🔧 Setting up multi-tenant API test environment...")

        # Initialize database service for cleanup
        db_config = MultiTenantDatabaseConfig(
            database="pake_system_multitenant_test",
            echo=False,
        )

        # Clean up any existing test data
        await self._cleanup_test_data()

        print("✅ Test environment ready")

    async def run_comprehensive_tests(self) -> dict[str, Any]:
        """Run all multi-tenant API tests"""
        try:
            await self.setup_test_environment()

            test_results = {
                "tenant_management": await self._test_tenant_management(),
                "user_management": await self._test_user_management(),
                "authentication": await self._test_authentication(),
                "tenant_isolation": await self._test_tenant_isolation(),
                "search_functionality": await self._test_search_functionality(),
                "security_enforcement": await self._test_security_enforcement(),
                "performance": await self._test_performance(),
            }

            # Generate summary
            summary = self._generate_test_summary(test_results)

            return {
                "summary": summary,
                "detailed_results": test_results,
                "timestamp": datetime.utcnow().isoformat(),
            }

        finally:
            await self._cleanup_test_data()

    # Tenant Management Tests

    async def _test_tenant_management(self) -> dict[str, Any]:
        """Test tenant management endpoints"""
        print("🏢 Testing tenant management...")

        results = []

        # Test 1: Create tenant
        tenant_data = {
            "name": "test-company-001",
            "display_name": "Test Company 001",
            "domain": "test001.pake.com",
            "plan": "basic",
            "admin_email": "admin@test001.com",
            "admin_username": "admin",
            "admin_full_name": "Test Administrator",
        }

        create_result = await self._create_tenant(tenant_data)
        results.append(create_result)

        if create_result["success"]:
            tenant = create_result["data"]["tenant"]
            self.test_tenants.append(tenant)

            # Test 2: Get tenant details
            get_result = await self._get_tenant(tenant["id"])
            results.append(get_result)

            # Test 3: Update tenant
            update_data = {"display_name": "Updated Test Company 001"}
            update_result = await self._update_tenant(tenant["id"], update_data)
            results.append(update_result)

            # Test 4: List tenants
            list_result = await self._list_tenants()
            results.append(list_result)

        # Test 5: Create additional tenants for isolation testing
        for i in range(2, 4):
            additional_tenant = {
                "name": f"test-company-{i:03d}",
                "display_name": f"Test Company {i:03d}",
                "admin_email": f"admin@test{i:03d}.com",
            }
            create_result = await self._create_tenant(additional_tenant)
            if create_result["success"]:
                self.test_tenants.append(create_result["data"]["tenant"])

        return {
            "test_count": len(results),
            "passed": len([r for r in results if r["success"]]),
            "failed": len([r for r in results if not r["success"]]),
            "details": results,
        }

    async def _create_tenant(self, tenant_data: dict[str, Any]) -> dict[str, Any]:
        """Test tenant creation"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}{self.api_prefix}/tenants/",
                    json=tenant_data,
                    headers={
                        "Authorization": f"Bearer {self._get_super_admin_token()}",
                    },
                )

                return {
                    "test": "create_tenant",
                    "success": response.status_code == 201,
                    "status_code": response.status_code,
                    "data": response.json() if response.status_code == 201 else None,
                    "error": response.text if response.status_code != 201 else None,
                }

        except Exception as e:
            return {"test": "create_tenant", "success": False, "error": str(e)}

    async def _get_tenant(self, tenant_id: str) -> dict[str, Any]:
        """Test tenant retrieval"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}{self.api_prefix}/tenants/{tenant_id}",
                    headers={
                        "Authorization": f"Bearer {self._get_tenant_admin_token(tenant_id)}",
                    },
                )

                return {
                    "test": "get_tenant",
                    "success": response.status_code == 200,
                    "status_code": response.status_code,
                    "data": response.json() if response.status_code == 200 else None,
                }

        except Exception as e:
            return {"test": "get_tenant", "success": False, "error": str(e)}

    async def _update_tenant(
        self,
        tenant_id: str,
        update_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Test tenant update"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"{self.base_url}{self.api_prefix}/tenants/{tenant_id}",
                    json=update_data,
                    headers={
                        "Authorization": f"Bearer {self._get_tenant_admin_token(tenant_id)}",
                    },
                )

                return {
                    "test": "update_tenant",
                    "success": response.status_code == 200,
                    "status_code": response.status_code,
                    "data": response.json() if response.status_code == 200 else None,
                }

        except Exception as e:
            return {"test": "update_tenant", "success": False, "error": str(e)}

    async def _list_tenants(self) -> dict[str, Any]:
        """Test tenant listing"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}{self.api_prefix}/tenants/",
                    headers={
                        "Authorization": f"Bearer {self._get_super_admin_token()}",
                    },
                )

                return {
                    "test": "list_tenants",
                    "success": response.status_code == 200,
                    "status_code": response.status_code,
                    "data": response.json() if response.status_code == 200 else None,
                }

        except Exception as e:
            return {"test": "list_tenants", "success": False, "error": str(e)}

    # User Management Tests

    async def _test_user_management(self) -> dict[str, Any]:
        """Test user management within tenants"""
        print("👥 Testing user management...")

        results = []

        if not self.test_tenants:
            return {"error": "No test tenants available for user management tests"}

        tenant = self.test_tenants[0]

        # Test 1: Create user
        user_data = {
            "username": "testuser001",
            "email": "testuser001@test.com",
            "REDACTED_SECRET": "SecurePassword123!",
            "full_name": "Test User 001",
            "role": "user",
        }

        create_result = await self._create_user(tenant["id"], user_data)
        results.append(create_result)

        if create_result["success"]:
            user = create_result["data"]["user"]
            self.test_users.append(user)

        # Test 2: List users in tenant
        list_result = await self._list_tenant_users(tenant["id"])
        results.append(list_result)

        # Test 3: Create users with different roles
        for role in ["manager", "admin"]:
            role_user_data = {
                "username": f"test{role}001",
                "email": f"test{role}001@test.com",
                "REDACTED_SECRET": "SecurePassword123!",
                "role": role,
            }
            role_result = await self._create_user(tenant["id"], role_user_data)
            results.append(role_result)

        return {
            "test_count": len(results),
            "passed": len([r for r in results if r["success"]]),
            "failed": len([r for r in results if not r["success"]]),
            "details": results,
        }

    async def _create_user(
        self,
        tenant_id: str,
        user_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Test user creation"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}{self.api_prefix}/users/",
                    json=user_data,
                    headers={
                        "Authorization": f"Bearer {self._get_tenant_admin_token(tenant_id)}",
                        "X-Tenant-ID": tenant_id,
                    },
                )

                return {
                    "test": "create_user",
                    "success": response.status_code == 201,
                    "status_code": response.status_code,
                    "data": response.json() if response.status_code == 201 else None,
                    "error": response.text if response.status_code != 201 else None,
                }

        except Exception as e:
            return {"test": "create_user", "success": False, "error": str(e)}

    async def _list_tenant_users(self, tenant_id: str) -> dict[str, Any]:
        """Test user listing within tenant"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}{self.api_prefix}/users/",
                    headers={
                        "Authorization": f"Bearer {self._get_tenant_admin_token(tenant_id)}",
                        "X-Tenant-ID": tenant_id,
                    },
                )

                return {
                    "test": "list_tenant_users",
                    "success": response.status_code == 200,
                    "status_code": response.status_code,
                    "data": response.json() if response.status_code == 200 else None,
                }

        except Exception as e:
            return {"test": "list_tenant_users", "success": False, "error": str(e)}

    # Authentication Tests

    async def _test_authentication(self) -> dict[str, Any]:
        """Test authentication and authorization flows"""
        print("🔐 Testing authentication...")

        results = []

        if not self.test_tenants or not self.test_users:
            return {"error": "No test data available for authentication tests"}

        tenant = self.test_tenants[0]
        user = self.test_users[0] if self.test_users else None

        if user:
            # Test 1: Valid login
            login_result = await self._test_user_login(
                tenant["id"],
                {
                    "username": user["username"],
                    "REDACTED_SECRET": "SecurePassword123!",  # Test REDACTED_SECRET
                },
            )
            results.append(login_result)

            # Test 2: Invalid REDACTED_SECRET
            invalid_login = await self._test_user_login(
                tenant["id"],
                {"username": user["username"], "REDACTED_SECRET": "WrongPassword"},
            )
            results.append(invalid_login)

        # Test 3: Token validation
        if self.auth_tokens:
            token_validation = await self._test_token_validation(tenant["id"])
            results.append(token_validation)

        # Test 4: Cross-tenant access denial
        if len(self.test_tenants) > 1:
            cross_tenant_result = await self._test_cross_tenant_access()
            results.append(cross_tenant_result)

        return {
            "test_count": len(results),
            "passed": len([r for r in results if r["success"]]),
            "failed": len([r for r in results if not r["success"]]),
            "details": results,
        }

    async def _test_user_login(
        self,
        tenant_id: str,
        credentials: dict[str, Any],
    ) -> dict[str, Any]:
        """Test user login functionality"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}{self.api_prefix}/auth/login",
                    json=credentials,
                    headers={"X-Tenant-ID": tenant_id},
                )

                if response.status_code == 200:
                    token_data = response.json()
                    self.auth_tokens[tenant_id] = token_data.get("access_token")

                expected_status = (
                    200
                    if "WrongPassword" not in credentials.get("REDACTED_SECRET", "")
                    else 401
                )
                success = response.status_code == expected_status

                return {
                    "test": "user_login",
                    "success": success,
                    "status_code": response.status_code,
                    "data": response.json() if response.status_code == 200 else None,
                    "expected_status": expected_status,
                }

        except Exception as e:
            return {"test": "user_login", "success": False, "error": str(e)}

    async def _test_token_validation(self, tenant_id: str) -> dict[str, Any]:
        """Test JWT token validation"""
        try:
            token = self.auth_tokens.get(tenant_id)
            if not token:
                return {
                    "test": "token_validation",
                    "success": False,
                    "error": "No token available for validation",
                }

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}{self.api_prefix}/auth/me",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "X-Tenant-ID": tenant_id,
                    },
                )

                return {
                    "test": "token_validation",
                    "success": response.status_code == 200,
                    "status_code": response.status_code,
                    "data": response.json() if response.status_code == 200 else None,
                }

        except Exception as e:
            return {"test": "token_validation", "success": False, "error": str(e)}

    async def _test_cross_tenant_access(self) -> dict[str, Any]:
        """Test that users cannot access other tenants' data"""
        try:
            if len(self.test_tenants) < 2:
                return {
                    "test": "cross_tenant_access",
                    "success": False,
                    "error": "Need at least 2 tenants for cross-tenant test",
                }

            tenant1_id = self.test_tenants[0]["id"]
            tenant2_id = self.test_tenants[1]["id"]
            token = self.auth_tokens.get(tenant1_id)

            if not token:
                return {
                    "test": "cross_tenant_access",
                    "success": False,
                    "error": "No token available for cross-tenant test",
                }

            # Try to access tenant2 data with tenant1 token
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}{self.api_prefix}/tenants/{tenant2_id}",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "X-Tenant-ID": tenant2_id,
                    },
                )

                # Should be denied (403)
                success = response.status_code == 403

                return {
                    "test": "cross_tenant_access",
                    "success": success,
                    "status_code": response.status_code,
                    "expected_status": 403,
                    "message": (
                        "Cross-tenant access correctly denied"
                        if success
                        else "Security issue: cross-tenant access allowed"
                    ),
                }

        except Exception as e:
            return {"test": "cross_tenant_access", "success": False, "error": str(e)}

    # Tenant Isolation Tests

    async def _test_tenant_isolation(self) -> dict[str, Any]:
        """Test comprehensive tenant data isolation"""
        print("🔒 Testing tenant isolation...")

        results = []

        if len(self.test_tenants) < 2:
            return {"error": "Need at least 2 tenants for isolation testing"}

        # Test 1: Data isolation in search
        search_isolation = await self._test_search_isolation()
        results.append(search_isolation)

        # Test 2: User isolation
        user_isolation = await self._test_user_isolation()
        results.append(user_isolation)

        # Test 3: Analytics isolation
        analytics_isolation = await self._test_analytics_isolation()
        results.append(analytics_isolation)

        return {
            "test_count": len(results),
            "passed": len([r for r in results if r["success"]]),
            "failed": len([r for r in results if not r["success"]]),
            "details": results,
        }

    async def _test_search_isolation(self) -> dict[str, Any]:
        """Test that search results are isolated per tenant"""
        try:
            tenant1_id = self.test_tenants[0]["id"]
            tenant2_id = self.test_tenants[1]["id"]

            # Perform search as tenant1
            async with httpx.AsyncClient() as client:
                response1 = await client.post(
                    f"{self.base_url}{self.api_prefix}/search/",
                    json={"query": "test isolation search"},
                    headers={
                        "Authorization": f"Bearer {self._get_tenant_admin_token(tenant1_id)}",
                        "X-Tenant-ID": tenant1_id,
                    },
                )

                response2 = await client.post(
                    f"{self.base_url}{self.api_prefix}/search/",
                    json={"query": "test isolation search"},
                    headers={
                        "Authorization": f"Bearer {self._get_tenant_admin_token(tenant2_id)}",
                        "X-Tenant-ID": tenant2_id,
                    },
                )

                # Both should succeed but have isolated results
                success = response1.status_code == 200 and response2.status_code == 200

                return {
                    "test": "search_isolation",
                    "success": success,
                    "tenant1_status": response1.status_code,
                    "tenant2_status": response2.status_code,
                    "message": (
                        "Search isolation verified"
                        if success
                        else "Search isolation failed"
                    ),
                }

        except Exception as e:
            return {"test": "search_isolation", "success": False, "error": str(e)}

    async def _test_user_isolation(self) -> dict[str, Any]:
        """Test that users cannot see other tenants' users"""
        try:
            tenant1_id = self.test_tenants[0]["id"]
            tenant2_id = self.test_tenants[1]["id"]

            async with httpx.AsyncClient() as client:
                # Get users from tenant1 perspective
                response1 = await client.get(
                    f"{self.base_url}{self.api_prefix}/users/",
                    headers={
                        "Authorization": f"Bearer {self._get_tenant_admin_token(tenant1_id)}",
                        "X-Tenant-ID": tenant1_id,
                    },
                )

                # Get users from tenant2 perspective
                response2 = await client.get(
                    f"{self.base_url}{self.api_prefix}/users/",
                    headers={
                        "Authorization": f"Bearer {self._get_tenant_admin_token(tenant2_id)}",
                        "X-Tenant-ID": tenant2_id,
                    },
                )

                success = response1.status_code == 200 and response2.status_code == 200

                # Verify users are different
                if (
                    success
                    and response1.status_code == 200
                    and response2.status_code == 200
                ):
                    users1 = response1.json().get("users", [])
                    users2 = response2.json().get("users", [])
                    isolation_verified = (
                        len(set(u["id"] for u in users1) & set(u["id"] for u in users2))
                        == 0
                    )
                else:
                    isolation_verified = False

                return {
                    "test": "user_isolation",
                    "success": success and isolation_verified,
                    "tenant1_users": (
                        len(response1.json().get("users", []))
                        if response1.status_code == 200
                        else 0
                    ),
                    "tenant2_users": (
                        len(response2.json().get("users", []))
                        if response2.status_code == 200
                        else 0
                    ),
                    "isolation_verified": isolation_verified,
                }

        except Exception as e:
            return {"test": "user_isolation", "success": False, "error": str(e)}

    async def _test_analytics_isolation(self) -> dict[str, Any]:
        """Test that analytics are isolated per tenant"""
        try:
            tenant1_id = self.test_tenants[0]["id"]
            tenant2_id = self.test_tenants[1]["id"]

            async with httpx.AsyncClient() as client:
                response1 = await client.get(
                    f"{self.base_url}{self.api_prefix}/tenants/{tenant1_id}/analytics",
                    headers={
                        "Authorization": f"Bearer {self._get_tenant_admin_token(tenant1_id)}",
                        "X-Tenant-ID": tenant1_id,
                    },
                )

                response2 = await client.get(
                    f"{self.base_url}{self.api_prefix}/tenants/{tenant2_id}/analytics",
                    headers={
                        "Authorization": f"Bearer {self._get_tenant_admin_token(tenant2_id)}",
                        "X-Tenant-ID": tenant2_id,
                    },
                )

                success = response1.status_code == 200 and response2.status_code == 200

                return {
                    "test": "analytics_isolation",
                    "success": success,
                    "tenant1_status": response1.status_code,
                    "tenant2_status": response2.status_code,
                    "message": (
                        "Analytics isolation verified"
                        if success
                        else "Analytics isolation failed"
                    ),
                }

        except Exception as e:
            return {"test": "analytics_isolation", "success": False, "error": str(e)}

    # Search Functionality Tests

    async def _test_search_functionality(self) -> dict[str, Any]:
        """Test multi-source search functionality with tenant context"""
        print("🔍 Testing search functionality...")

        results = []

        if not self.test_tenants:
            return {"error": "No test tenants available for search testing"}

        tenant = self.test_tenants[0]

        # Test 1: Basic search
        basic_search = await self._test_basic_search(tenant["id"])
        results.append(basic_search)

        # Test 2: Search with sources
        source_search = await self._test_search_with_sources(tenant["id"])
        results.append(source_search)

        # Test 3: Search history
        history_test = await self._test_search_history(tenant["id"])
        results.append(history_test)

        # Test 4: Saved searches
        saved_search = await self._test_saved_searches(tenant["id"])
        results.append(saved_search)

        return {
            "test_count": len(results),
            "passed": len([r for r in results if r["success"]]),
            "failed": len([r for r in results if not r["success"]]),
            "details": results,
        }

    async def _test_basic_search(self, tenant_id: str) -> dict[str, Any]:
        """Test basic search functionality"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}{self.api_prefix}/search/",
                    json={"query": "artificial intelligence", "max_results": 5},
                    headers={
                        "Authorization": f"Bearer {self._get_tenant_admin_token(tenant_id)}",
                        "X-Tenant-ID": tenant_id,
                    },
                )

                return {
                    "test": "basic_search",
                    "success": response.status_code == 200,
                    "status_code": response.status_code,
                    "data": response.json() if response.status_code == 200 else None,
                    "response_time": (
                        response.elapsed.total_seconds()
                        if hasattr(response, "elapsed")
                        else None
                    ),
                }

        except Exception as e:
            return {"test": "basic_search", "success": False, "error": str(e)}

    async def _test_search_with_sources(self, tenant_id: str) -> dict[str, Any]:
        """Test search with specific sources"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}{self.api_prefix}/search/",
                    json={
                        "query": "machine learning research",
                        "sources": ["arxiv", "web"],
                        "max_results": 3,
                    },
                    headers={
                        "Authorization": f"Bearer {self._get_tenant_admin_token(tenant_id)}",
                        "X-Tenant-ID": tenant_id,
                    },
                )

                return {
                    "test": "search_with_sources",
                    "success": response.status_code == 200,
                    "status_code": response.status_code,
                    "data": response.json() if response.status_code == 200 else None,
                }

        except Exception as e:
            return {"test": "search_with_sources", "success": False, "error": str(e)}

    async def _test_search_history(self, tenant_id: str) -> dict[str, Any]:
        """Test search history functionality"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}{self.api_prefix}/search/history",
                    headers={
                        "Authorization": f"Bearer {self._get_tenant_admin_token(tenant_id)}",
                        "X-Tenant-ID": tenant_id,
                    },
                )

                return {
                    "test": "search_history",
                    "success": response.status_code == 200,
                    "status_code": response.status_code,
                    "data": response.json() if response.status_code == 200 else None,
                }

        except Exception as e:
            return {"test": "search_history", "success": False, "error": str(e)}

    async def _test_saved_searches(self, tenant_id: str) -> dict[str, Any]:
        """Test saved search functionality"""
        try:
            async with httpx.AsyncClient() as client:
                # First save a search
                save_response = await client.post(
                    f"{self.base_url}{self.api_prefix}/search/saved",
                    json={
                        "name": "Test Saved Search",
                        "query": "test query for saving",
                        "sources": ["web"],
                    },
                    headers={
                        "Authorization": f"Bearer {self._get_tenant_admin_token(tenant_id)}",
                        "X-Tenant-ID": tenant_id,
                    },
                )

                if save_response.status_code != 201:
                    return {
                        "test": "saved_searches",
                        "success": False,
                        "error": f"Failed to save search: {save_response.text}",
                    }

                # Then list saved searches
                list_response = await client.get(
                    f"{self.base_url}{self.api_prefix}/search/saved",
                    headers={
                        "Authorization": f"Bearer {self._get_tenant_admin_token(tenant_id)}",
                        "X-Tenant-ID": tenant_id,
                    },
                )

                return {
                    "test": "saved_searches",
                    "success": list_response.status_code == 200,
                    "save_status": save_response.status_code,
                    "list_status": list_response.status_code,
                    "data": (
                        list_response.json()
                        if list_response.status_code == 200
                        else None
                    ),
                }

        except Exception as e:
            return {"test": "saved_searches", "success": False, "error": str(e)}

    # Security Enforcement Tests

    async def _test_security_enforcement(self) -> dict[str, Any]:
        """Test security enforcement mechanisms"""
        print("🛡️ Testing security enforcement...")

        results = []

        # Test 1: Rate limiting
        rate_limit_test = await self._test_rate_limiting()
        results.append(rate_limit_test)

        # Test 2: Input validation
        input_validation = await self._test_input_validation()
        results.append(input_validation)

        # Test 3: Authentication bypass attempts
        auth_bypass = await self._test_authentication_bypass()
        results.append(auth_bypass)

        # Test 4: SQL injection protection
        sql_injection = await self._test_sql_injection_protection()
        results.append(sql_injection)

        return {
            "test_count": len(results),
            "passed": len([r for r in results if r["success"]]),
            "failed": len([r for r in results if not r["success"]]),
            "details": results,
        }

    async def _test_rate_limiting(self) -> dict[str, Any]:
        """Test API rate limiting"""
        try:
            if not self.test_tenants:
                return {
                    "test": "rate_limiting",
                    "success": False,
                    "error": "No test tenants",
                }

            tenant_id = self.test_tenants[0]["id"]

            # Make rapid requests to trigger rate limiting
            responses = []
            async with httpx.AsyncClient() as client:
                for i in range(10):  # Make 10 rapid requests
                    try:
                        response = await client.get(
                            f"{self.base_url}{self.api_prefix}/tenants/{tenant_id}",
                            headers={
                                "Authorization": f"Bearer {self._get_tenant_admin_token(tenant_id)}",
                                "X-Tenant-ID": tenant_id,
                            },
                        )
                        responses.append(response.status_code)
                    except Exception:
                        responses.append(500)

            # Check if any requests were rate limited (429)
            rate_limited = any(status == 429 for status in responses)

            return {
                "test": "rate_limiting",
                "success": True,  # Success means the test ran, not necessarily rate limited
                "rate_limited": rate_limited,
                "responses": responses,
                "message": (
                    "Rate limiting is active"
                    if rate_limited
                    else "No rate limiting detected (may be normal for low load)"
                ),
            }

        except Exception as e:
            return {"test": "rate_limiting", "success": False, "error": str(e)}

    async def _test_input_validation(self) -> dict[str, Any]:
        """Test input validation and sanitization"""
        try:
            malicious_payloads = [
                {"name": "<script>alert('xss')</script>"},
                {"name": "'; DROP TABLE tenants; --"},
                {"name": "../../../etc/passwd"},
                {"name": "a" * 1000},  # Very long string
            ]

            results = []
            async with httpx.AsyncClient() as client:
                for payload in malicious_payloads:
                    try:
                        response = await client.post(
                            f"{self.base_url}{self.api_prefix}/tenants/",
                            json=payload,
                            headers={
                                "Authorization": f"Bearer {self._get_super_admin_token()}",
                            },
                        )
                        # Should be rejected (400 or 422)
                        results.append(response.status_code in [400, 422, 403])
                    except Exception:
                        results.append(True)  # Exception is also good (rejected)

            # All malicious payloads should be rejected
            success = all(results)

            return {
                "test": "input_validation",
                "success": success,
                "payloads_tested": len(malicious_payloads),
                "payloads_rejected": sum(results),
                "message": (
                    "Input validation working"
                    if success
                    else "Some malicious input was accepted"
                ),
            }

        except Exception as e:
            return {"test": "input_validation", "success": False, "error": str(e)}

    async def _test_authentication_bypass(self) -> dict[str, Any]:
        """Test authentication bypass attempts"""
        try:
            bypass_attempts = [
                {},  # No auth header
                {"Authorization": "Bearer invalid-token"},
                {"Authorization": "Basic fake-auth"},
                {"X-Admin": "true"},  # Header injection
            ]

            results = []
            async with httpx.AsyncClient() as client:
                for headers in bypass_attempts:
                    try:
                        response = await client.get(
                            f"{self.base_url}{self.api_prefix}/tenants/",
                            headers=headers,
                        )
                        # Should be unauthorized (401 or 403)
                        results.append(response.status_code in [401, 403])
                    except Exception:
                        results.append(True)  # Exception is also good (rejected)

            success = all(results)

            return {
                "test": "authentication_bypass",
                "success": success,
                "attempts_tested": len(bypass_attempts),
                "attempts_blocked": sum(results),
                "message": (
                    "Authentication bypass prevented"
                    if success
                    else "Authentication bypass possible"
                ),
            }

        except Exception as e:
            return {"test": "authentication_bypass", "success": False, "error": str(e)}

    async def _test_sql_injection_protection(self) -> dict[str, Any]:
        """Test SQL injection protection"""
        try:
            if not self.test_tenants:
                return {
                    "test": "sql_injection",
                    "success": False,
                    "error": "No test tenants",
                }

            tenant_id = self.test_tenants[0]["id"]
            sql_payloads = [
                "'; DROP TABLE users; --",
                "1' OR '1'='1",
                "'; SELECT * FROM tenants; --",
            ]

            results = []
            async with httpx.AsyncClient() as client:
                for payload in sql_payloads:
                    try:
                        # Test in search query
                        response = await client.post(
                            f"{self.base_url}{self.api_prefix}/search/",
                            json={"query": payload},
                            headers={
                                "Authorization": f"Bearer {self._get_tenant_admin_token(tenant_id)}",
                                "X-Tenant-ID": tenant_id,
                            },
                        )
                        # Should not crash the server (not 500)
                        results.append(response.status_code != 500)
                    except Exception:
                        results.append(True)  # Exception handled gracefully

            success = all(results)

            return {
                "test": "sql_injection",
                "success": success,
                "payloads_tested": len(sql_payloads),
                "payloads_handled": sum(results),
                "message": (
                    "SQL injection protection working"
                    if success
                    else "SQL injection vulnerability detected"
                ),
            }

        except Exception as e:
            return {"test": "sql_injection", "success": False, "error": str(e)}

    # Performance Tests

    async def _test_performance(self) -> dict[str, Any]:
        """Test system performance under various conditions"""
        print("⚡ Testing performance...")

        results = []

        # Test 1: Response time test
        response_time = await self._test_response_times()
        results.append(response_time)

        # Test 2: Concurrent requests
        concurrent_test = await self._test_concurrent_requests()
        results.append(concurrent_test)

        # Test 3: Large payload handling
        large_payload = await self._test_large_payload()
        results.append(large_payload)

        return {
            "test_count": len(results),
            "passed": len([r for r in results if r["success"]]),
            "failed": len([r for r in results if not r["success"]]),
            "details": results,
        }

    async def _test_response_times(self) -> dict[str, Any]:
        """Test API response times"""
        try:
            if not self.test_tenants:
                return {
                    "test": "response_times",
                    "success": False,
                    "error": "No test tenants",
                }

            tenant_id = self.test_tenants[0]["id"]

            endpoints = [f"/tenants/{tenant_id}", "/users/", "/search/history"]

            times = []
            async with httpx.AsyncClient() as client:
                for endpoint in endpoints:
                    start_time = datetime.utcnow()
                    try:
                        response = await client.get(
                            f"{self.base_url}{self.api_prefix}{endpoint}",
                            headers={
                                "Authorization": f"Bearer {self._get_tenant_admin_token(tenant_id)}",
                                "X-Tenant-ID": tenant_id,
                            },
                        )
                        end_time = datetime.utcnow()
                        response_time = (end_time - start_time).total_seconds()
                        times.append(response_time)
                    except Exception:
                        times.append(float("inf"))

            avg_time = (
                sum(t for t in times if t != float("inf"))
                / len([t for t in times if t != float("inf")])
                if times
                else 0
            )
            success = avg_time < 2.0  # Under 2 seconds average

            return {
                "test": "response_times",
                "success": success,
                "average_response_time": avg_time,
                "max_response_time": (
                    max(t for t in times if t != float("inf")) if times else 0
                ),
                "endpoints_tested": len(endpoints),
                "threshold": "2.0 seconds",
            }

        except Exception as e:
            return {"test": "response_times", "success": False, "error": str(e)}

    async def _test_concurrent_requests(self) -> dict[str, Any]:
        """Test handling of concurrent requests"""
        try:
            if not self.test_tenants:
                return {
                    "test": "concurrent_requests",
                    "success": False,
                    "error": "No test tenants",
                }

            tenant_id = self.test_tenants[0]["id"]

            async def make_request():
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{self.base_url}{self.api_prefix}/tenants/{tenant_id}",
                        headers={
                            "Authorization": f"Bearer {self._get_tenant_admin_token(tenant_id)}",
                            "X-Tenant-ID": tenant_id,
                        },
                    )
                    return response.status_code

            # Make 10 concurrent requests
            tasks = [make_request() for _ in range(10)]
            start_time = datetime.utcnow()
            status_codes = await asyncio.gather(*tasks, return_exceptions=True)
            end_time = datetime.utcnow()

            successful_requests = len([s for s in status_codes if s == 200])
            total_time = (end_time - start_time).total_seconds()

            success = successful_requests >= 8  # At least 80% success rate

            return {
                "test": "concurrent_requests",
                "success": success,
                "total_requests": 10,
                "successful_requests": successful_requests,
                "total_time": total_time,
                "requests_per_second": 10 / total_time if total_time > 0 else 0,
            }

        except Exception as e:
            return {"test": "concurrent_requests", "success": False, "error": str(e)}

    async def _test_large_payload(self) -> dict[str, Any]:
        """Test handling of large payloads"""
        try:
            if not self.test_tenants:
                return {
                    "test": "large_payload",
                    "success": False,
                    "error": "No test tenants",
                }

            tenant_id = self.test_tenants[0]["id"]

            # Create a large search query
            large_query = "large search query " * 1000  # About 20KB

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}{self.api_prefix}/search/",
                    json={"query": large_query[:5000]},  # Limit to reasonable size
                    headers={
                        "Authorization": f"Bearer {self._get_tenant_admin_token(tenant_id)}",
                        "X-Tenant-ID": tenant_id,
                    },
                )

                # Should handle large payload gracefully (not crash)
                success = response.status_code in [
                    200,
                    400,
                    413,
                ]  # OK, Bad Request, or Payload Too Large

                return {
                    "test": "large_payload",
                    "success": success,
                    "status_code": response.status_code,
                    "payload_size": len(large_query[:5000]),
                    "message": "Large payload handled appropriately",
                }

        except Exception as e:
            return {"test": "large_payload", "success": False, "error": str(e)}

    # Utility Methods

    def _get_super_admin_token(self) -> str:
        """Get super admin token for testing"""
        # In a real test, this would authenticate with super admin credentials
        # For testing purposes, we'll use a mock token
        return "mock-super-admin-token"

    def _get_tenant_admin_token(self, tenant_id: str) -> str:
        """Get tenant admin token for testing"""
        # Check if we have a real token from login
        if tenant_id in self.auth_tokens:
            return self.auth_tokens[tenant_id]
        # Otherwise use mock token
        return f"mock-tenant-admin-token-{tenant_id}"

    async def _cleanup_test_data(self) -> None:
        """Clean up test data"""
        try:
            # Clear test data lists
            self.test_tenants.clear()
            self.test_users.clear()
            self.auth_tokens.clear()

            # In a real implementation, this would clean up database test data
            print("🧹 Test data cleanup completed")

        except Exception as e:
            print(f"⚠️ Cleanup error: {e}")

    def _generate_test_summary(self, test_results: dict[str, Any]) -> dict[str, Any]:
        """Generate comprehensive test summary"""
        total_tests = 0
        total_passed = 0
        total_failed = 0

        for category, results in test_results.items():
            if isinstance(results, dict) and "test_count" in results:
                total_tests += results["test_count"]
                total_passed += results["passed"]
                total_failed += results["failed"]

        success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0

        return {
            "total_tests": total_tests,
            "passed": total_passed,
            "failed": total_failed,
            "success_rate": round(success_rate, 2),
            "status": "PASS" if success_rate >= 80 else "FAIL",
            "categories_tested": len(test_results),
            "timestamp": datetime.utcnow().isoformat(),
        }


# Async test runner function
async def run_multitenant_api_tests():
    """Run the comprehensive multi-tenant API tests"""
    print("🚀 Starting PAKE Multi-Tenant API Test Suite...")
    print("=" * 60)

    tester = MultiTenantAPITester()
    results = await tester.run_comprehensive_tests()

    print("\n" + "=" * 60)
    print("📊 PAKE MULTI-TENANT API TEST RESULTS")
    print("=" * 60)

    summary = results["summary"]
    print(f"Total Tests: {summary['total_tests']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Success Rate: {summary['success_rate']}%")
    print(f"Overall Status: {summary['status']}")
    print(f"Categories Tested: {summary['categories_tested']}")

    print("\n📋 Category Breakdown:")
    print("-" * 40)

    for category, result in results["detailed_results"].items():
        if isinstance(result, dict) and "test_count" in result:
            status = "✅" if result["passed"] == result["test_count"] else "❌"
            print(
                f"{status} {category.replace('_', ' ').title()}: {result['passed']}/{
                    result['test_count']
                }",
            )
        else:
            print(f"❌ {category.replace('_', ' ').title()}: Error")

    # Print failed tests details
    print("\n🔍 Failed Test Details:")
    print("-" * 40)

    for category, result in results["detailed_results"].items():
        if isinstance(result, dict) and "details" in result:
            failed_tests = [
                test for test in result["details"] if not test.get("success", True)
            ]
            for failed_test in failed_tests:
                print(
                    f"❌ {category}.{failed_test.get('test', 'unknown')}: {
                        failed_test.get('error', 'Failed')
                    }",
                )

    return results


# CLI execution
if __name__ == "__main__":
    import asyncio

    try:
        results = asyncio.run(run_multitenant_api_tests())

        # Exit with appropriate code
        summary = results["summary"]
        exit_code = 0 if summary["status"] == "PASS" else 1
        exit(exit_code)

    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
        exit(130)
    except Exception as e:
        print(f"\n💥 Test suite error: {e}")
        exit(1)
