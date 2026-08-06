"""
schema.py

Creates the SQLite database and tables for the Competency Tracking Tool,
based on the finalized ERD (Users, Competencies, Assessments, Assessment_Results).

Run this once to (re)build the database:
    python schema.py
"""

import sqlite3
import os

DB_PATH = "competency_tracker.db"

CREATE_USERS = """
CREATE TABLE IF NOT EXISTS users (
    user_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name    TEXT NOT NULL,
    last_name     TEXT NOT NULL,
    phone         TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    password      TEXT NOT NULL,
    active        INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    date_created  TEXT NOT NULL,
    hire_date     TEXT NOT NULL,
    user_type     TEXT NOT NULL CHECK (user_type IN ('user', 'manager'))
);
"""

CREATE_COMPETENCIES = """
CREATE TABLE IF NOT EXISTS competencies (
    competency_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    date_created  TEXT NOT NULL
);
"""

CREATE_ASSESSMENTS = """
CREATE TABLE IF NOT EXISTS assessments (
    assessment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    competency_id INTEGER NOT NULL,
    name          TEXT NOT NULL,
    date_created  TEXT NOT NULL,
    FOREIGN KEY (competency_id) REFERENCES competencies(competency_id)
);
"""

CREATE_ASSESSMENT_RESULTS = """
CREATE TABLE IF NOT EXISTS assessment_results (
    assessment_result_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL,
    assessment_id INTEGER NOT NULL,
    manager_id    INTEGER,
    score         INTEGER NOT NULL CHECK (score BETWEEN 0 AND 4),
    date_taken    TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (assessment_id) REFERENCES assessments(assessment_id),
    FOREIGN KEY (manager_id) REFERENCES users(user_id)
);
"""


def create_database(db_path: str = DB_PATH) -> None:
    """Create the database file and all tables if they don't already exist."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Enforce foreign key constraints (SQLite has them off by default)
    cursor.execute("PRAGMA foreign_keys = ON;")

    cursor.execute(CREATE_USERS)
    cursor.execute(CREATE_COMPETENCIES)
    cursor.execute(CREATE_ASSESSMENTS)
    cursor.execute(CREATE_ASSESSMENT_RESULTS)

    conn.commit()
    conn.close()
    print(f"Database created/verified at: {os.path.abspath(db_path)}")


if __name__ == "__main__":
    create_database()