#!/usr/bin/env python3
"""PAKE System - Real-time WebSocket Manager
Enterprise-grade WebSocket service for real-time notifications and live updates.
"""

import asyncio
import json
import logging
import uuid
import weakref
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import jwt
import websockets
from websockets.exceptions import ConnectionClosed
from websockets.server import WebSocketServerProtocol

from ..authentication.jwt_auth_service import JWTAuthenticationService
from ..caching.redis_cache_service import RedisCacheService
from ..database.postgresql_service import PostgreSQLService

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """WebSocket message types"""

    # Authentication
    AUTH = "auth"
    AUTH_SUCCESS = "auth_success"
    AUTH_FAILED = "auth_failed"

    # Search notifications
    SEARCH_STARTED = "search_started"
    SEARCH_PROGRESS = "search_progress"
    SEARCH_COMPLETED = "search_completed"
    SEARCH_FAILED = "search_failed"

    # User activity
    USER_ACTIVITY = "user_activity"
    SEARCH_HISTORY_UPDATED = "search_history_updated"
    PREFERENCES_UPDATED = "preferences_updated"

    # System notifications
    SYSTEM_ALERT = "system_alert"
    MAINTENANCE_MODE = "maintenance_mode"
    PERFORMANCE_UPDATE = "performance_update"

    # Admin notifications
    NEW_USER_REGISTERED = "new_user_registered"
    SYSTEM_METRICS = "system_metrics"
    SECURITY_ALERT = "security_alert"

    # Real-time collaboration
    USER_JOINED = "user_joined"
    USER_LEFT = "user_left"
    LIVE_SEARCH_SHARE = "live_search_share"

    # General
    PING = "ping"
    PONG = "pong"
    ERROR = "error"
    HEARTBEAT = "heartbeat"


@dataclass
class WebSocketMessage:
    """Structured WebSocket message"""

    message_type: MessageType
    data: dict[str, Any]
    timestamp: datetime
    user_id: str | None = None
    session_id: str | None = None
    message_id: str = None

    def __post_init__(self):
        if self.message_id is None:
            self.message_id = str(uuid.uuid4())


@dataclass
class ConnectedUser:
    """Connected user information"""

    user_id: str
    username: str
    websocket: WebSocketServerProtocol
    session_id: str
    connected_at: datetime
    last_activity: datetime
    is_admin: bool = False
    subscriptions: set[str] = None

    def __post_init__(self):
        if self.subscriptions is None:
            self.subscriptions = set()


@dataclass
class WebSocketConfig:
    """WebSocket server configuration"""

    host: str = "localhost"
    port: int = 8001
    max_connections: int = 1000
    heartbeat_interval: int = 30
    connection_timeout: int = 300
    message_queue_size: int = 100
    enable_compression: bool = True
    enable_auth: bool = True


