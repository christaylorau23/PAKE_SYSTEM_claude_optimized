#!/usr/bin/env python3
"""
Systematic F821 Resolution Tool
Following The Vanguard Protocol - Phase 2: The Great Import Sweep
"""

from collections import Counter, defaultdict
import os
from pathlib import Path
import re
import subprocess
from typing import Dict, List, Set, Tuple


class SystematicF821Resolver:
    """Systematic resolver for F821 undefined-name errors"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.fixes_applied = Counter()
        self.files_processed = set()
        
        # Common import patterns
        self.import_patterns = {
            'logger': 'import logging\nlogger = logging.getLogger(__name__)',
            'logging': 'import logging',
            'json': 'import json',
            'os': 'import os',
            'sys': 'import sys',
            'pathlib': 'from pathlib import Path',
            'Path': 'from pathlib import Path',
            'datetime': 'from datetime import datetime',
            'time': 'import time',
            're': 'import re',
            'uuid': 'import uuid',
            'hashlib': 'import hashlib',
            'base64': 'import base64',
            'requests': 'import requests',
            'httpx': 'import httpx',
            'asyncio': 'import asyncio',
            'typing': 'from typing import Dict, List, Optional, Any, Union',
            'Dict': 'from typing import Dict',
            'List': 'from typing import List',
            'Optional': 'from typing import Optional',
            'Any': 'from typing import Any',
            'Union': 'from typing import Union',
            'Tuple': 'from typing import Tuple',
            'Set': 'from typing import Set',
            'Callable': 'from typing import Callable',
            'Type': 'from typing import Type',
            'TypeVar': 'from typing import TypeVar',
            'Generic': 'from typing import Generic',
            'Protocol': 'from typing import Protocol',
            'dataclass': 'from dataclasses import dataclass',
            'field': 'from dataclasses import field',
            'Enum': 'from enum import Enum',
            'ABC': 'from abc import ABC',
            'abstractmethod': 'from abc import abstractmethod',
            'pydantic': 'from pydantic import BaseModel',
            'BaseModel': 'from pydantic import BaseModel',
            'Field': 'from pydantic import Field',
            'validator': 'from pydantic import validator',
            'FastAPI': 'from fastapi import FastAPI',
            'APIRouter': 'from fastapi import APIRouter',
            'HTTPException': 'from fastapi import HTTPException',
            'Depends': 'from fastapi import Depends',
            'Request': 'from fastapi import Request',
            'Response': 'from fastapi import Response',
            'JSONResponse': 'from fastapi.responses import JSONResponse',
            'Query': 'from fastapi import Query',
            'pytest': 'import pytest',
            'unittest': 'import unittest',
            'mock': 'from unittest.mock import Mock, patch',
            'Mock': 'from unittest.mock import Mock',
            'patch': 'from unittest.mock import patch',
        }
    
    def get_f821_errors_for_file(self, file_path: str) -> List[Dict]:
        """Get F821 errors for a specific file"""
        try:
            result = subprocess.run(
                ['ruff', 'check', file_path, '--select=F821', '--output-format=json'],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return []
            
            # Parse JSON output
            import json
            errors = json.loads(result.stdout)
            
            file_errors = []
            for error in errors:
                if isinstance(error, dict) and error.get('code') == 'F821':
                    file_errors.append({
                        'line': error.get('location', {}).get('row', 0),
                        'col': error.get('location', {}).get('column', 0),
                        'message': error.get('message', ''),
                        'undefined_name': self._extract_undefined_name(error.get('message', ''))
                    })
            
            return file_errors
            
        except (FileNotFoundError, PermissionError, OSError) as e:
            print(f"❌ Error checking {file_path}: {e}")
            return []
    
    def _extract_undefined_name(self, message: str) -> str:
        """Extract the undefined name from the error message"""
        match = re.search(r"Undefined name `([^`]+)`", message)
        return match.group(1) if match else ""
    
    def fix_file(self, file_path: str) -> bool:
        """Fix F821 errors in a specific file"""
        file_path = Path(file_path)
        if not file_path.exists():
            return False
        
        print(f"🔧 Processing {file_path}")
        
        # Get F821 errors for this file
        errors = self.get_f821_errors_for_file(str(file_path))
        if not errors:
            return True
        
        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.splitlines()
        except (FileNotFoundError, PermissionError, OSError) as e:
            print(f"❌ Error reading {file_path}: {e}")
            return False
        
        # Track what we need to fix
        needed_imports = set()
        parameter_fixes = []
        
        # Analyze each error
        for error in errors:
            undefined_name = error['undefined_name']
            line_num = error['line'] - 1  # Convert to 0-based index
            
            if line_num >= len(lines):
                continue
            
            # Check if this is a common import we can fix
            if undefined_name in self.import_patterns:
                needed_imports.add(undefined_name)
                self.fixes_applied['import_fix'] += 1
            else:
                # Check if it's a parameter name issue
                if self._is_parameter_issue(lines, line_num, undefined_name):
                    parameter_fixes.append((line_num, undefined_name))
                    self.fixes_applied['parameter_fix'] += 1
                else:
                    self.fixes_applied['unresolved'] += 1
        
        # Apply fixes
        modified = False
        
        # Add imports if needed
        if needed_imports:
            content = self._add_imports(content, needed_imports)
            modified = True
        
        # Fix parameter issues
        if parameter_fixes:
            content = self._fix_parameter_issues(content, parameter_fixes)
            modified = True
        
        # Write back if modified
        if modified:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"✅ Fixed {len(needed_imports)} imports and {len(parameter_fixes)} parameters in {file_path}")
                self.files_processed.add(str(file_path))
                return True
            except (FileNotFoundError, PermissionError, OSError) as e:
                print(f"❌ Error writing {file_path}: {e}")
                return False
        
        return True
    
    def _is_parameter_issue(self, lines: List[str], line_num: int, name: str) -> bool:
        """Check if undefined name is likely a missing function parameter"""
        # Look for function definition above this line
        for i in range(max(0, line_num - 20), line_num):
            line = lines[i].strip()
            if 'def ' in line and '(' in line and ')' in line:
                # Check if the parameter is missing
                func_line = line
                if name in lines[line_num] and name not in func_line:
                    return True
        return False
    
    def _add_imports(self, content: str, needed_imports: Set[str]) -> str:
        """Add necessary imports to the top of the file"""
        lines = content.splitlines()
        
        # Find the best place to insert imports
        import_section_end = 0
        in_docstring = False
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Skip shebang
            if stripped.startswith('#!'):
                continue
            
            # Skip module docstring
            if stripped.startswith('"""') or stripped.startswith("'''"):
                if not in_docstring:
                    in_docstring = True
                else:
                    in_docstring = False
                continue
            
            if in_docstring:
                continue
            
            # Found first import or non-comment line
            if stripped.startswith('import ') or stripped.startswith('from '):
                import_section_end = i + 1
            elif stripped and not stripped.startswith('#'):
                break
        
        # Generate import statements
        import_statements = []
        for name in sorted(needed_imports):
            if name in self.import_patterns:
                import_statements.append(self.import_patterns[name])
        
        # Remove duplicates while preserving order
        unique_imports = []
        seen = set()
        for imp in import_statements:
            if imp not in seen:
                unique_imports.append(imp)
                seen.add(imp)
        
        # Insert imports
        if unique_imports:
            # Insert after the import section
            for i, import_stmt in enumerate(unique_imports):
                lines.insert(import_section_end + i, import_stmt)
            
            # Add blank line after imports if needed
            if import_section_end + len(unique_imports) < len(lines):
                if lines[import_section_end + len(unique_imports)].strip():
                    lines.insert(import_section_end + len(unique_imports), '')
        
        return '\n'.join(lines)
    
    def _fix_parameter_issues(self, content: str, parameter_fixes: List[Tuple[int, str]]) -> str:
        """Fix parameter issues by adding missing parameters to function definitions"""
        lines = content.splitlines()
        
        for line_num, param_name in parameter_fixes:
            # Find the function definition above this line
            for i in range(max(0, line_num - 20), line_num):
                line = lines[i].strip()
                if 'def ' in line and '(' in line and ')' in line:
                    # Add parameter to function definition
                    func_line = lines[i]
                    if param_name not in func_line:
                        # Find the closing parenthesis
                        paren_pos = func_line.rfind(')')
                        if paren_pos != -1:
                            # Add parameter before closing parenthesis
                            if func_line[paren_pos-1].strip():
                                # There are already parameters
                                lines[i] = func_line[:paren_pos] + f', {param_name}' + func_line[paren_pos:]
                            else:
                                # No parameters yet
                                lines[i] = func_line[:paren_pos] + param_name + func_line[paren_pos:]
                    break
        
        return '\n'.join(lines)
    
    def process_high_priority_files(self) -> Dict[str, int]:
        """Process files with the most F821 errors first"""
        print("🎯 Processing high-priority files with F821 errors...")
        
        # Get list of Python files
        python_files = list(self.project_root.rglob("*.py"))
        
        # Check each file for F821 errors
        files_with_errors = []
        for py_file in python_files:
            errors = self.get_f821_errors_for_file(str(py_file))
            if errors:
                files_with_errors.append((str(py_file), len(errors)))
        
        # Sort by error count (highest first)
        files_with_errors.sort(key=lambda x: x[1], reverse=True)
        
        print(f"📁 Found {len(files_with_errors)} files with F821 errors")
        
        # Process top 20 files first
        for file_path, error_count in files_with_errors[:20]:
            print(f"🔧 Processing {file_path} ({error_count} errors)")
            self.fix_file(file_path)
        
        return dict(self.fixes_applied)
    
    def generate_report(self) -> str:
        """Generate resolution report"""
        report = []
        report.append("# F821 Resolution Report - The Great Import Sweep")
        report.append("")
        report.append(f"**Files Processed**: {len(self.files_processed)}")
        report.append("")
        
        report.append("## Fix Statistics")
        report.append("")
        for fix_type, count in self.fixes_applied.items():
            report.append(f"- **{fix_type.replace('_', ' ').title()}**: {count}")
        report.append("")
        
        report.append("## Files Processed")
        report.append("")
        for file_path in sorted(self.files_processed):
            report.append(f"- `{file_path}`")
        
        return "\n".join(report)

def main():
    """Main execution function"""
    project_root = "/home/chris/PAKE_SYSTEM_claude_optimized"
    
    resolver = SystematicF821Resolver(project_root)
    
    print("🚀 Starting systematic F821 resolution...")
    
    # Process high-priority files
    stats = resolver.process_high_priority_files()
    
    # Generate report
    report = resolver.generate_report()
    with open("F821_SYSTEMATIC_RESOLUTION_REPORT.md", "w") as f:
        f.write(report)
    
    print("✅ Systematic F821 Resolution Complete!")
    print(f"📄 Report written to: F821_SYSTEMATIC_RESOLUTION_REPORT.md")
    print(f"📊 Fix statistics: {stats}")

if __name__ == "__main__":
    main()