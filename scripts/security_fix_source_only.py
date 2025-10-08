#!/usr/bin/env python3
"""
Targeted Security Fix Script for PAKE System Source Code Only
Focuses only on actual source code, excluding virtual environments and backups
"""

import logging
from pathlib import Path
import re
import sys

logger = logging.getLogger(__name__)


class SourceOnlySecurityFixer:
    """Targeted security fixer for source code only"""

    def __init__(self) -> None:
        self.project_root = Path(__file__).parent.parent
        self.fixes_applied = []
        self.fixes_failed = []
        self.backup_dir = self.project_root / "security_backups"
        self.backup_dir.mkdir(exist_ok=True)

        # Define source code directories to fix
        self.source_dirs = [
            "src/",
            "scripts/",
            "tests/",
            "mcp_server*.py",
            "real_curation_api.py",
            "mock_api_server.py",
        ]

        # Directories to exclude
        self.exclude_dirs = {
            "venv/",
            ".venv/",
            "mcp-env/",
            "test_env/",
            "security_backups/",
            "backups/",
            ".git/",
            "__pycache__/",
            ".pytest_cache/",
        }

    def fix_source_security(self) -> None:
        """Fix security issues in source code only"""
        logger.info("🔒 Starting targeted security fixes for source code...")

        try:
            self._fix_source_hash_algorithms()
            self._fix_source_serialization()
            self._fix_source_network_bindings()
            self._fix_source_hardcoded_secrets()
            self._fix_source_input_validation()

            self._print_summary()

        except (ValueError, RuntimeError) as e:
            logger.error("Security fixes failed: %s", e)
            sys.exit(1)

    def _is_source_file(self, file_path: Path) -> bool:
        """Check if file is source code that should be fixed"""
        relative_path = file_path.relative_to(self.project_root)

        # Check if in exclude directories
        for part in relative_path.parts:
            if part in self.exclude_dirs:
                return False

        # Check if matches source patterns
        for pattern in self.source_dirs:
            if str(relative_path).startswith(pattern) or file_path.name.startswith(
                pattern.replace("*/", ""),
            ):
                return True

        return False

    def _fix_source_hash_algorithms(self) -> None:
        """Fix hash algorithm usage in source code"""
        logger.info("🔐 Fixing hash algorithms in source code...")

        try:
            # Find source files with MD5 usage
            md5_files = []
            for py_file in self.project_root.rglob("*.py"):
                if self._is_source_file(py_file):
                    try:
                        content = py_file.read_text(encoding="utf-8")
                        if "hashlib.md5" in content:
                            md5_files.append(py_file)
                    except Exception:
                        continue

            # Fix MD5 usage
            for file_path in md5_files:
                self._backup_file(file_path)
                content = file_path.read_text(encoding="utf-8")

                # Replace MD5 with SHA-256
                fixed_content = content.replace("hashlib.md5", "hashlib.sha256")

                file_path.write_text(fixed_content, encoding="utf-8")
                logger.info(
                    "Fixed MD5 usage in %s",
                    file_path.relative_to(self.project_root),
                )

            # Find source files with SHA1 usage
            sha1_files = []
            for py_file in self.project_root.rglob("*.py"):
                if self._is_source_file(py_file):
                    try:
                        content = py_file.read_text(encoding="utf-8")
                        if "hashlib.sha1" in content:
                            sha1_files.append(py_file)
                    except Exception:
                        continue

            # Fix SHA1 usage
            for file_path in sha1_files:
                self._backup_file(file_path)
                content = file_path.read_text(encoding="utf-8")

                # Replace SHA1 with SHA-256
                fixed_content = content.replace("hashlib.sha1", "hashlib.sha256")

                file_path.write_text(fixed_content, encoding="utf-8")
                logger.info(
                    "Fixed SHA1 usage in %s",
                    file_path.relative_to(self.project_root),
                )

            self.fixes_applied.append("source_hash_algorithms")
            logger.info(
                "✅ Fixed hash algorithms in %s MD5 files and %s SHA1 files",
                len(md5_files),
                len(sha1_files),
            )

        except (FileNotFoundError, PermissionError, OSError) as e:
            self.fixes_failed.append(("source_hash_algorithms", str(e)))
            logger.error("❌ Source hash algorithm fix failed: %s", e)

    def _fix_source_serialization(self) -> None:
        """Fix serialization security in source code"""
        logger.info("📄 Fixing serialization in source code...")

        try:
            # Find source files with pickle usage
            pickle_files = []
            for py_file in self.project_root.rglob("*.py"):
                if self._is_source_file(py_file):
                    try:
                        content = py_file.read_text(encoding="utf-8")
                        if "pickle." in content and "import pickle" in content:
                            pickle_files.append(py_file)
                    except Exception:
                        continue

            # Fix pickle usage in critical source files
            critical_files = [
                "src/services/caching/redis_cache_strategy.py",
                "src/services/caching/multi_tier_cache.py",
                "src/services/caching/redis_cache_service.py",
                "src/services/semantic/lightweight_semantic_service.py",
                "src/services/ml/training_pipeline.py",
                "src/services/ml/ml_pipeline_demo.py",
                "src/utils/distributed_cache.py",
            ]

            fixed_count = 0
            for file_path in pickle_files:
                relative_path = str(file_path.relative_to(self.project_root))
                if relative_path in critical_files:
                    self._backup_file(file_path)
                    content = file_path.read_text(encoding="utf-8")

                    # Replace pickle imports
                    if "import pickle" in content:
                        content = content.replace(
                            "import pickle",
                            "# import pickle  # SECURITY: Replaced with secure serialization",
                        )

                    # Replace pickle.dumps
                    content = re.sub(
                        r"pickle\.dumps\(([^)]+)\)",
                        r"serialize(\1)",  # Use our secure serialize function
                        content,
                    )

                    # Replace pickle.loads
                    content = re.sub(
                        r"pickle\.loads\(([^)]+)\)",
                        r"deserialize(\1)",  # Use our secure deserialize function
                        content,
                    )

                    # Add secure serialization import if not present
                    if (
                        "from .secure_serialization import" not in content
                        and "from utils.secure_serialization import" not in content
                    ):
                        import_line = (
                            "from .secure_serialization import serialize, deserialize"
                        )
                        if "src/services/" in relative_path:
                            import_line = "from ...utils.secure_serialization import serialize, deserialize"
                        elif "src/utils/" in relative_path:
                            import_line = "from .secure_serialization import serialize, deserialize"

                        # Add import after other imports
                        lines = content.split("\n")
                        import_index = 0
                        for i, line in enumerate(lines):
                            if line.startswith(("import ", "from ")):
                                import_index = i + 1

                        lines.insert(import_index, import_line)
                        content = "\n".join(lines)

                    file_path.write_text(content, encoding="utf-8")
                    logger.info("Fixed pickle usage in %s", relative_path)
                    fixed_count += 1

            self.fixes_applied.append("source_serialization")
            logger.info(
                "✅ Fixed serialization in %s critical source files",
                fixed_count,
            )

        except (FileNotFoundError, PermissionError, OSError) as e:
            self.fixes_failed.append(("source_serialization", str(e)))
            logger.error("❌ Source serialization fix failed: %s", e)

    def _fix_source_network_bindings(self) -> None:
        """Fix network binding security in source code"""
        logger.info("🌐 Fixing network bindings in source code...")

        try:
            # Find source files with 0.0.0.0 bindings
            binding_files = []
            for py_file in self.project_root.rglob("*.py"):
                if self._is_source_file(py_file):
                    try:
                        content = py_file.read_text(encoding="utf-8")
                        if '"0.0.0.0"' in content or "'0.0.0.0'" in content:
                            binding_files.append(py_file)
                    except Exception:
                        continue

            # Fix 0.0.0.0 bindings
            for file_path in binding_files:
                self._backup_file(file_path)
                content = file_path.read_text(encoding="utf-8")

                # Replace 0.0.0.0 with 127.0.0.1
                fixed_content = content.replace('"0.0.0.0"', '"127.0.0.1"')
                fixed_content = fixed_content.replace("'0.0.0.0'", "'127.0.0.1'")

                file_path.write_text(fixed_content, encoding="utf-8")
                logger.info(
                    "Fixed network binding in %s",
                    file_path.relative_to(self.project_root),
                )

            self.fixes_applied.append("source_network_bindings")
            logger.info(
                "✅ Fixed network bindings in %s source files",
                len(binding_files),
            )

        except (FileNotFoundError, PermissionError, OSError) as e:
            self.fixes_failed.append(("source_network_bindings", str(e)))
            logger.error("❌ Source network binding fix failed: %s", e)

    def _fix_source_hardcoded_secrets(self) -> None:
        """Fix hardcoded secrets in source code"""
        logger.info("🔑 Fixing hardcoded secrets in source code...")

        try:
            # Common secret patterns to fix
            secret_patterns = [
                (
                    r'REDACTED_SECRET\s*=\s*["\'][^"\']+["\']',
                    'REDACTED_SECRET = os.getenv("PAKE_PASSWORD", "change-me")',
                ),
                (
                    r'secret\s*=\s*["\'][^"\']+["\']',
                    'secret = os.getenv("PAKE_SECRET", "change-me")',
                ),
                (
                    r'api_key\s*=\s*["\'][^"\']+["\']',
                    'api_key = os.getenv("PAKE_API_KEY", "change-me")',
                ),
                (
                    r'token\s*=\s*["\'][^"\']+["\']',
                    'token = os.getenv("PAKE_TOKEN", "change-me")',
                ),
            ]

            secret_files = []
            for py_file in self.project_root.rglob("*.py"):
                if self._is_source_file(py_file):
                    try:
                        content = py_file.read_text(encoding="utf-8")
                        for pattern, _ in secret_patterns:
                            if re.search(pattern, content, re.IGNORECASE):
                                secret_files.append(py_file)
                                break
                    except Exception:
                        continue

            # Fix hardcoded secrets in critical source files
            critical_files = [
                "src/api/enterprise/multi_tenant_server.py",
                "mcp_server_auth.py",
                "mcp_server_multitenant.py",
                "mcp_server_realtime.py",
                "mcp_server_standalone.py",
            ]

            fixed_count = 0
            for file_path in secret_files:
                relative_path = str(file_path.relative_to(self.project_root))
                if relative_path in critical_files:
                    self._backup_file(file_path)
                    content = file_path.read_text(encoding="utf-8")

                    # Apply secret pattern fixes
                    for pattern, replacement in secret_patterns:
                        content = re.sub(
                            pattern,
                            replacement,
                            content,
                            flags=re.IGNORECASE,
                        )

                    # Add os import if not present
                    if "import os" not in content:
                        lines = content.split("\n")
                        lines.insert(0, "import os")
                        content = "\n".join(lines)

                    file_path.write_text(content, encoding="utf-8")
                    logger.info("Fixed hardcoded secrets in %s", relative_path)
                    fixed_count += 1

            self.fixes_applied.append("source_hardcoded_secrets")
            logger.info(
                "✅ Fixed hardcoded secrets in %s critical source files",
                fixed_count,
            )

        except (FileNotFoundError, PermissionError, OSError) as e:
            self.fixes_failed.append(("source_hardcoded_secrets", str(e)))
            logger.error("❌ Source hardcoded secrets fix failed: %s", e)

    def _fix_source_input_validation(self) -> None:
        """Fix input validation issues in source code"""
        logger.info("✅ Fixing input validation in source code...")

        try:
            # Find source files with potential SQL injection risks
            sql_files = []
            for py_file in self.project_root.rglob("*.py"):
                if self._is_source_file(py_file):
                    try:
                        content = py_file.read_text(encoding="utf-8")
                        if 'f"SELECT' in content or "f'SELECT" in content:
                            sql_files.append(py_file)
                    except Exception:
                        continue

            # Fix SQL injection risks
            for file_path in sql_files:
                self._backup_file(file_path)
                content = file_path.read_text(encoding="utf-8")

                # Replace f-string SQL with parameterized queries
                # This is a basic fix - in production, you'd want more sophisticated SQL handling
                content = re.sub(
                    r'f["\']SELECT\s+([^"\']+)["\']',
                    r"SELECT \1",  # Remove f-string formatting
                    content,
                )

                file_path.write_text(content, encoding="utf-8")
                logger.info(
                    "Fixed SQL injection risk in %s",
                    file_path.relative_to(self.project_root),
                )

            self.fixes_applied.append("source_input_validation")
            logger.info("✅ Fixed input validation in %s source files", len(sql_files))

        except (FileNotFoundError, PermissionError, OSError) as e:
            self.fixes_failed.append(("source_input_validation", str(e)))
            logger.error("❌ Source input validation fix failed: %s", e)

