# Database setup for FlatWatch.
import sqlite3
from pathlib import Path
from contextlib import contextmanager

from .config import DATABASE_PATH, DATABASE_URL


def get_db_path() -> Path:
    """Get the local SQLite database path, ensuring directory exists."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    return DATABASE_PATH


def using_postgres() -> bool:
    return DATABASE_URL.startswith(("postgresql://", "postgres://"))


def _connect_postgres():
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError as exc:
        raise RuntimeError("PostgreSQL mode requires psycopg to be installed.") from exc

    return psycopg.connect(DATABASE_URL, row_factory=dict_row)


class DbConnection:
    """Small DB-API compatibility wrapper for SQLite and psycopg."""

    def __init__(self, raw_conn, postgres: bool = False):
        self.raw_conn = raw_conn
        self.postgres = postgres

    def execute(self, query: str, params: tuple | list = ()):
        if self.postgres:
            query = query.replace("?", "%s")
            query = query.replace("datetime('now', '-1 hour')", "CURRENT_TIMESTAMP - INTERVAL '1 hour'")
            query = query.replace("datetime('now', '-24 hours')", "CURRENT_TIMESTAMP - INTERVAL '24 hours'")
            query = query.replace("datetime(timestamp)", "timestamp")
        return self.raw_conn.execute(query, params)

    def commit(self) -> None:
        self.raw_conn.commit()

    def close(self) -> None:
        self.raw_conn.close()


def init_db() -> None:
    """Initialize the configured database with required tables."""
    from .audit import init_audit_tables

    if using_postgres():
        _init_postgres_db()
        init_audit_tables()
        return

    db_path = get_db_path()
    with sqlite3.connect(db_path) as conn:
        _init_sqlite_db(conn)
        conn.commit()

    init_audit_tables()


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def get_db_connection():
    """Get a database connection for use with FastAPI dependencies."""
    if using_postgres():
        return DbConnection(_connect_postgres(), postgres=True)
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return DbConnection(conn)


def _init_sqlite_db(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at DATETIME DEFAULT CURRENT_TIMESTAMP
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
            password_hash TEXT,
            token_version INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
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
        CREATE TABLE IF NOT EXISTS challenges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            transaction_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            reason TEXT NOT NULL,
            evidence TEXT,
            status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'resolved', 'rejected')),
            assigned_reviewer_id INTEGER,
            response TEXT,
            resolution_reason TEXT,
            audit_receipt_id INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            resolved_at DATETIME,
            resolved_by INTEGER,
            FOREIGN KEY (transaction_id) REFERENCES transactions(id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (assigned_reviewer_id) REFERENCES users(id),
            FOREIGN KEY (resolved_by) REFERENCES users(id)
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
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agent_usage (
            subject_id TEXT NOT NULL,
            app_id TEXT NOT NULL,
            requests_used INTEGER NOT NULL DEFAULT 0,
            requests_limit INTEGER NOT NULL DEFAULT 0,
            period_start TEXT NOT NULL,
            period_end TEXT NOT NULL,
            estimated_cost_usd REAL NOT NULL DEFAULT 0,
            PRIMARY KEY (subject_id, app_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS payment_ingestion_events (
            idempotency_key TEXT PRIMARY KEY,
            provider TEXT NOT NULL,
            source_transaction_id TEXT NOT NULL,
            raw_payload TEXT NOT NULL,
            transaction_id INTEGER,
            status TEXT DEFAULT 'ingested',
            retry_count INTEGER DEFAULT 0,
            last_error TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (transaction_id) REFERENCES transactions(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE NOT NULL,
            original_filename TEXT,
            storage_key TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            content_type TEXT NOT NULL,
            size_bytes INTEGER NOT NULL,
            uploaded_by INTEGER NOT NULL,
            transaction_id INTEGER,
            retained_until TEXT,
            deleted_at TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (uploaded_by) REFERENCES users(id),
            FOREIGN KEY (transaction_id) REFERENCES transactions(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS receipt_extractions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            receipt_filename TEXT NOT NULL,
            transaction_id INTEGER,
            amount REAL,
            vendor TEXT,
            receipt_date TEXT,
            confidence REAL NOT NULL,
            extraction_method TEXT NOT NULL,
            source_hash TEXT NOT NULL,
            match_score INTEGER NOT NULL,
            matching_rule TEXT NOT NULL,
            needs_manual_review BOOLEAN NOT NULL DEFAULT 0,
            reviewer_outcome TEXT,
            audit_receipt_id INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trust_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wallet_address TEXT NOT NULL,
            trust_state TEXT NOT NULL,
            source_reference TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS invalidated_tokens (
            token_id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            invalidated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS society_profile (
            id INTEGER PRIMARY KEY CHECK(id = 1),
            name TEXT NOT NULL,
            registration_number TEXT,
            address TEXT,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    _migrate_sqlite_schema(conn)
    _seed_demo_users(conn)


def _sqlite_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    return {row[1] for row in cursor.fetchall()}


def _ensure_sqlite_columns(
    conn: sqlite3.Connection,
    table_name: str,
    columns: dict[str, str],
) -> None:
    existing = _sqlite_columns(conn, table_name)
    for column_name, column_definition in columns.items():
        if column_name not in existing:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")


def _migrate_sqlite_schema(conn: sqlite3.Connection) -> None:
    """Bring local SQLite databases created by older app versions up to date."""
    _ensure_sqlite_columns(
        conn,
        "users",
        {
            "password_hash": "TEXT",
            "token_version": "INTEGER DEFAULT 0",
        },
    )
    _ensure_sqlite_columns(
        conn,
        "challenges",
        {
            "assigned_reviewer_id": "INTEGER",
            "response": "TEXT",
            "resolution_reason": "TEXT",
            "audit_receipt_id": "INTEGER",
            "resolved_by": "INTEGER",
        },
    )
    _ensure_sqlite_columns(
        conn,
        "receipts",
        {
            "original_filename": "TEXT",
            "storage_key": "TEXT",
            "content_hash": "TEXT",
            "content_type": "TEXT",
            "size_bytes": "INTEGER DEFAULT 0",
            "retained_until": "TEXT",
            "deleted_at": "TEXT",
        },
    )
    _ensure_sqlite_columns(
        conn,
        "receipt_extractions",
        {
            "matching_rule": "TEXT DEFAULT 'unmatched'",
            "needs_manual_review": "BOOLEAN NOT NULL DEFAULT 0",
            "reviewer_outcome": "TEXT",
            "audit_receipt_id": "INTEGER",
        },
    )
    _ensure_sqlite_columns(
        conn,
        "payment_ingestion_events",
        {
            "retry_count": "INTEGER DEFAULT 0",
            "last_error": "TEXT",
            "updated_at": "DATETIME",
        },
    )


def _seed_demo_users(conn) -> None:
    from .auth import hash_password

    users = [
        ("mock_admin_123", "admin@flatwatch.test", "Admin User", "super_admin", "A-001", "admin-demo-password"),
        ("mock_resident_456", "resident@flatwatch.test", "Resident User", "resident", "B-101", "resident-demo-password"),
    ]
    for firebase_uid, email, name, role, flat_number, password in users:
        conn.execute(
            """
            INSERT INTO users (firebase_uid, email, name, role, flat_number, password_hash)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(firebase_uid) DO NOTHING
            """,
            (firebase_uid, email, name, role, flat_number, hash_password(password)),
        )


def _init_postgres_db() -> None:
    with _connect_postgres() as raw_conn:
        conn = DbConnection(raw_conn, postgres=True)
        for statement in POSTGRES_SCHEMA:
            conn.execute(statement)
        _seed_demo_users(conn)
        conn.commit()


POSTGRES_SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS schema_migrations (
        version TEXT PRIMARY KEY,
        applied_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        firebase_uid TEXT UNIQUE NOT NULL,
        email TEXT NOT NULL,
        name TEXT,
        role TEXT DEFAULT 'resident' CHECK(role IN ('resident', 'admin', 'super_admin')),
        flat_number TEXT,
        password_hash TEXT,
        token_version INTEGER DEFAULT 0,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS transactions (
        id SERIAL PRIMARY KEY,
        amount DOUBLE PRECISION NOT NULL,
        transaction_type TEXT NOT NULL CHECK(transaction_type IN ('inflow', 'outflow')),
        description TEXT,
        vpa TEXT,
        timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        receipt_path TEXT,
        verified BOOLEAN DEFAULT false,
        entered_by INTEGER REFERENCES users(id),
        approved_by INTEGER REFERENCES users(id),
        approved_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS challenges (
        id SERIAL PRIMARY KEY,
        transaction_id INTEGER NOT NULL REFERENCES transactions(id),
        user_id INTEGER NOT NULL REFERENCES users(id),
        reason TEXT NOT NULL,
        evidence TEXT,
        status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'resolved', 'rejected')),
        assigned_reviewer_id INTEGER REFERENCES users(id),
        response TEXT,
        resolution_reason TEXT,
        audit_receipt_id INTEGER,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        resolved_at TIMESTAMPTZ,
        resolved_by INTEGER REFERENCES users(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS agent_sessions (
        session_id TEXT PRIMARY KEY,
        app_id TEXT NOT NULL,
        user_id INTEGER NOT NULL REFERENCES users(id),
        subject_id TEXT NOT NULL,
        wallet_address TEXT,
        sdk_session_id TEXT,
        trust_state TEXT NOT NULL,
        mode TEXT NOT NULL,
        allowed_capabilities TEXT NOT NULL,
        task_type TEXT NOT NULL,
        context_json TEXT NOT NULL,
        messages_json TEXT NOT NULL,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS agent_usage (
        subject_id TEXT NOT NULL,
        app_id TEXT NOT NULL,
        requests_used INTEGER NOT NULL DEFAULT 0,
        requests_limit INTEGER NOT NULL DEFAULT 0,
        period_start TEXT NOT NULL,
        period_end TEXT NOT NULL,
        estimated_cost_usd DOUBLE PRECISION NOT NULL DEFAULT 0,
        PRIMARY KEY (subject_id, app_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS payment_ingestion_events (
        idempotency_key TEXT PRIMARY KEY,
        provider TEXT NOT NULL,
        source_transaction_id TEXT NOT NULL,
        raw_payload TEXT NOT NULL,
        transaction_id INTEGER REFERENCES transactions(id),
        status TEXT DEFAULT 'ingested',
        retry_count INTEGER DEFAULT 0,
        last_error TEXT,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS receipts (
        id SERIAL PRIMARY KEY,
        filename TEXT UNIQUE NOT NULL,
        original_filename TEXT,
        storage_key TEXT NOT NULL,
        content_hash TEXT NOT NULL,
        content_type TEXT NOT NULL,
        size_bytes INTEGER NOT NULL,
        uploaded_by INTEGER NOT NULL REFERENCES users(id),
        transaction_id INTEGER REFERENCES transactions(id),
        retained_until TEXT,
        deleted_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS receipt_extractions (
        id SERIAL PRIMARY KEY,
        receipt_filename TEXT NOT NULL,
        transaction_id INTEGER,
        amount DOUBLE PRECISION,
        vendor TEXT,
        receipt_date TEXT,
        confidence DOUBLE PRECISION NOT NULL,
        extraction_method TEXT NOT NULL,
        source_hash TEXT NOT NULL,
        match_score INTEGER NOT NULL,
        matching_rule TEXT NOT NULL,
        needs_manual_review BOOLEAN NOT NULL DEFAULT false,
        reviewer_outcome TEXT,
        audit_receipt_id INTEGER,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS trust_snapshots (
        id SERIAL PRIMARY KEY,
        wallet_address TEXT NOT NULL,
        trust_state TEXT NOT NULL,
        source_reference TEXT,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS invalidated_tokens (
        token_id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL REFERENCES users(id),
        invalidated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS society_profile (
        id INTEGER PRIMARY KEY CHECK(id = 1),
        name TEXT NOT NULL,
        registration_number TEXT,
        address TEXT,
        updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    )
    """,
]
