import logging
import os
import time
from typing import Any, Dict

import psycopg2

logger = logging.getLogger(__name__)


def check_primary_database_health() -> bool:
    """Check if primary database is healthy."""
    try:
        conn = psycopg2.connect(os.getenv("CHAOS_DATABASE_URL"))
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result[0] == 1
    except Exception as e:
        logger.error(f"Primary database health check failed: {e}")
        return False


def check_replica_database_health() -> bool:
    """Check if replica database is healthy."""
    try:
        replica_url = os.getenv("CHAOS_DATABASE_URL").replace(":5432", ":5433")
        conn = psycopg2.connect(replica_url)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result[0] == 1
    except Exception as e:
        logger.error(f"Replica database health check failed: {e}")
        return False


def measure_failover_time() -> float:
    """Measure time taken for database failover."""
    start_time = time.time()

    # Wait for failover to complete
    while True:
        try:
            conn = psycopg2.connect(os.getenv("CHAOS_DATABASE_URL"))
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            conn.close()

            if result[0] == 1:
                break
        except Exception:
            pass

        time.sleep(1)
        if time.time() - start_time > 600:  # 10 minute timeout
            raise Exception("Failover timeout exceeded")

    return time.time() - start_time


def verify_data_integrity() -> bool:
    """Verify data integrity after failover."""
    try:
        conn = psycopg2.connect(os.getenv("CHAOS_DATABASE_URL"))
        cursor = conn.cursor()

        # Check critical tables
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM documents")
        doc_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM research_sessions")
        session_count = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        # Verify counts are reasonable
        return user_count > 0 and doc_count > 0 and session_count >= 0
    except Exception as e:
        logger.error(f"Data integrity check failed: {e}")
        return False


def validate_restored_data_integrity() -> bool:
    """Validate data integrity after restore from backup."""
    try:
        conn = psycopg2.connect(os.getenv("CHAOS_RESTORE_DATABASE_URL"))
        cursor = conn.cursor()

        # Check critical tables exist and have data
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM documents")
        doc_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM research_sessions")
        session_count = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        # Verify counts are reasonable (should match production)
        return user_count > 0 and doc_count > 0 and session_count >= 0
    except Exception as e:
        logger.error(f"Restored data integrity check failed: {e}")
        return False
