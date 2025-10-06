#!/usr/bin/env python3
"""
Systematic F821 Fix Script - The Phoenix Protocol Phase 5.2
Fixes the most common F821 undefined name errors systematically
"""

from pathlib import Path
import re
import subprocess
from typing import Dict, List, Set, Tuple


def get_f821_errors_by_file() -> Dict[str, List[Tuple[int, str]]]:
    """Get F821 errors organized by file."""
    result = subprocess.run(
        ["ruff", "check", ".", "--select=F821"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    
    errors_by_file = {}
    output = result.stdout + result.stderr
    
    for line in output.splitlines():
        if "F821" in line and "Undefined name" in line and ":" in line:
            # Parse the line format: file:line:col: F821 Undefined name `name`
            parts = line.split(":")
            if len(parts) >= 3:
                file_path = parts[0]
                try:
                    line_num = int(parts[1])
                    name_match = re.search(r"Undefined name `([^`]+)`", line)
                    if name_match:
                        undefined_name = name_match.group(1)
                        if file_path not in errors_by_file:
                            errors_by_file[file_path] = []
                        errors_by_file[file_path].append((line_num, undefined_name))
                except ValueError:
                    continue
    
    return errors_by_file

def fix_missing_init_parameters(file_path: Path, errors: List[Tuple[int, str]]) -> Tuple[bool, int]:
    """Fix missing __init__ parameters."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    fixes_applied = 0
    
    # Find all __init__ methods
    init_pattern = r'def __init__\(self\) -> None:'
    init_matches = list(re.finditer(init_pattern, content))
    
    for match in reversed(init_matches):  # Process in reverse to maintain positions
        init_start = match.start()
        init_end = match.end()
        
        # Calculate line number of this __init__
        init_line_num = content[:init_start].count('\n') + 1
        
        # Find undefined names used within 50 lines after this __init__
        method_undefined_names = set()
        for line_num, undefined_name in errors:
            if init_line_num <= line_num <= init_line_num + 50:
                method_undefined_names.add(undefined_name)
        
        if method_undefined_names:
            # Create parameter list with appropriate types
            params = []
            for name in sorted(method_undefined_names):
                if name in ['vector_db', 'query_request', 'conversation', 'extraction', 'batch']:
                    params.append(f"{name}: Any = None")
                elif name in ['environment', 'config_file', 'config']:
                    params.append(f"{name}: str | None = None")
                elif name in ['rollback', 'operation', 'dal']:
                    params.append(f"{name}: bool = False")
                elif name in ['name', 'vault_path']:
                    params.append(f"{name}: str = ''")
                elif name in ['message', 'kwargs']:
                    params.append(f"{name}: Any = None")
                else:
                    params.append(f"{name}: Any = None")
            
            param_str = ", ".join(params)
            new_init = f'def __init__(self, {param_str}) -> None:'
            
            content = content[:init_start] + new_init + content[init_end:]
            fixes_applied += 1
            print(f"  Fixed __init__: added {len(method_undefined_names)} parameters")
    
    # Add Any import if needed
    if fixes_applied > 0 and 'Any' in content:
        if 'from typing import' in content:
            typing_import_pattern = r'from typing import ([^\n]+)'
            typing_match = re.search(typing_import_pattern, content)
            
            if typing_match:
                existing_imports = typing_match.group(1)
                if 'Any' not in existing_imports:
                    new_import = f"from typing import {existing_imports}, Any"
                    content = re.sub(typing_import_pattern, new_import, content)
                    print(f"  Added Any import")
        else:
            # Add typing import
            import_line = "from typing import Any\n"
            lines = content.split('\n')
            insert_line = 0
            for i, line in enumerate(lines):
                if line.startswith('import ') or line.startswith('from '):
                    insert_line = i + 1
                elif line.strip() == '' and insert_line > 0:
                    break
            
            lines.insert(insert_line, import_line)
            content = '\n'.join(lines)
            print(f"  Added typing import")
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True, fixes_applied
    
    return False, 0

def fix_missing_typing_imports(file_path: Path, errors: List[Tuple[int, str]]) -> Tuple[bool, int]:
    """Fix missing typing imports."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Common typing imports
    typing_imports = {
        'Dict', 'List', 'Tuple', 'Set', 'Optional', 'Union', 'Any', 
        'Callable', 'Type', 'TypeVar', 'Generic', 'Protocol', 'Literal',
        'Final', 'ClassVar', 'TYPE_CHECKING'
    }
    
    # Find which typing imports are used but missing
    missing_imports = set()
    for _, undefined_name in errors:
        if undefined_name in typing_imports:
            missing_imports.add(undefined_name)
    
    if missing_imports:
        # Check if typing is already imported
        if 'from typing import' in content:
            typing_import_pattern = r'from typing import ([^\n]+)'
            typing_match = re.search(typing_import_pattern, content)
            
            if typing_match:
                existing_imports = typing_match.group(1)
                all_imports = set(existing_imports.split(', ')) | missing_imports
                new_import = f"from typing import {', '.join(sorted(all_imports))}"
                content = re.sub(typing_import_pattern, new_import, content)
            else:
                # Add new typing import
                import_line = f"from typing import {', '.join(sorted(missing_imports))}\n"
                lines = content.split('\n')
                insert_line = 0
                for i, line in enumerate(lines):
                    if line.startswith('import ') or line.startswith('from '):
                        insert_line = i + 1
                    elif line.strip() == '' and insert_line > 0:
                        break
                
                lines.insert(insert_line, import_line)
                content = '\n'.join(lines)
        else:
            # Add new typing import
            import_line = f"from typing import {', '.join(sorted(missing_imports))}\n"
            lines = content.split('\n')
            insert_line = 0
            for i, line in enumerate(lines):
                if line.startswith('import ') or line.startswith('from '):
                    insert_line = i + 1
                elif line.strip() == '' and insert_line > 0:
                    break
            
            lines.insert(insert_line, import_line)
            content = '\n'.join(lines)
        
        print(f"  Added typing imports: {', '.join(sorted(missing_imports))}")
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, len(missing_imports)
    
    return False, 0

def fix_file(file_path: Path, errors: List[Tuple[int, str]]) -> Tuple[bool, int]:
    """Apply all fixes to a single file."""
    total_fixes = 0
    was_modified = False
    
    print(f"Fixing {file_path} ({len(errors)} errors)...")
    
    # Fix missing __init__ parameters
    modified, fixes = fix_missing_init_parameters(file_path, errors)
    if modified:
        was_modified = True
        total_fixes += fixes
    
    # Fix missing typing imports
    modified, fixes = fix_missing_typing_imports(file_path, errors)
    if modified:
        was_modified = True
        total_fixes += fixes
    
    if was_modified:
        print(f"  ✅ Fixed {total_fixes} issues")
    else:
        print(f"  ℹ️  No fixes applied")
    
    return was_modified, total_fixes

def main():
    """Main function to systematically fix F821 errors."""
    print("🔧 Systematic F821 Fix - The Phoenix Protocol Phase 5.2")
    print("=" * 70)
    
    # Get all F821 errors
    print("📊 Analyzing F821 errors...")
    errors_by_file = get_f821_errors_by_file()
    
    total_files = len(errors_by_file)
    total_errors = sum(len(errors) for errors in errors_by_file.values())
    
    print(f"Found {total_errors} F821 errors in {total_files} files")
    print()
    
    # Process files with most errors first
    sorted_files = sorted(errors_by_file.items(), key=lambda x: len(x[1]), reverse=True)
    
    fixed_files = 0
    total_fixes = 0
    
    print("🔧 Fixing files systematically...")
    for file_path_str, errors in sorted_files[:20]:  # Process top 20 files
        file_path = Path(file_path_str)
        if not file_path.exists():
            continue
        
        was_modified, fixes = fix_file(file_path, errors)
        if was_modified:
            fixed_files += 1
            total_fixes += fixes
        print()
    
    print("=" * 70)
    print(f"✅ Phase 5.2 Complete: Fixed {total_fixes} F821 issues in {fixed_files} files")
    print("=" * 70)

if __name__ == "__main__":
    main()
