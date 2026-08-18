"""
seed_test_data.py

One-off script to populate competency_tracker.db with realistic test
data for grading/demoing: several users (both roles, one inactive),
competencies from the CEO's initial list, assessments under each, and
assessment results with enough variety to exercise the reporting logic
(multiple attempts per competency so "most recent score" actually
matters, some competencies left unassessed so the "0 if never taken"
rule shows up, and a few results with no manager_id to simulate data
that came in through CSV import rather than the app).

Safe to re-run: skips any user whose email already exists instead of
crashing, and only inserts a competency/assessment if one with that
exact name doesn't already exist.

Run with: pipenv run python seed_test_data.py
"""

from datetime import date

from db import get_connection
from auth import create_user

conn = get_connection()


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

USERS = [
    # (first, last, phone, email, password, hire_date, user_type, active)
    ("Demo", "Manager", "555-0100", "demo.manager@example.com",
     "CorrectHorseBatteryStaple", "2025-01-15", "manager", True),
    ("Jamie", "Rivera", "555-0101", "jamie.rivera@example.com",
     "ManagerPass1", "2025-03-01", "manager", True),
    ("Alex", "Chen", "555-0201", "alex.chen@example.com",
     "UserPass1", "2025-06-10", "user", True),
    ("Priya", "Patel", "555-0202", "priya.patel@example.com",
     "UserPass1", "2025-07-22", "user", True),
    ("Sam", "Okafor", "555-0203", "sam.okafor@example.com",
     "UserPass1", "2025-09-05", "user", True),
    ("Taylor", "Brooks", "555-0204", "taylor.brooks@example.com",
     "UserPass1", "2026-01-12", "user", True),
    ("Jordan", "Kim", "555-0205", "jordan.kim@example.com",
     "UserPass1", "2026-02-20", "user", True),
    ("Morgan", "Lee", "555-0206", "morgan.lee@example.com",
     "UserPass1", "2024-11-01", "user", False),  # inactive -- former employee
]

email_to_id: dict[str, int] = {}

