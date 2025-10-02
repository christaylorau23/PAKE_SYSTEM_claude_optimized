#!/usr/bin/env python3
"""
PAKE System - Unified Service Configuration
Enterprise-grade configuration management with hierarchical loading and validation
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)

# Global config instance for singleton pattern
_config_instance = None


class Environment(Enum):
    """Environment types"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


@dataclass
class VaultConfig:
    """Obsidian vault configuration"""
    path: str = field(default_factory=lambda: os.getenv('OBSIDIAN_VAULT_PATH', './vault'))
    auto_sync: bool = field(default_factory=lambda: os.getenv('VAULT_AUTO_SYNC', 'true').lower() == 'true')
    backup_enabled: bool = field(default_factory=lambda: os.getenv('VAULT_BACKUP_ENABLED', 'true').lower() == 'true')
    backup_interval_hours: int = field(default_factory=lambda: int(os.getenv('VAULT_BACKUP_INTERVAL', '24')))

    # Test-expected attributes
    default_vault_name: str = field(default_factory=lambda: os.getenv('PAKE_VAULT_NAME', 'Knowledge-Vault'))
    max_filename_length: int = field(default_factory=lambda: int(os.getenv('PAKE_MAX_FILENAME_LENGTH', '50')))
    default_file_extension: str = field(default_factory=lambda: os.getenv('PAKE_FILE_EXTENSION', '.md'))
    summary_truncate_length: int = field(default_factory=lambda: int(os.getenv('PAKE_SUMMARY_LENGTH', '200')))
    default_confidence_score: float = field(default_factory=lambda: float(os.getenv('PAKE_CONFIDENCE_SCORE', '0.7')))

    def __post_init__(self):
        """Validate vault configuration"""
        if not self.path:
            raise ValueError("Vault path cannot be empty")
        if self.backup_interval_hours < 1:
            raise ValueError("Backup interval must be at least 1 hour")
        if self.max_filename_length < 1:
            raise ValueError("Max filename length must be at least 1")
        if not (0.0 <= self.default_confidence_score <= 1.0):
            raise ValueError("Confidence score must be between 0.0 and 1.0")


@dataclass
class SearchConfig:
    """Search service configuration"""
    firecrawl_api_key: str = field(default_factory=lambda: os.getenv('FIRECRAWL_API_KEY', ''))
    pubmed_email: str = field(default_factory=lambda: os.getenv('PUBMED_EMAIL', ''))
    arxiv_base_url: str = field(default_factory=lambda: os.getenv('ARXIV_BASE_URL', 'http://export.arxiv.org/api/query'))
    max_results_per_source: int = field(default_factory=lambda: int(os.getenv('MAX_RESULTS_PER_SOURCE', '10')))
    request_timeout: int = field(default_factory=lambda: int(os.getenv('REQUEST_TIMEOUT', '30')))

    # Test-expected attributes
    default_search_limit: int = field(default_factory=lambda: int(os.getenv('PAKE_SEARCH_LIMIT', '10')))
    max_search_limit: int = field(default_factory=lambda: int(os.getenv('PAKE_MAX_SEARCH_LIMIT', '100')))

    def __post_init__(self):
        """Validate search configuration"""
        if self.max_results_per_source < 1:
            raise ValueError("Max results per source must be at least 1")
        if self.request_timeout < 1:
            raise ValueError("Request timeout must be at least 1 second")
        if self.default_search_limit < 1:
            raise ValueError("Default search limit must be at least 1")
        if self.max_search_limit < self.default_search_limit:
            raise ValueError("Max search limit must be >= default search limit")


@dataclass
class CacheConfig:
    """Cache service configuration"""
    redis_url: str = field(default_factory=lambda: os.getenv('REDIS_URL', 'redis://localhost:6379'))
    cache_ttl_seconds: int = field(default_factory=lambda: int(os.getenv('CACHE_TTL_SECONDS', '3600')))
    max_memory_cache_size: int = field(default_factory=lambda: int(os.getenv('MAX_MEMORY_CACHE_SIZE', '1000')))
    cache_compression: bool = field(default_factory=lambda: os.getenv('CACHE_COMPRESSION', 'true').lower() == 'true')

    # Test-expected attributes
    default_ttl_seconds: int = field(default_factory=lambda: int(os.getenv('PAKE_CACHE_TTL', '300')))
    production_ttl_seconds: int = field(default_factory=lambda: int(os.getenv('PAKE_CACHE_PROD_TTL', '300')))
    development_ttl_seconds: int = field(default_factory=lambda: int(os.getenv('PAKE_CACHE_DEV_TTL', '0')))

    def __post_init__(self):
        """Validate cache configuration"""
        if self.cache_ttl_seconds < 1:
            raise ValueError("Cache TTL must be at least 1 second")
        if self.max_memory_cache_size < 1:
            raise ValueError("Max memory cache size must be at least 1")
        if self.default_ttl_seconds < 0:
            raise ValueError("Default TTL seconds cannot be negative")
        if self.production_ttl_seconds < 0:
            raise ValueError("Production TTL seconds cannot be negative")


