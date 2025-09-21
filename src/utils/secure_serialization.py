#!/usr/bin/env python3
"""Secure Serialization Utilities for PAKE System
Replaces insecure pickle with secure alternatives
"""

import hashlib
import json
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

try:
    import msgpack

    MSGPACK_AVAILABLE = True
except ImportError:
    MSGPACK_AVAILABLE = False

try:
    import cbor2

    CBOR_AVAILABLE = True
except ImportError:
    CBOR_AVAILABLE = False

logger = logging.getLogger(__name__)


class SerializationFormat(Enum):
    """Secure serialization formats"""

    JSON = "json"
    MSGPACK = "msgpack"
    CBOR = "cbor"


@dataclass
class SerializationConfig:
    """Configuration for secure serialization"""

    default_format: SerializationFormat = SerializationFormat.JSON
    enable_compression: bool = True
    enable_checksums: bool = True
    max_size_bytes: int = 10 * 1024 * 1024  # 10MB limit


class SecureSerializer:
    """Secure serialization service that replaces pickle
    Uses JSON, MessagePack, or CBOR for safe serialization
    """

    def __init__(self, config: SerializationConfig | None = None):
        self.config = config or SerializationConfig()
        self._validate_dependencies()

    def _validate_dependencies(self):
        """Validate that required dependencies are available"""
        if (
            self.config.default_format == SerializationFormat.MSGPACK
            and not MSGPACK_AVAILABLE
        ):
            logger.warning("MessagePack not available, falling back to JSON")
            self.config.default_format = SerializationFormat.JSON

        if (
            self.config.default_format == SerializationFormat.CBOR
            and not CBOR_AVAILABLE
        ):
            logger.warning("CBOR not available, falling back to JSON")
            self.config.default_format = SerializationFormat.JSON

    def serialize(
        self,
        data: Any,
        format: SerializationFormat | None = None,
    ) -> bytes:
        """Securely serialize data using the specified format

        Args:
            data: Data to serialize
            format: Serialization format (defaults to config default)

        Returns:
            Serialized bytes

        Raises:
            ValueError: If data cannot be serialized
            RuntimeError: If serialization fails
        """
        format = format or self.config.default_format

        try:
            if format == SerializationFormat.JSON:
                serialized = json.dumps(data, default=str).encode("utf-8")
            elif format == SerializationFormat.MSGPACK and MSGPACK_AVAILABLE:
                serialized = msgpack.packb(data, default=str)
            elif format == SerializationFormat.CBOR and CBOR_AVAILABLE:
                serialized = cbor2.dumps(data)
            else:
                raise ValueError(f"Unsupported serialization format: {format}")

            # Validate size
            if len(serialized) > self.config.max_size_bytes:
                raise ValueError(f"Serialized data too large: {len(serialized)} bytes")

            # Add checksum if enabled
            if self.config.enable_checksums:
                checksum = hashlib.sha256(serialized).hexdigest()[:16]
                serialized = f"CHECKSUM:{checksum}:".encode() + serialized

            # Add format identifier
            format_header = f"FORMAT:{format.value}:".encode()
            return format_header + serialized

        except Exception as e:
            logger.error(f"Serialization failed: {e}")
            raise RuntimeError(f"Failed to serialize data: {e}")

    def deserialize(self, data: bytes) -> Any:
        """Securely deserialize data

        Args:
            data: Serialized bytes

        Returns:
            Deserialized data

        Raises:
            ValueError: If data format is invalid
            RuntimeError: If deserialization fails
        """
        try:
            # Extract format identifier
            if not data.startswith(b"FORMAT:"):
                raise ValueError("Invalid serialized data format")

            format_end = data.find(b":", 7)
            if format_end == -1:
                raise ValueError("Invalid format header")

            format_str = data[7:format_end].decode()
            format = SerializationFormat(format_str)

            # Extract checksum if present
            payload_start = format_end + 1
            if data[payload_start : payload_start + 9] == b"CHECKSUM:":
                checksum_end = data.find(b":", payload_start + 9)
                if checksum_end == -1:
                    raise ValueError("Invalid checksum header")

                expected_checksum = data[payload_start + 9 : checksum_end].decode()
                payload_start = checksum_end + 1

                # Verify checksum
                payload = data[payload_start:]
                actual_checksum = hashlib.sha256(payload).hexdigest()[:16]
                if actual_checksum != expected_checksum:
                    raise ValueError("Checksum verification failed")
            else:
                payload = data[payload_start:]

            # Deserialize based on format
            if format == SerializationFormat.JSON:
                return json.loads(payload.decode("utf-8"))
            if format == SerializationFormat.MSGPACK and MSGPACK_AVAILABLE:
                return msgpack.unpackb(payload, raw=False)
            if format == SerializationFormat.CBOR and CBOR_AVAILABLE:
                return cbor2.loads(payload)
            raise ValueError(f"Unsupported deserialization format: {format}")

        except Exception as e:
            logger.error(f"Deserialization failed: {e}")
            raise RuntimeError(f"Failed to deserialize data: {e}")

    def serialize_to_file(
        self,
        data: Any,
        filepath: str,
        format: SerializationFormat | None = None,
    ) -> None:
        """Serialize data to file"""
        serialized = self.serialize(data, format)
        with open(filepath, "wb") as f:
            f.write(serialized)

    def deserialize_from_file(self, filepath: str) -> Any:
        """Deserialize data from file"""
        with open(filepath, "rb") as f:
            data = f.read()
        return self.deserialize(data)


# Global serializer instance
_serializer: SecureSerializer | None = None


def get_serializer() -> SecureSerializer:
    """Get global serializer instance"""
    global _serializer
    if _serializer is None:
        _serializer = SecureSerializer()
    return _serializer


def serialize(data: Any, format: SerializationFormat | None = None) -> bytes:
    """Convenience function for serialization"""
    return get_serializer().serialize(data, format)


def deserialize(data: bytes) -> Any:
    """Convenience function for deserialization"""
    return get_serializer().deserialize(data)


def serialize_to_file(
    data: Any,
    filepath: str,
    format: SerializationFormat | None = None,
) -> None:
    """Convenience function for file serialization"""
    get_serializer().serialize_to_file(data, filepath, format)


def deserialize_from_file(filepath: str) -> Any:
    """Convenience function for file deserialization"""
    return get_serializer().deserialize_from_file(filepath)


# Migration utilities for replacing pickle
def migrate_from_pickle(pickle_data: bytes) -> bytes:
    """Migrate pickle data to secure format
    This is a one-time migration utility
    """
    try:
        import pickle

        data = pickle.loads(pickle_data)
        return serialize(data)
    except Exception as e:
        logger.error(f"Failed to migrate pickle data: {e}")
        raise RuntimeError(f"Pickle migration failed: {e}")


def safe_pickle_replacement(data: Any) -> bytes:
    """Safe replacement for pickle.dumps()
    Use this to replace pickle.dumps() calls
    """
    return serialize(data)


def safe_pickle_loads_replacement(data: bytes) -> Any:
    """Safe replacement for pickle.loads()
    Use this to replace pickle.loads() calls
    """
    return deserialize(data)
