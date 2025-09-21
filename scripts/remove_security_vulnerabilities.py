#!/usr/bin/env python3
"""
Security Vulnerability Removal Script
Removes all hardcoded REDACTED_SECRET fallbacks and weak secrets from the codebase

CRITICAL: This script removes security vulnerabilities identified in the audit
"""

import os
import re
import sys
from pathlib import Path


class SecurityVulnerabilityRemover:
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.vulnerabilities_found = 0
        self.files_modified = 0

        # Patterns to remove (CRITICAL security vulnerabilities)
        self.vulnerability_patterns = [
            # Hardcoded weak REDACTED_SECRET fallbacks
            (
                r'process\.env\.PAKE_WEAK_PASSWORD\s*\|\|\s*[\'"]SECURE_WEAK_PASSWORD_REQUIRED[\'"]',
                "CRITICAL: Remove PAKE_WEAK_PASSWORD fallback",
            ),
            # Database REDACTED_SECRET fallbacks
            (
                r'process\.env\.DB_PASSWORD\s*\|\|\s*[\'"]SECURE_DB_PASSWORD_REQUIRED[\'"]',
                "CRITICAL: Remove DB_PASSWORD fallback",
            ),
            # API key fallbacks
            (
                r'process\.env\.PAKE_API_KEY\s*\|\|\s*[\'"]SECURE_API_KEY_REQUIRED[\'"]',
                "CRITICAL: Remove PAKE_API_KEY fallback",
            ),
            # JWT secret fallbacks
            (
                r'process\.env\.JWT_SECRET\s*\|\|\s*[\'"]SECURE_JWT_SECRET_REQUIRED[\'"]',
                "CRITICAL: Remove JWT_SECRET fallback",
            ),
            # Generic secret fallbacks
            (
                r'process\.env\.PAKE_SECRET_KEY\s*\|\|\s*[\'"]SECURE_SECRET_KEY_REQUIRED[\'"]',
                "CRITICAL: Remove PAKE_SECRET_KEY fallback",
            ),
            # Weak JWT secret
            (
                r'process\.env\.JWT_SECRET\s*\|\|\s*[\'"]your-super-secret-jwt-key-change-in-production[\'"]',
                "CRITICAL: Remove weak JWT secret fallback",
            ),
        ]

    def find_vulnerable_files(self) -> list[Path]:
        """Find all files containing security vulnerabilities"""
        vulnerable_files = []

        # Search for TypeScript/JavaScript files
        for pattern in ["**/*.ts", "**/*.js", "**/*.tsx", "**/*.jsx"]:
            for file_path in self.project_root.glob(pattern):
                if self.contains_vulnerabilities(file_path):
                    vulnerable_files.append(file_path)

        return vulnerable_files

    def contains_vulnerabilities(self, file_path: Path) -> bool:
        """Check if file contains security vulnerabilities"""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            for pattern, _ in self.vulnerability_patterns:
                if re.search(pattern, content):
                    return True
            return False
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return False

    def remove_vulnerabilities_from_file(self, file_path: Path) -> bool:
        """Remove security vulnerabilities from a single file"""
        try:
            with open(file_path, encoding="utf-8") as f:
                original_content = f.read()

            modified_content = original_content
            vulnerabilities_in_file = 0

            for pattern, description in self.vulnerability_patterns:
                matches = re.findall(pattern, modified_content)
                if matches:
                    vulnerabilities_in_file += len(matches)
                    print(f"  Found {len(matches)} instances of: {description}")

                    # Remove the fallback pattern, keeping only the environment variable
                    modified_content = re.sub(
                        pattern,
                        "process.env." + self.extract_env_var(pattern),
                        modified_content,
                    )

            if vulnerabilities_in_file > 0:
                # Write the modified content back
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(modified_content)

                self.vulnerabilities_found += vulnerabilities_in_file
                self.files_modified += 1
                print(
                    f"✅ Fixed {vulnerabilities_in_file} vulnerabilities in {file_path}",
                )
                return True

            return False

        except Exception as e:
            print(f"❌ Error processing {file_path}: {e}")
            return False

    def extract_env_var(self, pattern: str) -> str:
        """Extract environment variable name from pattern"""
        match = re.search(r"process\.env\.([A-Z_]+)", pattern)
        return match.group(1) if match else "UNKNOWN"

    def create_backup(self, file_path: Path) -> Path:
        """Create backup of file before modification"""
        backup_path = file_path.with_suffix(file_path.suffix + ".security_backup")
        try:
            with open(file_path, encoding="utf-8") as src:
                with open(backup_path, "w", encoding="utf-8") as dst:
                    dst.write(src.read())
            return backup_path
        except Exception as e:
            print(f"Warning: Could not create backup for {file_path}: {e}")
            return file_path

    def run(self):
        """Main execution method"""
        print("🔒 PAKE System Security Vulnerability Removal")
        print("=" * 50)
        print("CRITICAL: Removing hardcoded REDACTED_SECRET fallbacks and weak secrets")
        print()

        # Find all vulnerable files
        vulnerable_files = self.find_vulnerable_files()

        if not vulnerable_files:
            print("✅ No security vulnerabilities found!")
            return

        print(f"🚨 Found {len(vulnerable_files)} files with security vulnerabilities:")
        for file_path in vulnerable_files:
            print(f"  - {file_path}")
        print()

        # Process each vulnerable file
        for file_path in vulnerable_files:
            print(f"Processing: {file_path}")

            # Create backup
            backup_path = self.create_backup(file_path)
            if backup_path != file_path:
                print(f"  Backup created: {backup_path}")

            # Remove vulnerabilities
            if self.remove_vulnerabilities_from_file(file_path):
                print("  ✅ Security vulnerabilities removed")
            else:
                print("  ⚠️  No changes made")
            print()

        # Summary
        print("=" * 50)
        print("SECURITY VULNERABILITY REMOVAL SUMMARY")
        print("=" * 50)
        print(f"Files processed: {len(vulnerable_files)}")
        print(f"Files modified: {self.files_modified}")
        print(f"Vulnerabilities removed: {self.vulnerabilities_found}")
        print()

        if self.vulnerabilities_found > 0:
            print("✅ CRITICAL security vulnerabilities have been removed!")
            print("⚠️  IMPORTANT: Update your environment variables with proper secrets")
            print("⚠️  The application will now fail-fast if secrets are missing")
        else:
            print("ℹ️  No vulnerabilities were found to remove")


def main():
    if len(sys.argv) != 2:
        print("Usage: python remove_security_vulnerabilities.py <project_root>")
        sys.exit(1)

    project_root = sys.argv[1]
    if not os.path.exists(project_root):
        print(f"Error: Project root '{project_root}' does not exist")
        sys.exit(1)

    remover = SecurityVulnerabilityRemover(project_root)
    remover.run()


if __name__ == "__main__":
    main()
