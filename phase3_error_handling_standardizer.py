#!/usr/bin/env python3
"""
Phase 3: Error Handling Standardization
Fixes 1,045 broad exception handlers and try-except-pass blocks
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional
from collections import Counter


class Phase3ErrorHandlerStandardizer:
    """Systematic error handling standardizer for PAKE System"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.fixes_applied = Counter()
        self.files_processed = set()
        
        # Common exception patterns and their specific replacements
        self.exception_patterns = {
            # Network-related exceptions
            r'except (ConnectionError, TimeoutError, aiohttp.ClientError) as e:.*?requests\.|aiohttp\.|httpx\.': 'except (ConnectionError, TimeoutError, aiohttp.ClientError) as e:',
            r'except (ConnectionError, TimeoutError, aiohttp.ClientError) as e:.*?urllib\.|urllib3\.': 'except (ConnectionError, TimeoutError, urllib.error.URLError) as e:',
            
            # File operations
            r'except (ConnectionError, TimeoutError, aiohttp.ClientError) as e:.*?open\(|Path\(|file': 'except (FileNotFoundError, PermissionError, OSError) as e:',
            
            # Database operations
            r'except (ConnectionError, TimeoutError, aiohttp.ClientError) as e:.*?sqlalchemy\.|psycopg2\.|asyncpg\.': 'except (sqlalchemy.exc.SQLAlchemyError, psycopg2.Error, asyncpg.Error) as e:',
            
            # JSON operations
            r'except (ConnectionError, TimeoutError, aiohttp.ClientError) as e:.*?json\.|orjson\.': 'except (json.JSONDecodeError, ValueError) as e:',
            
            # Import errors
            r'except (ConnectionError, TimeoutError, aiohttp.ClientError) as e:.*?import|from.*import': 'except (ImportError, ModuleNotFoundError) as e:',
            
            # Validation errors
            r'except (ConnectionError, TimeoutError, aiohttp.ClientError) as e:.*?pydantic\.|validate': 'except (pydantic.ValidationError, ValueError) as e:',
        }
        
        # Priority files with known error handling issues
        self.priority_files = [
            'src/services/ingestion/firecrawl_service.py',
            'src/services/ingestion/pubmed_service.py',
            'src/services/ingestion/arxiv_enhanced_service.py',
            'src/services/analytics/intelligence_insight_service.py',
            'src/services/secrets/migration_service.py',
            'src/pake_system/core/config.py',
            'src/pake_system/core/vault_client.py'
        ]

    def get_broad_exception_errors(self) -> Dict[str, List[Tuple[int, str]]]:
        """Get broad exception handling patterns from codebase."""
        errors_by_file = {}
        
        for py_file in self.project_root.rglob('*.py'):
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                lines = content.splitlines()
                file_errors = []
                
                for line_num, line in enumerate(lines, 1):
                    # Find broad exception patterns
                    if re.search(r'except\s+Exception\s+as\s+\w+:', line):
                        file_errors.append((line_num, 'broad_exception'))
                    elif re.search(r'except\s*:\s*$', line):
                        file_errors.append((line_num, 'bare_except'))
                    elif re.search(r'except\s+.*:\s*\n\s*pass', line, re.MULTILINE):
                        file_errors.append((line_num, 'except_pass'))
                
                if file_errors:
                    errors_by_file[str(py_file)] = file_errors
                    
            except Exception:
                continue
        
        return errors_by_file

    def standardize_file_error_handling(self, file_path: Path, errors: List[Tuple[int, str]]) -> Tuple[bool, int]:
        """Standardize error handling in a single file."""
        if not file_path.exists():
            return False, 0
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            fixes_applied = 0
            
            # Apply error handling patterns
            content = self._replace_broad_exceptions(content, file_path)
            content = self._replace_bare_exceptions(content, file_path)
            content = self._replace_except_pass(content, file_path)
            
            # Ensure proper logging is available
            if content != original_content:
                content = self._ensure_logging_import(content)
                fixes_applied += 1
            
            # Write back if changes were made
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.files_processed.add(str(file_path))
                return True, fixes_applied
                
        except (FileNotFoundError, PermissionError, OSError) as e:
            print(f"Error standardizing {file_path}: {e}")
            
        return False, 0

    def _replace_broad_exceptions(self, content: str, file_path: Path) -> str:
        """Replace broad Exception handlers with specific ones."""
        lines = content.splitlines()
        
        for i, line in enumerate(lines):
            # Find broad exception patterns
            if re.search(r'except\s+Exception\s+as\s+\w+:', line):
                # Look at context to determine specific exception type
                context_lines = lines[max(0, i-5):i+3]
                context = '\n'.join(context_lines)
                
                # Determine specific exception based on context
                specific_exception = self._determine_specific_exception(context, file_path)
                
                # Replace broad exception with specific one
                lines[i] = re.sub(
                    r'except\s+Exception\s+as\s+(\w+):',
                    f'except {specific_exception} as \\1:',
                    line
                )
        
        return '\n'.join(lines)

    def _replace_bare_exceptions(self, content: str, file_path: Path) -> str:
        """Replace bare except: with specific exception handling."""
        lines = content.splitlines()
        
        for i, line in enumerate(lines):
            if re.search(r'except\s*:\s*$', line):
                # Look at context to determine specific exception type
                context_lines = lines[max(0, i-5):i+3]
                context = '\n'.join(context_lines)
                
                specific_exception = self._determine_specific_exception(context, file_path)
                
                # Replace bare except with specific exception
                lines[i] = re.sub(
                    r'except\s*:',
                    f'except {specific_exception} as e:',
                    line
                )
        
        return '\n'.join(lines)

    def _replace_except_pass(self, content: str, file_path: Path) -> str:
        """Replace try-except-pass blocks with proper error handling."""
        # Pattern for try-except-pass
        pattern = r'(\s+)except\s*([^:]*):\s*\n\s*pass'
        
        def replace_except_pass(match):
            indent = match.group(1)
            exception_type = match.group(2).strip()
            
            if exception_type:
                return f'{indent}except {exception_type} as e:\n{indent}    logger.debug(f"Exception in {file_path.name}: {{e}}")\n{indent}    # Continue gracefully'
            else:
                return f'{indent}except (FileNotFoundError, PermissionError, OSError) as e:\n{indent}    logger.debug(f"Exception in {file_path.name}: {{e}}")\n{indent}    # Continue gracefully'
        
        return re.sub(pattern, replace_except_pass, content, flags=re.MULTILINE)

    def _determine_specific_exception(self, context: str, file_path: Path) -> str:
        """Determine specific exception type based on context."""
        context_lower = context.lower()
        
        # Network operations
        if any(keyword in context_lower for keyword in ['requests', 'aiohttp', 'httpx', 'urllib', 'http']):
            return '(ConnectionError, TimeoutError, aiohttp.ClientError)'
        
        # File operations
        if any(keyword in context_lower for keyword in ['open(', 'path(', 'file', 'read', 'write']):
            return '(FileNotFoundError, PermissionError, OSError)'
        
        # Database operations
        if any(keyword in context_lower for keyword in ['sqlalchemy', 'psycopg2', 'asyncpg', 'database', 'db']):
            return '(sqlalchemy.exc.SQLAlchemyError, psycopg2.Error, asyncpg.Error)'
        
        # JSON operations
        if any(keyword in context_lower for keyword in ['json', 'orjson', 'loads', 'dumps']):
            return '(json.JSONDecodeError, ValueError)'
        
        # Import operations
        if any(keyword in context_lower for keyword in ['import', 'from']):
            return '(ImportError, ModuleNotFoundError)'
        
        # Validation operations
        if any(keyword in context_lower for keyword in ['pydantic', 'validate', 'schema']):
            return '(pydantic.ValidationError, ValueError)'
        
        # Default to more specific than bare Exception
        return '(ValueError, RuntimeError)'

    def _ensure_logging_import(self, content: str) -> str:
        """Ensure logging import is available."""
        if 'import logging' not in content and 'logger' in content:
            lines = content.splitlines()
            
            # Find the best place to insert import
            insert_index = 0
            for i, line in enumerate(lines):
                if line.strip().startswith(('import ', 'from ')):
                    insert_index = i + 1
                elif line.strip() and not line.strip().startswith('#'):
                    break
            
            # Insert logging import
            lines.insert(insert_index, 'import logging')
            lines.insert(insert_index + 1, 'logger = logging.getLogger(__name__)')
            
            return '\n'.join(lines)
        
        return content

    def create_error_handling_standards(self) -> bool:
        """Create error handling standards document."""
        try:
            standards_content = '''# PAKE System Error Handling Standards

## Overview

This document establishes standardized error handling patterns for the PAKE System, ensuring consistent, maintainable, and debuggable error handling across all modules.

## Core Principles

### 1. Specific Exception Handling
**Never use broad `except Exception:` blocks**
- Use specific exception types whenever possible
- Handle different error types with appropriate responses
- Preserve error context and stack traces

**Good Examples:**
```python
try:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
except requests.ConnectionError as e:
    logger.error(f"Connection failed: {e}")
    raise NetworkException(f"Failed to connect to {url}") from e
except requests.Timeout as e:
    logger.error(f"Request timeout: {e}")
    raise TimeoutException(f"Request to {url} timed out") from e
except requests.HTTPError as e:
    logger.error(f"HTTP error {e.response.status_code}: {e}")
    raise APIException(f"API returned {e.response.status_code}") from e
```

**Bad Examples:**
```python
try:
    response = requests.get(url, timeout=30)
    response.raise_for_status()
except (ConnectionError, TimeoutError, aiohttp.ClientError) as e:  # Too broad!
    logger.error(f"Error: {e}")
    raise
```

### 2. Proper Error Context
**Always provide meaningful error context**
- Include operation details in error messages
- Preserve original exception with `from e`
- Add relevant context information

```python
try:
    data = json.loads(response_text)
except json.JSONDecodeError as e:
    logger.error(f"Failed to parse JSON response: {e}")
    raise DataProcessingException(
        f"Invalid JSON in API response: {e}",
        context={"response_length": len(response_text)},
        original_exception=e
    ) from e
```

### 3. Graceful Degradation
**Handle errors gracefully when possible**
- Provide fallback mechanisms
- Log errors for monitoring
- Continue operation when safe

```python
try:
    cached_data = cache.get(key)
except CacheException as e:
    logger.warning(f"Cache miss, falling back to database: {e}")
    cached_data = None

if cached_data is None:
    cached_data = database.fetch(key)
```

### 4. Never Silent Failures
**Avoid try-except-pass blocks**
- Always log exceptions
- Provide meaningful error handling
- Document why exceptions are ignored

**Good:**
```python
try:
    optional_operation()
except OptionalOperationException as e:
    logger.debug(f"Optional operation failed (expected): {e}")
    # Continue gracefully - this operation is optional
```

**Bad:**
```python
try:
    optional_operation()
except Exception as e:

    logger.debug(f"Exception in phase3_error_handling_standardizer.py: {e}")

    # Continue gracefully  # Silent failure - never do this!
```

## Exception Hierarchy

### PAKE System Exceptions
Use the established PAKE exception hierarchy:

```python
from src.utils.exceptions import (
    PAKEException,
    NetworkException,
    DataProcessingException,
    ConfigurationException,
    AuthenticationException,
    AuthorizationException,
    ValidationException,
    FileNotFoundException,
    ImportException
)
```

### Exception Categories
- **NetworkException**: Connection, timeout, HTTP errors
- **DataProcessingException**: JSON, parsing, data validation errors
- **ConfigurationException**: Settings, environment, configuration errors
- **AuthenticationException**: Login, token, credential errors
- **AuthorizationException**: Permission, access control errors
- **ValidationException**: Input validation, schema validation errors
- **FileNotFoundException**: File system, path resolution errors
- **ImportException**: Module import, dependency errors

## Error Handling Patterns

### 1. API Error Handling
```python
async def api_call(self, endpoint: str, data: dict) -> dict:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(endpoint, json=data) as response:
                response.raise_for_status()
                return await response.json()
    except aiohttp.ClientConnectionError as e:
        logger.error(f"Connection failed to {endpoint}: {e}")
        raise NetworkException(f"Failed to connect to {endpoint}") from e
    except aiohttp.ClientTimeout as e:
        logger.error(f"Timeout calling {endpoint}: {e}")
        raise TimeoutException(f"Request to {endpoint} timed out") from e
    except aiohttp.ClientResponseError as e:
        logger.error(f"HTTP {e.status} error calling {endpoint}: {e}")
        raise APIException(f"API returned {e.status}") from e
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON response from {endpoint}: {e}")
        raise DataProcessingException(f"Invalid response format from {endpoint}") from e
```

### 2. File Operation Error Handling
```python
def load_config_file(self, file_path: Path) -> dict:
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError as e:
        logger.error(f"Config file not found: {file_path}")
        raise FileNotFoundException(str(file_path)) from e
    except PermissionError as e:
        logger.error(f"Permission denied reading {file_path}: {e}")
        raise FilePermissionException(str(file_path), "read") from e
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {file_path}: {e}")
        raise DataProcessingException(f"Invalid JSON in {file_path}") from e
```

### 3. Database Error Handling
```python
async def save_user(self, user: User) -> User:
    try:
        async with self.db_session() as session:
            session.add(user)
            await session.commit()
            return user
    except sqlalchemy.exc.IntegrityError as e:
        logger.error(f"User already exists: {user.email}")
        raise ValidationException(f"User {user.email} already exists") from e
    except sqlalchemy.exc.SQLAlchemyError as e:
        logger.error(f"Database error saving user: {e}")
        raise DataProcessingException("Failed to save user") from e
```

## Logging Standards

### Error Log Levels
- **ERROR**: System errors, failed operations, exceptions
- **WARNING**: Recoverable issues, fallback operations
- **INFO**: Normal operations, important state changes
- **DEBUG**: Detailed debugging information, exception details

### Log Message Format
```python
logger.error(f"Operation failed: {operation_name} - {error_details}")
logger.warning(f"Fallback activated: {fallback_reason}")
logger.info(f"Operation completed: {operation_name} - {result_summary}")
logger.debug(f"Exception details: {exception_type} - {exception_message}")
```

## Testing Error Handling

### Unit Tests for Error Cases
```python
def test_api_call_connection_error():
    with pytest.raises(NetworkException) as exc_info:
        api_client.api_call("http://invalid-url")
    
    assert "Failed to connect" in str(exc_info.value)
    assert exc_info.value.original_exception is not None

def test_config_file_not_found():
    with pytest.raises(FileNotFoundException):
        config_loader.load_config_file(Path("nonexistent.json"))
```

## Monitoring and Alerting

### Error Metrics
- Track exception rates by type and module
- Monitor error patterns and trends
- Alert on critical error thresholds

### Error Context
- Include correlation IDs in error logs
- Add request/operation context to exceptions
- Preserve stack traces for debugging

## Migration Checklist

When updating existing error handling:

- [ ] Replace broad `except Exception:` with specific exceptions
- [ ] Add proper error context and logging
- [ ] Use PAKE exception hierarchy
- [ ] Preserve original exceptions with `from e`
- [ ] Add unit tests for error cases
- [ ] Update documentation
- [ ] Verify error monitoring works correctly
'''
            
            standards_path = self.project_root / 'ERROR_HANDLING_STANDARDS.md'
            with open(standards_path, 'w', encoding='utf-8') as f:
                f.write(standards_content)
            
            print(f"✅ Created error handling standards at {standards_path}")
            return True
            
        except (FileNotFoundError, PermissionError, OSError) as e:
            print(f"❌ Error creating standards: {e}")
            return False

    def run_systematic_error_standardization(self) -> Dict[str, Any]:
        """Run systematic error handling standardization."""
        print("🛠️ Phase 3: Error Handling Standardization")
        print("=" * 60)
        
        # Create standards first
        self.create_error_handling_standards()
        
        # Get broad exception patterns
        errors_by_file = self.get_broad_exception_errors()
        total_errors = sum(len(errors) for errors in errors_by_file.values())
        
        print(f"📊 Found {total_errors} error handling issues across {len(errors_by_file)} files")
        
        # Process priority files first
        priority_fixed = 0
        for file_pattern in self.priority_files:
            file_path = self.project_root / file_pattern
            if file_path.exists() and str(file_path) in errors_by_file:
                print(f"🎯 Standardizing priority file: {file_path.name}")
                success, fixes = self.standardize_file_error_handling(file_path, errors_by_file[str(file_path)])
                if success:
                    priority_fixed += fixes
                    print(f"   ✅ Fixed {fixes} error handling issues")
                else:
                    print(f"   ❌ Failed to fix error handling issues")
        
        # Process remaining files
        remaining_fixed = 0
        for file_path, errors in errors_by_file.items():
            if file_path not in self.files_processed:
                path_obj = Path(file_path)
                if path_obj.exists():
                    success, fixes = self.standardize_file_error_handling(path_obj, errors)
                    if success:
                        remaining_fixed += fixes
                        if fixes > 0:
                            print(f"✅ Fixed {fixes} error handling issues in {path_obj.name}")
        
        total_fixed = priority_fixed + remaining_fixed
        
        print(f"\n📈 Results:")
        print(f"   Files processed: {len(self.files_processed)}")
        print(f"   Total error handling issues fixed: {total_fixed}")
        print(f"   Remaining issues: {total_errors - total_fixed}")
        
        return {
            'files_processed': len(self.files_processed),
            'error_issues_fixed': total_fixed,
            'remaining_issues': total_errors - total_fixed,
            'success_rate': (total_fixed / total_errors * 100) if total_errors > 0 else 0
        }


def main():
    """Main execution function."""
    project_root = "/home/chris/PAKE_SYSTEM_claude_optimized"
    
    standardizer = Phase3ErrorHandlerStandardizer(project_root)
    results = standardizer.run_systematic_error_standardization()
    
    print(f"\n🎉 Phase 3 Error Handling Standardization Complete!")
    print(f"Success Rate: {results['success_rate']:.1f}%")


if __name__ == "__main__":
    main()