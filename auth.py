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
