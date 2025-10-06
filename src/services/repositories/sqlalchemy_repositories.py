#!/usr/bin/env python3
"""PAKE System - Repository Pattern Implementation (Phase 2 Architectural Refactoring)
Concrete repository implementations using SQLAlchemy with classical mapping.
"""

from abc import ABC
import logging
from typing import Any, TypeVar

import sqlalchemy as sa

from ..domain.interfaces import (
    AbstractRepository,
    AbstractUserRepository,
)
from ..domain.models import (
    User,
    UserRole,
    UserStatus,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BaseRepository(AbstractRepository[T], ABC):
    """Base repository implementation with common functionality."""

    def __init__(self, session_maker: Any, model_class: Any) -> None:
        self._session_maker = session_maker
        self._model_class = model_class

    async def create(self, entity: T) -> T:
        """Create a new entity."""
        try:
            async with self._session_maker() as session:
                orm_entity = self._domain_to_orm(entity)
                session.add(orm_entity)
                await session.commit()
                await session.refresh(orm_entity)
                domain_entity = self._orm_to_domain(orm_entity)
                logger.debug(
                    "Created %s: %s", self._model_class.__name__, domain_entity.id
                )
                return domain_entity
        except (ValueError, RuntimeError) as e:
            logger.error("Failed to create %s: %s", self._model_class.__name__, e)
            raise

    async def get_by_id(self, entity_id: str) -> T | None:
        """Get entity by ID."""
        try:
            async with self._session_maker() as session:
                query = sa.select(self._model_class).where(
                    self._model_class.id == entity_id
                )
                result = await session.execute(query)
                orm_entity = result.scalar_one_or_none()

                if orm_entity:
                    return self._orm_to_domain(orm_entity)
                return None
        except (ValueError, RuntimeError) as e:
            logger.error(
                "Failed to get %s by ID %s: %s",
                self._model_class.__name__,
                entity_id,
                e,
            )
            raise

    async def update(self, entity: T) -> T:
        """Update existing entity."""
        try:
            async with self._session_maker() as session:
                orm_entity = self._domain_to_orm(entity)
                merged_entity = await session.merge(orm_entity)
                await session.commit()
                await session.refresh(merged_entity)
                domain_entity = self._orm_to_domain(merged_entity)
                logger.debug(
                    "Updated %s: %s", self._model_class.__name__, domain_entity.id
                )
                return domain_entity
        except (ValueError, RuntimeError) as e:
            logger.error("Failed to update %s: %s", self._model_class.__name__, e)
            raise

    async def delete(self, entity_id: str) -> bool:
        """Delete entity by ID."""
        try:
            async with self._session_maker() as session:
                query = sa.select(self._model_class).where(
                    self._model_class.id == entity_id
                )
                result = await session.execute(query)
                orm_entity = result.scalar_one_or_none()

                if orm_entity:
                    await session.delete(orm_entity)
                    await session.commit()
                    logger.debug(
                        "Deleted %s: %s", self._model_class.__name__, entity_id
                    )
                    return True
                return False
        except (ValueError, RuntimeError) as e:
            logger.error(
                "Failed to delete %s %s: %s", self._model_class.__name__, entity_id, e
            )
            raise

    async def list(self, limit: int = 100, offset: int = 0) -> list[T]:
        """List entities with pagination."""
        try:
            async with self._session_maker() as session:
                query = sa.select(self._model_class).offset(offset).limit(limit)
                result = await session.execute(query)
                orm_entities = result.scalars().all()
                domain_entities = [
                    self._orm_to_domain(orm_entity) for orm_entity in orm_entities
                ]
                logger.debug(
                    "Listed %s %s entities",
                    len(domain_entities),
                    self._model_class.__name__,
                )
                return domain_entities
        except (ValueError, RuntimeError) as e:
            logger.error(
                "Failed to list %s entities: %s", self._model_class.__name__, e
            )
            raise

    def _domain_to_orm(self, domain_entity: T) -> Any:
        """Convert domain model to ORM model - to be implemented by subclasses."""
        msg = "Subclasses must implement _domain_to_orm"
        raise NotImplementedError(msg)

    def _orm_to_domain(self, orm_entity: Any) -> T:
        """Convert ORM model to domain model - to be implemented by subclasses."""
        msg = "Subclasses must implement _orm_to_domain"
        raise NotImplementedError(msg)


class UserRepository(BaseRepository[User], AbstractUserRepository[User]):
    """User repository implementation."""

    def __init__(self, session_maker: Any) -> None:
        super().__init__(session_maker, UserORM)

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email."""
        try:
            async with self._session_maker() as session:
                query = sa.select(UserORM).where(UserORM.email == email)
                result = await session.execute(query)
                orm_user = result.scalar_one_or_none()

                if orm_user:
                    return self._orm_to_domain(orm_user)
                return None
        except (ValueError, RuntimeError) as e:
            logger.error("Failed to get user by email %s: %s", email, e)
            raise

    async def get_by_tenant(self, tenant_id: str) -> list[User]:
        """Get users by tenant."""
        try:
            async with self._session_maker() as session:
                query = sa.select(UserORM).where(UserORM.tenant_id == tenant_id)
                result = await session.execute(query)
                orm_users = result.scalars().all()
                domain_users = [self._orm_to_domain(orm_user) for orm_user in orm_users]
                logger.debug(
                    "Found %s users for tenant %s", len(domain_users), tenant_id
                )
                return domain_users
        except (ValueError, RuntimeError) as e:
            logger.error("Failed to get users by tenant %s: %s", tenant_id, e)
            raise

    def _domain_to_orm(self, domain_user: User) -> "UserORM":
        """Convert User domain model to UserORM."""
        return UserORM(
            id=domain_user.id,
            email=domain_user.email,
            hashed_password=domain_user.hashed_password,
            tenant_id=domain_user.tenant_id,
            first_name=domain_user.first_name,
            last_name=domain_user.last_name,
            role=domain_user.role.value,
            status=domain_user.status.value,
            created_at=domain_user.created_at,
            updated_at=domain_user.updated_at,
            last_login_at=domain_user.last_login_at,
            metadata=domain_user.metadata,
        )

    def _orm_to_domain(self, orm_user: "UserORM") -> User:
        """Convert UserORM to User domain model."""
        return User(
            id=orm_user.id,
            email=orm_user.email,
            hashed_password=orm_user.hashed_password,
            tenant_id=orm_user.tenant_id,
            first_name=orm_user.first_name,
            last_name=orm_user.last_name,
            role=UserRole(orm_user.role),
            status=UserStatus(orm_user.status),
            created_at=orm_user.created_at,
            updated_at=orm_user.updated_at,
            last_login_at=orm_user.last_login_at,
            metadata=orm_user.metadata or {},
        )


# Import ORM models
from .orm_models import UserORM