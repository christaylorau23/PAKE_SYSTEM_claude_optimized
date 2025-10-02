#!/usr/bin/env python3
"""PAKE System - Refactored User Service (Phase 2 Architectural Refactoring)
Single Responsibility Principle compliant user service with dependency injection.

This service demonstrates the refactored architecture by:
1. Following Single Responsibility Principle
2. Using dependency injection for all dependencies
3. Depending on abstractions, not concrete implementations
4. Being easily testable with mock dependencies
"""

import logging
from datetime import datetime
from typing import Any

from ..domain.interfaces import (
    AbstractAuthenticationService,
    AbstractNotificationService,
    AbstractUserRepository,
    ServiceResult,
    ServiceStatus,
)
from ..domain.models import User, UserRole, UserStatus, create_user

logger = logging.getLogger(__name__)


class UserService:
    """Refactored User Service following Single Responsibility Principle.
    
    Single Responsibility: Managing user lifecycle operations
    Dependencies: Injected through constructor (Dependency Injection)
    """
    
    def __init__(self,
                 user_repository: AbstractUserRepository[User],
                 auth_service: AbstractAuthenticationService,
                 notification_service: AbstractNotificationService):
        """Initialize UserService with injected dependencies"""
        self.user_repository = user_repository
        self.auth_service = auth_service
        self.notification_service = notification_service
        logger.info("UserService initialized with dependency injection")
    
    async def create_user(self, email: str, password: str, user_data: dict[str, Any]) -> ServiceResult[dict[str, Any]]:
        """Create new user with authentication and notification.
        
        This method orchestrates the user creation process by delegating
        specific responsibilities to specialized services.
        """
        try:
            # 1. Validate input data
            validation_result = self._validate_user_data(email, password, user_data)
            if not validation_result.is_valid:
                return ServiceResult(
                    status=ServiceStatus.FAILED,
                    error=f"Validation failed: {validation_result.error}"
                )
            
            # 2. Create user account through authentication service
            auth_result = await self.auth_service.create_user({
                'email': email,
                'password': password,
                'user_data': user_data
            })
            
            if auth_result.status != ServiceStatus.SUCCESS:
                return ServiceResult(
                    status=ServiceStatus.FAILED,
                    error=f"Authentication service failed: {auth_result.error}"
                )
            
            # 3. Create domain model
            user = create_user(
                email=email,
                hashed_password=auth_result.data['hashed_password'],
                tenant_id=user_data.get('tenant_id', 'default'),
                first_name=user_data.get('first_name'),
                last_name=user_data.get('last_name'),
                role=UserRole(user_data.get('role', 'user')),
                status=UserStatus.ACTIVE
            )
            
            # 4. Persist user through repository
            persisted_user = await self.user_repository.create(user)
            
            # 5. Send welcome notification
            notification_result = await self.notification_service.send_welcome_email(
                email=email,
                user_data={
                    'user_id': persisted_user.id,
                    'name': persisted_user.full_name,
                    'tenant_id': persisted_user.tenant_id
                }
            )
            
            if notification_result.status != ServiceStatus.SUCCESS:
                logger.warning(f"Welcome email failed for user {persisted_user.id}: {notification_result.error}")
            
            # 6. Return success result
            return ServiceResult(
                status=ServiceStatus.SUCCESS,
                data={
                    'user_id': persisted_user.id,
                    'email': persisted_user.email,
                    'name': persisted_user.full_name,
                    'tenant_id': persisted_user.tenant_id,
                    'role': persisted_user.role.value,
                    'status': persisted_user.status.value,
                    'created_at': persisted_user.created_at.isoformat()
                },
                metadata={
                    'notification_sent': notification_result.status == ServiceStatus.SUCCESS
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to create user {email}: {e}")
            return ServiceResult(
                status=ServiceStatus.FAILED,
                error=f"User creation failed: {str(e)}"
            )
    
    async def get_user_profile(self, user_id: str) -> ServiceResult[dict[str, Any]]:
        """Get user profile information.
        
        Single responsibility: Retrieving user profile data
        """
        try:
            # Get user from repository
            user = await self.user_repository.get_by_id(user_id)
            
            if not user:
                return ServiceResult(
                    status=ServiceStatus.FAILED,
                    error=f"User {user_id} not found"
                )
            
            # Return user profile data
            return ServiceResult(
                status=ServiceStatus.SUCCESS,
                data={
                    'user_id': user.id,
                    'email': user.email,
                    'name': user.full_name,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'role': user.role.value,
                    'status': user.status.value,
                    'tenant_id': user.tenant_id,
                    'created_at': user.created_at.isoformat(),
                    'updated_at': user.updated_at.isoformat(),
                    'last_login_at': user.last_login_at.isoformat() if user.last_login_at else None,
                    'is_active': user.is_active
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to get user profile {user_id}: {e}")
            return ServiceResult(
                status=ServiceStatus.FAILED,
                error=f"Profile retrieval failed: {str(e)}"
            )
    
    async def update_user_profile(self, user_id: str, updates: dict[str, Any]) -> ServiceResult[dict[str, Any]]:
        """Update user profile information.
        
        Single responsibility: Updating user profile data
        """
        try:
            # Get existing user
            user = await self.user_repository.get_by_id(user_id)
            
            if not user:
                return ServiceResult(
                    status=ServiceStatus.FAILED,
                    error=f"User {user_id} not found"
                )
            
            # Apply updates (create new immutable instance)
            updated_user = User(
                id=user.id,
                email=updates.get('email', user.email),
                hashed_password=user.hashed_password,  # Password updates handled separately
                tenant_id=user.tenant_id,
                first_name=updates.get('first_name', user.first_name),
                last_name=updates.get('last_name', user.last_name),
                role=UserRole(updates.get('role', user.role.value)),
                status=UserStatus(updates.get('status', user.status.value)),
                created_at=user.created_at,
                updated_at=datetime.utcnow(),
                last_login_at=user.last_login_at,
                metadata=updates.get('metadata', user.metadata)
            )
            
            # Persist updated user
            persisted_user = await self.user_repository.update(updated_user)
            
            return ServiceResult(
                status=ServiceStatus.SUCCESS,
                data={
                    'user_id': persisted_user.id,
                    'email': persisted_user.email,
                    'name': persisted_user.full_name,
                    'updated_at': persisted_user.updated_at.isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to update user profile {user_id}: {e}")
            return ServiceResult(
                status=ServiceStatus.FAILED,
                error=f"Profile update failed: {str(e)}"
            )
    
    async def get_users_by_tenant(self, tenant_id: str) -> ServiceResult[list[dict[str, Any]]]:
        """Get all users for a specific tenant.
        
        Single responsibility: Retrieving tenant users
        """
        try:
            users = await self.user_repository.get_by_tenant(tenant_id)
            
            user_data = []
            for user in users:
                user_data.append({
                    'user_id': user.id,
                    'email': user.email,
                    'name': user.full_name,
                    'role': user.role.value,
                    'status': user.status.value,
                    'created_at': user.created_at.isoformat(),
                    'last_login_at': user.last_login_at.isoformat() if user.last_login_at else None,
                    'is_active': user.is_active
                })
            
            return ServiceResult(
                status=ServiceStatus.SUCCESS,
                data=user_data,
                metadata={'count': len(user_data)}
            )
            
        except Exception as e:
            logger.error(f"Failed to get users for tenant {tenant_id}: {e}")
            return ServiceResult(
                status=ServiceStatus.FAILED,
                error=f"Tenant users retrieval failed: {str(e)}"
            )
    
    def _validate_user_data(self, email: str, password: str, user_data: dict[str, Any]) -> 'ValidationResult':
        """Validate user input data.
        
        Single responsibility: Input validation
        """
        errors = []
        
        # Email validation
        if not email or '@' not in email:
            errors.append("Invalid email address")
        
        # Password validation
        if not password or len(password) < 8:
            errors.append("Password must be at least 8 characters")
        
        # User data validation
        if 'tenant_id' in user_data and not user_data['tenant_id']:
            errors.append("Tenant ID cannot be empty")
        
        if 'role' in user_data and user_data['role'] not in [role.value for role in UserRole]:
            errors.append(f"Invalid role: {user_data['role']}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            error='; '.join(errors) if errors else None
        )


class ValidationResult:
    """Simple validation result container"""
    
    def __init__(self, is_valid: bool, error: str = None):
        self.is_valid = is_valid
        self.error = error
