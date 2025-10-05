#!/usr/bin/env python3
"""PAKE System - Formal Service Contracts (Phase 3 Architectural Health)
Comprehensive service contracts for inter-service communication decoupling.

This module defines formal contracts that enforce:
1. Clear service boundaries and responsibilities
2. Standardized communication patterns
3. Version compatibility and evolution
4. Independent service development and deployment
5. Comprehensive error handling and monitoring
"""

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Generic, TypeVar

# Generic types for contracts
T = TypeVar("T")
RequestType = TypeVar("RequestType")
ResponseType = TypeVar("ResponseType")


class ContractVersion(Enum):
    """Service contract versioning."""

    V1_0 = "1.0"
    V1_1 = "1.1"
    V2_0 = "2.0"


class ServiceContractType(Enum):
    """Types of service contracts."""

    REQUEST_RESPONSE = "request_response"
    PUBLISH_SUBSCRIBE = "publish_subscribe"
    COMMAND_QUERY = "command_query"
    EVENT_STREAMING = "event_streaming"
    BATCH_PROCESSING = "batch_processing"


class ContractStatus(Enum):
    """Contract execution status."""

    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    RATE_LIMITED = "rate_limited"
    UNAUTHORIZED = "unauthorized"
    VALIDATION_ERROR = "validation_error"
    SERVICE_UNAVAILABLE = "service_unavailable"


