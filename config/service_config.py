#!/usr/bin/env python3
"""
Unified Configuration System for PAKE System
Supports hierarchical configuration loading: defaults -> config.json -> environment variables
"""

import os
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union
from dataclasses import dataclass, field
from datetime import timedelta

logger = logging.getLogger(__name__)

@dataclass
class VaultConfig:
    """Vault-specific configuration settings"""
    # Path configuration
    default_vault_name: str = "Knowledge-Vault"
    folder_structure: Dict[str, str] = field(default_factory=lambda: {
        "SourceNote": "00-Inbox",
        "DailyNote": "01-Daily", 
        "ProjectNote": "01-Projects",
        "InsightNote": "02-Areas"
    })
    
    # File handling
    max_filename_length: int = 50
    default_file_extension: str = ".md"
    summary_truncate_length: int = 200
    
    # Note processing
    default_confidence_score: float = 0.7
    default_note_status: str = "Raw"
    default_verification_status: str = "pending"

@dataclass  
class SearchConfig:
    """Search and pagination configuration"""
    default_search_limit: int = 10
    max_search_limit: int = 100
    min_confidence_threshold: float = 0.0
    max_confidence_threshold: float = 1.0

@dataclass
class CacheConfig:
    """Caching configuration settings"""
    default_ttl_seconds: int = 300  # 5 minutes
    production_ttl_seconds: int = 300
    development_ttl_seconds: int = 0  # No cache in development
    max_ttl_seconds: int = 3600  # 1 hour

@dataclass
class LoggingConfig:
    """Logging configuration settings"""
    default_level: str = "INFO"
    json_formatting: bool = True
    include_stack_trace: bool = False
    max_stack_trace_lines: int = 5
    log_to_file: bool = False
    log_file_name: str = "pake_system.log"

@dataclass
class SecurityConfig:
    """Security-related configuration"""
    enable_path_traversal_protection: bool = True
    allowed_filename_chars: str = " -_"  # In addition to alphanumeric
    filename_replacement_char: str = "-"
    max_path_depth: int = 10
    
@dataclass
class ServerConfig:
    """Server and API configuration"""
    server_name: str = "pake-server"
    server_version: str = "1.0.0"
    mcp_server_port: int = 8000
    bridge_port: int = 3000
    health_check_path: str = "/health"
    api_timeout_seconds: int = 30

