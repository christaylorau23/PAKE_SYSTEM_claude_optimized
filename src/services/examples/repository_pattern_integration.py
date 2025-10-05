#!/usr/bin/env python3
"""PAKE System - Repository Pattern Integration Example
Demonstrates how to integrate the Repository Pattern into existing PAKE System services.

This example shows:
1. How to refactor existing services to use repositories
2. How to inject repositories using dependency injection
3. How to maintain backward compatibility
4. How to gradually migrate from direct SQLAlchemy usage
"""

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..business.user_service import UserService
from ..repositories.repository_container import RepositoryContainer, RepositoryFactory

logger = logging.getLogger(__name__)


class PAKESystemService:
    """Example PAKE System service using Repository Pattern."""

    def __init__(self) -> None:
        """Initialize service with repository container or session."""
        if repository_container:
            # Use provided repository container
            self.repository_container = repository_container
        elif session:
            # Create repository container from session
            self.repository_container = RepositoryFactory.create_container(session)
        else:
            msg = "Either repository_container or session must be provided"
            raise ValueError(msg)

        # Initialize services with injected repositories
        self.user_service = UserService(self.repository_container.get_user_repository())

        # TODO: Initialize other services as repositories are implemented
        # self.search_service = SearchService(
        #     self.repository_container.get_search_history_repository()
        # )

    async def create_user_account(
        self,
        username: str,
        email: str,
        password_hash: str,
        full_name: str | None = None,
    ) -> Dict[str, Any]:
        """Create user account with comprehensive business logic."""
        try:
            # Use user service with repository pattern
            user = await self.user_service.create_user(
                username=username,
                email=email,
                password_hash=password_hash,
                full_name=full_name,
            )

            # Additional business logic
            user_stats = await self.user_service.get_user_statistics()

            logger.info("Created user account: %s", user.id)

            return {
                "success": True,
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat(),
                "system_stats": user_stats,
            }

        except ValueError as e:
            logger.warning("User creation failed: %s", e)
            return {
                "success": False,
                "error": str(e),
                "error_type": "validation_error",
            }
        except Exception as e:
            logger.error("Unexpected error creating user: %s", e)
            return {
                "success": False,
                "error": "Internal server error",
                "error_type": "server_error",
            }

    async def authenticate_user(
        self,
        email: str,
        password_hash: str,
    ) -> Dict[str, Any]:
        """Authenticate user with comprehensive business logic."""
        try:
            # Use user service with repository pattern
            user = await self.user_service.authenticate_user(email, password_hash)

            if not user:
                return {
                    "success": False,
                    "error": "Invalid credentials",
                    "error_type": "authentication_error",
                }

            # Additional business logic
            user_stats = await self.user_service.get_user_statistics()

            logger.info("User authenticated: %s", user.id)

            return {
                "success": True,
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "is_admin": user.is_admin,
                "last_login": user.last_login.isoformat() if user.last_login else None,
                "system_stats": user_stats,
            }

        except Exception as e:
            logger.error("Authentication error: %s", e)
            return {
                "success": False,
                "error": "Authentication failed",
                "error_type": "server_error",
            }

    async def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile with business logic."""
        try:
            user = await self.user_service.get_user_by_id(user_id)

            if not user:
                return {
                    "success": False,
                    "error": "User not found",
                    "error_type": "not_found",
                }

            return {
                "success": True,
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "is_active": user.is_active,
                "is_admin": user.is_admin,
                "preferences": user.preferences,
                "created_at": user.created_at.isoformat(),
                "last_login": user.last_login.isoformat() if user.last_login else None,
            }

        except Exception as e:
            logger.error("Error getting user profile: %s", e)
            return {
                "success": False,
                "error": "Failed to retrieve user profile",
                "error_type": "server_error",
            }

    async def update_user_preferences(
        self,
        user_id: str,
        preferences: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update user preferences with business logic."""
        try:
            updated_user = await self.user_service.update_user_profile(
                user_id=user_id, preferences=preferences
            )

            if not updated_user:
                return {
                    "success": False,
                    "error": "User not found",
                    "error_type": "not_found",
                }

            logger.info("Updated preferences for user: %s", user_id)

            return {
                "success": True,
                "user_id": updated_user.id,
                "preferences": updated_user.preferences,
                "updated_at": updated_user.updated_at.isoformat(),
            }

        except ValueError as e:
            logger.warning("Preference update failed: %s", e)
            return {
                "success": False,
                "error": str(e),
                "error_type": "validation_error",
            }
        except Exception as e:
            logger.error("Error updating preferences: %s", e)
            return {
                "success": False,
                "error": "Failed to update preferences",
                "error_type": "server_error",
            }

    async def deactivate_user_account(
        self,
        user_id: str,
        deactivated_by: str,
    ) -> Dict[str, Any]:
        """Deactivate user account with business logic."""
        try:
            success = await self.user_service.deactivate_user(user_id, deactivated_by)

            if not success:
                return {
                    "success": False,
                    "error": "User not found or already inactive",
                    "error_type": "not_found",
                }

            # Get updated user info
            user = await self.user_service.get_user_by_id(user_id)
            user_stats = await self.user_service.get_user_statistics()

            logger.info("User account deactivated: %s by %s", user_id, deactivated_by)

            return {
                "success": True,
                "user_id": user.id,
                "is_active": user.is_active,
                "deactivated_by": deactivated_by,
                "system_stats": user_stats,
            }

        except ValueError as e:
            logger.warning("User deactivation failed: %s", e)
            return {
                "success": False,
                "error": str(e),
                "error_type": "validation_error",
            }
        except Exception as e:
            logger.error("Error deactivating user: %s", e)
            return {
                "success": False,
                "error": "Failed to deactivate user",
                "error_type": "server_error",
            }

    async def search_users(
        self,
        query: str,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Search users with business logic."""
        try:
            users = await self.user_service.search_users(
                query=query, limit=limit, offset=offset
            )

            # Convert users to response format
            user_list = []
            for user in users:
                user_list.append(
                    {
                        "user_id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "full_name": user.full_name,
                        "is_active": user.is_active,
                        "is_admin": user.is_admin,
                        "created_at": user.created_at.isoformat(),
                    }
                )

            return {
                "success": True,
                "users": user_list,
                "total_found": len(user_list),
                "query": query,
                "limit": limit,
                "offset": offset,
            }

        except ValueError as e:
            logger.warning("User search failed: %s", e)
            return {
                "success": False,
                "error": str(e),
                "error_type": "validation_error",
            }
        except Exception as e:
            logger.error("Error searching users: %s", e)
            return {
                "success": False,
                "error": "Search failed",
                "error_type": "server_error",
            }

    async def get_system_statistics(self) -> Dict[str, Any]:
        """Get comprehensive system statistics."""
        try:
            user_stats = await self.user_service.get_user_statistics()

            # TODO: Add other service statistics as repositories are implemented
            # search_stats = await self.search_service.get_statistics()
            # system_stats = await self.system_service.get_statistics()

            return {
                "success": True,
                "statistics": {
                    "users": user_stats,
                    # "searches": search_stats,
                    # "system": system_stats,
                },
                "timestamp": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            logger.error("Error getting system statistics: %s", e)
            return {
                "success": False,
                "error": "Failed to retrieve statistics",
                "error_type": "server_error",
            }

    async def health_check(self) -> Dict[str, Any]:
        """Comprehensive health check."""
        try:
            # Check repository container health
            repo_health = await self.repository_container.health_check()

            # Check user service health
            user_service_health = await self.user_service.health_check()

            # Determine overall health
            overall_healthy = (
                repo_health["status"] == "healthy"
                and user_service_health["status"] == "healthy"
            )

            return {
                "status": "healthy" if overall_healthy else "unhealthy",
                "services": {
                    "repository_container": repo_health,
                    "user_service": user_service_health,
                },
                "timestamp": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            logger.error("Health check failed: %s", e)
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(UTC).isoformat(),
            }


# Example usage functions
async def create_service_with_database_session(
    session: AsyncSession,
) -> PAKESystemService:
    """Create PAKE System service with database session."""
    return PAKESystemService(session=session)


async def create_service_with_repository_container(
    container: RepositoryContainer,
) -> PAKESystemService:
    """Create PAKE System service with repository container."""
    return PAKESystemService(repository_container=container)


async def create_service_for_testing() -> PAKESystemService:
    """Create PAKE System service with fake repositories for testing."""
    from ..repositories.repository_container import FakeRepositoryContainer

    fake_container = FakeRepositoryContainer()
    return PAKESystemService(repository_container=fake_container)


# Example integration with FastAPI
def create_fastapi_dependency(session: AsyncSession) -> PAKESystemService:
    """Create PAKE System service as FastAPI dependency."""
    return PAKESystemService(session=session)


# Example usage in existing code
async def migrate_existing_service_to_repository_pattern(self) -> None:
    """Example of how to migrate existing service to repository pattern."""
    # Before: Direct SQLAlchemy usage
    # async def old_create_user(self) -> None:
    #     user_orm = UserORM(username=username, email=email)
    #     session.add(user_orm)
    #     await session.commit()
    #     return user_orm

    # After: Repository pattern usage
    async def new_create_user(self) -> None:
        return await service.create_user_account(
            username=username, email=email, password_hash="hashed_password"
        )

    logger.info("Migration example completed")


if __name__ == "__main__":
    # Example usage
    import asyncio

    async def main(self) -> None:
        # Create service for testing
        service = await create_service_for_testing()

        # Test user creation
        result = await service.create_user_account(
            username="testuser",
            email="test@example.com",
            password_hash="hashed_password",
            full_name="Test User",
        )

        print("User creation result:", result)

        # Test health check
        health = await service.health_check()
        print("Health check result:", health)

    asyncio.run(main())
