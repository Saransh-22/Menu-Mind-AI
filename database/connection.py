"""
Database connection and initialization for MenuMind AI.
"""
import sqlite3
import logging
from pathlib import Path
from contextlib import contextmanager

from config.settings import DATABASE_PATH

logger = logging.getLogger(__name__)


def get_connection(db_path: str = DATABASE_PATH) -> sqlite3.Connection:
    """Return a new SQLite connection with row_factory set."""
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


@contextmanager
def db_session(db_path: str = DATABASE_PATH):
    """Context manager that auto-commits or rolls back."""
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize_database(db_path: str = DATABASE_PATH) -> None:
    """Create all tables if they do not exist."""
    from database.models import CREATE_TABLES_SQL
    with db_session(db_path) as conn:
        for sql in CREATE_TABLES_SQL:
            conn.execute(sql)
    logger.info("Database initialized at %s", db_path)
