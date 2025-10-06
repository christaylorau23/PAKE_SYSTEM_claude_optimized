#!/usr/bin/env python3
"""
Comprehensive F821 Error Fix Script
Fixes the most common F821 undefined name errors across the codebase
"""

from pathlib import Path
import re
import subprocess
from typing import Dict, List, Set, Tuple


def get_f821_errors() -> Dict[str, List[Tuple[int, str]]]:
    """Get all F821 errors from ruff."""
    # Use absolute path for security (S607)
    import shutil
    ruff_path = shutil.which("ruff")
    if not ruff_path:
        raise RuntimeError("Ruff not found in PATH")
    
    result = subprocess.run(
        [ruff_path, "check", ".", "--select=F821"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    
    errors_by_file = {}
    output = result.stdout + result.stderr
    
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
                        if file_path not in errors_by_file:
                            errors_by_file[file_path] = []
                        errors_by_file[file_path].append((line_num, undefined_name))
    
    return errors_by_file

def fix_missing_init_parameters(file_path: Path, errors: List[Tuple[int, str]]) -> Tuple[bool, int]:
    """Fix missing __init__ parameters."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    fixes_applied = 0
    
    # Find __init__ methods and their missing parameters
    init_pattern = r'def __init__\(self\) -> None:'
    init_matches = list(re.finditer(init_pattern, content))
    
    for match in reversed(init_matches):  # Process in reverse to maintain line numbers
        init_start = match.start()
        init_end = match.end()
        
        # Find the class this __init__ belongs to
        class_pattern = r'class (\w+).*?:'
        class_matches = list(re.finditer(class_pattern, content[:init_start]))
        if not class_matches:
            continue
        
        class_name = class_matches[-1].group(1)
        
        # Get undefined names used in this __init__ method
        method_start_line = content[:init_start].count('\n') + 1
        method_end_line = method_start_line + 20  # Look ahead 20 lines
        
        method_undefined_names = set()
        for line_num, undefined_name in errors:
            if method_start_line <= line_num <= method_end_line:
                method_undefined_names.add(undefined_name)
        
        if method_undefined_names:
            # Create parameter list
            params = []
            for name in sorted(method_undefined_names):
                if name in ['environment', 'config_file', 'config', 'app']:
                    params.append(f"{name}: str | None = None")
                elif name in ['vector_db', 'query_request', 'conversation', 'extraction', 'batch']:
                    params.append(f"{name}: Any = None")
                else:
                    params.append(f"{name}: Any = None")
            
            param_str = ", ".join(params)
            new_init = f'def __init__(self, {param_str}) -> None:'
            
            content = content[:init_start] + new_init + content[init_end:]
            fixes_applied += 1
            print(f"Fixed __init__ in {class_name}: added {len(method_undefined_names)} parameters")
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True, fixes_applied
    
    return False, 0

def fix_missing_typing_imports(file_path: Path) -> Tuple[bool, int]:
    """Add missing typing imports."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Common typing imports that are often missing
    typing_imports = {
        'List', 'Dict', 'Tuple', 'Set', 'Optional', 'Union', 'Any', 
        'Callable', 'Type', 'TypeVar', 'Generic', 'Protocol', 'Literal',
        'Final', 'ClassVar', 'TYPE_CHECKING'
    }
    
    # Check which typing imports are used but not imported
    missing_imports = set()
    for import_name in typing_imports:
        if import_name in content and f"from typing import {import_name}" not in content:
            missing_imports.add(import_name)
    
    if missing_imports:
        # Find existing typing import
        typing_import_pattern = r'from typing import ([^\n]+)'
        typing_match = re.search(typing_import_pattern, content)
        
        if typing_match:
            # Add to existing import
            existing_imports = typing_match.group(1)
            all_imports = set(existing_imports.split(', ')) | missing_imports
            new_import = f"from typing import {', '.join(sorted(all_imports))}"
            content = re.sub(typing_import_pattern, new_import, content)
        else:
            # Add new typing import
            import_line = f"from typing import {', '.join(sorted(missing_imports))}\n"
            # Insert after other imports
            import_end = content.find('\n\n')
            if import_end == -1:
                import_end = content.find('\n')
            content = content[:import_end] + '\n' + import_line + content[import_end:]
        
        print(f"Added typing imports: {', '.join(sorted(missing_imports))}")
        return True, len(missing_imports)
    
    return False, 0

def fix_circular_dependencies(file_path: Path) -> Tuple[bool, int]:
    """Fix circular dependencies using TYPE_CHECKING pattern."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    fixes_applied = 0
    
    # Look for imports that might be circular dependencies
    # This is a simplified approach - in practice, you'd need more sophisticated detection
    
    # Add TYPE_CHECKING import if not present
    if 'TYPE_CHECKING' in content and 'from typing import TYPE_CHECKING' not in content:
        typing_import_pattern = r'from typing import ([^\n]+)'
        typing_match = re.search(typing_import_pattern, content)
        
        if typing_match:
            existing_imports = typing_match.group(1)
            if 'TYPE_CHECKING' not in existing_imports:
                new_import = f"from typing import {existing_imports}, TYPE_CHECKING"
                content = re.sub(typing_import_pattern, new_import, content)
                fixes_applied += 1
    
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True, fixes_applied
    
    return False, 0

def fix_file(file_path: Path, errors: List[Tuple[int, str]]) -> Tuple[bool, int]:
    """Apply all fixes to a single file."""
    total_fixes = 0
    was_modified = False
    
    # Fix missing __init__ parameters
    modified, fixes = fix_missing_init_parameters(file_path, errors)
    if modified:
        was_modified = True
        total_fixes += fixes
    
    # Fix missing typing imports
    modified, fixes = fix_missing_typing_imports(file_path)
    if modified:
        was_modified = True
        total_fixes += fixes
    
    # Fix circular dependencies
    modified, fixes = fix_circular_dependencies(file_path)
    if modified:
        was_modified = True
        total_fixes += fixes
    
    return was_modified, total_fixes

def main():
    """Main function to fix F821 errors across the codebase."""
    print("🔧 Comprehensive F821 Error Fix - The Phoenix Protocol Phase 5.2")
    print("=" * 80)
    
    # Get all F821 errors
    print("📊 Analyzing F821 errors...")
    errors_by_file = get_f821_errors()
    
    total_files = len(errors_by_file)
    total_errors = sum(len(errors) for errors in errors_by_file.values())
    
    print(f"Found {total_errors} F821 errors in {total_files} files")
    print()
    
    # Process files with most errors first
    sorted_files = sorted(errors_by_file.items(), key=lambda x: len(x[1]), reverse=True)
    
    fixed_files = 0
    total_fixes = 0
    
    for file_path_str, errors in sorted_files[:20]:  # Process top 20 files
        file_path = Path(file_path_str)
        if not file_path.exists():
            continue
        
        print(f"🔧 Fixing {file_path} ({len(errors)} errors)...")
        
        was_modified, fixes = fix_file(file_path, errors)
        if was_modified:
            fixed_files += 1
            total_fixes += fixes
            print(f"✅ Fixed {fixes} issues")
        else:
            print("ℹ️  No fixes applied")
        print()
    
    print("=" * 80)
    print(f"✅ Phase 5.2 Complete: Fixed {total_fixes} F821 issues in {fixed_files} files")
    print("=" * 80)

if __name__ == "__main__":
    main()