class WebSocketManager:
    """Enterprise WebSocket manager for real-time communication.

    Features:
    - JWT Authentication
    - Connection management
    - Message broadcasting
    - Real-time notifications
    - User presence tracking
    - Admin monitoring
    - Performance metrics
    """

    def __init__(
        self,
        config: WebSocketConfig,
        auth_service: JWTAuthenticationService,
        database_service: PostgreSQLService,
        cache_service: RedisCacheService | None = None,
    ):
        self.config = config
        self.auth_service = auth_service
        self.database_service = database_service
        self.cache_service = cache_service

        # Connection tracking
        self.connected_users: dict[str, ConnectedUser] = {}
        self.websocket_to_user: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()
        self.user_subscriptions: dict[str, set[str]] = {}
        self.admin_connections: set[str] = set()

        # Message queues for offline users
        self.message_queues: dict[str, list[WebSocketMessage]] = {}

        # Performance tracking
        self.connection_count = 0
        self.total_messages_sent = 0
        self.start_time = datetime.utcnow()

        # Event handlers
        self.message_handlers: dict[MessageType, Callable] = {}
        self._setup_default_handlers()

        logger.info("🔗 WebSocket Manager initialized")

    async def start_server(self) -> None:
        """Start the WebSocket server"""
        try:
            self.server = await websockets.serve(
                self._handle_connection,
                self.config.host,
                self.config.port,
                max_size=2**20,  # 1MB max message size
                max_queue=self.config.message_queue_size,
                compression="deflate" if self.config.enable_compression else None,
                ping_interval=self.config.heartbeat_interval,
                ping_timeout=10,
                close_timeout=10,
            )

            # Start background tasks
            asyncio.create_task(self._heartbeat_task())
            asyncio.create_task(self._cleanup_task())
            asyncio.create_task(self._metrics_task())

            logger.info(
                f"🚀 WebSocket server started on {self.config.host}:{self.config.port}",
            )

        except Exception as e:
            logger.error(f"Failed to start WebSocket server: {e}")
            raise

    async def stop_server(self) -> None:
        """Stop the WebSocket server"""
        try:
            if hasattr(self, "server"):
                self.server.close()
                await self.server.wait_closed()

            # Notify all connected users
            await self._broadcast_to_all(
                {
                    "type": MessageType.MAINTENANCE_MODE.value,
                    "data": {"message": "Server shutting down"},
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

            # Close all connections
            for user in list(self.connected_users.values()):
                await user.websocket.close()

            logger.info("🛑 WebSocket server stopped")

        except Exception as e:
            logger.error(f"Error stopping WebSocket server: {e}")

    async def _handle_connection(
        self,
        websocket: WebSocketServerProtocol,
        path: str,
    ) -> None:
        """Handle new WebSocket connection"""
        session_id = str(uuid.uuid4())

        try:
            logger.info(f"🔌 New WebSocket connection: {websocket.remote_address}")

            # Connection limit check
            if len(self.connected_users) >= self.config.max_connections:
                await websocket.close(code=1008, reason="Connection limit reached")
                return

            # Wait for authentication if enabled
            user_data = None
            if self.config.enable_auth:
                user_data = await self._authenticate_connection(websocket, session_id)
                if not user_data:
                    await websocket.close(code=1008, reason="Authentication failed")
                    return

            # Register the connection
            await self._register_connection(websocket, session_id, user_data)

            # Send queued messages if user has any
            if user_data:
                await self._send_queued_messages(user_data["id"])

            # Handle messages
            async for message in websocket:
                try:
                    await self._handle_message(websocket, message)
                except Exception as e:
                    logger.error(f"Error handling message: {e}")
                    await self._send_error(websocket, str(e))

        except ConnectionClosed:
            logger.info(f"Connection closed: {websocket.remote_address}")
        except Exception as e:
            logger.error(f"Connection error: {e}")
        finally:
            await self._unregister_connection(websocket, session_id)

    async def _authenticate_connection(
        self,
        websocket: WebSocketServerProtocol,
        session_id: str,
    ) -> dict[str, Any] | None:
        """Authenticate WebSocket connection"""
        try:
            # Wait for auth message
            auth_timeout = 30  # 30 seconds to authenticate
            auth_message = await asyncio.wait_for(
                websocket.recv(),
                timeout=auth_timeout,
            )

            message_data = json.loads(auth_message)

            if message_data.get("type") != MessageType.AUTH.value:
                await self._send_message(
                    websocket,
                    WebSocketMessage(
                        message_type=MessageType.AUTH_FAILED,
                        data={"error": "Authentication required"},
                    ),
                )
                return None

            # Extract and verify JWT token
            token = message_data.get("data", {}).get("token")
            if not token:
                await self._send_message(
                    websocket,
                    WebSocketMessage(
                        message_type=MessageType.AUTH_FAILED,
                        data={"error": "Token required"},
                    ),
                )
                return None

            # Verify token
            try:
                payload = jwt.decode(
                    token,
                    self.auth_service.config.secret_key,
                    algorithms=[self.auth_service.config.algorithm],
                )

                user_id = payload.get("sub")
                if not user_id:
                    raise jwt.InvalidTokenError("Invalid user ID")

                # Get user data
                user_data = await self.database_service.get_user_by_id(user_id)
                if not user_data or not user_data.get("is_active"):
                    raise jwt.InvalidTokenError("User not found or inactive")

                # Send success message
                await self._send_message(
                    websocket,
                    WebSocketMessage(
                        message_type=MessageType.AUTH_SUCCESS,
                        data={
                            "user_id": user_id,
                            "username": user_data["username"],
                            "session_id": session_id,
                        },
                    ),
                )

                return user_data

            except jwt.InvalidTokenError as e:
                await self._send_message(
                    websocket,
                    WebSocketMessage(
                        message_type=MessageType.AUTH_FAILED,
                        data={"error": f"Invalid token: {str(e)}"},
                    ),
                )
                return None

        except TimeoutError:
            await self._send_message(
                websocket,
                WebSocketMessage(
                    message_type=MessageType.AUTH_FAILED,
                    data={"error": "Authentication timeout"},
                ),
            )
            return None
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None

    async def _register_connection(
        self,
        websocket: WebSocketServerProtocol,
        session_id: str,
        user_data: dict[str, Any] | None,
    ) -> None:
        """Register a new connection"""
        try:
            if user_data:
                user_id = user_data["id"]
                username = user_data["username"]
                is_admin = user_data.get("is_admin", False)

                # Create connected user
                connected_user = ConnectedUser(
                    user_id=user_id,
                    username=username,
                    websocket=websocket,
                    session_id=session_id,
                    connected_at=datetime.utcnow(),
                    last_activity=datetime.utcnow(),
                    is_admin=is_admin,
                    subscriptions={"user_activity", "search_updates"},
                )

                # Store connection
                self.connected_users[user_id] = connected_user
                self.websocket_to_user[websocket] = connected_user

                # Add to admin connections if admin
                if is_admin:
                    self.admin_connections.add(user_id)
                    connected_user.subscriptions.update(
                        {"system_metrics", "security_alerts", "admin_notifications"},
                    )

                # Notify other users
                await self._broadcast_to_subscribed(
                    "user_activity",
                    {
                        "type": MessageType.USER_JOINED.value,
                        "data": {
                            "user_id": user_id,
                            "username": username,
                            "joined_at": datetime.utcnow().isoformat(),
                        },
                    },
                )

                logger.info(f"👤 User {username} connected via WebSocket")

            else:
                # Anonymous connection
                self.websocket_to_user[websocket] = {
                    "session_id": session_id,
                    "connected_at": datetime.utcnow(),
                    "is_anonymous": True,
                }

            self.connection_count += 1

        except Exception as e:
            logger.error(f"Failed to register connection: {e}")

    async def _unregister_connection(
        self,
        websocket: WebSocketServerProtocol,
        session_id: str,
    ) -> None:
        """Unregister a connection"""
        try:
            # Find user by websocket
            user_info = self.websocket_to_user.get(websocket)

            if user_info and hasattr(user_info, "user_id"):
                user_id = user_info.user_id
                username = user_info.username

                # Remove from tracking
                if user_id in self.connected_users:
                    del self.connected_users[user_id]

                if user_id in self.admin_connections:
                    self.admin_connections.remove(user_id)

                # Notify other users
                await self._broadcast_to_subscribed(
                    "user_activity",
                    {
                        "type": MessageType.USER_LEFT.value,
                        "data": {
                            "user_id": user_id,
                            "username": username,
                            "left_at": datetime.utcnow().isoformat(),
                        },
                    },
                )

                logger.info(f"👤 User {username} disconnected from WebSocket")

            # Remove from websocket tracking
            if websocket in self.websocket_to_user:
                del self.websocket_to_user[websocket]

            self.connection_count = max(0, self.connection_count - 1)

        except Exception as e:
            logger.error(f"Failed to unregister connection: {e}")

    async def _handle_message(
        self,
        websocket: WebSocketServerProtocol,
        raw_message: str,
    ) -> None:
        """Handle incoming WebSocket message"""
        try:
            message_data = json.loads(raw_message)
            message_type = MessageType(message_data.get("type"))

            # Update last activity
            user_info = self.websocket_to_user.get(websocket)
            if user_info and hasattr(user_info, "last_activity"):
                user_info.last_activity = datetime.utcnow()

            # Handle message based on type
            if message_type in self.message_handlers:
                await self.message_handlers[message_type](websocket, message_data)
            else:
                logger.warning(f"Unhandled message type: {message_type}")

        except ValueError as e:
            await self._send_error(websocket, f"Invalid message format: {e}")
        except Exception as e:
            logger.error(f"Message handling error: {e}")
            await self._send_error(websocket, "Internal server error")

    async def _send_message(
        self,
        websocket: WebSocketServerProtocol,
        message: WebSocketMessage,
    ) -> bool:
        """Send message to specific websocket"""
        try:
            message_dict = {
                "type": message.message_type.value,
                "data": message.data,
                "timestamp": message.timestamp.isoformat(),
                "message_id": message.message_id,
            }

            await websocket.send(json.dumps(message_dict))
            self.total_messages_sent += 1
            return True

        except ConnectionClosed:
            logger.debug("Connection closed while sending message")
            return False
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False

    async def _send_error(self, websocket: WebSocketServerProtocol, error: str) -> None:
        """Send error message"""
        await self._send_message(
            websocket,
            WebSocketMessage(
                message_type=MessageType.ERROR,
                data={"error": error},
                timestamp=datetime.utcnow(),
            ),
        )

    # Public API Methods

    async def send_to_user(self, user_id: str, message: WebSocketMessage) -> bool:
        """Send message to specific user"""
        try:
            if user_id in self.connected_users:
                user = self.connected_users[user_id]
                return await self._send_message(user.websocket, message)
            # Queue message for offline user
            if user_id not in self.message_queues:
                self.message_queues[user_id] = []

            self.message_queues[user_id].append(message)

            # Limit queue size
            if len(self.message_queues[user_id]) > self.config.message_queue_size:
                self.message_queues[user_id].pop(0)

            logger.info(f"📬 Queued message for offline user {user_id}")
            return False

        except Exception as e:
            logger.error(f"Failed to send to user {user_id}: {e}")
            return False

    async def broadcast_to_all(self, message: WebSocketMessage) -> int:
        """Broadcast message to all connected users"""
        sent_count = 0

        for user in list(self.connected_users.values()):
            if await self._send_message(user.websocket, message):
                sent_count += 1

        logger.info(f"📢 Broadcasted message to {sent_count} users")
        return sent_count

    async def broadcast_to_admins(self, message: WebSocketMessage) -> int:
        """Broadcast message to admin users only"""
        sent_count = 0

        for user_id in self.admin_connections:
            if user_id in self.connected_users:
                user = self.connected_users[user_id]
                if await self._send_message(user.websocket, message):
                    sent_count += 1

        logger.info(f"👨‍💼 Broadcasted admin message to {sent_count} admins")
        return sent_count

    async def _broadcast_to_subscribed(
        self,
        subscription: str,
        message_data: dict[str, Any],
    ) -> int:
        """Broadcast to users subscribed to a specific topic"""
        sent_count = 0

        message = WebSocketMessage(
            message_type=MessageType(message_data["type"]),
            data=message_data["data"],
            timestamp=datetime.utcnow(),
        )

        for user in list(self.connected_users.values()):
            if subscription in user.subscriptions:
                if await self._send_message(user.websocket, message):
                    sent_count += 1

        return sent_count

    async def _send_queued_messages(self, user_id: str) -> None:
        """Send queued messages to user who just connected"""
        if user_id in self.message_queues:
            messages = self.message_queues[user_id]
            sent_count = 0

            for message in messages:
                if await self.send_to_user(user_id, message):
                    sent_count += 1

            # Clear the queue
            del self.message_queues[user_id]

            logger.info(f"📬 Sent {sent_count} queued messages to user {user_id}")

    # Background Tasks

    async def _heartbeat_task(self) -> None:
        """Send periodic heartbeat to maintain connections"""
        while True:
            try:
                await asyncio.sleep(self.config.heartbeat_interval)

                heartbeat_message = WebSocketMessage(
                    message_type=MessageType.HEARTBEAT,
                    data={"timestamp": datetime.utcnow().isoformat()},
                    timestamp=datetime.utcnow(),
                )

                await self.broadcast_to_all(heartbeat_message)

            except Exception as e:
                logger.error(f"Heartbeat task error: {e}")

    async def _cleanup_task(self) -> None:
        """Clean up stale connections and old message queues"""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute

                now = datetime.utcnow()
                timeout_threshold = now - timedelta(
                    seconds=self.config.connection_timeout,
                )

                # Remove stale connections
                stale_users = []
                for user_id, user in self.connected_users.items():
                    if user.last_activity < timeout_threshold:
                        stale_users.append(user_id)

                for user_id in stale_users:
                    user = self.connected_users[user_id]
                    try:
                        await user.websocket.close()
                    except BaseException:
                        pass
                    await self._unregister_connection(user.websocket, user.session_id)
                    logger.info(f"🧹 Cleaned up stale connection for user {user_id}")

                # Clean old message queues (older than 24 hours)
                old_threshold = now - timedelta(hours=24)
                old_queues = []

                for user_id, messages in self.message_queues.items():
                    if messages and messages[0].timestamp < old_threshold:
                        old_queues.append(user_id)

                for user_id in old_queues:
                    del self.message_queues[user_id]
                    logger.info(f"🧹 Cleaned up old message queue for user {user_id}")

            except Exception as e:
                logger.error(f"Cleanup task error: {e}")

    async def _metrics_task(self) -> None:
        """Collect and broadcast performance metrics"""
        while True:
            try:
                await asyncio.sleep(300)  # Every 5 minutes

                uptime = datetime.utcnow() - self.start_time

                metrics = {
                    "connected_users": len(self.connected_users),
                    "admin_connections": len(self.admin_connections),
                    "total_messages_sent": self.total_messages_sent,
                    "queued_messages": sum(
                        len(q) for q in self.message_queues.values()
                    ),
                    "uptime_seconds": uptime.total_seconds(),
                    "timestamp": datetime.utcnow().isoformat(),
                }

                # Send to admins
                metrics_message = WebSocketMessage(
                    message_type=MessageType.SYSTEM_METRICS,
                    data={"metrics": metrics},
                    timestamp=datetime.utcnow(),
                )

                await self.broadcast_to_admins(metrics_message)

                # Store in cache for dashboard
                if self.cache_service:
                    await self.cache_service.set(
                        "websocket_metrics",
                        metrics,
                        ttl=600,  # 10 minutes
                    )

            except Exception as e:
                logger.error(f"Metrics task error: {e}")

    def _setup_default_handlers(self) -> None:
        """Setup default message handlers"""

        async def handle_ping(websocket, message_data):
            pong_message = WebSocketMessage(
                message_type=MessageType.PONG,
                data={"timestamp": datetime.utcnow().isoformat()},
                timestamp=datetime.utcnow(),
            )
            await self._send_message(websocket, pong_message)

        async def handle_subscribe(websocket, message_data):
            user_info = self.websocket_to_user.get(websocket)
            if user_info and hasattr(user_info, "subscriptions"):
                subscriptions = message_data.get("data", {}).get("subscriptions", [])
                user_info.subscriptions.update(subscriptions)

                await self._send_message(
                    websocket,
                    WebSocketMessage(
                        message_type=MessageType.AUTH_SUCCESS,
                        data={"subscribed": list(user_info.subscriptions)},
                        timestamp=datetime.utcnow(),
                    ),
                )

        self.message_handlers[MessageType.PING] = handle_ping

    # Public notification methods for integration

    async def notify_search_started(
        self,
        user_id: str,
        search_data: dict[str, Any],
    ) -> None:
        """Notify user that search has started"""
        message = WebSocketMessage(
            message_type=MessageType.SEARCH_STARTED,
            data=search_data,
            timestamp=datetime.utcnow(),
            user_id=user_id,
        )
        await self.send_to_user(user_id, message)

    async def notify_search_progress(
        self,
        user_id: str,
        progress_data: dict[str, Any],
    ) -> None:
        """Notify user of search progress"""
        message = WebSocketMessage(
            message_type=MessageType.SEARCH_PROGRESS,
            data=progress_data,
            timestamp=datetime.utcnow(),
            user_id=user_id,
        )
        await self.send_to_user(user_id, message)

    async def notify_search_completed(
        self,
        user_id: str,
        results_data: dict[str, Any],
    ) -> None:
        """Notify user that search is completed"""
        message = WebSocketMessage(
            message_type=MessageType.SEARCH_COMPLETED,
            data=results_data,
            timestamp=datetime.utcnow(),
            user_id=user_id,
        )
        await self.send_to_user(user_id, message)

    async def notify_system_alert(
        self,
        alert_data: dict[str, Any],
        admin_only: bool = False,
    ) -> None:
        """Send system alert notification"""
        message = WebSocketMessage(
            message_type=MessageType.SYSTEM_ALERT,
            data=alert_data,
            timestamp=datetime.utcnow(),
        )

        if admin_only:
            await self.broadcast_to_admins(message)
        else:
            await self.broadcast_to_all(message)

    def get_connection_stats(self) -> dict[str, Any]:
        """Get current connection statistics"""
        return {
            "connected_users": len(self.connected_users),
            "admin_connections": len(self.admin_connections),
            "total_connections": self.connection_count,
            "total_messages_sent": self.total_messages_sent,
            "queued_messages": sum(len(q) for q in self.message_queues.values()),
            "uptime_seconds": (datetime.utcnow() - self.start_time).total_seconds(),
        }


# Factory function


async def create_websocket_manager(
    config: WebSocketConfig,
    auth_service: JWTAuthenticationService,
    database_service: PostgreSQLService,
    cache_service: RedisCacheService | None = None,
) -> WebSocketManager:
    """Create and initialize WebSocket manager"""
    manager = WebSocketManager(config, auth_service, database_service, cache_service)
    logger.info("✅ WebSocket Manager created successfully")
    return manager