@dataclass
class LoggingConfig:
    """Logging configuration"""
    default_level: str = field(default_factory=lambda: os.getenv('PAKE_LOG_LEVEL', 'INFO'))
    json_formatting: bool = field(default_factory=lambda: os.getenv('PAKE_LOG_JSON', 'true').lower() == 'true')
    log_file: Optional[str] = field(default_factory=lambda: os.getenv('PAKE_LOG_FILE', None))

    def __post_init__(self):
        """Validate logging configuration"""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.default_level.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        # Normalize to uppercase
        self.default_level = self.default_level.upper()


@dataclass
class DatabaseConfig:
    """Database configuration"""
    url: str = field(default_factory=lambda: os.getenv('DATABASE_URL', 'postgresql://user:pass@localhost:5432/pake'))
    pool_size: int = field(default_factory=lambda: int(os.getenv('DB_POOL_SIZE', '10')))
    max_overflow: int = field(default_factory=lambda: int(os.getenv('DB_MAX_OVERFLOW', '20')))
    echo_sql: bool = field(default_factory=lambda: os.getenv('DB_ECHO_SQL', 'false').lower() == 'true')

    def __post_init__(self):
        """Validate database configuration"""
        if not self.url:
            raise ValueError("Database URL cannot be empty")
        if self.pool_size < 1:
            raise ValueError("Database pool size must be at least 1")


@dataclass
class SecurityConfig:
    """Security configuration"""
    jwt_secret_key: str = field(default_factory=lambda: os.getenv('JWT_SECRET_KEY', ''))
    jwt_algorithm: str = field(default_factory=lambda: os.getenv('JWT_ALGORITHM', 'HS256'))
    jwt_expire_minutes: int = field(default_factory=lambda: int(os.getenv('JWT_EXPIRE_MINUTES', '30')))
    bcrypt_rounds: int = field(default_factory=lambda: int(os.getenv('BCRYPT_ROUNDS', '12')))

    def __post_init__(self):
        """Validate security configuration"""
        if not self.jwt_secret_key:
            # Check environment from global config or environment variable
            env_str = os.getenv('PAKE_ENVIRONMENT', 'development').lower()
            if env_str in ['prod', 'production']:
                raise ValueError("JWT secret key must be set in production environment")
            logger.warning("JWT secret key not set - using default (not secure for production)")
            self.jwt_secret_key = os.getenv('JWT_SECRET_KEY_FALLBACK', 'dev-secret-key-change-in-production')
        if self.jwt_expire_minutes < 1:
            raise ValueError("JWT expire minutes must be at least 1")


@dataclass
class ServerConfig:
    """Server configuration"""
    server_name: str = field(default_factory=lambda: os.getenv('PAKE_SERVER_NAME', 'pake-server'))
    server_version: str = field(default_factory=lambda: os.getenv('PAKE_SERVER_VERSION', '1.0.0'))
    mcp_server_port: int = field(default_factory=lambda: int(os.getenv('PAKE_MCP_PORT', '8000')))
    bridge_port: int = field(default_factory=lambda: int(os.getenv('BRIDGE_PORT', '3001')))

    def __post_init__(self):
        """Validate server configuration"""
        if not self.server_name:
            raise ValueError("Server name cannot be empty")
        if self.mcp_server_port < 1 or self.mcp_server_port > 65535:
            raise ValueError("MCP server port must be between 1 and 65535")
        if self.bridge_port < 1 or self.bridge_port > 65535:
            raise ValueError("Bridge port must be between 1 and 65535")