class ServiceConfig:
    """
    Unified configuration manager with hierarchical loading:
    1. Default values (from dataclasses)
    2. Config file overrides
    3. Environment variable overrides
    """
    
    def __init__(self, config_file: Optional[Union[str, Path]] = None, 
                 environment_prefix: str = "PAKE_"):
        self.environment_prefix = environment_prefix
        self.config_file_path = None
        
        # Initialize with default configurations
        self.vault = VaultConfig()
        self.search = SearchConfig()
        self.cache = CacheConfig()
        self.logging = LoggingConfig()
        self.security = SecurityConfig()
        self.server = ServerConfig()
        
        # Load configuration hierarchy
        self._load_configuration(config_file)
        
        logger.info(f"ServiceConfig initialized with file: {self.config_file_path}")

    def _load_configuration(self, config_file: Optional[Union[str, Path]]):
        """Load configuration in hierarchical order"""
        
        # Step 1: Find and load config file
        config_data = self._load_config_file(config_file)
        
        # Step 2: Apply config file overrides
        if config_data:
            self._apply_config_overrides(config_data)
            
        # Step 3: Apply environment variable overrides
        self._apply_environment_overrides()
        
    def _find_config_file(self, config_file: Optional[Union[str, Path]]) -> Optional[Path]:
        """Find configuration file using multiple search strategies"""
        
        search_paths = []
        
        # 1. Explicit config file path
        if config_file:
            search_paths.append(Path(config_file))
            
        # 2. Environment variable
        env_config_path = os.getenv(f"{self.environment_prefix}CONFIG_FILE")
        if env_config_path:
            search_paths.append(Path(env_config_path))
            
        # 3. Standard locations relative to current working directory
        cwd = Path.cwd()
        search_paths.extend([
            cwd / "config.json",
            cwd / "configs" / "config.json",
            cwd / "config" / "config.json"
        ])
        
        # 4. Standard locations relative to script directory
        if __file__:
            script_dir = Path(__file__).parent
            search_paths.extend([
                script_dir / "config.json",
                script_dir / ".." / "config.json",
                script_dir / ".." / "configs" / "config.json"
            ])
            
        # Return first existing file
        for path in search_paths:
            try:
                if path.exists() and path.is_file():
                    return path.resolve()
            except (OSError, PermissionError):
                continue
                
        return None
        
    def _load_config_file(self, config_file: Optional[Union[str, Path]]) -> Optional[Dict[str, Any]]:
        """Load configuration from JSON file"""
        
        config_path = self._find_config_file(config_file)
        if not config_path:
            logger.info("No configuration file found, using defaults")
            return None
            
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                self.config_file_path = config_path
                logger.info(f"Loaded configuration from: {config_path}")
                return config_data
                
        except (FileNotFoundError, PermissionError) as e:
            logger.warning(f"Cannot read config file {config_path}: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file {config_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error loading config file {config_path}: {e}")
            return None
            
    def _apply_config_overrides(self, config_data: Dict[str, Any]):
        """Apply configuration file overrides to default values"""
        
        config_sections = {
            'vault': self.vault,
            'search': self.search, 
            'cache': self.cache,
            'logging': self.logging,
            'security': self.security,
            'server': self.server
        }
        
        for section_name, section_obj in config_sections.items():
            if section_name in config_data:
                section_config = config_data[section_name]
                for key, value in section_config.items():
                    if hasattr(section_obj, key):
                        # Type validation
                        current_value = getattr(section_obj, key)
                        if isinstance(current_value, type(value)) or current_value is None:
                            setattr(section_obj, key, value)
                            logger.debug(f"Config override: {section_name}.{key} = {value}")
                        else:
                            logger.warning(f"Type mismatch for {section_name}.{key}: expected {type(current_value)}, got {type(value)}")
                    else:
                        logger.warning(f"Unknown config key: {section_name}.{key}")
                        
    def _apply_environment_overrides(self):
        """Apply environment variable overrides"""
        
        # Define environment variable mappings
        env_mappings = {
            # Vault configuration
            f"{self.environment_prefix}VAULT_PATH": ("vault", "vault_path"),
            f"{self.environment_prefix}MAX_FILENAME_LENGTH": ("vault", "max_filename_length"),
            f"{self.environment_prefix}SUMMARY_LENGTH": ("vault", "summary_truncate_length"),
            f"{self.environment_prefix}DEFAULT_CONFIDENCE": ("vault", "default_confidence_score"),
            
            # Search configuration  
            f"{self.environment_prefix}SEARCH_LIMIT": ("search", "default_search_limit"),
            f"{self.environment_prefix}MAX_SEARCH_LIMIT": ("search", "max_search_limit"),
            
            # Cache configuration
            f"{self.environment_prefix}CACHE_TTL": ("cache", "default_ttl_seconds"),
            f"{self.environment_prefix}CACHE_TTL_PROD": ("cache", "production_ttl_seconds"),
            f"{self.environment_prefix}CACHE_TTL_DEV": ("cache", "development_ttl_seconds"),
            
            # Logging configuration
            f"{self.environment_prefix}LOG_LEVEL": ("logging", "default_level"),
            f"{self.environment_prefix}LOG_JSON": ("logging", "json_formatting"),
            f"{self.environment_prefix}LOG_STACK_LINES": ("logging", "max_stack_trace_lines"),
            
            # Server configuration
            f"{self.environment_prefix}SERVER_PORT": ("server", "mcp_server_port"),
            f"{self.environment_prefix}BRIDGE_PORT": ("server", "bridge_port"),
            f"{self.environment_prefix}API_TIMEOUT": ("server", "api_timeout_seconds"),
        }
        
        for env_var, (section_name, attr_name) in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                section_obj = getattr(self, section_name)
                current_value = getattr(section_obj, attr_name)
                
                # Type conversion based on current value type
                try:
                    if isinstance(current_value, bool):
                        converted_value = env_value.lower() in ('true', '1', 'yes', 'on')
                    elif isinstance(current_value, int):
                        converted_value = int(env_value)
                    elif isinstance(current_value, float):
                        converted_value = float(env_value)
                    else:
                        converted_value = env_value
                        
                    setattr(section_obj, attr_name, converted_value)
                    logger.debug(f"Environment override: {section_name}.{attr_name} = {converted_value}")
                    
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid environment value for {env_var}: {env_value} ({e})")
                    
    def get_vault_path(self) -> Path:
        """Get the vault path with platform-independent handling"""
        
        # Check for explicit vault path from environment or config
        vault_path_str = os.getenv('VAULT_PATH')
        
        if vault_path_str:
            return Path(vault_path_str).resolve()
            
        # Use platform-independent default
        home_dir = Path.home()
        default_vault_path = home_dir / self.vault.default_vault_name
        
        return default_vault_path.resolve()
        
    def get_cache_ttl(self, environment: str = None) -> int:
        """Get appropriate cache TTL based on environment"""
        
        if environment is None:
            environment = os.getenv("NODE_ENV", "development").lower()
            
        if environment == "production":
            return self.cache.production_ttl_seconds
        else:
            return self.cache.development_ttl_seconds
            
    def get_log_level(self) -> str:
        """Get log level from environment with fallback"""
        return os.getenv("LOG_LEVEL", self.logging.default_level).upper()
        
    def get_folder_for_note_type(self, note_type: str) -> str:
        """Get vault folder for specific note type"""
        return self.vault.folder_structure.get(note_type, self.vault.folder_structure["SourceNote"])
        
    def validate_configuration(self) -> bool:
        """Validate configuration values are within acceptable ranges"""
        
        issues = []
        
        # Validate search limits
        if self.search.default_search_limit > self.search.max_search_limit:
            issues.append("default_search_limit cannot be greater than max_search_limit")
            
        if self.search.max_search_limit <= 0:
            issues.append("max_search_limit must be positive")
            
        # Validate confidence thresholds
        if not (0.0 <= self.vault.default_confidence_score <= 1.0):
            issues.append("default_confidence_score must be between 0.0 and 1.0")
            
        # Validate cache TTL
        if self.cache.default_ttl_seconds < 0:
            issues.append("cache TTL cannot be negative")
            
        if self.cache.default_ttl_seconds > self.cache.max_ttl_seconds:
            issues.append("default_ttl_seconds cannot exceed max_ttl_seconds")
            
        # Validate filename length
        if self.vault.max_filename_length <= 0:
            issues.append("max_filename_length must be positive")
            
        if issues:
            for issue in issues:
                logger.error(f"Configuration validation error: {issue}")
            return False
            
        logger.info("Configuration validation passed")
        return True
        
    def to_dict(self) -> Dict[str, Any]:
        """Export configuration as dictionary for inspection/debugging"""
        
        return {
            "vault": {
                "default_vault_name": self.vault.default_vault_name,
                "folder_structure": self.vault.folder_structure,
                "max_filename_length": self.vault.max_filename_length,
                "default_file_extension": self.vault.default_file_extension,
                "summary_truncate_length": self.vault.summary_truncate_length,
                "default_confidence_score": self.vault.default_confidence_score,
                "default_note_status": self.vault.default_note_status,
                "default_verification_status": self.vault.default_verification_status
            },
            "search": {
                "default_search_limit": self.search.default_search_limit,
                "max_search_limit": self.search.max_search_limit,
                "min_confidence_threshold": self.search.min_confidence_threshold,
                "max_confidence_threshold": self.search.max_confidence_threshold
            },
            "cache": {
                "default_ttl_seconds": self.cache.default_ttl_seconds,
                "production_ttl_seconds": self.cache.production_ttl_seconds,
                "development_ttl_seconds": self.cache.development_ttl_seconds,
                "max_ttl_seconds": self.cache.max_ttl_seconds
            },
            "logging": {
                "default_level": self.logging.default_level,
                "json_formatting": self.logging.json_formatting,
                "include_stack_trace": self.logging.include_stack_trace,
                "max_stack_trace_lines": self.logging.max_stack_trace_lines,
                "log_to_file": self.logging.log_to_file,
                "log_file_name": self.logging.log_file_name
            },
            "security": {
                "enable_path_traversal_protection": self.security.enable_path_traversal_protection,
                "allowed_filename_chars": self.security.allowed_filename_chars,
                "filename_replacement_char": self.security.filename_replacement_char,
                "max_path_depth": self.security.max_path_depth
            },
            "server": {
                "server_name": self.server.server_name,
                "server_version": self.server.server_version,
                "mcp_server_port": self.server.mcp_server_port,
                "bridge_port": self.server.bridge_port,
                "health_check_path": self.server.health_check_path,
                "api_timeout_seconds": self.server.api_timeout_seconds
            },
            "_metadata": {
                "config_file_path": str(self.config_file_path) if self.config_file_path else None,
                "environment_prefix": self.environment_prefix,
                "vault_path": str(self.get_vault_path()),
                "current_cache_ttl": self.get_cache_ttl(),
                "current_log_level": self.get_log_level()
            }
        }

# Global configuration instance
_config_instance: Optional[ServiceConfig] = None

def get_config(config_file: Optional[Union[str, Path]] = None, 
               force_reload: bool = False) -> ServiceConfig:
    """Get global configuration instance (singleton pattern)"""
    
    global _config_instance
    
    if _config_instance is None or force_reload:
        _config_instance = ServiceConfig(config_file)
        
    return _config_instance