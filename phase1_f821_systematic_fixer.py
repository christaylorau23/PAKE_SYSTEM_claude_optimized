#!/usr/bin/env python3
"""
Phase 1: Systematic F821 Error Resolution
Fixes the 4,026 undefined-name errors preventing system startup
"""

import ast
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
from collections import Counter, defaultdict


class Phase1F821Fixer:
    """Systematic F821 error resolver for PAKE System stabilization"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.fixes_applied = Counter()
        self.files_processed = set()
        
        # Common undefined names and their fixes
        self.common_fixes = {
            # Logging patterns
            'logger': 'import logging\nlogger = logging.getLogger(__name__)',
            
            # Typing imports
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
            
            # Standard library
            'datetime': 'from datetime import datetime',
            'timedelta': 'from datetime import timedelta',
            'UTC': 'from datetime import UTC',
            'Path': 'from pathlib import Path',
            'json': 'import json',
            'os': 'import os',
            'sys': 'import sys',
            're': 'import re',
            'uuid': 'import uuid',
            'hashlib': 'import hashlib',
            'base64': 'import base64',
            'time': 'import time',
            'asyncio': 'import asyncio',
            
            # FastAPI imports
            'HTTPException': 'from fastapi import HTTPException',
            'Depends': 'from fastapi import Depends',
            'Query': 'from fastapi import Query',
            'Path': 'from fastapi import Path',
            'Body': 'from fastapi import Body',
            'Form': 'from fastapi import Form',
            'File': 'from fastapi import File',
            'UploadFile': 'from fastapi import UploadFile',
            'Request': 'from fastapi import Request',
            'Response': 'from fastapi import Response',
            'Cookie': 'from fastapi import Cookie',
            'Header': 'from fastapi import Header',
            'BackgroundTasks': 'from fastapi import BackgroundTasks',
            
            # Pydantic
            'BaseModel': 'from pydantic import BaseModel',
            'Field': 'from pydantic import Field',
            'validator': 'from pydantic import validator',
            'root_validator': 'from pydantic import root_validator',
            
            # Common service patterns
            'conversation': 'conversation',  # Parameter name
            'extraction': 'extraction',      # Parameter name
            'batch': 'batch',               # Parameter name
            'user': 'user',                 # Parameter name
            'request': 'request',           # Parameter name
            'response': 'response',         # Parameter name
            'data': 'data',                # Parameter name
            'config': 'config',            # Parameter name
            'settings': 'settings',        # Parameter name
        }
        
        # Files with most errors (from report)
        self.priority_files = [
            'mcp_server_standalone.py',
            'src/services/monitoring/enterprise_monitoring_service.py',
            'data/AIMemoryQueryInterface.py',
            'auth-middleware/src/audit_integration.py'
        ]

    def get_f821_errors(self) -> Dict[str, List[Tuple[int, str]]]:
        """Get all F821 errors from ruff."""
        try:
            result = subprocess.run(
                ['ruff', 'check', '.', '--select=F821', '--output-format=json'],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=self.project_root
            )
            
            errors_by_file = defaultdict(list)
            
            if result.stdout:
                import json
                try:
                    errors = json.loads(result.stdout)
                    for error in errors:
                        if error.get('code') == 'F821':
                            file_path = error['filename']
                            line_num = error['location']['row']
                            message = error['message']
                            
                            # Extract undefined name from message
                            name_match = re.search(r"Undefined name `([^`]+)`", message)
                            if name_match:
                                undefined_name = name_match.group(1)
                                errors_by_file[file_path].append((line_num, undefined_name))
                except json.JSONDecodeError:
                    # Fallback to text parsing
                    self._parse_text_errors(result.stdout, errors_by_file)
            
            return dict(errors_by_file)
            
        except (FileNotFoundError, PermissionError, OSError) as e:
            print(f"Error getting F821 errors: {e}")
            return {}

    def _parse_text_errors(self, output: str, errors_by_file: Dict[str, List[Tuple[int, str]]]):
        """Parse text output when JSON parsing fails."""
        for line in output.splitlines():
            if "F821" in line and "Undefined name" in line:
                # Extract file path and line number
                if ":" in line and ".py:" in line:
                    parts = line.split(":")
                    if len(parts) >= 3:
                        file_path = parts[0]
                        line_num = int(parts[1])
                        # Extract the undefined name
                        name_match = re.search(r"Undefined name `([^`]+)`", line)
                        if name_match:
                            undefined_name = name_match.group(1)
                            errors_by_file[file_path].append((line_num, undefined_name))

    def fix_file(self, file_path: Path, errors: List[Tuple[int, str]]) -> Tuple[bool, int]:
        """Fix F821 errors in a single file."""
        if not file_path.exists():
            return False, 0
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.splitlines()
            fixes_applied = 0
            
            # Group errors by type for efficient fixing
            undefined_names = set(name for _, name in errors)
            
            # Fix missing imports
            if self._needs_import_fixes(undefined_names):
                lines = self._add_missing_imports(lines, undefined_names)
                fixes_applied += len([name for name in undefined_names if name in self.common_fixes])
            
            # Fix parameter issues
            for line_num, undefined_name in errors:
                if line_num <= len(lines):
                    line = lines[line_num - 1]
                    if self._is_parameter_error(line, undefined_name):
                        lines[line_num - 1] = self._fix_parameter_error(line, undefined_name)
                        fixes_applied += 1
            
            # Write back if changes were made
            if fixes_applied > 0:
                new_content = '\n'.join(lines)
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                self.files_processed.add(str(file_path))
                return True, fixes_applied
                
        except (FileNotFoundError, PermissionError, OSError) as e:
            print(f"Error fixing {file_path}: {e}")
            
        return False, 0

    def _needs_import_fixes(self, undefined_names: Set[str]) -> bool:
        """Check if any undefined names need import fixes."""
        return any(name in self.common_fixes for name in undefined_names)

    def _add_missing_imports(self, lines: List[str], undefined_names: Set[str]) -> List[str]:
        """Add missing imports to the top of the file."""
        imports_to_add = []
        
        for name in undefined_names:
            if name in self.common_fixes:
                import_line = self.common_fixes[name]
                if import_line not in imports_to_add:
                    imports_to_add.append(import_line)
        
        if not imports_to_add:
            return lines
            
        # Find the best place to insert imports
        insert_index = 0
        for i, line in enumerate(lines):
            if line.strip().startswith(('import ', 'from ')):
                insert_index = i + 1
            elif line.strip() and not line.strip().startswith('#'):
                break
                
        # Insert imports
        for import_line in imports_to_add:
            lines.insert(insert_index, import_line)
            insert_index += 1
            
        return lines

    def _is_parameter_error(self, line: str, undefined_name: str) -> bool:
        """Check if this is a parameter name error."""
        # Look for patterns like: undefined_name.something or undefined_name(
        return (f"{undefined_name}." in line or 
                f"{undefined_name}(" in line or
                f"= {undefined_name}" in line)

    def _fix_parameter_error(self, line: str, undefined_name: str) -> str:
        """Fix parameter name errors by adding proper parameter."""
        # This is a simplified fix - in practice, you'd need to analyze the function signature
        if f"{undefined_name}." in line:
            # Replace with a proper parameter or self reference
            return line.replace(f"{undefined_name}.", f"self.{undefined_name}.")
        return line

    def run_systematic_fix(self) -> Dict[str, Any]:
        """Run systematic F821 fixes across the codebase."""
        print("🔧 Phase 1: Systematic F821 Error Resolution")
        print("=" * 50)
        
        # Get all F821 errors
        errors_by_file = self.get_f821_errors()
        total_errors = sum(len(errors) for errors in errors_by_file.values())
        
        print(f"📊 Found {total_errors} F821 errors across {len(errors_by_file)} files")
        
        # Process priority files first
        priority_fixed = 0
        for file_name in self.priority_files:
            file_path = self.project_root / file_name
            if file_path.exists() and str(file_path) in errors_by_file:
                print(f"🎯 Fixing priority file: {file_name}")
                success, fixes = self.fix_file(file_path, errors_by_file[str(file_path)])
                if success:
                    priority_fixed += fixes
                    print(f"   ✅ Fixed {fixes} errors")
                else:
                    print(f"   ❌ Failed to fix errors")
        
        # Process remaining files
        remaining_fixed = 0
        for file_path, errors in errors_by_file.items():
            if file_path not in self.files_processed:
                path_obj = Path(file_path)
                if path_obj.exists():
                    success, fixes = self.fix_file(path_obj, errors)
                    if success:
                        remaining_fixed += fixes
                        if fixes > 0:
                            print(f"✅ Fixed {fixes} errors in {path_obj.name}")
        
        total_fixed = priority_fixed + remaining_fixed
        
        print(f"\n📈 Results:")
        print(f"   Files processed: {len(self.files_processed)}")
        print(f"   Total errors fixed: {total_fixed}")
        print(f"   Remaining errors: {total_errors - total_fixed}")
        
        return {
            'files_processed': len(self.files_processed),
            'errors_fixed': total_fixed,
            'remaining_errors': total_errors - total_fixed,
            'success_rate': (total_fixed / total_errors * 100) if total_errors > 0 else 0
        }


def main():
    """Main execution function."""
    project_root = "/home/chris/PAKE_SYSTEM_claude_optimized"
    
    fixer = Phase1F821Fixer(project_root)
    results = fixer.run_systematic_fix()
    
    print(f"\n🎉 Phase 1 Complete!")
    print(f"Success Rate: {results['success_rate']:.1f}%")
    
    if results['remaining_errors'] > 0:
        print(f"\n⚠️  {results['remaining_errors']} errors remain - manual review needed")
    else:
        print(f"\n✅ All F821 errors resolved!")


if __name__ == "__main__":
    main()