class ServiceConfig:
    """
    Unified service configuration manager

    Features:
    - Hierarchical configuration loading
    - Environment-based overrides
    - Validation and type checking
    - Platform independence
    - Singleton pattern
    """

    def __init__(self, config_file: Optional[str] = None, environment: Optional[Environment] = None):
        """
        Initialize service configuration

        Args:
            config_file: Optional path to configuration file
            environment: Environment type (auto-detected if not provided)
        """
        self.environment = environment or self._detect_environment()
        self.config_file = config_file

        # Initialize configuration sections
        self.vault = VaultConfig()
        self.search = SearchConfig()
        self.cache = CacheConfig()
        self.logging = LoggingConfig()
        self.database = DatabaseConfig()
        self.security = SecurityConfig()
        self.server = ServerConfig()

        # Load configuration from file if provided
        if config_file:
            self._load_from_file(config_file)

        # Apply environment-specific overrides
        self._apply_environment_overrides()

        logger.info(f"Service configuration loaded for environment: {self.environment.value}")

    def _detect_environment(self) -> Environment:
        """Auto-detect environment from environment variables"""
        env_name = os.getenv('PAKE_ENVIRONMENT', 'development').lower()

        if env_name in ['test', 'testing']:
            return Environment.TESTING
        elif env_name in ['stage', 'staging']:
            return Environment.STAGING
        elif env_name in ['prod', 'production']:
            return Environment.PRODUCTION
        else:
            return Environment.DEVELOPMENT

    def _load_from_file(self, config_file: str) -> None:
        """Load configuration from JSON file"""
        try:
            config_path = Path(config_file)
            if not config_path.exists():
                logger.warning(f"Configuration file not found: {config_file}")
                return

            with open(config_path, 'r') as f:
                config_data = json.load(f)

            # Update configuration sections from file
            if 'vault' in config_data:
                self._update_config_section(self.vault, config_data['vault'])
            if 'search' in config_data:
                self._update_config_section(self.search, config_data['search'])
            if 'cache' in config_data:
                self._update_config_section(self.cache, config_data['cache'])
            if 'database' in config_data:
                self._update_config_section(self.database, config_data['database'])
            if 'security' in config_data:
                self._update_config_section(self.security, config_data['security'])
            if 'server' in config_data:
                self._update_config_section(self.server, config_data['server'])

            logger.info(f"Configuration loaded from file: {config_file}")

        except Exception as e:
            logger.error(f"Failed to load configuration from file {config_file}: {e}")
            raise

    def _update_config_section(self, config_obj: Any, config_data: Dict[str, Any]) -> None:
        """Update configuration object with data from file"""
        for key, value in config_data.items():
            if hasattr(config_obj, key):
                setattr(config_obj, key, value)

    def _apply_environment_overrides(self) -> None:
        """Apply environment-specific configuration overrides"""
        if self.environment == Environment.TESTING:
            # Test environment overrides
            self.database.url = os.getenv('TEST_DATABASE_URL', 'postgresql://test:test@localhost:5432/pake_test')
            self.cache.redis_url = os.getenv('TEST_REDIS_URL', 'redis://localhost:6379/1')
            self.security.jwt_expire_minutes = 5  # Short expiry for tests

        elif self.environment == Environment.PRODUCTION:
            # Production environment validations
            if not self.search.firecrawl_api_key:
                logger.warning("Firecrawl API key not set in production")
            if not self.search.pubmed_email:
                logger.warning("PubMed email not set in production")

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'environment': self.environment.value,
            'vault': self.vault.__dict__,
            'search': self.search.__dict__,
            'cache': self.cache.__dict__,
            'database': self.database.__dict__,
            'security': {k: v for k, v in self.security.__dict__.items() if k != 'jwt_secret_key'},  # Exclude secret
            'server': self.server.__dict__
        }

    def validate(self) -> List[str]:
        """Validate configuration and return list of issues"""
        issues = []

        try:
            # Validate each section
            self.vault.__post_init__()
        except ValueError as e:
            issues.append(f"Vault config: {e}")

        try:
            self.search.__post_init__()
        except ValueError as e:
            issues.append(f"Search config: {e}")

        try:
            self.cache.__post_init__()
        except ValueError as e:
            issues.append(f"Cache config: {e}")

        try:
            self.database.__post_init__()
        except ValueError as e:
            issues.append(f"Database config: {e}")

        try:
            self.security.__post_init__()
        except ValueError as e:
            issues.append(f"Security config: {e}")

        try:
            self.server.__post_init__()
        except ValueError as e:
            issues.append(f"Server config: {e}")

        return issues

    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment == Environment.PRODUCTION

    def is_testing(self) -> bool:
        """Check if running in testing environment"""
        return self.environment == Environment.TESTING

    def get_log_level(self) -> str:
        """Get the configured log level"""
        return self.logging.default_level

    def get_vault_path(self) -> Path:
        """Get the vault path as a Platform-independent Path object"""
        vault_path = os.getenv('VAULT_PATH', self.vault.path)

        # If no explicit path or path is relative, use default under home
        if not vault_path or not os.path.isabs(vault_path):
            return Path.home() / self.vault.default_vault_name

        return Path(vault_path).resolve()


def get_config(config_file: Optional[str] = None, force_reload: bool = False) -> ServiceConfig:
    """
    Get global service configuration instance (singleton pattern)

    Args:
        config_file: Optional path to configuration file
        force_reload: Force reload of configuration

    Returns:
        ServiceConfig instance
    """
    global _config_instance

    if _config_instance is None or force_reload:
        _config_instance = ServiceConfig(config_file=config_file)

    return _config_instance


def reset_config() -> None:
    """Reset global configuration instance (mainly for testing)"""
    global _config_instance
    _config_instance = None


# Export main classes and functions
__all__ = [
    'ServiceConfig',
    'VaultConfig',
    'SearchConfig',
    'CacheConfig',
    'DatabaseConfig',
    'SecurityConfig',
    'ServerConfig',
    'Environment',
    'get_config',
    'reset_config'
]
