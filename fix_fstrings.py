#!/usr/bin/env python3
"""
Script to fix unterminated f-strings in Python files.
This script finds f-strings that are split across multiple lines incorrectly
and fixes them by joining the lines properly.
"""

import re
import os
import sys
from pathlib import Path

def fix_fstrings_in_file(file_path):
    """Fix f-string issues in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Pattern to match f-strings that are split across lines incorrectly
        # This matches f"text {variable} more text" patterns
        pattern = r'f"([^"]*)\{\s*([^}]+)\s*\}([^"]*)"'
        
        def fix_match(match):
            prefix = match.group(1)
            variable = match.group(2).strip()
            suffix = match.group(3)
            return f'f"{prefix}{{{variable}}}{suffix}"'
        
        # Apply the fix
        content = re.sub(pattern, fix_match, content, flags=re.MULTILINE | re.DOTALL)
        
        # Also fix patterns where the f-string is split across multiple lines
        # Pattern for multi-line f-strings with variables
        multiline_pattern = r'f"([^"]*)\{\s*\n\s*([^}]+)\s*\n\s*\}([^"]*)"'
        
        def fix_multiline_match(match):
            prefix = match.group(1)
            variable = match.group(2).strip()
            suffix = match.group(3)
            return f'f"{prefix}{{{variable}}}{suffix}"'
        
        content = re.sub(multiline_pattern, fix_multiline_match, content, flags=re.MULTILINE | re.DOTALL)
        
        # Write back if changed
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed f-strings in: {file_path}")
            return True
        return False
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Main function to fix f-strings in all Python files."""
    src_dir = Path("/home/chris/projects/PAKE_SYSTEM_claude_optimized/src")
    
    if not src_dir.exists():
        print(f"Source directory {src_dir} does not exist")
        return
    
    fixed_count = 0
    total_count = 0
    
    # Find all Python files
    for py_file in src_dir.rglob("*.py"):
        total_count += 1
        if fix_fstrings_in_file(py_file):
            fixed_count += 1
    
    print(f"Processed {total_count} Python files")
    print(f"Fixed f-strings in {fixed_count} files")

if __name__ == "__main__":
    main()
