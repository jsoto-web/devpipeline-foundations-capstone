"""
db.py

Shared database connection helper for the Competency Tracking Tool.
Import get_connection() anywhere you need to talk to the database.
"""

import sqlite3

DB_PATH = "competency_tracker.db"


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection with foreign keys enforced and
    rows returned as dict-like objects (access columns by name)."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn