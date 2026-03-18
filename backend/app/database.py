# SQLite database setup for FlatWatch
import sqlite3
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

from .config import DATABASE_PATH


def get_db_path() -> Path:
    """Get the database path, ensuring directory exists."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    return DATABASE_PATH


def init_db() -> None:
    """Initialize the database with required tables."""
    from .audit import init_audit_tables

    db_path = get_db_path()

    with sqlite3.connect(db_path) as conn:
        # Create transactions table with attribution
        conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL NOT NULL,
                transaction_type TEXT NOT NULL CHECK(transaction_type IN ('inflow', 'outflow')),
                description TEXT,
                vpa TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                receipt_path TEXT,
                verified BOOLEAN DEFAULT 0,
                entered_by INTEGER,
                approved_by INTEGER,
                approved_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (entered_by) REFERENCES users(id),
                FOREIGN KEY (approved_by) REFERENCES users(id)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                firebase_uid TEXT UNIQUE NOT NULL,
                email TEXT NOT NULL,
                name TEXT,
                role TEXT DEFAULT 'resident' CHECK(role IN ('resident', 'admin', 'super_admin')),
                flat_number TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS challenges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                reason TEXT NOT NULL,
                status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'resolved', 'rejected')),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                resolved_at DATETIME,
                FOREIGN KEY (transaction_id) REFERENCES transactions(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS agent_sessions (
                session_id TEXT PRIMARY KEY,
                app_id TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                subject_id TEXT NOT NULL,
                wallet_address TEXT,
                sdk_session_id TEXT,
                trust_state TEXT NOT NULL,
                mode TEXT NOT NULL,
                allowed_capabilities TEXT NOT NULL,
                task_type TEXT NOT NULL,
                context_json TEXT NOT NULL,
                messages_json TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        conn.commit()

    # Initialize audit tables
    init_audit_tables()


@contextmanager
def get_db():
    """Context manager for database connections."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def get_db_connection() -> sqlite3.Connection:
    """Get a database connection (for use with FastAPI dependencies)."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
