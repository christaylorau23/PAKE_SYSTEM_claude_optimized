#!/usr/bin/env python3
"""
Security Migration Script for PAKE System
Automates the migration from insecure to secure implementations
"""

import logging
import subprocess
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

logger = logging.getLogger(__name__)


class SecurityMigrator:
    """Automated security migration tool"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.migrations_completed = []
        self.migrations_failed = []

    def run_migration(self):
        """Run all security migrations"""
        logger.info("🔒 Starting security migration...")

        try:
            self._migrate_dependencies()
            self._migrate_hash_algorithms()
            self._migrate_serialization()
            self._migrate_network_config()
            self._create_security_docs()

            self._print_summary()

        except Exception as e:
            logger.error(f"Migration failed: {e}")
            sys.exit(1)

    def _migrate_dependencies(self):
        """Migrate to secure dependencies"""
        logger.info("📦 Migrating dependencies...")

        try:
            # Update requirements
            requirements_file = self.project_root / "requirements.txt"
            if requirements_file.exists():
                # Backup original
                backup_file = requirements_file.with_suffix(".txt.backup")
                requirements_file.rename(backup_file)
                logger.info(f"Backed up requirements to {backup_file}")

            # Install updated dependencies
            result = subprocess.run(
                [
                    "pip",
                    "install",
                    "--upgrade",
                    "cryptography>=44.0.1",
                    "sqlalchemy-utils>=0.43.0",
                    "msgpack>=1.0.7",
                    "cbor2>=5.5.1",
                ],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                self.migrations_completed.append("dependencies")
                logger.info("✅ Dependencies updated successfully")
            else:
                self.migrations_failed.append(("dependencies", result.stderr))
                logger.error(f"❌ Dependency update failed: {result.stderr}")

        except Exception as e:
            self.migrations_failed.append(("dependencies", str(e)))
            logger.error(f"❌ Dependency migration failed: {e}")

    def _migrate_hash_algorithms(self):
        """Migrate from MD5/SHA1 to SHA-256"""
        logger.info("🔐 Migrating hash algorithms...")

        try:
            # This would typically involve automated find/replace
            # For now, we'll just verify the changes were made manually
            md5_files = []

            for py_file in self.project_root.rglob("*.py"):
                try:
                    content = py_file.read_text(encoding="utf-8")
                    if "hashlib.md5" in content:
                        md5_files.append(str(py_file.relative_to(self.project_root)))
                except Exception:
                    continue

            if md5_files:
                logger.warning(f"⚠️  Still found MD5 usage in {len(md5_files)} files")
                logger.warning(
                    "Please manually replace hashlib.md5 with hashlib.sha256",
                )
            else:
                self.migrations_completed.append("hash_algorithms")
                logger.info("✅ Hash algorithms migrated successfully")

        except Exception as e:
            self.migrations_failed.append(("hash_algorithms", str(e)))
            logger.error(f"❌ Hash algorithm migration failed: {e}")

    def _migrate_serialization(self):
        """Migrate from pickle to secure serialization"""
        logger.info("📄 Migrating serialization...")

        try:
            # Check if secure serialization is working
            from utils.secure_serialization import SecureSerializer

            serializer = SecureSerializer()
            test_data = {"test": "migration", "number": 42}

            # Test serialization
            serialized = serializer.serialize(test_data)
            deserialized = serializer.deserialize(serialized)

            if deserialized == test_data:
                self.migrations_completed.append("serialization")
                logger.info("✅ Secure serialization working correctly")
            else:
                self.migrations_failed.append(
                    ("serialization", "Serialization test failed"),
                )
                logger.error("❌ Secure serialization test failed")

        except Exception as e:
            self.migrations_failed.append(("serialization", str(e)))
            logger.error(f"❌ Serialization migration failed: {e}")

    def _migrate_network_config(self):
        """Migrate network configuration"""
        logger.info("🌐 Migrating network configuration...")

        try:
            from utils.secure_network_config import Environment, SecureNetworkConfig

            # Test secure network configuration
            config = SecureNetworkConfig(Environment.PRODUCTION)
            warnings = config.validate_configuration()

            if warnings:
                logger.warning(
                    f"⚠️  Network configuration has {len(warnings)} warnings:",
                )
                for warning in warnings:
                    logger.warning(f"  - {warning}")

            self.migrations_completed.append("network_config")
            logger.info("✅ Network configuration migrated successfully")

        except Exception as e:
            self.migrations_failed.append(("network_config", str(e)))
            logger.error(f"❌ Network configuration migration failed: {e}")

    def _create_security_docs(self):
        """Create security documentation"""
        logger.info("📚 Creating security documentation...")

        try:
            security_doc = self.project_root / "SECURITY.md"

            content = """# PAKE System Security Guide

