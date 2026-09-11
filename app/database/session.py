import sqlite3
import os
from contextlib import contextmanager
from typing import Generator

if os.environ.get("VERCEL") == "1":
    default_db = "/tmp/society.db"
else:
    default_db = os.path.join(os.path.dirname(os.path.dirname(__file__)), "society.db")

DB_PATH = os.environ.get("SOCIETY_DB_PATH", default_db)

def _ensure_schema(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tenants'")
    if not cursor.fetchone():
        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
        with open(schema_path, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        try:
            from app.database.seed import seed_database
            # Seeds initial demo societies
            cursor.execute("SELECT COUNT(*) as c FROM tenants")
            if cursor.fetchone()["c"] == 0:
                seed_database()
        except Exception as e:
            print("Auto-seed info:", e)

def get_db_connection() -> sqlite3.Connection:
    """Creates a new SQLite database connection with row factory and foreign keys enabled."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    _ensure_schema(conn)
    return conn

@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Context manager for database transactions."""
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db(force: bool = False):
    """Initializes the database schema."""
    schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
    if force and os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()
        
    with get_db() as conn:
        conn.executescript(schema_sql)
