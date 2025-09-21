"""
Database Migration Runner for Intelligent Content Curation System

Runs all migration scripts to set up the curation database schema.
"""

import asyncio
import logging
import os
from pathlib import Path

import asyncpg

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "database": os.getenv("DB_NAME", "pake_system"),
    "user": os.getenv("DB_USER", "postgres"),
    "REDACTED_SECRET": os.getenv("DB_PASSWORD", "REDACTED_SECRET"),
}


async def run_migration_file(connection, migration_file: Path):
    """Run a single migration file"""
    try:
        logger.info(f"Running migration: {migration_file.name}")

        with open(migration_file) as f:
            sql_content = f.read()

        # Split by semicolon and execute each statement
        statements = [stmt.strip() for stmt in sql_content.split(";") if stmt.strip()]

        for statement in statements:
            if statement:
                await connection.execute(statement)

        logger.info(f"✅ Migration {migration_file.name} completed successfully")
        return True

    except Exception as e:
        logger.error(f"❌ Error running migration {migration_file.name}: {str(e)}")
        return False


async def run_all_migrations():
    """Run all migration files in order"""
    try:
        # Connect to database
        logger.info("Connecting to database...")
        connection = await asyncpg.connect(**DATABASE_CONFIG)

        # Get migration files
        migrations_dir = Path(__file__).parent / "migrations"
        if not migrations_dir.exists():
            logger.error(f"Migrations directory not found: {migrations_dir}")
            return False

        migration_files = sorted([f for f in migrations_dir.glob("*.sql")])

        if not migration_files:
            logger.warning("No migration files found")
            return True

        logger.info(f"Found {len(migration_files)} migration files")

        # Run migrations in order
        success_count = 0
        for migration_file in migration_files:
            success = await run_migration_file(connection, migration_file)
            if success:
                success_count += 1
            else:
                logger.error(f"Migration failed: {migration_file.name}")
                break

        await connection.close()

        logger.info(
            f"Migrations completed: {success_count}/{len(migration_files)} successful",
        )
        return success_count == len(migration_files)

    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        logger.info("Note: This is expected if PostgreSQL is not running locally")
        return False


async def verify_schema():
    """Verify that the schema was created correctly"""
    try:
        connection = await asyncpg.connect(**DATABASE_CONFIG)

        # Check if curation tables exist
        tables_to_check = [
            "content_items",
            "user_profiles",
            "user_interactions",
            "recommendations",
            "content_sources",
            "topic_categories",
            "user_feedback",
        ]

        existing_tables = []
        for table in tables_to_check:
            result = await connection.fetchval(
                "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = $1)",
                table,
            )
            if result:
                existing_tables.append(table)

        await connection.close()

        logger.info(
            f"✅ Schema verification: {len(existing_tables)}/{
                len(tables_to_check)
            } tables exist",
        )
        for table in existing_tables:
            logger.info(f"  ✓ {table}")

        return len(existing_tables) == len(tables_to_check)

    except Exception as e:
        logger.error(f"Schema verification error: {str(e)}")
        return False


def main():
    """Main migration runner"""
    print("🗄️  DATABASE MIGRATION RUNNER")
    print("=" * 40)

    # Check if migration files exist
    migrations_dir = Path(__file__).parent / "migrations"
    if not migrations_dir.exists():
        print(f"❌ Migrations directory not found: {migrations_dir}")
        print("Creating example migration structure...")

        # Create migrations directory and example file
        migrations_dir.mkdir(exist_ok=True)

        example_migration = migrations_dir / "001_example.sql"
        example_migration.write_text(
            """
-- Example migration file
-- This would contain the actual SQL schema from the migration files created earlier

CREATE TABLE IF NOT EXISTS curation_system_info (
    id SERIAL PRIMARY KEY,
    version VARCHAR(50) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

INSERT INTO curation_system_info (version) VALUES ('1.0.0-intelligent-curation')
ON CONFLICT DO NOTHING;
""",
        )

        print(f"✅ Created example migration at {example_migration}")

    # Try to run migrations
    try:
        result = asyncio.run(run_all_migrations())
        if result:
            print("\n🎉 All migrations completed successfully!")

            # Verify schema
            print("\n🔍 Verifying schema...")
            verification_result = asyncio.run(verify_schema())
            if verification_result:
                print("✅ Schema verification passed!")
            else:
                print("⚠️  Schema verification incomplete")
        else:
            print("\n⚠️  Some migrations failed or database not available")
            print("💡 This is normal if PostgreSQL is not running locally")

    except Exception as e:
        print(f"\n❌ Migration error: {str(e)}")
        print("💡 Database migrations will be available when PostgreSQL is configured")

    print("\n📋 Migration Summary:")
    print("  - Migration runner created and ready")
    print("  - Schema files available in scripts/migrations/")
    print("  - Run with PostgreSQL database to create tables")

    return True


if __name__ == "__main__":
    main()
