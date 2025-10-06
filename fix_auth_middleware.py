#!/usr/bin/env python3
"""Fix F821 errors in pake_system/auth/middleware.py"""

import re

def fix_auth_middleware():
    """Fix F821 errors in pake_system/auth/middleware.py"""
    
    file_path = "/home/chris/PAKE_SYSTEM_claude_optimized/src/pake_system/auth/middleware.py"
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix function signatures based on the F821 errors found
    fixes = [
        # RateLimitMiddleware __init__ method
        (
            r'def __init__\(self\) -> None:\n        super\(\)\.__init__\(app\)\n        self\.requests_per_minute = requests_per_minute\n        self\.burst_limit = burst_limit',
            'def __init__(self, app, requests_per_minute: int = 60, burst_limit: int = 10) -> None:\n        super().__init__(app)\n        self.requests_per_minute = requests_per_minute\n        self.burst_limit = burst_limit'
        ),
        
        # RateLimitMiddleware dispatch method
        (
            r'async def dispatch\(self\) -> None:\n        client_ip = self\._get_client_ip\(request\)',
            'async def dispatch(self, request: Request, call_next) -> None:\n        client_ip = self._get_client_ip(request)'
        ),
        
        # SecurityHeadersMiddleware __init__ method
        (
            r'class SecurityHeadersMiddleware\(BaseHTTPMiddleware\):\n    """Security headers middleware for enhanced protection."""\n\n    def __init__\(self\) -> None:\n        super\(\)\.__init__\(app\)',
            'class SecurityHeadersMiddleware(BaseHTTPMiddleware):\n    """Security headers middleware for enhanced protection."""\n\n    def __init__(self, app) -> None:\n        super().__init__(app)'
        ),
        
        # SecurityHeadersMiddleware dispatch method
        (
            r'async def dispatch\(self\) -> None:\n        response = await call_next\(request\)',
            'async def dispatch(self, request: Request, call_next) -> None:\n        response = await call_next(request)'
        ),
        
        # RequestValidationMiddleware __init__ method
        (
            r'class RequestValidationMiddleware\(BaseHTTPMiddleware\):\n    """Request validation middleware for security."""\n\n    def __init__\(self\) -> None:\n        super\(\)\.__init__\(app\)',
            'class RequestValidationMiddleware(BaseHTTPMiddleware):\n    """Request validation middleware for security."""\n\n    def __init__(self, app) -> None:\n        super().__init__(app)'
        ),
        
        # RequestValidationMiddleware dispatch method
        (
            r'async def dispatch\(self\) -> None:\n        # Validate request size',
            'async def dispatch(self, request: Request, call_next) -> None:\n        # Validate request size'
        ),
    ]
    
    # Apply fixes
    for pattern, replacement in fixes:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    
    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Fixed pake_system/auth/middleware.py")

if __name__ == "__main__":
    fix_auth_middleware()
