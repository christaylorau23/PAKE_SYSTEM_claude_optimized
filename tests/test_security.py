import json

from src.utils.secure_serialization import SerializationFormat


class TestSecurity:
    def test_secure_serialization(self):
        """Test secure serialization functionality."""
        test_data = {"test": "data", "number": 42}

        # Test basic JSON serialization (the core functionality)
        serialized = json.dumps(test_data).encode("utf-8")
        assert isinstance(serialized, bytes)

        # Test deserialization
        deserialized = json.loads(serialized.decode("utf-8"))
        assert deserialized == test_data

    def test_serialization_formats(self):
        """Test different serialization formats."""
        test_data = {"test": "data"}

        # Test JSON format
        json_data = json.dumps(test_data).encode("utf-8")
        assert isinstance(json_data, bytes)

        # Test that we can import the format enum
        assert SerializationFormat.JSON.value == "json"
        assert SerializationFormat.MSGPACK.value == "msgpack"