@dataclass(frozen=True)
class ContractRequest[T]:
    """Standardized service request contract."""

    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    contract_version: ContractVersion = ContractVersion.V1_0
    service_name: str = ""
    operation: str = ""
    payload: RequestType = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    timeout_seconds: int = 30
    retry_count: int = 0
    max_retries: int = 3

    def to_dict(self) -> dict[str, Any]:
        """Convert request to dictionary for serialization."""
        return {
            "request_id": self.request_id,
            "contract_version": self.contract_version.value,
            "service_name": self.service_name,
            "operation": self.operation,
            "payload": self.payload,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "timeout_seconds": self.timeout_seconds,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContractRequest":
        """Create request from dictionary."""
        return cls(
            request_id=data["request_id"],
            contract_version=ContractVersion(data["contract_version"]),
            service_name=data["service_name"],
            operation=data["operation"],
            payload=data["payload"],
            metadata=data["metadata"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            timeout_seconds=data["timeout_seconds"],
            retry_count=data["retry_count"],
            max_retries=data["max_retries"],
        )


@dataclass(frozen=True)
class ContractResponse[T]:
    """Standardized service response contract."""

    request_id: str
    contract_version: ContractVersion = ContractVersion.V1_0
    status: ContractStatus = ContractStatus.SUCCESS
    payload: T | None = None
    error_message: str | None = None
    error_code: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    processing_time_ms: float = 0.0
    service_version: str = "1.0.0"

    def to_dict(self) -> dict[str, Any]:
        """Convert response to dictionary for serialization."""
        return {
            "request_id": self.request_id,
            "contract_version": self.contract_version.value,
            "status": self.status.value,
            "payload": self.payload,
            "error_message": self.error_message,
            "error_code": self.error_code,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat(),
            "processing_time_ms": self.processing_time_ms,
            "service_version": self.service_version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ContractResponse":
        """Create response from dictionary."""
        return cls(
            request_id=data["request_id"],
            contract_version=ContractVersion(data["contract_version"]),
            status=ContractStatus(data["status"]),
            payload=data.get("payload"),
            error_message=data.get("error_message"),
            error_code=data.get("error_code"),
            metadata=data["metadata"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            processing_time_ms=data["processing_time_ms"],
            service_version=data["service_version"],
        )


# ============================================================================
# Core Service Contract Interfaces
# ============================================================================


class ServiceContract[RequestType, ResponseType](ABC):
    """Abstract base class for all service contracts."""

    @property
    @abstractmethod
    def contract_name(self) -> str:
        """Contract identifier."""

    @property
    @abstractmethod
    def contract_version(self) -> ContractVersion:
        """Contract version."""

    @property
    @abstractmethod
    def contract_type(self) -> ServiceContractType:
        """Type of contract."""

    @abstractmethod
    async def execute(
        self, request: ContractRequest[RequestType]
    ) -> ContractResponse[ResponseType]:
        """Execute contract operation."""

    @abstractmethod
    def validate_request(self, request: ContractRequest[RequestType]) -> bool:
        """Validate incoming request."""

    @abstractmethod
    def get_schema(self) -> dict[str, Any]:
        """Get contract schema for validation."""


# ============================================================================
# Authentication Service Contracts
# ============================================================================


@dataclass(frozen=True)
class AuthenticationRequest:
    """Authentication service request payload."""

    email: str
    password: str
    tenant_id: str | None = None
    device_info: dict[str, Any] | None = None


@dataclass(frozen=True)
class AuthenticationResponse:
    """Authentication service response payload."""

    user_id: str
    access_token: str
    refresh_token: str
    expires_in: int
    token_type: str = "Bearer"
    permissions: list[str] = field(default_factory=list)
    user_profile: dict[str, Any] = field(default_factory=dict)


class AuthenticationServiceContract(
    ServiceContract[AuthenticationRequest, AuthenticationResponse]
):
    """Formal contract for authentication service."""

    @property
    def contract_name(self) -> str:
        return "authentication_service"

    @property
    def contract_version(self) -> ContractVersion:
        return ContractVersion.V1_0

    @property
    def contract_type(self) -> ServiceContractType:
        return ServiceContractType.REQUEST_RESPONSE

    def validate_request(self, request: ContractRequest[AuthenticationRequest]) -> bool:
        """Validate authentication request."""
        if not request.payload:
            return False

        payload = request.payload
        return (
            isinstance(payload, AuthenticationRequest)
            and isinstance(payload.email, str)
            and len(payload.email) > 0
            and isinstance(payload.password, str)
            and len(payload.password) >= 8
        )

    def get_schema(self) -> dict[str, Any]:
        """Get authentication contract schema."""
        return {
            "type": "object",
            "properties": {
                "email": {"type": "string", "format": "email"},
                "password": {"type": "string", "minLength": 8},
                "tenant_id": {"type": "string", "nullable": True},
                "device_info": {"type": "object", "nullable": True},
            },
            "required": ["email", "password"],
        }

    async def execute(
        self, request: ContractRequest[AuthenticationRequest]
    ) -> ContractResponse[AuthenticationResponse]:
        """Execute authentication contract."""
        # This would be implemented by the actual authentication service
        msg = "Must be implemented by concrete service"
        raise NotImplementedError(msg)


# ============================================================================
# Data Service Contracts
# ============================================================================


@dataclass(frozen=True)
class DataQueryRequest:
    """Data service query request payload."""

    query_type: str  # "search", "get_by_id", "list", "aggregate"
    filters: dict[str, Any] = field(default_factory=dict)
    limit: int = 100
    offset: int = 0
    sort_by: str | None = None
    sort_order: str = "asc"


@dataclass(frozen=True)
class DataQueryResponse:
    """Data service query response payload."""

    results: list[dict[str, Any]] = field(default_factory=list)
    total_count: int = 0
    has_more: bool = False
    next_offset: int | None = None
    query_metadata: dict[str, Any] = field(default_factory=dict)


class DataServiceContract(ServiceContract[DataQueryRequest, DataQueryResponse]):
    """Formal contract for data service."""

    @property
    def contract_name(self) -> str:
        return "data_service"

    @property
    def contract_version(self) -> ContractVersion:
        return ContractVersion.V1_0

    @property
    def contract_type(self) -> ServiceContractType:
        return ServiceContractType.REQUEST_RESPONSE

    def validate_request(self, request: ContractRequest[DataQueryRequest]) -> bool:
        """Validate data query request."""
        if not request.payload:
            return False

        payload = request.payload
        return (
            isinstance(payload, DataQueryRequest)
            and isinstance(payload.query_type, str)
            and payload.query_type in ["search", "get_by_id", "list", "aggregate"]
            and isinstance(payload.limit, int)
            and 1 <= payload.limit <= 1000
            and isinstance(payload.offset, int)
            and payload.offset >= 0
        )

    def get_schema(self) -> dict[str, Any]:
        """Get data service contract schema."""
        return {
            "type": "object",
            "properties": {
                "query_type": {
                    "type": "string",
                    "enum": ["search", "get_by_id", "list", "aggregate"],
                },
                "filters": {"type": "object"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 1000},
                "offset": {"type": "integer", "minimum": 0},
                "sort_by": {"type": "string", "nullable": True},
                "sort_order": {"type": "string", "enum": ["asc", "desc"]},
            },
            "required": ["query_type"],
        }

    async def execute(
        self, request: ContractRequest[DataQueryRequest]
    ) -> ContractResponse[DataQueryResponse]:
        """Execute data query contract."""
        # This would be implemented by the actual data service
        msg = "Must be implemented by concrete service"
        raise NotImplementedError(msg)


# ============================================================================
# AI Service Contracts
# ============================================================================


@dataclass(frozen=True)
class AIProcessingRequest:
    """AI service processing request payload."""

    operation_type: str  # "embedding", "classification", "generation", "analysis"
    input_data: str | list[str] | dict[str, Any]
    model_config: dict[str, Any] = field(default_factory=dict)
    processing_options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AIProcessingResponse:
    """AI service processing response payload."""

    results: list[float] | list[str] | dict[str, Any]
    model_used: str
    processing_time_ms: float
    confidence_scores: dict[str, float] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class AIServiceContract(ServiceContract[AIProcessingRequest, AIProcessingResponse]):
    """Formal contract for AI service."""

    @property
    def contract_name(self) -> str:
        return "ai_service"

    @property
    def contract_version(self) -> ContractVersion:
        return ContractVersion.V1_0

    @property
    def contract_type(self) -> ServiceContractType:
        return ServiceContractType.REQUEST_RESPONSE

    def validate_request(self, request: ContractRequest[AIProcessingRequest]) -> bool:
        """Validate AI processing request."""
        if not request.payload:
            return False

        payload = request.payload
        return (
            isinstance(payload, AIProcessingRequest)
            and isinstance(payload.operation_type, str)
            and payload.operation_type
            in ["embedding", "classification", "generation", "analysis"]
            and payload.input_data is not None
        )

    def get_schema(self) -> dict[str, Any]:
        """Get AI service contract schema."""
        return {
            "type": "object",
            "properties": {
                "operation_type": {
                    "type": "string",
                    "enum": ["embedding", "classification", "generation", "analysis"],
                },
                "input_data": {
                    "oneOf": [
                        {"type": "string"},
                        {"type": "array", "items": {"type": "string"}},
                        {"type": "object"},
                    ]
                },
                "model_config": {"type": "object"},
                "processing_options": {"type": "object"},
            },
            "required": ["operation_type", "input_data"],
        }

    async def execute(
        self, request: ContractRequest[AIProcessingRequest]
    ) -> ContractResponse[AIProcessingResponse]:
        """Execute AI processing contract."""
        # This would be implemented by the actual AI service
        msg = "Must be implemented by concrete service"
        raise NotImplementedError(msg)


# ============================================================================
# Event Streaming Contracts
# ============================================================================


@dataclass(frozen=True)
class EventMessage:
    """Event streaming message payload."""

    event_type: str
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_service: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    correlation_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EventSubscription:
    """Event subscription configuration."""

    event_types: list[str]
    callback_url: str | None = None
    filter_conditions: dict[str, Any] = field(default_factory=dict)
    batch_size: int = 1
    max_retries: int = 3


class EventStreamingContract(ServiceContract[EventMessage, None]):
    """Formal contract for event streaming service."""

    @property
    def contract_name(self) -> str:
        return "event_streaming_service"

    @property
    def contract_version(self) -> ContractVersion:
        return ContractVersion.V1_0

    @property
    def contract_type(self) -> ServiceContractType:
        return ServiceContractType.EVENT_STREAMING

    def validate_request(self, request: ContractRequest[EventMessage]) -> bool:
        """Validate event message."""
        if not request.payload:
            return False

        payload = request.payload
        return (
            isinstance(payload, EventMessage)
            and isinstance(payload.event_type, str)
            and len(payload.event_type) > 0
            and isinstance(payload.source_service, str)
            and len(payload.source_service) > 0
        )

    def get_schema(self) -> dict[str, Any]:
        """Get event streaming contract schema."""
        return {
            "type": "object",
            "properties": {
                "event_type": {"type": "string", "minLength": 1},
                "event_id": {"type": "string", "format": "uuid"},
                "source_service": {"type": "string", "minLength": 1},
                "payload": {"type": "object"},
                "timestamp": {"type": "string", "format": "date-time"},
                "correlation_id": {"type": "string", "nullable": True},
                "metadata": {"type": "object"},
            },
            "required": ["event_type", "source_service"],
        }

    async def execute(
        self, request: ContractRequest[EventMessage]
    ) -> ContractResponse[None]:
        """Execute event streaming contract."""
        # This would be implemented by the actual event streaming service
        msg = "Must be implemented by concrete service"
        raise NotImplementedError(msg)


# ============================================================================
# Contract Registry and Management
# ============================================================================


class ContractRegistry:
    """Registry for managing service contracts."""

    def __init__(self) -> None:
        self._contracts: dict[str, ServiceContract] = {}
        self._versions: dict[str, list[ContractVersion]] = {}

    def register_contract(self, contract: ServiceContract) -> None:
        """Register a service contract."""
        contract_key = f"{contract.contract_name}:{contract.contract_version.value}"
        self._contracts[contract_key] = contract

        if contract.contract_name not in self._versions:
            self._versions[contract.contract_name] = []

        if contract.contract_version not in self._versions[contract.contract_name]:
            self._versions[contract.contract_name].append(contract.contract_version)

    def get_contract(
        self, contract_name: str, version: ContractVersion | None = None
    ) -> ServiceContract | None:
        """Get a service contract by name and version."""
        if version:
            contract_key = f"{contract_name}:{version.value}"
            return self._contracts.get(contract_key)

        # Return latest version if no version specified
        if contract_name in self._versions:
            latest_version = max(self._versions[contract_name], key=lambda v: v.value)
            contract_key = f"{contract_name}:{latest_version.value}"
            return self._contracts.get(contract_key)

        return None

    def list_contracts(self) -> dict[str, list[str]]:
        """List all registered contracts."""
        return {
            name: [v.value for v in versions]
            for name, versions in self._versions.items()
        }

    def validate_contract_compatibility(
        self, contract_name: str, version: ContractVersion
    ) -> bool:
        """Validate contract version compatibility."""
        if contract_name not in self._versions:
            return False

        return version in self._versions[contract_name]


# Global contract registry
contract_registry = ContractRegistry()


def register_pake_contracts() -> None:
    """Register all PAKE System service contracts."""
    # Register authentication contract
    auth_contract = AuthenticationServiceContract()
    contract_registry.register_contract(auth_contract)

    # Register data service contract
    data_contract = DataServiceContract()
    contract_registry.register_contract(data_contract)

    # Register AI service contract
    ai_contract = AIServiceContract()
    contract_registry.register_contract(ai_contract)

    # Register event streaming contract
    event_contract = EventStreamingContract()
    contract_registry.register_contract(event_contract)


# Initialize contracts
register_pake_contracts()
