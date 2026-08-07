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

