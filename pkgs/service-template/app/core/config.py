"""
Configuration management for PAKE services
"""

import os
from functools import lru_cache
from typing import List, Optional

from pydantic import BaseSettings, Field, validator


class Settings(BaseSettings):
    """Application settings."""

    # Basic settings
    PROJECT_NAME: str = Field(default="PAKE Service", env="PROJECT_NAME")
    PROJECT_DESCRIPTION: str = Field(default="PAKE System Microservice", env="PROJECT_DESCRIPTION")
    VERSION: str = Field(default="1.0.0", env="VERSION")
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=False, env="DEBUG")

    # Server settings
    HOST: str = Field(default="127.0.0.1", env="HOST")
    PORT: int = Field(default=8000, env="PORT")

    # Security settings
    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, env="REFRESH_TOKEN_EXPIRE_DAYS")
    ALGORITHM: str = Field(default="HS256", env="ALGORITHM")

    # CORS settings
    ALLOWED_HOSTS: List[str] = Field(default=["*"], env="ALLOWED_HOSTS")

    # Database settings
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    DATABASE_POOL_SIZE: int = Field(default=10, env="DATABASE_POOL_SIZE")
    DATABASE_MAX_OVERFLOW: int = Field(default=20, env="DATABASE_MAX_OVERFLOW")

    # Redis settings
    REDIS_URL: str = Field(..., env="REDIS_URL")
    REDIS_POOL_SIZE: int = Field(default=10, env="REDIS_POOL_SIZE")

    # External API settings
    FIRECRAWL_API_KEY: Optional[str] = Field(default=None, env="FIRECRAWL_API_KEY")
    ARXIV_API_URL: str = Field(default="http://export.arxiv.org/api/query", env="ARXIV_API_URL")
    PUBMED_API_URL: str = Field(default="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/", env="PUBMED_API_URL")

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

    @validator("ALLOWED_HOSTS", pre=True)
    def parse_allowed_hosts(cls, v):
        """Parse ALLOWED_HOSTS from string or list."""
        if isinstance(v, str):
            return [host.strip() for host in v.split(",")]
        return v

    @validator("ENVIRONMENT")
    def validate_environment(cls, v):
        """Validate environment setting."""
        allowed_envs = ["development", "staging", "production"]
        if v not in allowed_envs:
            raise ValueError(f"Environment must be one of: {allowed_envs}")
        return v

    @validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        """Validate log level setting."""
        allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed_levels:
            raise ValueError(f"Log level must be one of: {allowed_levels}")
        return v.upper()

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
