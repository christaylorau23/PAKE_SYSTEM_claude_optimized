#!/usr/bin/env python3
"""
Quick fix for Black formatting issue
"""

import subprocess
import sys
import os

def fix_formatting():
    """Fix Black formatting issues"""
    try:
        # Change to project directory
        os.chdir('/root/projects/PAKE_SYSTEM_claude_optimized')
        
        # Run Black on the specific file
        result = subprocess.run([
            sys.executable, '-m', 'black', 
            'src/utils/security_guards.py',
            '--line-length', '88'
        ], capture_output=True, text=True)
        
        print(f"Black exit code: {result.returncode}")
        print(f"Black stdout: {result.stdout}")
        print(f"Black stderr: {result.stderr}")
        
        if result.returncode == 0:
            print("✅ Black formatting successful")
        else:
            print("❌ Black formatting failed")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fix_formatting()
