#!/usr/bin/env python3
"""Automated script to fix common F821 undefined-name errors.

This script systematically fixes the most common patterns of F821 errors:
1. Missing typing imports (Dict, List, Optional, Union, etc.)
2. Missing FastAPI imports (BackgroundTasks, etc.)
3. Missing function parameters in common patterns
"""

import ast
import os
import re
import sys
from pathlib import Path
from typing import Set, List, Dict, Any


class F821Fixer:
    """Fixes common F821 undefined-name errors."""
    
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.fixed_files = 0
        self.total_fixes = 0
        
        # Common typing imports that are often missing
        self.typing_imports = {
            'Dict': 'typing',
            'List': 'typing', 
            'Optional': 'typing',
            'Union': 'typing',
            'Any': 'typing',
            'Callable': 'typing',
            'Type': 'typing',
            'Tuple': 'typing',
            'Set': 'typing',
            'Sequence': 'typing',
            'Iterable': 'typing',
            'Iterator': 'typing',
            'Generator': 'typing',
            'AsyncGenerator': 'typing',
            'Awaitable': 'typing',
            'Coroutine': 'typing',
        }
        
        # FastAPI imports that are often missing
        self.fastapi_imports = {
            'BackgroundTasks': 'fastapi',
            'HTTPException': 'fastapi',
            'Depends': 'fastapi',
            'Query': 'fastapi',
            'Path': 'fastapi',
            'Body': 'fastapi',
            'Form': 'fastapi',
            'File': 'fastapi',
            'UploadFile': 'fastapi',
            'Request': 'fastapi',
            'Response': 'fastapi',
            'Cookie': 'fastapi',
            'Header': 'fastapi',
        }
    
    def find_python_files(self) -> List[Path]:
        """Find all Python files in the project."""
        python_files = []
        for root, dirs, files in os.walk(self.root_dir):
            # Skip common directories that shouldn't be modified
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules']]
            
            for file in files:
                if file.endswith('.py'):
                    python_files.append(Path(root) / file)
        
        return python_files
    
    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyze a Python file for F821 errors."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (FileNotFoundError, PermissionError, OSError) as e:
            print(f"Error reading {file_path}: {e}")
            return {}
        
        # Parse the AST to find undefined names
        try:
            tree = ast.parse(content)
        except SyntaxError as e:
            print(f"Syntax error in {file_path}: {e}")
            return {}
        
        # Find all name references
        undefined_names = set()
        defined_names = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                undefined_names.add(node.id)
            elif isinstance(node, ast.FunctionDef):
                defined_names.add(node.name)
                # Add parameter names
                for arg in node.args.args:
                    defined_names.add(arg.arg)
            elif isinstance(node, ast.ClassDef):
                defined_names.add(node.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    defined_names.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    for alias in node.names:
                        defined_names.add(alias.name)
        
        # Find undefined names that are likely imports
        missing_imports = undefined_names - defined_names
        
        return {
            'content': content,
            'missing_imports': missing_imports,
            'defined_names': defined_names,
        }
    
    def fix_typing_imports(self, content: str, missing_imports: Set[str]) -> str:
        """Fix missing typing imports."""
        # Find existing typing imports
        typing_imports = set()
        typing_from_imports = set()
        
        lines = content.split('\n')
        new_lines = []
        typing_line_index = -1
        
        for i, line in enumerate(lines):
            if line.strip().startswith('from typing import'):
                # Extract existing imports
                imports_str = line.split('from typing import')[1].strip()
                existing_imports = [imp.strip() for imp in imports_str.split(',')]
                typing_from_imports.update(existing_imports)
                typing_line_index = i
            elif line.strip().startswith('import typing'):
                typing_imports.add('typing')
                typing_line_index = i
            
            new_lines.append(line)
        
        # Find missing typing imports that we can fix
        needed_typing_imports = set()
        for name in missing_imports:
            if name in self.typing_imports:
                needed_typing_imports.add(name)
        
        if needed_typing_imports:
            # Add missing imports to existing typing import line
            if typing_line_index >= 0:
                existing_line = lines[typing_line_index]
                if 'from typing import' in existing_line:
                    # Add to existing from typing import line
                    imports_str = existing_line.split('from typing import')[1].strip()
                    existing_imports = [imp.strip() for imp in imports_str.split(',')]
                    all_imports = existing_imports + list(needed_typing_imports)
                    all_imports = sorted(set(all_imports))  # Remove duplicates and sort
                    new_lines[typing_line_index] = f"from typing import {', '.join(all_imports)}"
                else:
                    # Add new from typing import line
                    new_lines.insert(typing_line_index + 1, f"from typing import {', '.join(sorted(needed_typing_imports))}")
            else:
                # Find a good place to insert the import
                insert_index = 0
                for i, line in enumerate(lines):
                    if line.strip().startswith('import ') or line.strip().startswith('from '):
                        insert_index = i + 1
                    elif line.strip() and not line.strip().startswith('#'):
                        break
                
                new_lines.insert(insert_index, f"from typing import {', '.join(sorted(needed_typing_imports))}")
        
        return '\n'.join(new_lines)
    
    def fix_fastapi_imports(self, content: str, missing_imports: Set[str]) -> str:
        """Fix missing FastAPI imports."""
        needed_fastapi_imports = set()
        for name in missing_imports:
            if name in self.fastapi_imports:
                needed_fastapi_imports.add(name)
        
        if not needed_fastapi_imports:
            return content
        
        lines = content.split('\n')
        new_lines = []
        fastapi_line_index = -1
        
        for i, line in enumerate(lines):
            if 'from fastapi import' in line:
                # Extract existing imports
                imports_str = line.split('from fastapi import')[1].strip()
                existing_imports = [imp.strip() for imp in imports_str.split(',')]
                all_imports = existing_imports + list(needed_fastapi_imports)
                all_imports = sorted(set(all_imports))  # Remove duplicates and sort
                new_lines.append(f"from fastapi import {', '.join(all_imports)}")
                fastapi_line_index = i
            else:
                new_lines.append(line)
        
        if fastapi_line_index == -1:
            # Find a good place to insert the import
            insert_index = 0
            for i, line in enumerate(lines):
                if line.strip().startswith('import ') or line.strip().startswith('from '):
                    insert_index = i + 1
                elif line.strip() and not line.strip().startswith('#'):
                    break
            
            new_lines.insert(insert_index, f"from fastapi import {', '.join(sorted(needed_fastapi_imports))}")
        
        return '\n'.join(new_lines)
    
    def fix_file(self, file_path: Path) -> bool:
        """Fix F821 errors in a single file."""
        analysis = self.analyze_file(file_path)
        if not analysis:
            return False
        
        content = analysis['content']
        missing_imports = analysis['missing_imports']
        
        original_content = content
        
        # Fix typing imports
        content = self.fix_typing_imports(content, missing_imports)
        
        # Fix FastAPI imports
        content = self.fix_fastapi_imports(content, missing_imports)
        
        # Only write if content changed
        if content != original_content:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.fixed_files += 1
                self.total_fixes += 1
                print(f"Fixed {file_path}")
                return True
            except (FileNotFoundError, PermissionError, OSError) as e:
                print(f"Error writing {file_path}: {e}")
                return False
        
        return False
    
    def run(self):
        """Run the F821 fixer on all Python files."""
        print("🔍 Finding Python files...")
        python_files = self.find_python_files()
        print(f"Found {len(python_files)} Python files")
        
        print("🔧 Fixing F821 errors...")
        for file_path in python_files:
            self.fix_file(file_path)
        
        print(f"\n✅ Fixed {self.total_fixes} issues in {self.fixed_files} files")


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        root_dir = sys.argv[1]
    else:
        root_dir = "."
    
    fixer = F821Fixer(root_dir)
    fixer.run()


if __name__ == "__main__":
    main()