print("--- Users ---")
for first, last, phone, email, password, hire_date, user_type, active in USERS:
    existing = conn.execute("SELECT user_id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        email_to_id[email] = existing["user_id"]
        print(f"  already exists: {email}")
        continue

    user_id = create_user(conn, first, last, phone, email, password, hire_date, user_type)
    if not active:
        conn.execute("UPDATE users SET active = 0 WHERE user_id = ?", (user_id,))
        conn.commit()
    email_to_id[email] = user_id
    print(f"  created: {email} (user_id={user_id}, {user_type}, {'active' if active else 'inactive'})")

manager_id = email_to_id["demo.manager@example.com"]
manager2_id = email_to_id["jamie.rivera@example.com"]


# ---------------------------------------------------------------------------
# Competencies -- a subset of the CEO's initial list
# ---------------------------------------------------------------------------

COMPETENCIES = [
    "Data Types",
    "Variables",
    "Functions",
    "Loops",
    "Data Structures",
    "Exception Handling",
    "Object-Oriented Programming",
    "Databases",
]

competency_name_to_id: dict[str, int] = {}

print("\n--- Competencies ---")
today = date.today().isoformat()
for name in COMPETENCIES:
    existing = conn.execute("SELECT competency_id FROM competencies WHERE name = ?", (name,)).fetchone()
    if existing:
        competency_name_to_id[name] = existing["competency_id"]
        print(f"  already exists: {name}")
        continue

    cursor = conn.execute(
        "INSERT INTO competencies (name, date_created) VALUES (?, ?)", (name, today)
    )
    conn.commit()
    competency_name_to_id[name] = cursor.lastrowid
    print(f"  created: {name} (competency_id={cursor.lastrowid})")


# ---------------------------------------------------------------------------
# Assessments -- one or two per competency
# ---------------------------------------------------------------------------

ASSESSMENTS = [
    ("Data Types", "Data Types Quiz"),
    ("Data Types", "Data Types Practical"),
    ("Variables", "Variables Quiz"),
    ("Functions", "Functions Quiz"),
    ("Functions", "Functions Code Review"),
    ("Loops", "Loops Quiz"),
    ("Data Structures", "Data Structures Quiz"),
    ("Exception Handling", "Exception Handling Quiz"),
    ("Object-Oriented Programming", "OOP Interview"),
    ("Databases", "Databases Quiz"),
]

assessment_name_to_id: dict[str, int] = {}

print("\n--- Assessments ---")
for competency_name, assessment_name in ASSESSMENTS:
    existing = conn.execute(
        "SELECT assessment_id FROM assessments WHERE name = ?", (assessment_name,)
    ).fetchone()
    if existing:
        assessment_name_to_id[assessment_name] = existing["assessment_id"]
        print(f"  already exists: {assessment_name}")
        continue

    competency_id = competency_name_to_id[competency_name]
    cursor = conn.execute(
        "INSERT INTO assessments (competency_id, name, date_created) VALUES (?, ?, ?)",
        (competency_id, assessment_name, today),
    )
    conn.commit()
    assessment_name_to_id[assessment_name] = cursor.lastrowid
    print(f"  created: {assessment_name} -> {competency_name} (assessment_id={cursor.lastrowid})")


# ---------------------------------------------------------------------------
# Assessment Results
# ---------------------------------------------------------------------------
# (user_email, assessment_name, score, date_taken, manager_email_or_None)
# manager_email=None simulates a result that came in through CSV import,
# which never records who administered it.

RESULTS = [
    # Alex Chen -- solid performer, retook Data Types and improved
    ("alex.chen@example.com", "Data Types Quiz", 2, "2025-07-01", "demo.manager@example.com"),
    ("alex.chen@example.com", "Data Types Quiz", 3, "2025-09-15", "demo.manager@example.com"),
    ("alex.chen@example.com", "Variables Quiz", 3, "2025-07-01", "demo.manager@example.com"),
    ("alex.chen@example.com", "Functions Quiz", 4, "2025-10-01", "demo.manager@example.com"),
    ("alex.chen@example.com", "Loops Quiz", 3, "2025-11-05", "jamie.rivera@example.com"),
    # Databases left unassessed for Alex -- exercises the "0 if never taken" rule

    # Priya Patel -- newer, fewer results, one CSV-imported (no manager)
    ("priya.patel@example.com", "Data Types Quiz", 1, "2025-08-01", "demo.manager@example.com"),
    ("priya.patel@example.com", "Variables Quiz", 2, "2025-08-15", None),
    ("priya.patel@example.com", "Functions Quiz", 2, "2025-09-20", "jamie.rivera@example.com"),

    # Sam Okafor -- broad coverage, mid scores
    ("sam.okafor@example.com", "Data Types Quiz", 3, "2025-10-01", "demo.manager@example.com"),
    ("sam.okafor@example.com", "Variables Quiz", 3, "2025-10-01", "demo.manager@example.com"),
    ("sam.okafor@example.com", "Loops Quiz", 2, "2025-10-15", "demo.manager@example.com"),
    ("sam.okafor@example.com", "Data Structures Quiz", 2, "2025-11-01", "demo.manager@example.com"),
    ("sam.okafor@example.com", "Exception Handling Quiz", 1, "2025-11-20", "jamie.rivera@example.com"),
    ("sam.okafor@example.com", "Databases Quiz", 3, "2026-01-10", "demo.manager@example.com"),

    # Taylor Brooks -- brand new hire, single low score, retested once
    ("taylor.brooks@example.com", "Data Types Quiz", 0, "2026-01-20", "demo.manager@example.com"),
    ("taylor.brooks@example.com", "Data Types Quiz", 1, "2026-03-01", "demo.manager@example.com"),

    # Jordan Kim -- strong across the board, expert in OOP
    ("jordan.kim@example.com", "Data Types Quiz", 4, "2026-03-01", "jamie.rivera@example.com"),
    ("jordan.kim@example.com", "Variables Quiz", 4, "2026-03-01", "jamie.rivera@example.com"),
    ("jordan.kim@example.com", "Functions Quiz", 4, "2026-03-05", "jamie.rivera@example.com"),
    ("jordan.kim@example.com", "OOP Interview", 4, "2026-04-01", "demo.manager@example.com"),
    ("jordan.kim@example.com", "Databases Quiz", 3, "2026-04-10", "demo.manager@example.com"),

    # Demo Manager themself has a couple of results too -- managers can be assessed too
    ("demo.manager@example.com", "OOP Interview", 4, "2025-02-01", None),
    ("demo.manager@example.com", "Databases Quiz", 4, "2025-02-15", None),
]

print("\n--- Assessment Results ---")
inserted = 0
skipped = 0
for user_email, assessment_name, score, date_taken, manager_email in RESULTS:
    user_id = email_to_id[user_email]
    assessment_id = assessment_name_to_id[assessment_name]
    recorded_by = email_to_id[manager_email] if manager_email else None

    # Avoid duplicating the exact same result if this script runs twice
    existing = conn.execute(
        "SELECT assessment_result_id FROM assessment_results "
        "WHERE user_id = ? AND assessment_id = ? AND date_taken = ?",
        (user_id, assessment_id, date_taken),
    ).fetchone()
    if existing:
        skipped += 1
        continue

    conn.execute(
        """
        INSERT INTO assessment_results (user_id, assessment_id, manager_id, score, date_taken)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, assessment_id, recorded_by, score, date_taken),
    )
    inserted += 1

conn.commit()
print(f"  inserted {inserted} result(s), skipped {skipped} already-present result(s)")

conn.close()
print("\nDone. Log in as demo.manager@example.com / CorrectHorseBatteryStaple "
      "(or jamie.rivera@example.com / ManagerPass1) to explore the seeded data.")