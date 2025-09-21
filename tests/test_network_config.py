from src.utils.secure_network_config import Environment, SecureNetworkConfig


class TestNetworkConfig:
    def test_development_config(self):
        """Test development network configuration."""
        config = SecureNetworkConfig(Environment.DEVELOPMENT)

        assert config.config.bind_address == "127.0.0.1"
        assert config.config.port == 8000
        assert not config.config.enable_ssl

    def test_production_config(self):
        """Test production network configuration."""
        config = SecureNetworkConfig(Environment.PRODUCTION)

        assert config.config.bind_address != "0.0.0.0"
        assert config.config.enable_ssl
        assert config.config.enable_rate_limiting

    def test_config_validation(self):
        """Test configuration validation."""
        config = SecureNetworkConfig(Environment.PRODUCTION)
        warnings = config.validate_configuration()

        # Should not have critical warnings for production
        critical_warnings = [w for w in warnings if "CRITICAL" in w]
        assert len(critical_warnings) == 0
