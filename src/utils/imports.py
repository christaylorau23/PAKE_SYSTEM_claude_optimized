#!/usr/bin/env python3
"""PAKE System - Centralized Import Utility
Provides safe, consistent import patterns to replace sys.path.append() usage
"""

import importlib
import importlib.util
import logging
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ImportError(Exception):
    """Custom import exception for PAKE system"""


class SafeImporter:
    """Centralized import manager for the PAKE system

    Provides safe, predictable import patterns to replace dynamic sys.path manipulation
    """

    def __init__(self):
        self._import_cache: dict[str, Any] = {}
        self._failed_imports: list[str] = []

    def safe_import_module(
        self,
        module_name: str,
        package: str | None = None,
        fallback_modules: list[str] | None = None,
    ) -> Any | None:
        """Safely import a module with fallback options

        Args:
            module_name: Name of the module to import
            package: Package context for relative imports
            fallback_modules: List of fallback module names

        Returns:
            Imported module or None if all imports fail

        Raises:
            ImportError: If module cannot be imported and no fallbacks work
        """
        cache_key = f"{package}.{module_name}" if package else module_name

        # Check cache first
        if cache_key in self._import_cache:
            return self._import_cache[cache_key]

        # Skip if previously failed
        if cache_key in self._failed_imports:
            return None

        try:
            module = importlib.import_module(module_name, package)
            self._import_cache[cache_key] = module
            logger.debug(f"Successfully imported {cache_key}")
            return module

        except ImportError as e:
            logger.warning(f"Failed to import {cache_key}: {e}")

            # Try fallback modules
            if fallback_modules:
                for fallback in fallback_modules:
                    try:
                        fallback_module = importlib.import_module(fallback, package)
                        self._import_cache[cache_key] = fallback_module
                        logger.info(f"Using fallback {fallback} for {cache_key}")
                        return fallback_module
                    except ImportError:
                        continue

            # Mark as failed and return None
            self._failed_imports.append(cache_key)
            return None

    def safe_import_from(
        self,
        module_name: str,
        attr_names: str | list[str],
        package: str | None = None,
        required: bool = True,
    ) -> dict[str, Any]:
        """Safely import specific attributes from a module

        Args:
            module_name: Name of the module
            attr_names: Attribute name(s) to import
            package: Package context for relative imports
            required: Whether to raise exception if import fails

        Returns:
            Dictionary mapping attribute names to imported objects

        Raises:
            ImportError: If required=True and import fails
        """
        if isinstance(attr_names, str):
            attr_names = [attr_names]

        result = {}

        try:
            module = self.safe_import_module(module_name, package)
            if module is None:
                if required:
                    raise ImportError(f"Could not import required module {module_name}")
                return result

            for attr_name in attr_names:
                if hasattr(module, attr_name):
                    result[attr_name] = getattr(module, attr_name)
                elif required:
                    raise ImportError(
                        f"Module {module_name} has no attribute {attr_name}",
                    )
                else:
                    logger.warning(
                        f"Module {module_name} missing optional attribute {attr_name}",
                    )

        except ImportError as e:
            if required:
                raise ImportError(f"Failed to import from {module_name}: {e}")
            logger.warning(f"Optional import failed: {e}")

        return result

    def import_from_path(
        self,
        file_path: str | Path,
        module_name: str | None = None,
    ) -> Any | None:
        """Import a module from a specific file path

        Args:
            file_path: Path to the Python file
            module_name: Name to give the module (defaults to filename)

        Returns:
            Imported module or None if import fails
        """
        file_path = Path(file_path)

        if not file_path.exists():
            logger.error(f"File not found: {file_path}")
            return None

        if module_name is None:
            module_name = file_path.stem

        try:
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if spec is None or spec.loader is None:
                logger.error(f"Could not create spec for {file_path}")
                return None

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            self._import_cache[str(file_path)] = module
            logger.debug(f"Successfully imported {module_name} from {file_path}")
            return module

        except Exception as e:
            logger.error(f"Failed to import {file_path}: {e}")
            return None

    @contextmanager
    def temporary_path(self, path: str | Path):
        """Temporarily add a path to sys.path (context manager)

        Args:
            path: Path to temporarily add
        """
        path_str = str(Path(path).resolve())

        if path_str not in sys.path:
            sys.path.insert(0, path_str)
            try:
                yield
            finally:
                if path_str in sys.path:
                    sys.path.remove(path_str)
        else:
            yield

    def clear_cache(self):
        """Clear the import cache"""
        self._import_cache.clear()
        self._failed_imports.clear()
        logger.debug("Import cache cleared")

    def get_import_stats(self) -> dict[str, Any]:
        """Get statistics about imports"""
        return {
            "cached_imports": len(self._import_cache),
            "failed_imports": len(self._failed_imports),
            "cached_modules": list(self._import_cache.keys()),
            "failed_modules": self._failed_imports.copy(),
        }


# Global importer instance
_importer = SafeImporter()


# Convenience functions
def safe_import(
    module_name: str,
    package: str | None = None,
    fallback_modules: list[str] | None = None,
) -> Any | None:
    """Convenience function for safe module import

    Args:
        module_name: Name of the module to import
        package: Package context for relative imports
        fallback_modules: List of fallback module names

    Returns:
        Imported module or None if import fails
    """
    return _importer.safe_import_module(module_name, package, fallback_modules)


def safe_import_from(
    module_name: str,
    attr_names: str | list[str],
    package: str | None = None,
    required: bool = True,
) -> dict[str, Any]:
    """Convenience function for safe attribute import

    Args:
        module_name: Name of the module
        attr_names: Attribute name(s) to import
        package: Package context for relative imports
        required: Whether to raise exception if import fails

    Returns:
        Dictionary mapping attribute names to imported objects
    """
    return _importer.safe_import_from(module_name, attr_names, package, required)


def import_with_fallback(*module_names: str) -> Any | None:
    """Import the first available module from a list

    Args:
        module_names: Module names to try in order

    Returns:
        First successfully imported module or None
    """
    for module_name in module_names:
        module = _importer.safe_import_module(module_name)
        if module is not None:
            return module
    return None


def require_import(module_name: str, package: str | None = None) -> Any:
    """Import a required module, raising exception if it fails

    Args:
        module_name: Name of the module to import
        package: Package context for relative imports

    Returns:
        Imported module

    Raises:
        ImportError: If module cannot be imported
    """
    module = _importer.safe_import_module(module_name, package)
    if module is None:
        raise ImportError(f"Required module {module_name} could not be imported")
    return module


# Legacy compatibility functions (to replace existing patterns)
def add_to_path_temporarily(path: str | Path):
    """Context manager to temporarily add path (replaces sys.path.append patterns)

    Args:
        path: Path to temporarily add

    Returns:
        Context manager
    """
    return _importer.temporary_path(path)


def clear_import_cache():
    """Clear the global import cache"""
    _importer.clear_cache()


def get_import_statistics() -> dict[str, Any]:
    """Get global import statistics"""
    return _importer.get_import_stats()
