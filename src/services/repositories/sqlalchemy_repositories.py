#!/usr/bin/env python3
"""PAKE System - Repository Pattern Implementation (Phase 2 Architectural Refactoring)
Concrete repository implementations using SQLAlchemy with classical mapping.
"""

import logging
from abc import ABC
from typing import Any, Generic, Optional, TypeVar

import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from ..domain.interfaces import (
    AbstractContentRepository,
    AbstractRepository,
    AbstractUserRepository,
)
from ..domain.models import (
    ContentItem,
    ContentSource,
    ContentType,
    ProcessingStatus,
    User,
    UserRole,
    UserStatus,
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


class BaseRepository(AbstractRepository[T], ABC):
    """Base repository implementation with common functionality"""
    
    def __init__(self, session_maker: sessionmaker, model_class: type):
        self._session_maker = session_maker
        self._model_class = model_class
    
    async def create(self, entity: T) -> T:
        """Create a new entity"""
        try:
            async with self._session_maker() as session:
                orm_entity = self._domain_to_orm(entity)
                session.add(orm_entity)
                await session.commit()
                await session.refresh(orm_entity)
                domain_entity = self._orm_to_domain(orm_entity)
                logger.debug(f"Created {self._model_class.__name__}: {domain_entity.id}")
                return domain_entity
        except Exception as e:
            logger.error(f"Failed to create {self._model_class.__name__}: {e}")
            raise
    
    async def get_by_id(self, entity_id: str) -> Optional[T]:
        """Get entity by ID"""
        try:
            async with self._session_maker() as session:
                query = sa.select(self._model_class).where(self._model_class.id == entity_id)
                result = await session.execute(query)
                orm_entity = result.scalar_one_or_none()
                
                if orm_entity:
                    return self._orm_to_domain(orm_entity)
                return None
        except Exception as e:
            logger.error(f"Failed to get {self._model_class.__name__} by ID {entity_id}: {e}")
            raise
    
    async def update(self, entity: T) -> T:
        """Update existing entity"""
        try:
            async with self._session_maker() as session:
                orm_entity = self._domain_to_orm(entity)
                merged_entity = await session.merge(orm_entity)
                await session.commit()
                await session.refresh(merged_entity)
                domain_entity = self._orm_to_domain(merged_entity)
                logger.debug(f"Updated {self._model_class.__name__}: {domain_entity.id}")
                return domain_entity
        except Exception as e:
            logger.error(f"Failed to update {self._model_class.__name__}: {e}")
            raise
    
    async def delete(self, entity_id: str) -> bool:
        """Delete entity by ID"""
        try:
            async with self._session_maker() as session:
                query = sa.select(self._model_class).where(self._model_class.id == entity_id)
                result = await session.execute(query)
                orm_entity = result.scalar_one_or_none()
                
                if orm_entity:
                    await session.delete(orm_entity)
                    await session.commit()
                    logger.debug(f"Deleted {self._model_class.__name__}: {entity_id}")
                    return True
                return False
        except Exception as e:
            logger.error(f"Failed to delete {self._model_class.__name__} {entity_id}: {e}")
            raise
    
    async def list(self, limit: int = 100, offset: int = 0) -> list[T]:
        """List entities with pagination"""
        try:
            async with self._session_maker() as session:
                query = sa.select(self._model_class).offset(offset).limit(limit)
                result = await session.execute(query)
                orm_entities = result.scalars().all()
                domain_entities = [self._orm_to_domain(orm_entity) for orm_entity in orm_entities]
                logger.debug(f"Listed {len(domain_entities)} {self._model_class.__name__} entities")
                return domain_entities
        except Exception as e:
            logger.error(f"Failed to list {self._model_class.__name__} entities: {e}")
            raise
    
    def _domain_to_orm(self, domain_entity: T) -> Any:
        """Convert domain model to ORM model - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement _domain_to_orm")
    
    def _orm_to_domain(self, orm_entity: Any) -> T:
        """Convert ORM model to domain model - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement _orm_to_domain")


class UserRepository(BaseRepository[User], AbstractUserRepository[User]):
    """User repository implementation"""
    
    def __init__(self, session_maker: sessionmaker):
        super().__init__(session_maker, UserORM)
    
    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        try:
            async with self._session_maker() as session:
                query = sa.select(UserORM).where(UserORM.email == email)
                result = await session.execute(query)
                orm_user = result.scalar_one_or_none()
                
                if orm_user:
                    return self._orm_to_domain(orm_user)
                return None
        except Exception as e:
            logger.error(f"Failed to get user by email {email}: {e}")
            raise
    
    async def get_by_tenant(self, tenant_id: str) -> list[User]:
        """Get users by tenant"""
        try:
            async with self._session_maker() as session:
                query = sa.select(UserORM).where(UserORM.tenant_id == tenant_id)
                result = await session.execute(query)
                orm_users = result.scalars().all()
                domain_users = [self._orm_to_domain(orm_user) for orm_user in orm_users]
                logger.debug(f"Found {len(domain_users)} users for tenant {tenant_id}")
                return domain_users
        except Exception as e:
            logger.error(f"Failed to get users by tenant {tenant_id}: {e}")
            raise
    
    def _domain_to_orm(self, domain_user: User) -> 'UserORM':
        """Convert User domain model to UserORM"""
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
            metadata=domain_user.metadata
        )
    
    def _orm_to_domain(self, orm_user: 'UserORM') -> User:
        """Convert UserORM to User domain model"""
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
            metadata=orm_user.metadata or {}
        )


# Import ORM models
from .orm_models import UserORM