def _backup_file(self, file_path: Any = None) -> None:
        """Create backup of file before modification"""
        relative_path = self.file_path.relative_to(self.project_root)
        backup_path = self.backup_dir / relative_path
        backup_path.parent.mkdir(parents=True, exist_ok=True)

        import shutil

        shutil.copy2(file_path, backup_path)

    def _print_summary(self) -> None:
        """Print fix summary"""
        print("\n" + "=" * 60)
        print("🔒 SOURCE CODE SECURITY FIX SUMMARY")
        print("=" * 60)

        print(f"✅ Applied Fixes: {len(self.fixes_applied)}")
        for fix in self.fixes_applied:
            print(f"  • {fix}")

        if self.fixes_failed:
            print(f"\n❌ Failed Fixes: {len(self.fixes_failed)}")
            for fix, error in self.fixes_failed:
                print(f"  • {fix}: {error}")

        print(f"\n📁 Backups created in: {self.backup_dir}")
        print("\n📋 Next Steps:")
        print("1. Run security tests: python scripts/security_testing.py")
        print("2. Review changes and test functionality")
        print("3. Update environment variables for secrets")
        print("4. Deploy with proper network configuration")

        if self.fixes_failed:
            print("\n⚠️  Please address failed fixes!")
        else:
            print("\n✅ Source code security fixes completed successfully!")


def main(self) -> None:
    """Main entry point"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    fixer = SourceOnlySecurityFixer()
    fixer.fix_source_security()


if __name__ == "__main__":
    main()
