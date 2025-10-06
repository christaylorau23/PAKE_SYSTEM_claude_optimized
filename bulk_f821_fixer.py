#!/usr/bin/env python3
"""Bulk F821 Fixer - Phase 2: Comprehensive Parameter Fixes

This script systematically fixes the remaining F821 errors by:
1. Identifying the most common error patterns across all files
2. Applying bulk fixes for common patterns
3. Targeting high-impact files for manual fixes
"""

import ast
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple


class BulkF821Fixer:
    """Bulk F821 fixer for comprehensive error resolution."""
    
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.fixed_files = 0
        self.total_fixes = 0
        
        # Common parameter patterns and their likely types
        self.parameter_patterns = {
            'config': 'dict[str, Any] | None = None',
            'request': 'Request | None = None', 
            'call_next': 'Callable | None = None',
            'dal': 'Any = Depends(get_dal)',
            'security_enforcer': 'Any = Depends(get_security_enforcer)',
            'tenant_service': 'Any = Depends(get_tenant_service)',
            'tenant_id': 'str | None = None',
            'user_id': 'str | None = None',
            'message': 'str | None = None',
            'kwargs': 'dict[str, Any] | None = None',
            'model_id': 'str | None = None',
            'name': 'str | None = None',
            'args': 'tuple | None = None',
            'stream': 'Any | None = None',
            'value': 'Any | None = None',
            'func': 'Callable | None = None',
            'event': 'Any | None = None',
            'job': 'Any | None = None',
            'content_item': 'Any | None = None',
            'test_id': 'str | None = None',
            'error': 'Exception | None = None',
            'record': 'Any | None = None',
            'result': 'Any | None = None',
            'platform': 'str | None = None',
            'task': 'Any | None = None',
            'interactions': 'List[Any] | None = None',
            'content_id': 'str | None = None',
            'features': 'Dict[str, Any] | None = None',
            'client_ip': 'str | None = None',
            'current_time': 'float | None = None',
            'response': 'Response | None = None',
            'app': 'Any | None = None',
        }
    
    def get_files_with_most_errors(self, limit: int = 20) -> List[Tuple[str, int]]:
        """Get files with the most F821 errors."""
        try:
            result = subprocess.run([
                'ruff', 'check', str(self.root_dir / 'src'), 
                '--select', 'F821', '--output-format', 'json'
            ], capture_output=True, text=True, cwd=self.root_dir)
            
            if result.returncode != 0:
                return []
            
            # Parse JSON output to count errors per file
            import json
            errors = json.loads(result.stdout)
            
            file_counts = {}
            for error in errors:
                filename = error.get('filename', '')
                if filename:
                    file_counts[filename] = file_counts.get(filename, 0) + 1
            
            # Sort by error count and return top files
            sorted_files = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)
            return sorted_files[:limit]
            
        except (FileNotFoundError, PermissionError, OSError) as e:
            print(f"Error getting file counts: {e}")
            return []
    
    def get_most_common_errors(self) -> Dict[str, int]:
        """Get the most common F821 error patterns."""
        try:
            result = subprocess.run([
                'ruff', 'check', str(self.root_dir / 'src'), 
                '--select', 'F821', '--output-format', 'json'
            ], capture_output=True, text=True, cwd=self.root_dir)
            
            if result.returncode != 0:
                return {}
            
            import json
            errors = json.loads(result.stdout)
            
            error_counts = {}
            for error in errors:
                message = error.get('message', '')
                if 'Undefined name `' in message:
                    # Extract the undefined name
                    name_match = re.search(r'Undefined name `([^`]+)`', message)
                    if name_match:
                        name = name_match.group(1)
                        error_counts[name] = error_counts.get(name, 0) + 1
            
            return error_counts
            
        except (ValueError, RuntimeError) as e:
            print(f"Error getting error counts: {e}")
            return {}
    
    def fix_common_patterns_bulk(self):
        """Fix common patterns across all files."""
        print("🔍 Analyzing most common F821 error patterns...")
        error_counts = self.get_most_common_errors()
        
        if not error_counts:
            print("No F821 errors found")
            return
        
        print("Top 10 most common F821 errors:")
        sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
        for name, count in sorted_errors[:10]:
            print(f"  {name}: {count} errors")
        
        print("\n🔧 Applying bulk fixes for common patterns...")
        
        # Get all Python files
        python_files = list(self.root_dir.glob('src/**/*.py'))
        print(f"Found {len(python_files)} Python files")
        
        # Apply bulk fixes
        for file_path in python_files:
            if self.fix_file_common_patterns(file_path):
                self.fixed_files += 1
        
        print(f"\n✅ Applied bulk fixes to {self.fixed_files} files")
    
    def fix_file_common_patterns(self, file_path: Path) -> bool:
        """Fix common patterns in a single file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (FileNotFoundError, PermissionError, OSError) as e:
            return False
        
        original_content = content
        fixes_applied = 0
        
        # Fix common patterns
        patterns_to_fix = [
            # Add missing typing imports
            (r'from typing import ([^\\n]+)', self._add_typing_imports),
            # Fix FastAPI imports
            (r'from fastapi import ([^\\n]+)', self._add_fastapi_imports),
            # Fix common function parameter patterns
            (r'def __init__\(self\) -> None:', self._fix_init_methods),
            (r'async def dispatch\(self\) -> None:', self._fix_dispatch_methods),
            (r'async def ([^(]+)\(self\) -> None:', self._fix_async_methods),
        ]
        
        for pattern, fix_func in patterns_to_fix:
            new_content, fixes = fix_func(content)
            if fixes > 0:
                content = new_content
                fixes_applied += fixes
        
        # Write back if changes were made
        if fixes_applied > 0:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"Fixed {fixes_applied} issues in {file_path.name}")
                return True
            except (FileNotFoundError, PermissionError, OSError) as e:
                print(f"Error writing {file_path}: {e}")
                return False
        
        return False
    
    def _add_typing_imports(self, content: str) -> Tuple[str, int]:
        """Add missing typing imports."""
        fixes = 0
        
        # Check what's already imported
        typing_match = re.search(r'from typing import ([^\\n]+)', content)
        if typing_match:
            current_imports = typing_match.group(1)
            imports_to_add = []
            
            # Check for missing common imports
            common_imports = ['Dict', 'List', 'Any', 'Callable', 'Optional', 'Union']
            for imp in common_imports:
                if imp not in current_imports and imp in content:
                    imports_to_add.append(imp)
            
            if imports_to_add:
                new_imports = current_imports + ', ' + ', '.join(imports_to_add)
                content = content.replace(
                    f'from typing import {current_imports}',
                    f'from typing import {new_imports}'
                )
                fixes += len(imports_to_add)
        
        return content, fixes
    
    def _add_fastapi_imports(self, content: str) -> Tuple[str, int]:
        """Add missing FastAPI imports."""
        fixes = 0
        
        # Check what's already imported
        fastapi_match = re.search(r'from fastapi import ([^\\n]+)', content)
        if fastapi_match:
            current_imports = fastapi_match.group(1)
            imports_to_add = []
            
            # Check for missing common imports
            common_imports = ['Request', 'Response', 'BackgroundTasks']
            for imp in common_imports:
                if imp not in current_imports and imp in content:
                    imports_to_add.append(imp)
            
            if imports_to_add:
                new_imports = current_imports + ', ' + ', '.join(imports_to_add)
                content = content.replace(
                    f'from fastapi import {current_imports}',
                    f'from fastapi import {new_imports}'
                )
                fixes += len(imports_to_add)
        
        return content, fixes
    
    def _fix_init_methods(self, content: str) -> Tuple[str, int]:
        """Fix __init__ methods missing parameters."""
        fixes = 0
        
        # Pattern for __init__ methods that use undefined variables
        pattern = r'def __init__\(self\) -> None:\n(\s+)self\.(\w+) = (\w+)'
        matches = re.finditer(pattern, content, re.MULTILINE)
        
        for match in matches:
            indent = match.group(1)
            attr_name = match.group(2)
            var_name = match.group(3)
            
            if var_name in self.parameter_patterns:
                param_type = self.parameter_patterns[var_name]
                new_signature = f'def __init__(self, {var_name}: {param_type}) -> None:'
                content = content.replace(match.group(0), new_signature + '\n' + indent + f'self.{attr_name} = {var_name}')
                fixes += 1
        
        return content, fixes
    
    def _fix_dispatch_methods(self, content: str) -> Tuple[str, int]:
        """Fix dispatch methods missing parameters."""
        fixes = 0
        
        # Pattern for dispatch methods
        pattern = r'async def dispatch\(self\) -> None:'
        if re.search(pattern, content):
            new_signature = 'async def dispatch(self, request: Request, call_next) -> None:'
            content = re.sub(pattern, new_signature, content)
            fixes += 1
        
        return content, fixes
    
    def _fix_async_methods(self, content: str) -> Tuple[str, int]:
        """Fix async methods missing parameters."""
        fixes = 0
        
        # This is a placeholder for more complex async method fixes
        # Could be expanded based on specific patterns found
        
        return content, fixes
    
    def run_comprehensive_fixes(self):
        """Run comprehensive F821 fixes."""
        print("🚀 Starting Comprehensive F821 Error Resolution")
        print("=" * 50)
        
        # Step 1: Bulk pattern fixes
        self.fix_common_patterns_bulk()
        
        # Step 2: Target high-impact files
        print("\n🎯 Targeting high-impact files...")
        top_files = self.get_files_with_most_errors(10)
        
        if top_files:
            print(f"Found {len(top_files)} files with most errors:")
            for filename, count in top_files:
                print(f"  {Path(filename).name}: {count} errors")
        
        print(f"\n✅ Comprehensive fixes completed!")
        print(f"Total files processed: {self.fixed_files}")
        print(f"Total fixes applied: {self.total_fixes}")


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        root_dir = sys.argv[1]
    else:
        root_dir = "."
    
    fixer = BulkF821Fixer(root_dir)
    fixer.run_comprehensive_fixes()


if __name__ == "__main__":
    main()