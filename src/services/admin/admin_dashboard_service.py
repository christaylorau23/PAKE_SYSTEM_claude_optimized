#!/usr/bin/env python3
"""PAKE System - Admin Dashboard Service
Comprehensive admin dashboard with user management, system monitoring, and analytics.
"""

import asyncio
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from ..authentication.jwt_auth_service import JWTAuthenticationService
from ..caching.redis_cache_service import RedisCacheService
from ..database.postgresql_service import PostgreSQLService
from ..realtime.websocket_manager import WebSocketManager
from ..user.search_history_service import SearchHistoryService

logger = logging.getLogger(__name__)


class UserAction(Enum):
    """Admin actions on users"""

    ACTIVATE = "activate"
    DEACTIVATE = "deactivate"
    PROMOTE_ADMIN = "promote_admin"
    DEMOTE_ADMIN = "demote_admin"
    RESET_PASSWORD = "reset_REDACTED_SECRET"
    DELETE_USER = "delete_user"
    CLEAR_HISTORY = "clear_history"


class SystemMetricType(Enum):
    """System metric categories"""

    PERFORMANCE = "performance"
    USAGE = "usage"
    SECURITY = "security"
    ERRORS = "errors"
    CACHE = "cache"
    DATABASE = "database"


@dataclass
class UserSummary:
    """User summary for admin dashboard"""

    id: str
    username: str
    email: str
    full_name: str | None
    is_active: bool
    is_admin: bool
    created_at: datetime
    last_login: datetime | None
    search_count: int
    total_execution_time: float
    avg_quality_score: float | None
    is_online: bool
    preferences: dict[str, Any]


@dataclass
class SystemHealth:
    """System health status"""

    status: str  # healthy, degraded, unhealthy
    uptime_seconds: float
    cpu_usage: float
    memory_usage: float
    disk_usage: float
    active_connections: int
    cache_hit_rate: float
    avg_response_time: float
    error_rate: float
    database_status: str
    redis_status: str
    websocket_status: str


@dataclass
class SystemAnalytics:
    """Comprehensive system analytics"""

    total_users: int
    active_users_24h: int
    total_searches: int
    searches_24h: int
    avg_search_time: float
    cache_hit_rate: float
    top_queries: list[tuple[str, int]]
    user_growth: list[tuple[str, int]]  # date, count
    search_trends: list[tuple[str, int]]  # date, count
    source_distribution: dict[str, int]
    quality_metrics: dict[str, float]
    error_summary: dict[str, int]


@dataclass
class SecurityEvent:
    """Security event tracking"""

    id: str
    event_type: str
    severity: str
    user_id: str | None
    ip_address: str
    user_agent: str
    details: dict[str, Any]
    timestamp: datetime
    resolved: bool = False


