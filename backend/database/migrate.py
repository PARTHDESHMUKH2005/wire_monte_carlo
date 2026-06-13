import os
import logging

logger = logging.getLogger(__name__)


def run_migrations():
    """Run database migrations for schema changes."""
    try:
        from database.connection import engine, DATABASE_URL

        if DATABASE_URL.startswith("sqlite"):
            _migrate_sqlite()
        else:
            _migrate_postgres()

        logger.info("Database migrations completed")
    except Exception as e:
        logger.warning(f"Migration failed (non-fatal): {e}")


def _migrate_postgres():
    """Add new columns to PostgreSQL tables."""
    try:
        from sqlalchemy import text
        from database.connection import engine

        with engine.connect() as conn:
            # Check if password_hash column exists in users table
            result = conn.execute(
                text("SELECT column_name FROM information_schema.columns WHERE table_name='users' AND column_name='password_hash'")
            )
            if result.rowcount == 0:
                conn.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)"))
                conn.execute(text("ALTER TABLE users ADD COLUMN name VARCHAR(255)"))
                conn.commit()
                logger.info("Added password_hash and name columns to users table")
    except Exception as e:
        logger.warning(f"PostgreSQL migration error: {e}")


def _migrate_sqlite():
    """SQLite doesn't support ALTER TABLE ADD COLUMN easily, so we recreate."""
    try:
        from database.connection import engine

        with engine.connect() as conn:
            # Check if password_hash column exists
            result = conn.execute(
                text("PRAGMA table_info(users)")
            )
            columns = [row[1] for row in result]
            if "password_hash" not in columns:
                # SQLite doesn't support IF NOT EXISTS for ALTER TABLE
                try:
                    conn.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)"))
                    conn.execute(text("ALTER TABLE users ADD COLUMN name VARCHAR(255)"))
                    conn.commit()
                    logger.info("Added password_hash and name columns to users table")
                except Exception:
                    logger.warning("Could not add columns to SQLite users table")
    except Exception as e:
        logger.warning(f"SQLite migration error: {e}")


if __name__ == "__main__":
    run_migrations()
