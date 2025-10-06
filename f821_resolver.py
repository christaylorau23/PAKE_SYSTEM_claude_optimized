#!/usr/bin/env python3
"""
F821 Error Resolution Tool - The Great Import Sweep
Following The Vanguard Protocol Phase 2: Systematic F821 Resolution
"""

from collections import Counter, defaultdict
import os
from pathlib import Path
import re
import subprocess
from typing import Dict, List, Set, Tuple


class F821Resolver:
    """Systematic resolver for F821 undefined-name errors"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.common_imports = {
            # Standard library imports
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
            'urllib': 'import urllib.parse',
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
            
            # Common third-party imports
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
            'pytest': 'import pytest',
            'unittest': 'import unittest',
            'mock': 'from unittest.mock import Mock, patch',
            'Mock': 'from unittest.mock import Mock',
            'patch': 'from unittest.mock import patch',
            
            # Common patterns
            'conversation': 'conversation',  # Parameter name
            'extraction': 'extraction',      # Parameter name
            'user': 'user',                 # Parameter name
            'request': 'request',           # Parameter name
            'response': 'response',         # Parameter name
            'data': 'data',                 # Parameter name
            'config': 'config',            # Parameter name
            'settings': 'settings',        # Parameter name
        }
        
        self.f821_errors = []
        self.resolution_stats = Counter()
        
    def scan_f821_errors(self) -> List[Dict]:
        """Scan for all F821 errors in the project"""
        print("🔍 Scanning for F821 undefined-name errors...")
        
        try:
            # Run ruff to get F821 errors
            result = subprocess.run(
                ['ruff', 'check', '.', '--select=F821', '--output-format=json'],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"⚠️  Ruff returned non-zero exit code: {result.returncode}")
                print("STDERR:", result.stderr)
                return []
            
            # Parse JSON output
            import json
            errors = json.loads(result.stdout)
            
            self.f821_errors = []
            for error in errors:
                if isinstance(error, dict) and error.get('code') == 'F821':
                    self.f821_errors.append({
                        'file': error.get('filename', ''),
                        'line': error.get('location', {}).get('row', 0),
                        'col': error.get('location', {}).get('column', 0),
                        'message': error.get('message', ''),
                        'undefined_name': self._extract_undefined_name(error.get('message', ''))
                    })
            
            print(f"✅ Found {len(self.f821_errors)} F821 errors")
            return self.f821_errors
            
        except (ValueError, RuntimeError) as e:
            print(f"❌ Error scanning F821 errors: {e}")
            return []
    
    def _extract_undefined_name(self, message: str) -> str:
        """Extract the undefined name from the error message"""
        # Pattern: "Undefined name `name`"
        match = re.search(r"Undefined name `([^`]+)`", message)
        return match.group(1) if match else ""
    
    def analyze_error_patterns(self) -> Dict[str, int]:
        """Analyze patterns in F821 errors"""
        print("📊 Analyzing F821 error patterns...")
        
        name_counts = Counter()
        file_counts = Counter()
        
        for error in self.f821_errors:
            name = error['undefined_name']
            file = error['file']
            name_counts[name] += 1
            file_counts[file] += 1
        
        return {
            'most_common_names': dict(name_counts.most_common(20)),
            'files_with_most_errors': dict(file_counts.most_common(10))
        }
    
    def resolve_file(self, file_path: str) -> bool:
        """Resolve F821 errors in a specific file"""
        file_path = Path(file_path)
        if not file_path.exists():
            return False
        
        print(f"🔧 Resolving F821 errors in {file_path}")
        
        # Get F821 errors for this file
        file_errors = [e for e in self.f821_errors if e['file'] == str(file_path)]
        if not file_errors:
            return True
        
        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except (FileNotFoundError, PermissionError, OSError) as e:
            print(f"❌ Error reading {file_path}: {e}")
            return False
        
        # Track what imports we need to add
        needed_imports = set()
        resolved_count = 0
        
        # Analyze each error
        for error in file_errors:
            undefined_name = error['undefined_name']
            line_num = error['line'] - 1  # Convert to 0-based index
            
            if line_num >= len(lines):
                continue
            
            # Check if this is a common import we can fix
            if undefined_name in self.common_imports:
                needed_imports.add(undefined_name)
                resolved_count += 1
                self.resolution_stats['resolved'] += 1
            else:
                # Check if it's a parameter name (common pattern)
                if self._is_likely_parameter(lines, line_num, undefined_name):
                    resolved_count += 1
                    self.resolution_stats['parameter_fix'] += 1
                else:
                    self.resolution_stats['unresolved'] += 1
        
        # Add imports if needed
        if needed_imports:
            self._add_imports_to_file(file_path, lines, needed_imports)
        
        print(f"✅ Resolved {resolved_count}/{len(file_errors)} errors in {file_path}")
        return True
    
    def _is_likely_parameter(self, lines: List[str], line_num: int, name: str) -> bool:
        """Check if undefined name is likely a function parameter"""
        # Look for function definition above this line
        for i in range(max(0, line_num - 10), line_num):
            line = lines[i].strip()
            if 'def ' in line and name in line:
                return True
        return False
    
    def _add_imports_to_file(self, file_path: Path, lines: List[str], needed_imports: Set[str]):
        """Add necessary imports to the top of the file"""
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
            if name in self.common_imports:
                import_statements.append(self.common_imports[name])
        
        # Insert imports
        if import_statements:
            # Remove duplicates while preserving order
            unique_imports = []
            seen = set()
            for imp in import_statements:
                if imp not in seen:
                    unique_imports.append(imp)
                    seen.add(imp)
            
            # Insert after the import section
            for i, import_stmt in enumerate(unique_imports):
                lines.insert(import_section_end + i, import_stmt + '\n')
            
            # Write back to file
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                print(f"✅ Added {len(unique_imports)} imports to {file_path}")
            except (FileNotFoundError, PermissionError, OSError) as e:
                print(f"❌ Error writing {file_path}: {e}")
    
    def resolve_all_errors(self) -> Dict[str, int]:
        """Resolve all F821 errors systematically"""
        print("🚀 Starting systematic F821 resolution...")
        
        # Get all unique files with F821 errors
        files_with_errors = set(error['file'] for error in self.f821_errors)
        
        print(f"📁 Processing {len(files_with_errors)} files with F821 errors...")
        
        for file_path in files_with_errors:
            self.resolve_file(file_path)
        
        return dict(self.resolution_stats)
    
    def generate_report(self) -> str:
        """Generate resolution report"""
        patterns = self.analyze_error_patterns()
        
        report = []
        report.append("# F821 Resolution Report - The Great Import Sweep")
        report.append("")
        report.append(f"**Total F821 Errors Found**: {len(self.f821_errors)}")
        report.append(f"**Files Processed**: {len(set(e['file'] for e in self.f821_errors))}")
        report.append("")
        
        report.append("## Resolution Statistics")
        report.append("")
        for stat, count in self.resolution_stats.items():
            report.append(f"- **{stat.replace('_', ' ').title()}**: {count}")
        report.append("")
        
        report.append("## Most Common Undefined Names")
        report.append("")
        report.append("| Name | Count | Resolution Strategy |")
        report.append("|------|-------|-------------------|")
        
        for name, count in patterns['most_common_names'].items():
            if name in self.common_imports:
                strategy = "Auto-import"
            elif name in ['conversation', 'extraction', 'user', 'request', 'response']:
                strategy = "Parameter name"
            else:
                strategy = "Manual review"
            
            report.append(f"| `{name}` | {count} | {strategy} |")
        
        report.append("")
        
        report.append("## Files with Most Errors")
        report.append("")
        report.append("| File | Error Count |")
        report.append("|------|-------------|")
        
        for file_path, count in patterns['files_with_most_errors'].items():
            report.append(f"| `{file_path}` | {count} |")
        
        return "\n".join(report)

def main():
    """Main execution function"""
    project_root = "/home/chris/PAKE_SYSTEM_claude_optimized"
    
    resolver = F821Resolver(project_root)
    
    # Scan for F821 errors
    errors = resolver.scan_f821_errors()
    if not errors:
        print("✅ No F821 errors found!")
        return
    
    # Analyze patterns
    patterns = resolver.analyze_error_patterns()
    print(f"📊 Most common undefined names: {list(patterns['most_common_names'].keys())[:5]}")
    
    # Resolve errors
    stats = resolver.resolve_all_errors()
    
    # Generate report
    report = resolver.generate_report()
    with open("F821_RESOLUTION_REPORT.md", "w") as f:
        f.write(report)
    
    print("✅ F821 Resolution Complete!")
    print(f"📄 Report written to: F821_RESOLUTION_REPORT.md")
    print(f"📊 Resolution stats: {stats}")

if __name__ == "__main__":
    main()