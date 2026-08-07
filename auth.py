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

def authenticate(conn: sqlite3.Connection, email: str, plain_password: str):
    """Attempt to log in. Returns the user row (sqlite3.Row) on success,
    or None if the email doesn't exist, the account is inactive, or the
    password is wrong."""
    row = conn.execute(
        "SELECT * FROM users WHERE email = ?", (email,)
    ).fetchone()

    if row is None:
        return None
    if row["active"] != 1:
        return None
    if not verify_password(plain_password, row["password"]):
        return None

    return row

if __name__ == "__main__":
    # Quick manual test / demo. Run: pipenv run python auth.py
    conn = get_connection()

    test_email = "demo.manager@example.com"
    existing = conn.execute(
        "SELECT * FROM users WHERE email = ?", (test_email,)
    ).fetchone()

    if existing is None:
        user_id = create_user(
            conn,
            first_name="Demo",
            last_name="Manager",
            phone="555-0100",
            email=test_email,
            plain_password="CorrectHorseBatteryStaple",
            hire_date="2026-01-15",
            user_type="manager",
        )
        print(f"Created test user with user_id={user_id}")
    else:
        print("Test user already exists, skipping creation.")

    result = authenticate(conn, test_email, "wrong-password")
    print("Login with wrong password:", "SUCCESS" if result else "REJECTED (expected)")

    result = authenticate(conn, test_email, "CorrectHorseBatteryStaple")
    print("Login with correct password:", "SUCCESS" if result else "REJECTED (unexpected!)")
    if result:
        print(f"  Logged in as: {result['first_name']} {result['last_name']} ({result['user_type']})")

    conn.close()