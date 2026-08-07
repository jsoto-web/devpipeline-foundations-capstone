'''
Handles password hashing and login for the competency tracking tool.

passwords are never stored in plain text. Each password is hashed with bcrypt, 
which generates and embeds a unique random salt automatically as part of the
hash string itself -- so the users.password column just stores the bcrypt hash
directly, no extra salt column or delimiter needed.
'''

import sqlite3
from datetime import date

import bcrypt

from db import get_connection

def hash_password(plain_password: str) -> str:
    '''Hash a plain-text password with bcrypt. Returns the hash as a string
    (safe to store directly in the users.password TEXT column).
    '''
    hashed_bytes = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt())
    return hashed_bytes.decode("utf-8")

def verify_password(plain_password: str, stored_password: str) -> bool:
    '''check a plain-text password attempt against the stored bcrypt hash.'''
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), stored_password.encode("utf-8"))
    except ValueError:
        # stored password isn't a valid bcrypt hash (e.g. corrupted data)
        return False

def create_user(
    conn: sqlite3.Connection,
    first_name: str,
    last_name: str,
    phone: str,
    email: str,
    plain_password: str,
    hire_date: str,
    user_type: str,
) -> int:
    """Insert a new user with a securely hashed password.
    Returns the new user_id. Raises sqlite3.IntegrityError if the
    email is already taken (email is UNIQUE in the schema)."""
    hashed = hash_password(plain_password)
    today = date.today().isoformat()

    cursor = conn.execute(
        """
        INSERT INTO users
            (first_name, last_name, phone, email, password,
             active, date_created, hire_date, user_type)
        VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)
        """,
        (first_name, last_name, phone, email, hashed, today, hire_date, user_type),
    )
    conn.commit()
    return cursor.lastrowid