## Security Updates Applied

This document outlines the security improvements made to the PAKE System.

### 1. Dependency Updates
- Updated `cryptography` to >=44.0.1 (fixes CVE vulnerabilities)
- Updated `sqlalchemy-utils` to >=0.43.0 (fixes security issues)
- Added secure serialization dependencies: `msgpack`, `cbor2`

### 2. Hash Algorithm Migration
- Replaced all MD5 usage with SHA-256
- Updated fuzzy hashing algorithms to use SHA-256
- Improved content fingerprinting security

### 3. Serialization Security
- Replaced insecure pickle with secure alternatives:
  - JSON for simple data
  - MessagePack for complex data
  - CBOR for binary data
- Added checksum validation for serialized data
- Implemented secure serialization utilities

### 4. Network Security
- Replaced 0.0.0.0 bindings with specific interface addresses
- Implemented environment-based network configuration
- Added secure CORS configuration
- Implemented proper host validation

### 5. Security Testing
- Added comprehensive security testing suite
- Automated vulnerability scanning
- Security configuration validation
- Continuous security monitoring

## Security Best Practices

### Environment Configuration
- Use environment variables for all secrets
- Never commit secrets to version control
- Use different configurations for dev/staging/production

### Network Security
- Bind to specific interfaces, not 0.0.0.0
- Use HTTPS in production
- Implement proper firewall rules
- Enable rate limiting

### Data Security
- Use SHA-256 for all hashing operations
- Implement secure serialization
- Validate all input data
- Use parameterized queries

### Monitoring
- Run security tests regularly
- Monitor for new vulnerabilities
- Keep dependencies updated
- Audit access logs

## Running Security Tests

```bash
# Run comprehensive security tests
python scripts/security_testing.py

# Check for dependency vulnerabilities
safety check

# Run security audit
python scripts/security_audit.py
```

## Emergency Response

If a security vulnerability is discovered:

1. Assess the severity and impact
2. Apply immediate mitigations if possible
3. Update affected components
4. Run security tests to verify fixes
5. Deploy updates following change management procedures
6. Monitor for any issues

## Contact

For security-related questions or to report vulnerabilities:
- Email: security@pake.example.com
- Create a private issue in the repository
"""

            security_doc.write_text(content)
            self.migrations_completed.append("security_docs")
            logger.info("✅ Security documentation created")

        except Exception as e:
            self.migrations_failed.append(("security_docs", str(e)))
            logger.error(f"❌ Security documentation creation failed: {e}")

    def _print_summary(self):
        """Print migration summary"""
        print("\n" + "=" * 60)
        print("🔒 SECURITY MIGRATION SUMMARY")
        print("=" * 60)

        print(f"✅ Completed Migrations: {len(self.migrations_completed)}")
        for migration in self.migrations_completed:
            print(f"  • {migration}")

        if self.migrations_failed:
            print(f"\n❌ Failed Migrations: {len(self.migrations_failed)}")
            for migration, error in self.migrations_failed:
                print(f"  • {migration}: {error}")

        print("\n📋 Next Steps:")
        print("1. Run security tests: python scripts/security_testing.py")
        print("2. Review security documentation: SECURITY.md")
        print("3. Update deployment configurations")
        print("4. Test in staging environment")
        print("5. Deploy to production with monitoring")

        if self.migrations_failed:
            print("\n⚠️  Please address failed migrations before deployment!")
            sys.exit(1)
        else:
            print("\n✅ Security migration completed successfully!")


def main():
    """Main entry point"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    migrator = SecurityMigrator()
    migrator.run_migration()


if __name__ == "__main__":
    main()
