"""Configuration management for PAKE System
Enterprise-grade configuration with Pydantic validation

Security Features:
- Integrates with HashiCorp Vault for secure secrets management
- Falls back to environment variables when Vault is unavailable
- Never logs or prints sensitive configuration values
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings

# Import Vault client (graceful degradation if not available)
try:
    from src.pake_system.core.vault_client import VaultClientError, get_vault_client

    VAULT_AVAILABLE = True
except ImportError:
    VAULT_AVAILABLE = False
    VaultClientError = Exception


class Settings(BaseSettings):
    """Enterprise PAKE System settings with comprehensive validation."""

    # Basic settings
    PROJECT_NAME: str = Field(default="PAKE System", env="PROJECT_NAME")
    PROJECT_DESCRIPTION: str = Field(
        default="Enterprise Knowledge Management & AI Research Platform",
        env="PROJECT_DESCRIPTION",
    )
    VERSION: str = Field(default="10.1.0", env="VERSION")
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=False, env="DEBUG")

    # Server settings
    HOST: str = Field(default="127.0.0.1", env="HOST")
    PORT: int = Field(default=8000, env="PORT")

    # Security settings
    # Note: SECRET_KEY can come from Vault or environment variable
    SECRET_KEY: Optional[str] = Field(default=None, env="SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    ALGORITHM: str = Field(default="HS256", env="ALGORITHM")

    # CORS settings
    ALLOWED_HOSTS: list[str] = Field(default=["*"], env="ALLOWED_HOSTS")

    # Database settings
    # Note: DATABASE_URL can come from Vault or environment variable
    DATABASE_URL: Optional[str] = Field(default=None, env="DATABASE_URL")
    DATABASE_POOL_SIZE: int = Field(default=10, env="DATABASE_POOL_SIZE")
    DATABASE_MAX_OVERFLOW: int = Field(default=20, env="DATABASE_MAX_OVERFLOW")

    # Redis settings
    # Note: REDIS_URL can come from Vault or environment variable
    REDIS_URL: Optional[str] = Field(default=None, env="REDIS_URL")
    REDIS_POOL_SIZE: int = Field(default=10, env="REDIS_POOL_SIZE")

    # External API settings
    FIRECRAWL_API_KEY: Optional[str] = Field(default=None, env="FIRECRAWL_API_KEY")
    ARXIV_API_URL: str = Field(
        default="http://export.arxiv.org/api/query", env="ARXIV_API_URL"
    )
    PUBMED_API_URL: str = Field(
        default="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/", env="PUBMED_API_URL"
    )

    # Monitoring settings
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    ENABLE_METRICS: bool = Field(default=True, env="ENABLE_METRICS")
    METRICS_PORT: int = Field(default=9090, env="METRICS_PORT")

    # Rate limiting
    RATE_LIMIT_REQUESTS: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    RATE_LIMIT_WINDOW: int = Field(default=60, env="RATE_LIMIT_WINDOW")

    # Cache settings
    CACHE_TTL: int = Field(default=3600, env="CACHE_TTL")  # 1 hour
    CACHE_MAX_SIZE: int = Field(default=1000, env="CACHE_MAX_SIZE")

    # Vault settings
    VAULT_URL: Optional[str] = Field(default=None, env="VAULT_URL")
    VAULT_TOKEN: Optional[str] = Field(default=None, env="VAULT_TOKEN")
    VAULT_MOUNT_POINT: str = Field(default="secret", env="VAULT_MOUNT_POINT")

    # Performance settings
    MAX_WORKERS: int = Field(default=4, env="MAX_WORKERS")
    TIMEOUT_SECONDS: int = Field(default=30, env="TIMEOUT_SECONDS")

    # SQL Query Logging - Phase 5: Performance Under Pressure
    # Enable SQL echo for N+1 query detection and performance analysis
    SQL_ECHO: bool = Field(default=False, env="SQL_ECHO")
    SQL_LOG_LEVEL: str = Field(default="WARNING", env="SQL_LOG_LEVEL")

    # Query performance monitoring
    SLOW_QUERY_THRESHOLD_MS: int = Field(default=1000, env="SLOW_QUERY_THRESHOLD_MS")
    LOG_SLOW_QUERIES: bool = Field(default=True, env="LOG_SLOW_QUERIES")

    # N+1 query detection
    DETECT_N_PLUS_1: bool = Field(default=False, env="DETECT_N_PLUS_1")
    MAX_QUERIES_PER_REQUEST: int = Field(default=50, env="MAX_QUERIES_PER_REQUEST")

    # Enable/disable Vault integration
    USE_VAULT: bool = Field(default=True, env="USE_VAULT")

    @model_validator(mode="after")
    def load_secrets_from_vault(self):
        """Load secrets from HashiCorp Vault with fail-fast security.

        This validator runs after field validation. It implements fail-fast security:
        - Application refuses to start if required secrets are missing
        - No hardcoded fallbacks allowed
        - All secrets must be configured in Vault or environment variables
        - Comprehensive error messages guide proper configuration

        Security Features:
        - Fail-fast: Application stops if secrets are missing
        - No hardcoded fallbacks: Prevents accidental secret exposure
        - Audit logging: All secret access is logged
        - Environment validation: Ensures proper configuration
        """
        # Validate environment configuration
        if self.ENVIRONMENT not in ["development", "staging", "production", "test"]:
            raise ValueError(f"Invalid environment: {self.ENVIRONMENT}")

        # For production, Vault is mandatory
        if self.ENVIRONMENT == "production" and not self.USE_VAULT:
            raise ValueError(
                "Vault integration is mandatory for production environment. "
                "Set USE_VAULT=true and configure VAULT_URL and VAULT_TOKEN."
            )

        # Skip Vault integration if disabled or not available
        if not self.USE_VAULT or not VAULT_AVAILABLE:
            # Validate required secrets are set via environment
            missing_secrets = []
            if not self.SECRET_KEY:
                missing_secrets.append("SECRET_KEY")
            if not self.DATABASE_URL:
                missing_secrets.append("DATABASE_URL")
            if not self.REDIS_URL:
                missing_secrets.append("REDIS_URL")

            if missing_secrets:
                raise ValueError(
                    f"Required secrets missing when Vault is disabled: {', '.join(missing_secrets)}. "
                    f"Set these environment variables or enable Vault integration."
                )
            return self

        # Validate Vault configuration
        if not self.VAULT_URL or not self.VAULT_TOKEN:
            raise ValueError(
                "Vault integration enabled but configuration incomplete. "
                "Set VAULT_URL and VAULT_TOKEN environment variables. "
                "This is a security requirement."
            )

        # Attempt to fetch secrets from Vault with fail-fast security
        try:
            vault_client = get_vault_client()

            # Validate Vault connection and required secrets
            health_check = vault_client.health_check()
            if health_check["status"] == "unhealthy":
                raise ValueError(f"Vault connection failed: {health_check['message']}")

            if not health_check["all_secrets_available"]:
                missing_secrets = [
                    path
                    for path, available in health_check["secrets_validation"].items()
                    if not available
                ]
                raise ValueError(
                    f"Required secrets missing in Vault: {', '.join(missing_secrets)}. "
                    f"Configure these secrets in Vault or set corresponding environment variables."
                )

            # Fetch SECRET_KEY from Vault if not already set
            if not self.SECRET_KEY:
                self.SECRET_KEY = vault_client.get_secret_key()

            # Fetch DATABASE_URL from Vault if not already set
            if not self.DATABASE_URL:
                self.DATABASE_URL = vault_client.get_database_url()

            # Fetch REDIS_URL from Vault if not already set
            if not self.REDIS_URL:
                self.REDIS_URL = vault_client.get_redis_url()

            # Fetch API keys from Vault if not already set
            if not self.FIRECRAWL_API_KEY:
                self.FIRECRAWL_API_KEY = vault_client.get_api_key("firecrawl_api_key")

        except VaultClientError as e:
            # Fail-fast: Don't start if secrets can't be loaded
            raise ValueError(
                f"Failed to load secrets from Vault: {e}. "
                f"This is a security requirement - application cannot start without proper secrets configuration."
            )

        return self

    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, v):
        """Parse ALLOWED_HOSTS from string or list."""
        if isinstance(v, str):
            return [host.strip() for host in v.split(",")]
        return v

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v):
        """Validate environment setting."""
        allowed_envs = ["development", "staging", "production", "test"]
        if v not in allowed_envs:
            raise ValueError(f"Environment must be one of: {allowed_envs}")
        return v

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level setting."""
        allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed_levels:
            raise ValueError(f"Log level must be one of: {allowed_levels}")
        return v.upper()

    @field_validator("SQL_LOG_LEVEL")
    @classmethod
    def validate_sql_log_level(cls, v):
        """Validate SQL log level setting."""
        allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed_levels:
            raise ValueError(f"SQL log level must be one of: {allowed_levels}")
        return v.upper()

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
