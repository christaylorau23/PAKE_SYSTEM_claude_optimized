# Type Annotation Fix Guide for PAKE System

## Overview
This guide addresses the most common type annotation issues found in the PAKE system, following the principles outlined in your comprehensive analysis.

## Common Type Issues and Solutions

### 1. "None" cannot be assigned to parameter of type "str"

**Problem**: Function expects a string but receives None
```python
# ❌ Problematic code
def process_name(name: str) -> str:
    return name.upper()

# This will cause: "None" cannot be assigned to parameter of type "str"
result = process_name(None)  # Error!
```

**Solution**: Use Optional types and type narrowing
```python
# ✅ Fixed code
from typing import Optional

def process_name(name: Optional[str]) -> Optional[str]:
    if name is not None:
        return name.upper()
    return None

# Or with modern Python 3.10+ syntax
def process_name(name: str | None) -> str | None:
    if name is not None:
        return name.upper()
    return None
```

### 2. "None" cannot be assigned to parameter of type "Dict[str, Any]"

**Problem**: Function expects a dictionary but receives None
```python
# ❌ Problematic code
def process_data(data: Dict[str, Any]) -> Dict[str, Any]:
    return {"processed": True, **data}

# This will cause: "None" cannot be assigned to parameter of type "Dict[str, Any]"
result = process_data(None)  # Error!
```

**Solution**: Handle optional dictionaries properly
```python
# ✅ Fixed code
from typing import Optional, Dict, Any

def process_data(data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if data is None:
        return {"processed": True, "empty": True}
    return {"processed": True, **data}

# Or with modern syntax
def process_data(data: Dict[str, Any] | None) -> Dict[str, Any]:
    if data is None:
        return {"processed": True, "empty": True}
    return {"processed": True, **data}
```

### 3. Missing Type Annotations for Function Parameters

**Problem**: Functions without type hints
```python
# ❌ Problematic code
def calculate_score(items, threshold):
    return sum(item.value for item in items if item.value > threshold)
```

**Solution**: Add comprehensive type annotations
```python
# ✅ Fixed code
from typing import List, Protocol

class ScorableItem(Protocol):
    value: float

def calculate_score(items: List[ScorableItem], threshold: float) -> float:
    return sum(item.value for item in items if item.value > threshold)
```

### 4. Environment Variable Handling

**Problem**: Environment variables can be None
```python
# ❌ Problematic code
import os

def get_api_key() -> str:
    return os.getenv("API_KEY")  # Returns Optional[str], not str
```

**Solution**: Handle None cases explicitly
```python
# ✅ Fixed code
import os
from typing import Optional

def get_api_key() -> Optional[str]:
    return os.getenv("API_KEY")

def get_api_key_required() -> str:
    api_key = os.getenv("API_KEY")
    if api_key is None:
        raise ValueError("API_KEY environment variable is required")
    return api_key
```

### 5. Database Query Results

**Problem**: Database queries can return None
```python
# ❌ Problematic code
def get_user_by_id(user_id: int) -> User:
    result = db.query(User).filter(User.id == user_id).first()
    return result  # result can be None
```

**Solution**: Handle None results properly
```python
# ✅ Fixed code
from typing import Optional

def get_user_by_id(user_id: int) -> Optional[User]:
    result = db.query(User).filter(User.id == user_id).first()
    return result

def get_user_by_id_required(user_id: int) -> User:
    result = db.query(User).filter(User.id == user_id).first()
    if result is None:
        raise ValueError(f"User with id {user_id} not found")
    return result
```

### 6. Async Function Type Annotations

**Problem**: Missing return type annotations for async functions
```python
# ❌ Problematic code
async def fetch_data(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()
```

**Solution**: Add proper async type annotations
```python
# ✅ Fixed code
from typing import Dict, Any, Optional
import aiohttp

async def fetch_data(url: str) -> Optional[Dict[str, Any]]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                return None
    except Exception:
        return None
```

## Type Narrowing Patterns

### Pattern 1: Conditional Check
```python
def process_optional_data(data: str | None) -> str:
    if data is not None:
        # Type checker knows data is str here
        return data.upper()
    return "default"
```

### Pattern 2: Assert Statement
```python
def process_required_data(data: str | None) -> str:
    assert data is not None, "Data cannot be None"
    # Type checker knows data is str here
    return data.upper()
```

### Pattern 3: Early Return
```python
def process_data(data: str | None) -> str:
    if data is None:
        return "default"
    # Type checker knows data is str here
    return data.upper()
```

## Configuration for Type Checking

### VS Code Settings (.vscode/settings.json)
```json
{
    "python.analysis.typeCheckingMode": "standard",
    "python.analysis.diagnosticSeverityOverrides": {
        "reportMissingImports": "warning",
        "reportOptionalMemberAccess": "warning",
        "reportArgumentType": "error",
        "reportGeneralTypeIssues": "error"
    }
}
```

### Flake8 Configuration (.flake8)
```ini
[flake8]
max-line-length = 88
extend-ignore = E203,W503,E501,F401,F841,E402
exclude = .git,__pycache__,.venv,.pytest_cache,node_modules
```

## Best Practices

1. **Always use type hints** for function parameters and return values
2. **Handle None cases explicitly** - don't ignore them
3. **Use Optional[T] or T | None** for values that can be None
4. **Use type narrowing** to safely handle optional values
5. **Prefer modern union syntax** (T | None) over Optional[T] for Python 3.10+
6. **Use Protocol** for structural typing when appropriate
7. **Add type annotations incrementally** - don't try to fix everything at once

## Common Import Patterns

```python
# Modern Python 3.10+ imports
from typing import Protocol, TypeVar, Generic

# For older Python versions
from typing import Optional, Union, Dict, List, Any, Callable

# Common patterns
T = TypeVar('T')
OptionalStr = str | None  # Python 3.10+
OptionalStr = Optional[str]  # Older Python
```

This guide should help resolve the majority of type annotation issues in your PAKE system.

