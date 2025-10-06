#!/usr/bin/env python3
"""
Targeted F821 Fix Script - Focus on Missing Typing Imports
Fixes the most common F821 errors: missing Dict, List, and other typing imports
"""

from pathlib import Path
import re
import subprocess
from typing import Set


def get_files_with_typing_errors() -> Set[Path]:
    """Get files that have F821 errors related to missing typing imports."""
    result = subprocess.run(
        ["ruff", "check", ".", "--select=F821"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    
    files_with_errors = set()
    output = result.stdout + result.stderr
    
    # Common typing names that are often missing
    typing_names = {'Dict', 'List', 'Tuple', 'Set', 'Optional', 'Union', 'Any', 'Callable'}
    
    for line in output.splitlines():
        if "F821" in line and "Undefined name" in line:
            for typing_name in typing_names:
                if f"Undefined name `{typing_name}`" in line:
                    # Extract file path
                    if ":" in line and ".py:" in line:
                        file_path = line.split(":")[0]
                        files_with_errors.add(Path(file_path))
                    break
    
    return files_with_errors

def fix_typing_imports(file_path: Path) -> bool:
    """Fix missing typing imports in a file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Common typing imports that are often missing
    typing_imports = {
        'Dict', 'List', 'Tuple', 'Set', 'Optional', 'Union', 'Any', 
        'Callable', 'Type', 'TypeVar', 'Generic', 'Protocol', 'Literal',
        'Final', 'ClassVar', 'TYPE_CHECKING'
    }
    
    # Check which typing imports are used but not imported
    missing_imports = set()
    for import_name in typing_imports:
        if import_name in content and f"from typing import {import_name}" not in content:
            # Check if it's not already imported in a different way
            if f"import {import_name}" not in content:
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
        
        # Write the fixed content back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    
    return False

def main():
    """Main function to fix missing typing imports."""
    print("🔧 Targeted F821 Fix - Missing Typing Imports")
    print("=" * 60)
    
    # Get files with typing-related F821 errors
    print("📊 Finding files with missing typing imports...")
    files_with_errors = get_files_with_typing_errors()
    
    print(f"Found {len(files_with_errors)} files with typing-related F821 errors")
    print()
    
    fixed_files = 0
    
    print("🔧 Fixing missing typing imports...")
    for file_path in sorted(files_with_errors):
        if not file_path.exists():
            continue
        
        print(f"Fixing {file_path}...")
        
        was_modified = fix_typing_imports(file_path)
        if was_modified:
            fixed_files += 1
            print(f"  ✅ Fixed")
        else:
            print(f"  ℹ️  No fixes needed")
        print()
    
    print("=" * 60)
    print(f"✅ Complete: Fixed typing imports in {fixed_files} files")
    print("=" * 60)

if __name__ == "__main__":
    main()