class AdminDashboardService:
    """Comprehensive admin dashboard service.

    Features:
    - User management and monitoring
    - System health and performance
    - Real-time analytics
    - Security monitoring
    - Configuration management
    - Maintenance operations
    """

    def __init__(
        self,
        database_service: PostgreSQLService,
        auth_service: JWTAuthenticationService,
        search_history_service: SearchHistoryService,
        websocket_manager: WebSocketManager | None = None,
        cache_service: RedisCacheService | None = None,
    ):
        self.database_service = database_service
        self.auth_service = auth_service
        self.search_history_service = search_history_service
        self.websocket_manager = websocket_manager
        self.cache_service = cache_service

        # Cache settings
        self.CACHE_TTL_SHORT = 300  # 5 minutes
        self.CACHE_TTL_MEDIUM = 1800  # 30 minutes
        self.CACHE_TTL_LONG = 3600  # 1 hour

        logger.info("👨‍💼 Admin Dashboard Service initialized")

    # User Management

    async def get_all_users(
        self,
        limit: int = 50,
        offset: int = 0,
        search_query: str | None = None,
        filter_active: bool | None = None,
        filter_admin: bool | None = None,
    ) -> dict[str, Any]:
        """Get all users with filtering and pagination"""
        try:
            # Build filters
            filters = {}
            if search_query:
                filters["search"] = search_query
            if filter_active is not None:
                filters["is_active"] = filter_active
            if filter_admin is not None:
                filters["is_admin"] = filter_admin

            # Get users from database
            users_data = await self.database_service.get_users_paginated(
                limit=limit,
                offset=offset,
                filters=filters,
            )

            # Get online status from WebSocket manager
            online_users = set()
            if self.websocket_manager:
                online_users = set(self.websocket_manager.connected_users.keys())

            # Enhance user data with analytics
            user_summaries = []
            for user in users_data["users"]:
                # Get user search statistics
                search_stats = await self._get_user_search_stats(user["id"])

                user_summary = UserSummary(
                    id=user["id"],
                    username=user["username"],
                    email=user["email"],
                    full_name=user.get("full_name"),
                    is_active=user["is_active"],
                    is_admin=user["is_admin"],
                    created_at=user["created_at"],
                    last_login=user.get("last_login"),
                    search_count=search_stats["total_searches"],
                    total_execution_time=search_stats["total_execution_time"],
                    avg_quality_score=search_stats["avg_quality_score"],
                    is_online=user["id"] in online_users,
                    preferences=user.get("preferences", {}),
                )
                user_summaries.append(user_summary)

            return {
                "users": [asdict(summary) for summary in user_summaries],
                "total_count": users_data["total_count"],
                "page_info": {
                    "limit": limit,
                    "offset": offset,
                    "has_next": offset + limit < users_data["total_count"],
                },
            }

        except Exception as e:
            logger.error(f"Failed to get users: {e}")
            raise

    async def get_user_details(self, user_id: str) -> dict[str, Any]:
        """Get detailed user information"""
        try:
            # Get user data
            user = await self.database_service.get_user_by_id(user_id)
            if not user:
                raise ValueError("User not found")

            # Get search history analytics
            search_analytics = await self.search_history_service.get_user_analytics(
                user_id,
                days=30,
            )

            # Get recent search history
            recent_searches = await self.search_history_service.get_user_search_history(
                user_id,
                limit=10,
            )

            # Get user preferences
            preferences = await self.search_history_service.get_user_preferences(
                user_id,
            )

            # Check online status
            is_online = False
            session_info = None
            if (
                self.websocket_manager
                and user_id in self.websocket_manager.connected_users
            ):
                is_online = True
                connected_user = self.websocket_manager.connected_users[user_id]
                session_info = {
                    "session_id": connected_user.session_id,
                    "connected_at": connected_user.connected_at.isoformat(),
                    "last_activity": connected_user.last_activity.isoformat(),
                }

            return {
                "user": user,
                "analytics": asdict(search_analytics),
                "recent_searches": [asdict(search) for search in recent_searches],
                "preferences": asdict(preferences),
                "online_status": {"is_online": is_online, "session_info": session_info},
            }

        except Exception as e:
            logger.error(f"Failed to get user details: {e}")
            raise

    async def perform_user_action(
        self,
        admin_user_id: str,
        target_user_id: str,
        action: UserAction,
        reason: str | None = None,
        **kwargs,
    ) -> bool:
        """Perform admin action on user"""
        try:
            # Verify admin permissions
            admin_user = await self.database_service.get_user_by_id(admin_user_id)
            if not admin_user or not admin_user.get("is_admin"):
                raise ValueError("Insufficient permissions")

            # Get target user
            target_user = await self.database_service.get_user_by_id(target_user_id)
            if not target_user:
                raise ValueError("Target user not found")

            success = False

            if action == UserAction.ACTIVATE:
                success = await self.database_service.update_user_status(
                    target_user_id,
                    is_active=True,
                )

            elif action == UserAction.DEACTIVATE:
                success = await self.database_service.update_user_status(
                    target_user_id,
                    is_active=False,
                )
                # Disconnect user if online
                if (
                    self.websocket_manager
                    and target_user_id in self.websocket_manager.connected_users
                ):
                    user_conn = self.websocket_manager.connected_users[target_user_id]
                    await user_conn.websocket.close(
                        code=1008,
                        reason="Account deactivated",
                    )

            elif action == UserAction.PROMOTE_ADMIN:
                success = await self.database_service.update_user_admin_status(
                    target_user_id,
                    is_admin=True,
                )

            elif action == UserAction.DEMOTE_ADMIN:
                success = await self.database_service.update_user_admin_status(
                    target_user_id,
                    is_admin=False,
                )

            elif action == UserAction.RESET_PASSWORD:
                # Generate temporary REDACTED_SECRET
                temp_REDACTED_SECRET = kwargs.get("temp_REDACTED_SECRET", "TempPass123!")
                REDACTED_SECRET_hash = self.auth_service.hash_REDACTED_SECRET(temp_REDACTED_SECRET)
                success = await self.database_service.update_user_REDACTED_SECRET(
                    target_user_id,
                    REDACTED_SECRET_hash,
                )

            elif action == UserAction.DELETE_USER:
                success = await self.database_service.delete_user(target_user_id)

            elif action == UserAction.CLEAR_HISTORY:
                before_date = kwargs.get("before_date")
                cleared_count = await self.search_history_service.clear_user_history(
                    target_user_id,
                    before_date,
                )
                success = cleared_count > 0

            # Log the action
            if success:
                await self._log_admin_action(
                    admin_user_id=admin_user_id,
                    target_user_id=target_user_id,
                    action=action.value,
                    reason=reason,
                    details=kwargs,
                )

                # Notify via WebSocket if available
                if self.websocket_manager:
                    await self.websocket_manager.notify_system_alert(
                        {
                            "type": "admin_action",
                            "admin_user": admin_user["username"],
                            "target_user": target_user["username"],
                            "action": action.value,
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                        admin_only=True,
                    )

            return success

        except Exception as e:
            logger.error(f"Failed to perform user action {action}: {e}")
            raise

    # System Monitoring

    async def get_system_health(self) -> SystemHealth:
        """Get current system health status"""
        try:
            # Check cache first
            cache_key = "admin:system_health"
            if self.cache_service:
                cached_health = await self.cache_service.get(cache_key)
                if cached_health:
                    return SystemHealth(**cached_health)

            # Gather system metrics
            health_checks = await asyncio.gather(
                self._check_database_health(),
                self._check_redis_health(),
                self._check_websocket_health(),
                self._get_performance_metrics(),
                return_exceptions=True,
            )

            db_status = (
                health_checks[0]
                if not isinstance(health_checks[0], Exception)
                else "error"
            )
            redis_status = (
                health_checks[1]
                if not isinstance(health_checks[1], Exception)
                else "error"
            )
            ws_status = (
                health_checks[2]
                if not isinstance(health_checks[2], Exception)
                else "error"
            )
            performance = (
                health_checks[3] if not isinstance(health_checks[3], Exception) else {}
            )

            # Calculate overall status
            statuses = [db_status, redis_status, ws_status]
            if all(s == "healthy" for s in statuses):
                overall_status = "healthy"
            elif any(s == "error" for s in statuses):
                overall_status = "unhealthy"
            else:
                overall_status = "degraded"

            # Get WebSocket connection count
            active_connections = 0
            if self.websocket_manager:
                active_connections = len(self.websocket_manager.connected_users)

            health = SystemHealth(
                status=overall_status,
                uptime_seconds=performance.get("uptime_seconds", 0),
                cpu_usage=performance.get("cpu_usage", 0),
                memory_usage=performance.get("memory_usage", 0),
                disk_usage=performance.get("disk_usage", 0),
                active_connections=active_connections,
                cache_hit_rate=performance.get("cache_hit_rate", 0),
                avg_response_time=performance.get("avg_response_time", 0),
                error_rate=performance.get("error_rate", 0),
                database_status=db_status,
                redis_status=redis_status,
                websocket_status=ws_status,
            )

            # Cache the health status
            if self.cache_service:
                await self.cache_service.set(
                    cache_key,
                    asdict(health),
                    ttl=self.CACHE_TTL_SHORT,
                )

            return health

        except Exception as e:
            logger.error(f"Failed to get system health: {e}")
            raise

    async def get_system_analytics(self, days: int = 30) -> SystemAnalytics:
        """Get comprehensive system analytics"""
        try:
            # Check cache
            cache_key = f"admin:system_analytics:{days}"
            if self.cache_service:
                cached_analytics = await self.cache_service.get(cache_key)
                if cached_analytics:
                    return SystemAnalytics(**cached_analytics)

            # Calculate date range
            start_date = datetime.utcnow() - timedelta(days=days)

            # Gather analytics data
            analytics_data = await asyncio.gather(
                self._get_user_statistics(start_date),
                self._get_search_statistics(start_date),
                self._get_performance_statistics(start_date),
                self._get_error_statistics(start_date),
                return_exceptions=True,
            )

            user_stats = (
                analytics_data[0]
                if not isinstance(analytics_data[0], Exception)
                else {}
            )
            search_stats = (
                analytics_data[1]
                if not isinstance(analytics_data[1], Exception)
                else {}
            )
            perf_stats = (
                analytics_data[2]
                if not isinstance(analytics_data[2], Exception)
                else {}
            )
            error_stats = (
                analytics_data[3]
                if not isinstance(analytics_data[3], Exception)
                else {}
            )

            analytics = SystemAnalytics(
                total_users=user_stats.get("total_users", 0),
                active_users_24h=user_stats.get("active_users_24h", 0),
                total_searches=search_stats.get("total_searches", 0),
                searches_24h=search_stats.get("searches_24h", 0),
                avg_search_time=search_stats.get("avg_search_time", 0),
                cache_hit_rate=perf_stats.get("cache_hit_rate", 0),
                top_queries=search_stats.get("top_queries", []),
                user_growth=user_stats.get("user_growth", []),
                search_trends=search_stats.get("search_trends", []),
                source_distribution=search_stats.get("source_distribution", {}),
                quality_metrics=search_stats.get("quality_metrics", {}),
                error_summary=error_stats.get("error_summary", {}),
            )

            # Cache the analytics
            if self.cache_service:
                await self.cache_service.set(
                    cache_key,
                    asdict(analytics),
                    ttl=self.CACHE_TTL_MEDIUM,
                )

            return analytics

        except Exception as e:
            logger.error(f"Failed to get system analytics: {e}")
            raise

    async def get_security_events(
        self,
        limit: int = 50,
        severity: str | None = None,
        resolved: bool | None = None,
    ) -> list[SecurityEvent]:
        """Get security events and alerts"""
        try:
            # Build filters
            filters = {}
            if severity:
                filters["severity"] = severity
            if resolved is not None:
                filters["resolved"] = resolved

            # Get events from database
            events_data = await self.database_service.get_security_events(
                limit=limit,
                filters=filters,
            )

            # Convert to SecurityEvent objects
            security_events = []
            for event in events_data:
                security_event = SecurityEvent(
                    id=event["id"],
                    event_type=event["event_type"],
                    severity=event["severity"],
                    user_id=event.get("user_id"),
                    ip_address=event["ip_address"],
                    user_agent=event["user_agent"],
                    details=event["details"],
                    timestamp=event["timestamp"],
                    resolved=event["resolved"],
                )
                security_events.append(security_event)

            return security_events

        except Exception as e:
            logger.error(f"Failed to get security events: {e}")
            raise

    # System Configuration

    async def get_system_config(self) -> dict[str, Any]:
        """Get current system configuration"""
        try:
            config = await self.database_service.get_system_config()

            # Add runtime information
            runtime_config = {
                "websocket_enabled": self.websocket_manager is not None,
                "cache_enabled": self.cache_service is not None,
                "active_features": [],
                "version": "2.0.0",
                "last_updated": datetime.utcnow().isoformat(),
            }

            # Determine active features
            if self.websocket_manager:
                runtime_config["active_features"].append("real_time_notifications")
            if self.cache_service:
                runtime_config["active_features"].append("intelligent_caching")

            return {"database_config": config, "runtime_config": runtime_config}

        except Exception as e:
            logger.error(f"Failed to get system config: {e}")
            raise

    async def update_system_config(
        self,
        admin_user_id: str,
        config_updates: dict[str, Any],
    ) -> bool:
        """Update system configuration"""
        try:
            # Verify admin permissions
            admin_user = await self.database_service.get_user_by_id(admin_user_id)
            if not admin_user or not admin_user.get("is_admin"):
                raise ValueError("Insufficient permissions")

            # Update configuration
            success = await self.database_service.update_system_config(config_updates)

            if success:
                # Log the configuration change
                await self._log_admin_action(
                    admin_user_id=admin_user_id,
                    target_user_id=None,
                    action="update_config",
                    reason="System configuration update",
                    details=config_updates,
                )

                # Notify admins of configuration change
                if self.websocket_manager:
                    await self.websocket_manager.notify_system_alert(
                        {
                            "type": "config_update",
                            "admin_user": admin_user["username"],
                            "updates": list(config_updates.keys()),
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                        admin_only=True,
                    )

            return success

        except Exception as e:
            logger.error(f"Failed to update system config: {e}")
            raise

    # Maintenance Operations

    async def perform_maintenance_operation(
        self,
        admin_user_id: str,
        operation: str,
        **kwargs,
    ) -> dict[str, Any]:
        """Perform system maintenance operations"""
        try:
            # Verify admin permissions
            admin_user = await self.database_service.get_user_by_id(admin_user_id)
            if not admin_user or not admin_user.get("is_admin"):
                raise ValueError("Insufficient permissions")

            result = {"success": False, "message": "", "details": {}}

            if operation == "clear_cache":
                if self.cache_service:
                    cache_keys = kwargs.get("cache_keys", [])
                    if cache_keys:
                        for key in cache_keys:
                            await self.cache_service.delete(key)
                    else:
                        await self.cache_service.clear_all()
                    result = {"success": True, "message": "Cache cleared successfully"}
                else:
                    result = {
                        "success": False,
                        "message": "Cache service not available",
                    }

            elif operation == "cleanup_old_data":
                days = kwargs.get("days", 90)
                cutoff_date = datetime.utcnow() - timedelta(days=days)

                # Clean old search history
                deleted_searches = (
                    await self.database_service.cleanup_old_search_history(cutoff_date)
                )

                # Clean old system metrics
                deleted_metrics = await self.database_service.cleanup_old_metrics(
                    cutoff_date,
                )

                result = {
                    "success": True,
                    "message": f"Cleaned up data older than {days} days",
                    "details": {
                        "deleted_searches": deleted_searches,
                        "deleted_metrics": deleted_metrics,
                    },
                }

            elif operation == "rebuild_indexes":
                indexes_rebuilt = await self.database_service.rebuild_database_indexes()
                result = {
                    "success": True,
                    "message": f"Rebuilt {indexes_rebuilt} database indexes",
                }

            elif operation == "backup_database":
                backup_path = await self.database_service.create_database_backup()
                result = {
                    "success": True,
                    "message": "Database backup created",
                    "details": {"backup_path": backup_path},
                }

            else:
                result = {
                    "success": False,
                    "message": f"Unknown operation: {operation}",
                }

            # Log the maintenance operation
            if result["success"]:
                await self._log_admin_action(
                    admin_user_id=admin_user_id,
                    target_user_id=None,
                    action="maintenance",
                    reason=f"Maintenance operation: {operation}",
                    details={"operation": operation, "result": result},
                )

            return result

        except Exception as e:
            logger.error(f"Failed to perform maintenance operation {operation}: {e}")
            raise

    # Helper Methods

    async def _get_user_search_stats(self, user_id: str) -> dict[str, Any]:
        """Get user search statistics"""
        try:
            stats = await self.database_service.get_user_search_summary(user_id)
            return {
                "total_searches": stats.get("total_searches", 0),
                "total_execution_time": stats.get("total_execution_time", 0),
                "avg_quality_score": stats.get("avg_quality_score"),
            }
        except BaseException:
            return {
                "total_searches": 0,
                "total_execution_time": 0,
                "avg_quality_score": None,
            }

    async def _check_database_health(self) -> str:
        """Check database health"""
        try:
            await self.database_service.health_check()
            return "healthy"
        except BaseException:
            return "error"

    async def _check_redis_health(self) -> str:
        """Check Redis health"""
        try:
            if self.cache_service:
                await self.cache_service.ping()
                return "healthy"
            return "disabled"
        except BaseException:
            return "error"

    async def _check_websocket_health(self) -> str:
        """Check WebSocket health"""
        try:
            if self.websocket_manager:
                # Simple health check based on connection count
                if hasattr(self.websocket_manager, "server"):
                    return "healthy"
                return "starting"
            return "disabled"
        except BaseException:
            return "error"

    async def _get_performance_metrics(self) -> dict[str, Any]:
        """Get system performance metrics"""
        try:
            import psutil

            # Get system metrics
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            # Get cache hit rate if available
            cache_hit_rate = 0
            if self.cache_service:
                cache_stats = await self.cache_service.get_stats()
                cache_hit_rate = cache_stats.get("hit_rate", 0)

            return {
                "cpu_usage": cpu_usage,
                "memory_usage": memory.percent,
                "disk_usage": disk.percent,
                "cache_hit_rate": cache_hit_rate,
                "uptime_seconds": 0,  # Would need to track from service start
                "avg_response_time": 0,  # Would need request tracking
                "error_rate": 0,  # Would need error tracking
            }
        except ImportError:
            # psutil not available
            return {
                "cpu_usage": 0,
                "memory_usage": 0,
                "disk_usage": 0,
                "cache_hit_rate": 0,
                "uptime_seconds": 0,
                "avg_response_time": 0,
                "error_rate": 0,
            }
        except Exception as e:
            logger.error(f"Failed to get performance metrics: {e}")
            return {}

    async def _get_user_statistics(self, start_date: datetime) -> dict[str, Any]:
        """Get user statistics"""
        try:
            return await self.database_service.get_user_statistics(start_date)
        except Exception as e:
            logger.error(f"Failed to get user statistics: {e}")
            return {}

    async def _get_search_statistics(self, start_date: datetime) -> dict[str, Any]:
        """Get search statistics"""
        try:
            return await self.database_service.get_search_statistics(start_date)
        except Exception as e:
            logger.error(f"Failed to get search statistics: {e}")
            return {}

    async def _get_performance_statistics(self, start_date: datetime) -> dict[str, Any]:
        """Get performance statistics"""
        try:
            return await self.database_service.get_performance_statistics(start_date)
        except Exception as e:
            logger.error(f"Failed to get performance statistics: {e}")
            return {}

    async def _get_error_statistics(self, start_date: datetime) -> dict[str, Any]:
        """Get error statistics"""
        try:
            return await self.database_service.get_error_statistics(start_date)
        except Exception as e:
            logger.error(f"Failed to get error statistics: {e}")
            return {}

    async def _log_admin_action(
        self,
        admin_user_id: str,
        target_user_id: str | None,
        action: str,
        reason: str | None,
        details: dict[str, Any],
    ) -> None:
        """Log admin action for audit trail"""
        try:
            await self.database_service.log_admin_action(
                admin_user_id=admin_user_id,
                target_user_id=target_user_id,
                action=action,
                reason=reason,
                details=details,
                timestamp=datetime.utcnow(),
            )
        except Exception as e:
            logger.error(f"Failed to log admin action: {e}")


# Factory function


async def create_admin_dashboard_service(
    database_service: PostgreSQLService,
    auth_service: JWTAuthenticationService,
    search_history_service: SearchHistoryService,
    websocket_manager: WebSocketManager | None = None,
    cache_service: RedisCacheService | None = None,
) -> AdminDashboardService:
    """Create and initialize admin dashboard service"""
    service = AdminDashboardService(
        database_service,
        auth_service,
        search_history_service,
        websocket_manager,
        cache_service,
    )
    logger.info("✅ Admin Dashboard Service created successfully")
    return service
