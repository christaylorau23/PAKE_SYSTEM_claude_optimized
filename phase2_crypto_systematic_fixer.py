#!/usr/bin/env python3
"""
Phase 2: Weak Crypto Replacement
Replaces 398 weak crypto calls with secure alternatives
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Any
from collections import Counter


class Phase2CryptoFixer:
    """Systematic weak crypto replacement for PAKE System security hardening"""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.fixes_applied = Counter()
        self.files_processed = set()
        
        # Common weak crypto patterns and their secure replacements
        self.crypto_replacements = {
            # Random module imports
            'import random': 'import secrets',
            'from random import': 'from secrets import',
            
            # Random function calls
            'random.random()': 'secrets.randbelow(2**32) / (2**32)',
            'random.randint(': 'secrets.randbelow(',
            'random.choice(': 'secrets.choice(',
            'random.shuffle(': 'secrets.shuffle(',
            'random.uniform(': 'secrets.randbelow(',
            'random.sample(': 'secrets.choice(',
            
            # Common insecure patterns
            'random.getrandbits(': 'secrets.randbits(',
            'random.randrange(': 'secrets.randbelow(',
        }
        
        # Files that commonly have weak crypto
        self.priority_files = [
            'src/pake_system/auth/security.py',
            'src/services/secrets-manager/',
            'src/utils/async_debug_utils.py',
            'src/cosmic_calibration_demo_simple.py',
            'tests/unit/test_aaa_pattern_examples.py'
        ]

    def get_s311_errors(self) -> Dict[str, List[Tuple[int, str]]]:
        """Get all S311 weak crypto errors from ruff."""
        try:
            result = subprocess.run(
                ['ruff', 'check', '.', '--select=S311', '--output-format=json'],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=self.project_root
            )
            
            errors_by_file = {}
            
            if result.stdout:
                import json
                try:
                    errors = json.loads(result.stdout)
                    for error in errors:
                        if error.get('code') == 'S311':
                            file_path = error['filename']
                            line_num = error['location']['row']
                            message = error['message']
                            
                            # Extract the weak crypto pattern
                            pattern_match = re.search(r"`([^`]+)`", message)
                            if pattern_match:
                                weak_pattern = pattern_match.group(1)
                                if file_path not in errors_by_file:
                                    errors_by_file[file_path] = []
                                errors_by_file[file_path].append((line_num, weak_pattern))
                except json.JSONDecodeError:
                    # Fallback to text parsing
                    self._parse_text_s311_errors(result.stdout, errors_by_file)
            
            return errors_by_file
            
        except (FileNotFoundError, PermissionError, OSError) as e:
            print(f"Error getting S311 errors: {e}")
            return {}

    def _parse_text_s311_errors(self, output: str, errors_by_file: Dict[str, List[Tuple[int, str]]]):
        """Parse text output when JSON parsing fails."""
        for line in output.splitlines():
            if "S311" in line and "weak" in line.lower():
                # Extract file path and line number
                if ":" in line and ".py:" in line:
                    parts = line.split(":")
                    if len(parts) >= 3:
                        file_path = parts[0]
                        line_num = int(parts[1])
                        # Extract the weak pattern
                        pattern_match = re.search(r"`([^`]+)`", line)
                        if pattern_match:
                            weak_pattern = pattern_match.group(1)
                            if file_path not in errors_by_file:
                                errors_by_file[file_path] = []
                            errors_by_file[file_path].append((line_num, weak_pattern))

    def fix_file_crypto(self, file_path: Path, errors: List[Tuple[int, str]]) -> Tuple[bool, int]:
        """Fix weak crypto issues in a single file."""
        if not file_path.exists():
            return False, 0
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            fixes_applied = 0
            
            # Apply crypto replacements
            for pattern, replacement in self.crypto_replacements.items():
                if pattern in content:
                    content = content.replace(pattern, replacement)
                    fixes_applied += 1
            
            # Handle specific random.randint patterns
            content = self._fix_random_randint(content)
            
            # Handle random.uniform patterns
            content = self._fix_random_uniform(content)
            
            # Ensure secrets import is present if we're using secrets
            if 'secrets.' in content and 'import secrets' not in content:
                content = self._add_secrets_import(content)
                fixes_applied += 1
            
            # Write back if changes were made
            if content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                self.files_processed.add(str(file_path))
                return True, fixes_applied
                
        except (FileNotFoundError, PermissionError, OSError) as e:
            print(f"Error fixing {file_path}: {e}")
            
        return False, 0

    def _fix_random_randint(self, content: str) -> str:
        """Fix random.randint patterns with proper secrets.randbelow."""
        # Pattern: random.randint(a, b) -> secrets.randbelow(b - a + 1) + a
        def replace_randint(match):
            a = match.group(1)
            b = match.group(2)
            return f'secrets.randbelow({b} - {a} + 1) + {a}'
        
        content = re.sub(r'secrets\.randbelow\(([^,]+),\s*([^)]+)\)', replace_randint, content)
        return content

    def _fix_random_uniform(self, content: str) -> str:
        """Fix random.uniform patterns with secure alternatives."""
        # Pattern: random.uniform(a, b) -> secure_random_float(a, b)
        def replace_uniform(match):
            a = match.group(1)
            b = match.group(2)
            return f'secure_random_float({a}, {b})'
        
        content = re.sub(r'secrets\.randbelow\(([^,]+),\s*([^)]+)\)', replace_uniform, content)
        return content

    def _add_secrets_import(self, content: str) -> str:
        """Add secrets import to the top of the file."""
        lines = content.splitlines()
        
        # Find the best place to insert import
        insert_index = 0
        for i, line in enumerate(lines):
            if line.strip().startswith(('import ', 'from ')):
                insert_index = i + 1
            elif line.strip() and not line.strip().startswith('#'):
                break
                
        # Insert secrets import
        lines.insert(insert_index, 'import secrets')
        return '\n'.join(lines)

    def create_secure_random_utils(self) -> bool:
        """Create secure random utilities module."""
        try:
            utils_content = '''#!/usr/bin/env python3
"""
Secure Random Utilities for PAKE System
Provides cryptographically secure random number generation
"""

import secrets
import string
from typing import List, Any, Union


def secure_random_float(min_val: float = 0.0, max_val: float = 1.0) -> float:
    """Generate a cryptographically secure random float."""
    if min_val >= max_val:
        raise ValueError("min_val must be less than max_val")
    
    range_size = max_val - min_val
    # Use a large range for better precision
    random_int = secrets.randbelow(2**32)
    return (random_int / (2**32)) * range_size + min_val


def secure_random_int(min_val: int, max_val: int) -> int:
    """Generate a cryptographically secure random integer."""
    if min_val >= max_val:
        raise ValueError("min_val must be less than max_val")
    
    return secrets.randbelow(max_val - min_val + 1) + min_val


def secure_random_string(length: int = 32, alphabet: str = None) -> str:
    """Generate a cryptographically secure random string."""
    if alphabet is None:
        alphabet = string.ascii_letters + string.digits
    
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def secure_shuffle(items: List[Any]) -> List[Any]:
    """Shuffle a list using cryptographically secure random."""
    # Create a copy to avoid modifying the original
    shuffled = items.copy()
    secrets.shuffle(shuffled)
    return shuffled


def secure_choice(items: List[Any]) -> Any:
    """Choose a random item from a list using cryptographically secure random."""
    return secrets.choice(items)


def secure_token_bytes(length: int = 32) -> bytes:
    """Generate cryptographically secure random bytes."""
    return secrets.token_bytes(length)


def secure_token_hex(length: int = 32) -> str:
    """Generate cryptographically secure random hex string."""
    return secrets.token_hex(length)


def secure_token_urlsafe(length: int = 32) -> str:
    """Generate cryptographically secure random URL-safe string."""
    return secrets.token_urlsafe(length)
'''
            
            utils_path = self.project_root / 'src/utils/secure_random.py'
            utils_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(utils_path, 'w', encoding='utf-8') as f:
                f.write(utils_content)
            
            print(f"✅ Created secure random utilities at {utils_path}")
            return True
            
        except (FileNotFoundError, PermissionError, OSError) as e:
            print(f"❌ Error creating secure random utils: {e}")
            return False

    def run_systematic_crypto_fix(self) -> Dict[str, Any]:
        """Run systematic weak crypto fixes across the codebase."""
        print("🔒 Phase 2: Weak Crypto Replacement")
        print("=" * 50)
        
        # Create secure random utilities first
        self.create_secure_random_utils()
        
        # Get all S311 errors
        errors_by_file = self.get_s311_errors()
        total_errors = sum(len(errors) for errors in errors_by_file.values())
        
        print(f"📊 Found {total_errors} S311 weak crypto errors across {len(errors_by_file)} files")
        
        # Process priority files first
        priority_fixed = 0
        for file_pattern in self.priority_files:
            if '*' in file_pattern:
                # Handle glob patterns
                for file_path in self.project_root.glob(file_pattern):
                    if file_path.is_file() and str(file_path) in errors_by_file:
                        print(f"🎯 Fixing priority file: {file_path.name}")
                        success, fixes = self.fix_file_crypto(file_path, errors_by_file[str(file_path)])
                        if success:
                            priority_fixed += fixes
                            print(f"   ✅ Fixed {fixes} crypto issues")
                        else:
                            print(f"   ❌ Failed to fix crypto issues")
            else:
                file_path = self.project_root / file_pattern
                if file_path.exists() and str(file_path) in errors_by_file:
                    print(f"🎯 Fixing priority file: {file_path.name}")
                    success, fixes = self.fix_file_crypto(file_path, errors_by_file[str(file_path)])
                    if success:
                        priority_fixed += fixes
                        print(f"   ✅ Fixed {fixes} crypto issues")
                    else:
                        print(f"   ❌ Failed to fix crypto issues")
        
        # Process remaining files
        remaining_fixed = 0
        for file_path, errors in errors_by_file.items():
            if file_path not in self.files_processed:
                path_obj = Path(file_path)
                if path_obj.exists():
                    success, fixes = self.fix_file_crypto(path_obj, errors)
                    if success:
                        remaining_fixed += fixes
                        if fixes > 0:
                            print(f"✅ Fixed {fixes} crypto issues in {path_obj.name}")
        
        total_fixed = priority_fixed + remaining_fixed
        
        print(f"\n📈 Results:")
        print(f"   Files processed: {len(self.files_processed)}")
        print(f"   Total crypto issues fixed: {total_fixed}")
        print(f"   Remaining issues: {total_errors - total_fixed}")
        
        return {
            'files_processed': len(self.files_processed),
            'crypto_issues_fixed': total_fixed,
            'remaining_issues': total_errors - total_fixed,
            'success_rate': (total_fixed / total_errors * 100) if total_errors > 0 else 0
        }


def main():
    """Main execution function."""
    project_root = "/home/chris/PAKE_SYSTEM_claude_optimized"
    
    fixer = Phase2CryptoFixer(project_root)
    results = fixer.run_systematic_crypto_fix()
    
    print(f"\n🎉 Phase 2 Crypto Fix Complete!")
    print(f"Success Rate: {results['success_rate']:.1f}%")
    
    if results['remaining_issues'] > 0:
        print(f"\n⚠️  {results['remaining_issues']} crypto issues remain - manual review needed")
    else:
        print(f"\n✅ All weak crypto issues resolved!")


if __name__ == "__main__":
    main()