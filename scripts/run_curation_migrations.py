#!/usr/bin/env python3
"""
Intelligent Content Curation - Database Migration Runner

This script runs all database migrations for the curation system in the correct order.
It ensures that the database schema is properly set up for the curation functionality.

Usage:
    python scripts/run_curation_migrations.py [--dry-run] [--rollback]

Environment Variables:
    DATABASE_URL: PostgreSQL connection string
    CURATION_DB_HOST: Database host (default: localhost)
    CURATION_DB_PORT: Database port (default: 5432)
    CURATION_DB_NAME: Database name (default: pake_curation)
    CURATION_DB_USER: Database user
    CURATION_DB_PASSWORD: Database REDACTED_SECRET
"""

import argparse
import asyncio
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import asyncpg

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("logs/curation_migrations.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class MigrationRunner:
    """Handles database migrations for the curation system."""

    def __init__(self, connection_config: dict[str, Any]):
        self.connection_config = connection_config
        self.migrations_dir = Path(__file__).parent / "migrations"
        self.migration_files = [
            "001_content_items.sql",
            "002_user_profiles.sql",
            "003_user_interactions.sql",
            "004_content_sources.sql",
            "005_recommendations.sql",
            "006_topic_categories.sql",
            "007_user_feedback.sql",
        ]

    async def create_connection(self) -> asyncpg.Connection:
        """Create a connection to the PostgreSQL database."""
        try:
            if "database_url" in self.connection_config:
                conn = await asyncpg.connect(self.connection_config["database_url"])
            else:
                conn = await asyncpg.connect(
                    host=self.connection_config["host"],
                    port=self.connection_config["port"],
                    database=self.connection_config["database"],
                    user=self.connection_config["user"],
                    REDACTED_SECRET=self.connection_config["REDACTED_SECRET"],
                )
            logger.info("Successfully connected to database")
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    async def create_migration_table(self, conn: asyncpg.Connection) -> None:
        """Create the migration tracking table if it doesn't exist."""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS curation_migrations (
            id SERIAL PRIMARY KEY,
            filename VARCHAR(255) NOT NULL UNIQUE,
            applied_at TIMESTAMP NOT NULL DEFAULT NOW(),
            checksum VARCHAR(64),
            execution_time_ms INTEGER
        );

        CREATE INDEX IF NOT EXISTS idx_curation_migrations_filename
        ON curation_migrations (filename);
        """

        try:
            await conn.execute(create_table_sql)
            logger.info("Migration tracking table ready")
        except Exception as e:
            logger.error(f"Failed to create migration table: {e}")
            raise

    async def get_applied_migrations(self, conn: asyncpg.Connection) -> list[str]:
        """Get list of already applied migrations."""
        try:
            rows = await conn.fetch(
                "SELECT filename FROM curation_migrations ORDER BY applied_at",
            )
            return [row["filename"] for row in rows]
        except Exception as e:
            logger.error(f"Failed to fetch applied migrations: {e}")
            return []

    def calculate_checksum(self, content: str) -> str:
        """Calculate MD5 checksum of migration content."""
        import hashlib

        return hashlib.sha256(content.encode()).hexdigest()

    async def execute_migration(
        self,
        conn: asyncpg.Connection,
        filename: str,
        dry_run: bool = False,
    ) -> bool:
        """Execute a single migration file."""
        migration_file = self.migrations_dir / filename

        if not migration_file.exists():
            logger.error(f"Migration file not found: {migration_file}")
            return False

        try:
            with open(migration_file) as f:
                content = f.read()

            checksum = self.calculate_checksum(content)

            if dry_run:
                logger.info(f"DRY RUN: Would execute migration {filename}")
                logger.info(f"Content preview: {content[:200]}...")
                return True

            logger.info(f"Executing migration: {filename}")
            start_time = datetime.now()

            # Execute migration within a transaction
            async with conn.transaction():
                await conn.execute(content)

                # Record migration as applied
                execution_time = int(
                    (datetime.now() - start_time).total_seconds() * 1000,
                )
                await conn.execute(
                    """
                    INSERT INTO curation_migrations (filename, checksum, execution_time_ms)
                    VALUES ($1, $2, $3)
                    """,
                    filename,
                    checksum,
                    execution_time,
                )

            logger.info(
                f"Successfully executed migration {filename} in {execution_time}ms",
            )
            return True

        except Exception as e:
            logger.error(f"Failed to execute migration {filename}: {e}")
            return False

    async def run_migrations(self, dry_run: bool = False) -> bool:
        """Run all pending migrations."""
        try:
            conn = await self.create_connection()

            # Ensure migration table exists
            await self.create_migration_table(conn)

            # Get already applied migrations
            applied_migrations = await self.get_applied_migrations(conn)

            # Find pending migrations
            pending_migrations = [
                filename
                for filename in self.migration_files
                if filename not in applied_migrations
            ]

            if not pending_migrations:
                logger.info("No pending migrations found")
                return True

            logger.info(f"Found {len(pending_migrations)} pending migrations")

            success = True
            for filename in pending_migrations:
                if not await self.execute_migration(conn, filename, dry_run):
                    success = False
                    break

            await conn.close()

            if success:
                if dry_run:
                    logger.info("DRY RUN: All migrations would execute successfully")
                else:
                    logger.info("All migrations executed successfully")
            else:
                logger.error("Migration execution failed")

            return success

        except Exception as e:
            logger.error(f"Migration process failed: {e}")
            return False

    async def rollback_migration(self, filename: str) -> bool:
        """Rollback a specific migration (if rollback script exists)."""
        rollback_file = self.migrations_dir / f"rollback_{filename}"

        if not rollback_file.exists():
            logger.error(f"No rollback script found for {filename}")
            return False

        try:
            conn = await self.create_connection()

            with open(rollback_file) as f:
                content = f.read()

            logger.info(f"Rolling back migration: {filename}")

            async with conn.transaction():
                await conn.execute(content)

                # Remove migration record
                await conn.execute(
                    "DELETE FROM curation_migrations WHERE filename = $1",
                    filename,
                )

            await conn.close()

            logger.info(f"Successfully rolled back migration {filename}")
            return True

        except Exception as e:
            logger.error(f"Failed to rollback migration {filename}: {e}")
            return False

    async def get_migration_status(self) -> dict[str, Any]:
        """Get current migration status."""
        try:
            conn = await self.create_connection()

            applied_migrations = await self.get_applied_migrations(conn)
            pending_migrations = [
                filename
                for filename in self.migration_files
                if filename not in applied_migrations
            ]

            # Get detailed information about applied migrations
            rows = await conn.fetch(
                """
                SELECT filename, applied_at, execution_time_ms
                FROM curation_migrations
                ORDER BY applied_at
            """,
            )

            await conn.close()

            return {
                "total_migrations": len(self.migration_files),
                "applied_count": len(applied_migrations),
                "pending_count": len(pending_migrations),
                "applied_migrations": [
                    {
                        "filename": row["filename"],
                        "applied_at": row["applied_at"].isoformat(),
                        "execution_time_ms": row["execution_time_ms"],
                    }
                    for row in rows
                ],
                "pending_migrations": pending_migrations,
            }

        except Exception as e:
            logger.error(f"Failed to get migration status: {e}")
            return {"error": str(e)}


def get_database_config() -> dict[str, Any]:
    """Get database connection configuration from environment variables."""
    # Check for full database URL first
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return {"database_url": database_url}

    # Individual connection parameters
    config = {
        "host": os.getenv("CURATION_DB_HOST", "localhost"),
        "port": int(os.getenv("CURATION_DB_PORT", "5432")),
        "database": os.getenv("CURATION_DB_NAME", "pake_curation"),
        "user": os.getenv("CURATION_DB_USER", "pake_user"),
        "REDACTED_SECRET": os.getenv("CURATION_DB_PASSWORD", ""),
    }

    if not config["REDACTED_SECRET"]:
        # Try to get from existing PAKE configuration
        config["REDACTED_SECRET"] = os.getenv("POSTGRES_PASSWORD", "pake_REDACTED_SECRET")
        config["database"] = os.getenv("POSTGRES_DB", "pake_system")

    return config


async def main():
    """Main entry point for the migration runner."""
    parser = argparse.ArgumentParser(description="Run curation database migrations")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be executed without running migrations",
    )
    parser.add_argument(
        "--rollback",
        type=str,
        metavar="FILENAME",
        help="Rollback a specific migration",
    )
    parser.add_argument("--status", action="store_true", help="Show migration status")

    args = parser.parse_args()

    # Load environment variables from .env files
    env_files = [".env", ".env.curation", ".env.local"]
    for env_file in env_files:
        if os.path.exists(env_file):
            with open(env_file) as f:
                for line in f:
                    if line.strip() and not line.startswith("#"):
                        key, value = line.strip().split("=", 1)
                        os.environ.setdefault(key, value)

    # Get database configuration
    db_config = get_database_config()

    # Create migration runner
    runner = MigrationRunner(db_config)

    try:
        if args.status:
            status = await runner.get_migration_status()
            if "error" in status:
                logger.error(f"Failed to get status: {status['error']}")
                sys.exit(1)

            print("\n=== Migration Status ===")
            print(f"Total migrations: {status['total_migrations']}")
            print(f"Applied: {status['applied_count']}")
            print(f"Pending: {status['pending_count']}")

            if status["applied_migrations"]:
                print("\nApplied migrations:")
                for migration in status["applied_migrations"]:
                    print(
                        f"  ✓ {migration['filename']} ({
                            migration['execution_time_ms']
                        }ms)",
                    )

            if status["pending_migrations"]:
                print("\nPending migrations:")
                for filename in status["pending_migrations"]:
                    print(f"  ○ {filename}")

        elif args.rollback:
            success = await runner.rollback_migration(args.rollback)
            sys.exit(0 if success else 1)

        else:
            success = await runner.run_migrations(dry_run=args.dry_run)
            sys.exit(0 if success else 1)

    except KeyboardInterrupt:
        logger.info("Migration process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)

    # Run the main function
    asyncio.run(main())
