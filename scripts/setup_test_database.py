#!/usr/bin/env python3
"""
Test Database Setup Script for CI/CD Pipeline
Creates and initializes test database for automated testing
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    import asyncpg
    from sqlalchemy import create_engine, text
    from sqlalchemy.ext.asyncio import create_async_engine
except ImportError:
    print("Installing required database packages...")
    os.system("pip install asyncpg sqlalchemy[asyncio] alembic")
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine


async def setup_test_database():
    """Setup test database for CI/CD pipeline"""
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/pake_test",
    )
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

    print(f"Setting up test database: {database_url}")

    try:
        # Convert to asyncpg URL if needed
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace(
                "postgresql://",
                "postgresql+asyncpg://",
                1,
            )

        # Create async engine for database operations
        engine = create_async_engine(database_url)

        # Test database connection
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.fetchone()
            print(f"✅ Database connected: {version[0]}")

            # Create basic test tables
            await conn.execute(
                text(
                    """
                CREATE TABLE IF NOT EXISTS test_health_check (
                    id SERIAL PRIMARY KEY,
                    status VARCHAR(50) DEFAULT 'healthy',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """,
                ),
            )

            # Insert test data
            await conn.execute(
                text(
                    """
                INSERT INTO test_health_check (status)
                VALUES ('test_ready')
                ON CONFLICT DO NOTHING
            """,
                ),
            )

            # Commit the transaction
            await conn.commit()

        await engine.dispose()
        print("✅ Test database setup completed")

        # Test Redis connection if available
        try:
            import redis

            r = redis.from_url(redis_url)
            r.ping()
            r.set("test:setup", "success")
            print("✅ Redis connection verified")
        except Exception as e:
            print(f"⚠️  Redis connection failed (non-critical): {e}")

        return True

    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False


def setup_environment_variables():
    """Set up required environment variables for testing"""
    env_vars = {
        "TESTING": "true",
        "DATABASE_URL": os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5432/pake_test",
        ),
        "REDIS_URL": os.getenv("REDIS_URL", "redis://localhost:6379"),
        "FIRECRAWL_API_KEY": os.getenv("FIRECRAWL_API_KEY", "test-key"),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY", "test-key"),
        "JWT_SECRET_KEY": os.getenv("JWT_SECRET_KEY", "test-secret-key-for-testing"),
    }

    for key, value in env_vars.items():
        os.environ[key] = value
        print(f"✅ Set {key}")

    return True


if __name__ == "__main__":
    print("🚀 Setting up test environment for CI/CD...")

    # Setup environment variables
    setup_environment_variables()

    # Setup test database
    success = asyncio.run(setup_test_database())

    if success:
        print("✅ Test environment setup completed successfully!")
        sys.exit(0)
    else:
        print("❌ Test environment setup failed!")
        sys.exit(1)
