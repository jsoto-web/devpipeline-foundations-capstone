"""
main.py
 
Console entry point for the Competency Tracking Tool.
Run with: pipenv run python main.py
 
Handles the login loop, then branches into a user menu or a manager
menu based on users.user_type. 
"""
 
import csv
import sqlite3
from datetime import date
from typing import Any, Callable

from auth import authenticate, create_user, hash_password
from db import get_connection

Connection = sqlite3.Connection
Row = sqlite3.Row

# ---------------------------------------------------------------------------
# Small input helpers
# ---------------------------------------------------------------------------
 
def prompt(label: str) -> str:
    return input(f"{label}: ").strip()
 
 
def prompt_choice(label: str, valid_choices: set[str]) -> str:
    while True:
        choice = prompt(label)
        if choice in valid_choices:
            return choice
        print(f"  Please enter one of: {', '.join(valid_choices)}")


def prompt_id_or_back(label: str, valid_ids: set[str]) -> str | None:
    """Prompt for one of valid_ids, or 'b' to cancel and go back.
    Returns None if the person backs out instead of choosing an id."""
    while True:
        choice = prompt(f"{label} (or 'b' to go back)")
        if choice.lower() == "b":
            return None
        if choice in valid_ids:
            return choice
        print(f"  Please enter one of: {', '.join(sorted(valid_ids))}, or 'b' to go back")


def prompt_required(label: str) -> str:
    """Loop until the person enters something non-blank."""
    while True:
        value = prompt(label)
        if value:
            return value
        print("    This field can't be blank.")

def prompt_date(label: str, allow_blank: bool = False) -> str:
    """Loop until the person enters a valid YYY-MM-DD date. If
    allow_blank is True, an empty input is accepted and returned as empty-string."""
    while True:
        value = prompt(label)
        if not value:
            if allow_blank:
                return ""
            print("    This field can't be blank.")
            continue
        try:
            date.fromisoformat(value)
            return value
        except ValueError:
            print("    Please enter a date as YYYY-MM-DD, e.g. 2023-09-01.")

def prompt_score_optional(label: str = "New score (0-4, blank to keep)") -> str:
    """Loop until the person enters 0-4 or leaves it blank."""
    while True:
        value = prompt(label)
        if not value:
            return ""
        if value in {"0", "1", "2", "3", "4"}:
            return value
        print("    Score must be 0-4 (or blank to keep the current value).")

def safe_call(action: Callable[[Connection, Row], Any], conn: Connection, user: Row) -> Any:
    """Run a menu action and catch anything unexpected so one bad action
    can't take down the whole session. Returns whatever the action returns
    (some actions, like edit_own_name, return an updated user row)."""
    try:
        return action(conn, user)
    except sqlite3.Error as e:
        print(f"\nDatabase error: {e}\nNothing was changed.")
        return None
    except Exception as e:
        print(f"\nSomething went wrong: {e}\nReturning to the menu.")
        return None

 
# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
 

def login_screen(conn: Connection) -> Row | None:
    """Loop until a successful login or the person chooses to quit.
    Returns the logged-in user row, or None if they quit."""
    print("\n=== Competency Tracking Tool ===")
    while True:
        print("\n1) Log in")
        print("2) Quit")
        choice = prompt_choice("Choose an option", {"1", "2"})
 
        if choice == "2":
            return None
 
        email = prompt("Email")
        password = prompt("Password")
 
        try:
            user = authenticate(conn, email, password)
        except sqlite3.Error as e:
            print(f"Database error during login: {e}")
            continue
 
        if user is None:
            print("Login failed. Check your email/password (or the account may be inactive).")
            continue
 
        print(f"\nWelcome, {user['first_name']} {user['last_name']}!")
        return user
 

# ---------------------------------------------------------------------------
# Shared / "user" features -- both user_type='user' and 'manager' can do these
# ---------------------------------------------------------------------------
 
def view_own_profile(conn: Connection, user: Row) -> None:
    print("\n--- Your Profile ---")
    print(f"Name:        {user['first_name']} {user['last_name']}")
    print(f"Email:       {user['email']}")
    print(f"Phone:       {user['phone']}")
    print(f"User type:   {user['user_type']}")
    print(f"Hire date:   {user['hire_date']}")
    print(f"Active:      {'Yes' if user['active'] else 'No'}")

def edit_own_name(conn: Connection, user: Row) -> Row:
    print("\n--- Edit My Name ---")
    print("Leave a field blank to keep its current value.")
    new_first = prompt(f"First name [{user['first_name']}]")
    new_last = prompt(f"Last name [{user['last_name']}]")
 
    if not new_first and not new_last:
        print("No changes made.")
        return user
 
    if new_first:
        conn.execute("UPDATE users SET first_name = ? WHERE user_id = ?",
                      (new_first, user["user_id"]))
    if new_last:
        conn.execute("UPDATE users SET last_name = ? WHERE user_id = ?",
                      (new_last, user["user_id"]))
    conn.commit()
    print("Name updated.")
 
    return conn.execute("SELECT * FROM users WHERE user_id = ?", (user["user_id"],)).fetchone()

 
def change_own_password(conn: Connection, user: Row) -> None:
    print("\n--- Change Password ---")
    new_password = prompt_required("New password")
    confirm = prompt("Confirm new password")
 
    if new_password != confirm:
        print("Passwords don't match. Nothing was changed.")
        return
 
    hashed = hash_password(new_password)
    conn.execute(
        "UPDATE users SET password = ? WHERE user_id = ?",
        (hashed, user["user_id"]),
    )
    conn.commit()
    print("Password updated.")


def get_latest_result(conn: Connection, user_id: int | str, competency_id: int | str) -> Row | None:
    """Most recent assessment_result for a given user + competency, or
    None if that user has never been assessed on that competency."""
    return conn.execute(
        """
        SELECT ar.score, a.name AS assessment_name, ar.date_taken
        FROM assessment_results ar
        JOIN assessments a ON ar.assessment_id = a.assessment_id
        WHERE ar.user_id = ? AND a.competency_id = ?
        ORDER BY ar.date_taken DESC, ar.assessment_result_id DESC
        LIMIT 1
        """,
        (user_id, competency_id),
    ).fetchone()


def print_user_competency_summary(conn: Connection, target_user: Row) -> None:
    """The 'User Competency Summary' report for a single user: their
    most recent score per competency (0 if never assessed), plus a
    simple average across all competencies."""
    print(f"\n--- Competency Summary: {target_user['first_name']} {target_user['last_name']} ---")
    print(f"Email: {target_user['email']}")
 
    competencies = list_competencies(conn)
    if not competencies:
        print("No competencies exist yet.")
        return
 
    total = 0
    for c in competencies:
        latest = get_latest_result(conn, target_user["user_id"], c["competency_id"])
        score = latest["score"] if latest else 0
        total += score
        print(f"  {c['name']}: {score}")
 
    average = total / len(competencies)
    print(f"\nAverage competency score: {average:.2f}")

def view_own_competency_summary(conn: Connection, user: Row) -> None:
    print_user_competency_summary(conn, user)
 
def user_menu(conn: Connection, user: Row) -> None:
    while True:
        print("\n--- User Menu ---")
        print("1) View my profile")
        print("2) Edit my name")
        print("3) Change my password")
        print("4) View my competency summary")
        print("5) Log out")
        choice = prompt_choice("Choose an option", {"1", "2", "3", "4", "5"})
 
        if choice == "1":
            safe_call(view_own_profile, conn, user)
        elif choice == "2":
            updated = safe_call(edit_own_name, conn, user)
            if updated is not None:
                user = updated
        elif choice == "3":
            safe_call(change_own_password, conn, user)
        elif choice == "4":
            safe_call(view_own_competency_summary, conn, user)
        elif choice == "5":
            print("Logging out...")
            return


 
# ---------------------------------------------------------------------------
# Manager-only features
# ---------------------------------------------------------------------------
 

def view_all_users(conn: Connection, user: Row) -> None:
    print("\n--- All Users ---")
    rows = conn.execute(
        "SELECT user_id, first_name, last_name, email, user_type, active "
        "FROM users ORDER BY last_name, first_name"
    ).fetchall()
 
    if not rows:
        print("No users found.")
        return
 
    for row in rows:
        status = "active" if row["active"] else "inactive"
        print(f"  [{row['user_id']}] {row['first_name']} {row['last_name']} "
              f"<{row['email']}> - {row['user_type']} ({status})")
 
 
def search_users(conn: Connection, user: Row) -> None:
    print("\n--- Search Users ---")
    term = prompt("Search by first or last name")
    like_term = f"%{term}%"
    rows = conn.execute(
        "SELECT user_id, first_name, last_name, email, user_type, active "
        "FROM users WHERE first_name LIKE ? OR last_name LIKE ? "
        "ORDER BY last_name, first_name",
        (like_term, like_term),
    ).fetchall()
 
    if not rows:
        print("No matching users.")
        return
 
    for row in rows:
        status = "active" if row["active"] else "inactive"
        print(f"  [{row['user_id']}] {row['first_name']} {row['last_name']} "
              f"<{row['email']}> - {row['user_type']} ({status})")
 
 
def add_user(conn: Connection, user: Row) -> None:
    print("\n--- Add User ---")
    first_name = prompt_required("First name")
    last_name = prompt_required("Last name")
    phone = prompt_required("Phone")
    email = prompt_required("Email")
    password = prompt_required("Temporary password")
    hire_date = prompt_date("Hire date (YYYY-MM-DD)")
    user_type = prompt_choice("User type (user/manager)", {"user", "manager"})
 
    try:
        new_id = create_user(
            conn, first_name, last_name, phone, email, password, hire_date, user_type
        )
        print(f"Created user_id={new_id}.")
    except sqlite3.IntegrityError as e:
        print(f"Could not create user (likely a duplicate email): {e}")
 
 
def list_assessment_results_for_user(conn: Connection, user_id: int | str) -> list[Row]:
    return conn.execute(
        """
        SELECT ar.assessment_result_id, ar.score, ar.date_taken,
               a.name AS assessment_name, c.name AS competency_name,
               m.first_name AS manager_first_name, m.last_name AS manager_last_name
        FROM assessment_results ar
        JOIN assessments a ON ar.assessment_id = a.assessment_id
        JOIN competencies c ON a.competency_id = c.competency_id
        LEFT JOIN users m ON ar.manager_id = m.user_id
        WHERE ar.user_id = ?
        ORDER BY ar.date_taken DESC, ar.assessment_result_id DESC
        """,
        (user_id,),
    ).fetchall()
 
 
def view_assessments_for_user(conn: Connection, user: Row) -> None:
    print("\n--- View a User's Assessment History ---")
    target_id = choose_user(conn)
    if target_id is None:
        return
    target = conn.execute("SELECT * FROM users WHERE user_id = ?", (target_id,)).fetchone()
 
    rows = list_assessment_results_for_user(conn, target_id)
    print(f"\n--- Assessments taken by {target['first_name']} {target['last_name']} ---")
    if not rows:
        print("No assessments taken yet.")
        return
 
    for row in rows:
        manager_str = (f"{row['manager_first_name']} {row['manager_last_name']}"
                        if row["manager_first_name"] else "none")
        print(f"  [{row['assessment_result_id']}] {row['assessment_name']} "
              f"({row['competency_name']}): score {row['score']} on {row['date_taken']} "
              f"(recorded by {manager_str})")
 
 
def choose_any_user(conn: Connection, prompt_label: str = "Enter the user_id") -> str | None:
    """Like choose_user, but includes inactive accounts too -- needed for
    editing, since reactivating someone is part of editing their info."""
    rows = conn.execute(
        "SELECT user_id, first_name, last_name, active FROM users "
        "ORDER BY last_name, first_name"
    ).fetchall()
    if not rows:
        print("No users exist.")
        return None
 
    for row in rows:
        status = "active" if row["active"] else "inactive"
        print(f"  [{row['user_id']}] {row['first_name']} {row['last_name']} ({status})")
    valid_ids = {str(row["user_id"]) for row in rows}
    return prompt_id_or_back(prompt_label, valid_ids)
 
 
def edit_user(conn: Connection, user: Row) -> None:
    print("\n--- Edit a User ---")
    target_id = choose_any_user(conn, "Enter the user_id to edit")
    if target_id is None:
        return
 
    target = conn.execute("SELECT * FROM users WHERE user_id = ?", (target_id,)).fetchone()
 
    print(f"\nEditing {target['first_name']} {target['last_name']}.")
    print("Leave a field blank to keep its current value.")
 
    fields: dict[str, str] = {
        "first_name": prompt(f"First name [{target['first_name']}]"),
        "last_name": prompt(f"Last name [{target['last_name']}]"),
        "phone": prompt(f"Phone [{target['phone']}]"),
        "email": prompt(f"Email [{target['email']}]"),
        "hire_date": prompt_date(f"Hire date [{target['hire_date']}]", allow_blank=True),
    }
 
    change_type = prompt_choice("Change user type? (y/n)", {"y", "n"})
    if change_type == "y":
        fields["user_type"] = prompt_choice("New user type (user/manager)", {"user", "manager"})
 
    change_active = prompt_choice(
        f"Change active status? Currently {'active' if target['active'] else 'inactive'}. (y/n)",
        {"y", "n"},
    )
    if change_active == "y":
        fields["active"] = prompt_choice("Set active? (1=active, 0=inactive)", {"0", "1"})
 
    updates = {k: v for k, v in fields.items() if v}
    if not updates:
        print("No changes made.")
        return
 
    set_clause = ", ".join(f"{col} = ?" for col in updates)
    values = list(updates.values()) + [target_id]
 
    try:
        conn.execute(f"UPDATE users SET {set_clause} WHERE user_id = ?", values)
        conn.commit()
        print("User updated.")
    except sqlite3.IntegrityError as e:
        print(f"Could not update user (likely a duplicate email): {e}")
 
 
def view_user_competency_report(conn: Connection, user: Row) -> None:
    print("\n--- View a User's Competency Report ---")
    target_user_id = choose_user(conn)
    if target_user_id is None:
        return
    target_user = conn.execute(
        "SELECT * FROM users WHERE user_id = ?", (target_user_id,)
    ).fetchone()
    print_user_competency_summary(conn, target_user)
 
 
def print_competency_results_summary(conn: Connection, competency: Row) -> None:
    """The 'Competency Results Summary' report for a single competency:
    every active user's most recent score on it (0 if never assessed),
    plus a simple average across active users."""
    print(f"\n--- Results Summary: {competency['name']} ---")
 
    active_users = conn.execute(
        "SELECT * FROM users WHERE active = 1 ORDER BY last_name, first_name"
    ).fetchall()
    if not active_users:
        print("No active users.")
        return
 
    total = 0
    for u in active_users:
        latest = get_latest_result(conn, u["user_id"], competency["competency_id"])
        score = latest["score"] if latest else 0
        assessment_name = latest["assessment_name"] if latest else ""
        date_taken = latest["date_taken"] if latest else ""
        total += score
        print(f"  {u['first_name']} {u['last_name']}: score {score}"
              + (f", assessment '{assessment_name}' on {date_taken}" if latest else ""))
 
    average = total / len(active_users)
    print(f"\nAverage score across active users: {average:.2f}")
 
 
def view_competency_results_summary(conn: Connection, user: Row) -> None:
    print("\n--- Competency Results Summary ---")
    competency_id = choose_competency(conn)
    if competency_id is None:
        return
    competency = conn.execute(
        "SELECT * FROM competencies WHERE competency_id = ?", (competency_id,)
    ).fetchone()
    print_competency_results_summary(conn, competency)
 


# ---------------------------------------------------------------------------
# Assessments -- view / add / edit only (same reasoning as competencies:
# the spec's Delete list only mentions deleting an assessment result).
# ---------------------------------------------------------------------------
 
def list_assessments(conn: Connection) -> list[Row]:
    return conn.execute(
        """
        SELECT a.assessment_id, a.name, a.date_created,
               c.competency_id, c.name AS competency_name
        FROM assessments a
        JOIN competencies c ON a.competency_id = c.competency_id
        ORDER BY c.name, a.name
        """
    ).fetchall()
 
 
def view_assessments(conn: Connection, user: Row) -> None:
    print("\n--- Assessments ---")
    rows = list_assessments(conn)
    if not rows:
        print("No assessments yet.")
        return
    for row in rows:
        print(f"  [{row['assessment_id']}] {row['name']} "
              f"-- competency: {row['competency_name']} (added {row['date_created']})")
 
 
def choose_competency(conn: Connection) -> str | None:
    """Show competencies and prompt for a valid competency_id. Returns the
    id as a string, or None if there are no competencies to choose from."""
    rows = list_competencies(conn)
    if not rows:
        print("No competencies exist yet -- add one first.")
        return None
 
    for row in rows:
        print(f"  [{row['competency_id']}] {row['name']}")
    valid_ids = {str(row["competency_id"]) for row in rows}
    return prompt_id_or_back("Enter the competency_id", valid_ids)
 
 
def add_assessment(conn: Connection, user: Row) -> None:
    print("\n--- Add Assessment ---")
    competency_id = choose_competency(conn)
    if competency_id is None:
        return
 
    name = prompt_required("Assessment name")
 
    today = date.today().isoformat()
    cursor = conn.execute(
        "INSERT INTO assessments (competency_id, name, date_created) VALUES (?, ?, ?)",
        (competency_id, name, today),
    )
    conn.commit()
    print(f"Added assessment_id={cursor.lastrowid} ({name}).")
 
 
def edit_assessment(conn: Connection, user: Row) -> None:
    print("\n--- Edit Assessment ---")
    view_assessments(conn, user)
    rows = list_assessments(conn)
    if not rows:
        return
 
    valid_ids = {str(row["assessment_id"]) for row in rows}
    assessment_id = prompt_id_or_back("Enter the assessment_id to edit", valid_ids)
 
    print("Leave the name blank to keep it unchanged.")
    new_name = prompt("New name")
 
    new_competency_id = None
    if prompt_choice("Change the competency? (y/n)", {"y", "n"}) == "y":
        new_competency_id = choose_competency(conn)
 
    if not new_name and new_competency_id is None:
        print("No changes made.")
        return
 
    if new_name:
        conn.execute(
            "UPDATE assessments SET name = ? WHERE assessment_id = ?",
            (new_name, assessment_id),
        )
    if new_competency_id is not None:
        conn.execute(
            "UPDATE assessments SET competency_id = ? WHERE assessment_id = ?",
            (new_competency_id, assessment_id),
        )
    conn.commit()
    print("Assessment updated.")
 
 
def manage_assessments(conn: Connection, user: Row) -> None:
    while True:
        print("\n--- Manage Assessments ---")
        print("1) View assessments")
        print("2) Add an assessment")
        print("3) Edit an assessment")
        print("4) Back to manager menu")
        choice = prompt_choice("Choose an option", {"1", "2", "3", "4"})
 
        if choice == "1":
            safe_call(view_assessments, conn, user)
        elif choice == "2":
            safe_call(add_assessment, conn, user)
        elif choice == "3":
            safe_call(edit_assessment, conn, user)
        elif choice == "4":
            return

# ---------------------------------------------------------------------------
# Assessment Results -- the one entity the spec explicitly allows deleting.
# ---------------------------------------------------------------------------
 

def list_assessment_results(conn: Connection) -> list[Row]:
    return conn.execute(
        """
        SELECT ar.assessment_result_id, ar.score, ar.date_taken,
               u.user_id, u.first_name, u.last_name,
               a.name AS assessment_name,
               m.first_name AS manager_first_name, m.last_name AS manager_last_name
        FROM assessment_results ar
        JOIN users u ON ar.user_id = u.user_id
        JOIN assessments a ON ar.assessment_id = a.assessment_id
        LEFT JOIN users m ON ar.manager_id = m.user_id
        ORDER BY ar.date_taken DESC, ar.assessment_result_id DESC
        """
    ).fetchall()
 
 
def view_assessment_results(conn: Connection, user: Row) -> None:
    print("\n--- Assessment Results ---")
    rows = list_assessment_results(conn)
    if not rows:
        print("No assessment results yet.")
        return
    for row in rows:
        manager_str = (f"{row['manager_first_name']} {row['manager_last_name']}"
                        if row["manager_first_name"] else "none")
        print(f"  [{row['assessment_result_id']}] {row['first_name']} {row['last_name']} "
              f"-- {row['assessment_name']}: score {row['score']} on {row['date_taken']} "
              f"(recorded by {manager_str})")
 
 
def choose_user(conn: Connection, prompt_label: str = "Enter the user_id") -> str | None:
    """Show all active users and prompt for a valid user_id. Returns the id
    as a string, or None if there are no active users."""
    rows = conn.execute(
        "SELECT user_id, first_name, last_name FROM users WHERE active = 1 "
        "ORDER BY last_name, first_name"
    ).fetchall()
    if not rows:
        print("No active users exist.")
        return None
 
    for row in rows:
        print(f"  [{row['user_id']}] {row['first_name']} {row['last_name']}")
    valid_ids = {str(row["user_id"]) for row in rows}
    return prompt_id_or_back(prompt_label, valid_ids)
 
 
def choose_assessment(conn: Connection) -> str | None:
    """Show all assessments and prompt for a valid assessment_id. Returns
    the id as a string, or None if there are no assessments."""
    rows = list_assessments(conn)
    if not rows:
        print("No assessments exist yet -- add one first.")
        return None
 
    for row in rows:
        print(f"  [{row['assessment_id']}] {row['name']} ({row['competency_name']})")
    valid_ids = {str(row["assessment_id"]) for row in rows}
    return prompt_id_or_back("Enter the assessment_id", valid_ids)
 
 
def prompt_score() -> str:
    return prompt_choice("Score (0-4)", {"0", "1", "2", "3", "4"})
 
 
def add_assessment_result(conn: Connection, user: Row) -> None:
    print("\n--- Add Assessment Result ---")
    target_user_id = choose_user(conn, "Enter the user_id being assessed")
    if target_user_id is None:
        return
 
    assessment_id = choose_assessment(conn)
    if assessment_id is None:
        return
 
    score = prompt_score()
    date_taken = prompt_date("Date taken (YYYY-MM-DD, blank for today)", allow_blank=True)
    if not date_taken:
        date_taken = date.today().isoformat()
 
    try:
        cursor = conn.execute(
            """
            INSERT INTO assessment_results (user_id, assessment_id, manager_id, score, date_taken)
            VALUES (?, ?, ?, ?, ?)
            """,
            (target_user_id, assessment_id, user["user_id"], score, date_taken),
        )
        conn.commit()
        print(f"Added assessment_result_id={cursor.lastrowid}.")
    except sqlite3.IntegrityError as e:
        print(f"Could not add assessment result: {e}")
 
 
def edit_assessment_result(conn: Connection, user: Row) -> None:
    print("\n--- Edit Assessment Result ---")
    view_assessment_results(conn, user)
    rows = list_assessment_results(conn)
    if not rows:
        return
 
    valid_ids = {str(row["assessment_result_id"]) for row in rows}
    result_id = prompt_id_or_back("Enter the assessment_result_id to edit", valid_ids)
 
    print("Leave a field blank to keep its current value.")
    new_score = prompt_score_optional()
    new_date = prompt_date("New date taken (YYYY-MM-DD)", allow_blank=True)
 
    if not new_score and not new_date:
        print("No changes made.")
        return
 
    if new_score:
        conn.execute(
            "UPDATE assessment_results SET score = ? WHERE assessment_result_id = ?",
            (new_score, result_id),
        )
    if new_date:
        conn.execute(
            "UPDATE assessment_results SET date_taken = ? WHERE assessment_result_id = ?",
            (new_date, result_id),
        )
    conn.commit()
    print("Assessment result updated.")
 
 
def delete_assessment_result(conn: Connection, user: Row) -> None:
    print("\n--- Delete Assessment Result ---")
    view_assessment_results(conn, user)
    rows = list_assessment_results(conn)
    if not rows:
        return
 
    valid_ids = {str(row["assessment_result_id"]) for row in rows}
    result_id = prompt_choice("Enter the assessment_result_id to delete", valid_ids)
 
    confirm = prompt_choice(f"Delete result {result_id}? This can't be undone. (y/n)", {"y", "n"})
    if confirm != "y":
        print("Cancelled.")
        return
 
    conn.execute(
        "DELETE FROM assessment_results WHERE assessment_result_id = ?", (result_id,)
    )
    conn.commit()
    print("Assessment result deleted.")
 
 
def manage_assessment_results(conn: Connection, user: Row) -> None:
    while True:
        print("\n--- Manage Assessment Results ---")
        print("1) View assessment results")
        print("2) Add an assessment result")
        print("3) Edit an assessment result")
        print("4) Delete an assessment result")
        print("5) Back to manager menu")
        choice = prompt_choice("Choose an option", {"1", "2", "3", "4", "5"})
 
        if choice == "1":
            safe_call(view_assessment_results, conn, user)
        elif choice == "2":
            safe_call(add_assessment_result, conn, user)
        elif choice == "3":
            safe_call(edit_assessment_result, conn, user)
        elif choice == "4":
            safe_call(delete_assessment_result, conn, user)
        elif choice == "5":
            return
 
 
def export_users_csv(conn: Connection, user: Row) -> None:
    filename = "users_export.csv"
    rows = conn.execute(
        "SELECT user_id, first_name, last_name, phone, email, active, "
        "date_created, hire_date, user_type FROM users ORDER BY last_name, first_name"
    ).fetchall()
 
    try:
        with open(filename, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["user_id", "first_name", "last_name", "phone", "email",
                              "active", "date_created", "hire_date", "user_type"])
            for row in rows:
                writer.writerow(list(row))
    except OSError as e:
        print(f"Could not write '{filename}': {e}")
        return
 
    print(f"Exported {len(rows)} users to {filename}.")
 
 
def export_competencies_csv(conn: Connection, user: Row) -> None:
    filename = "competencies_export.csv"
    rows = list_competencies(conn)
 
    try:
        with open(filename, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["competency_id", "name", "date_created"])
            for row in rows:
                writer.writerow(list(row))
    except OSError as e:
        print(f"Could not write '{filename}': {e}")
        return
 
    print(f"Exported {len(rows)} competencies to {filename}.")
 
 
def export_user_competency_summary_csv(conn: Connection, user: Row) -> None:
    print("\n--- Export User Competency Summary ---")
    target_user_id = choose_user(conn)
    if target_user_id is None:
        return
    target_user = conn.execute(
        "SELECT * FROM users WHERE user_id = ?", (target_user_id,)
    ).fetchone()
 
    competencies = list_competencies(conn)
    filename = f"user_{target_user_id}_competency_summary.csv"
 
    try:
        with open(filename, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["competency_name", "score"])
            total = 0
            for c in competencies:
                latest = get_latest_result(conn, target_user_id, c["competency_id"])
                score = latest["score"] if latest else 0
                total += score
                writer.writerow([c["name"], score])
            average = total / len(competencies) if competencies else 0
            writer.writerow(["AVERAGE", f"{average:.2f}"])
    except OSError as e:
        print(f"Could not write '{filename}': {e}")
        return
 
    print(f"Exported summary for {target_user['first_name']} {target_user['last_name']} to {filename}.")
 
 
def export_competency_results_summary_csv(conn: Connection, user: Row) -> None:
    print("\n--- Export Competency Results Summary ---")
    competency_id = choose_competency(conn)
    if competency_id is None:
        return
    competency = conn.execute(
        "SELECT * FROM competencies WHERE competency_id = ?", (competency_id,)
    ).fetchone()
 
    active_users = conn.execute(
        "SELECT * FROM users WHERE active = 1 ORDER BY last_name, first_name"
    ).fetchall()
    filename = f"competency_{competency_id}_results_summary.csv"
 
    try:
        with open(filename, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["user_name", "competency_score", "assessment", "date_taken"])
            total = 0
            for u in active_users:
                latest = get_latest_result(conn, u["user_id"], competency_id)
                score = latest["score"] if latest else 0
                assessment_name = latest["assessment_name"] if latest else ""
                date_taken = latest["date_taken"] if latest else ""
                total += score
                writer.writerow([f"{u['first_name']} {u['last_name']}", score, assessment_name, date_taken])
            average = total / len(active_users) if active_users else 0
            writer.writerow(["AVERAGE", f"{average:.2f}", "", ""])
    except OSError as e:
        print(f"Could not write '{filename}': {e}")
        return
 
    print(f"Exported results summary for {competency['name']} to {filename}.")
 
 
def csv_export_menu(conn: Connection, user: Row) -> None:
    while True:
        print("\n--- CSV Export ---")
        print("1) Export Users list")
        print("2) Export Competencies list")
        print("3) Export a User's Competency Summary")
        print("4) Export a Competency's Results Summary")
        print("5) Back to manager menu")
        choice = prompt_choice("Choose an option", {"1", "2", "3", "4", "5"})
 
        if choice == "1":
            safe_call(export_users_csv, conn, user)
        elif choice == "2":
            safe_call(export_competencies_csv, conn, user)
        elif choice == "3":
            safe_call(export_user_competency_summary_csv, conn, user)
        elif choice == "4":
            safe_call(export_competency_results_summary_csv, conn, user)
        elif choice == "5":
            return
 
 
def import_assessment_results_csv(conn: Connection, user: Row) -> None:
    print("\n--- Import Assessment Results from CSV ---")
    filename = prompt("CSV filename (e.g. results.csv)")
 
    required_columns = {"user_id", "assessment_id", "score", "date_taken"}
 
    try:
        f = open(filename, newline="")
    except OSError as e:
        print(f"Couldn't open '{filename}': {e}")
        return
 
    imported = 0
    skipped = 0
 
    with f:
        reader = csv.DictReader(f)
 
        if reader.fieldnames is None or not required_columns.issubset(set(reader.fieldnames)):
            print(f"CSV is missing required columns. Expected at least: {', '.join(sorted(required_columns))}")
            return
 
        for row_num, row in enumerate(reader, start=2):  # row 1 is the header
            try:
                user_id = int(row["user_id"])
                assessment_id = int(row["assessment_id"])
                score = int(row["score"])
                date_taken = row["date_taken"].strip()
 
                if not (0 <= score <= 4):
                    raise ValueError(f"score {score} out of range 0-4")
                date.fromisoformat(date_taken)  # raises ValueError if malformed/blank
 
                conn.execute(
                    """
                    INSERT INTO assessment_results (user_id, assessment_id, manager_id, score, date_taken)
                    VALUES (?, ?, NULL, ?, ?)
                    """,
                    (user_id, assessment_id, score, date_taken),
                )
                imported += 1
            except (ValueError, KeyError, sqlite3.IntegrityError) as e:
                print(f"  Skipped row {row_num}: {e}")
                skipped += 1
 
    conn.commit()
    print(f"\nImport complete: {imported} row(s) imported, {skipped} row(s) skipped.")
 
 
def csv_import_menu(conn: Connection, user: Row) -> None:
    safe_call(import_assessment_results_csv, conn, user)


# ---------------------------------------------------------------------------
# Competencies -- view / add / edit only. The requirements only list
# "delete an assessment result" under Delete, so competencies don't get
# a delete option here.
# ---------------------------------------------------------------------------
 

def list_competencies(conn: Connection) -> list[Row]:
    return conn.execute(
        "SELECT competency_id, name, date_created FROM competencies ORDER BY name"
    ).fetchall()
 
 
def view_competencies(conn: Connection, user: Row) -> None:
    print("\n--- Competencies ---")
    rows = list_competencies(conn)
    if not rows:
        print("No competencies yet.")
        return
    for row in rows:
        print(f"  [{row['competency_id']}] {row['name']} (added {row['date_created']})")
 
 
def add_competency(conn: Connection, user: Row) -> None:
    print("\n--- Add Competency ---")
    name = prompt_required("Competency name")
 
    today = date.today().isoformat()
    cursor = conn.execute(
        "INSERT INTO competencies (name, date_created) VALUES (?, ?)",
        (name, today),
    )
    conn.commit()
    print(f"Added competency_id={cursor.lastrowid} ({name}).")
 
 
def edit_competency(conn: Connection, user: Row) -> None:
    print("\n--- Edit Competency ---")
    view_competencies(conn, user)
    rows = list_competencies(conn)
    if not rows:
        return
 
    valid_ids = {str(row["competency_id"]) for row in rows}
    competency_id = prompt_choice("Enter the competency_id to edit", valid_ids)
 
    new_name = prompt("New name (leave blank to cancel)")
    if not new_name:
        print("No changes made.")
        return
 
    conn.execute(
        "UPDATE competencies SET name = ? WHERE competency_id = ?",
        (new_name, competency_id),
    )
    conn.commit()
    print("Competency updated.")
 
 
def manage_competencies(conn: Connection, user: Row) -> None:
    while True:
        print("\n--- Manage Competencies ---")
        print("1) View competencies")
        print("2) Add a competency")
        print("3) Edit a competency")
        print("4) Back to manager menu")
        choice = prompt_choice("Choose an option", {"1", "2", "3", "4"})
 
        if choice == "1":
            safe_call(view_competencies, conn, user)
        elif choice == "2":
            safe_call(add_competency, conn, user)
        elif choice == "3":
            safe_call(edit_competency, conn, user)
        elif choice == "4":
            return
 
 
def manager_menu(conn: Connection, user: Row) -> None:
    while True:
        print("\n--- Manager Menu ---")
        print("1) View my profile")
        print("2) Edit my name")
        print("3) Change my password")
        print("4) View all users")
        print("5) Search users")
        print("6) Add a user")
        print("7) Edit a user")
        print("8) View a user's competency report")
        print("9) View a user's assessment history")
        print("10) Manage competencies")
        print("11) Manage assessments")
        print("12) Manage assessment results")
        print("13) View competency results summary (all users)")
        print("14) Export CSV")
        print("15) Import CSV")
        print("16) Log out")
 
        choice = prompt_choice(
            "Choose an option",
            {str(n) for n in range(1, 17)},
        )
 
        if choice == "1":
            safe_call(view_own_profile, conn, user)
        elif choice == "2":
            updated = safe_call(edit_own_name, conn, user)
            if updated is not None:
                user = updated
        elif choice == "3":
            safe_call(change_own_password, conn, user)
        elif choice == "4":
            safe_call(view_all_users, conn, user)
        elif choice == "5":
            safe_call(search_users, conn, user)
        elif choice == "6":
            safe_call(add_user, conn, user)
        elif choice == "7":
            safe_call(edit_user, conn, user)
        elif choice == "8":
            safe_call(view_user_competency_report, conn, user)
        elif choice == "9":
            safe_call(view_assessments_for_user, conn, user)
        elif choice == "10":
            manage_competencies(conn, user)
        elif choice == "11":
            manage_assessments(conn, user)
        elif choice == "12":
            manage_assessment_results(conn, user)
        elif choice == "13":
            safe_call(view_competency_results_summary, conn, user)
        elif choice == "14":
            csv_export_menu(conn, user)
        elif choice == "15":
            safe_call(csv_import_menu, conn, user)
        elif choice == "16":
            print("Logging out...")
            return
 
# ---------------------------------------------------------------------------
# App loop
# ---------------------------------------------------------------------------
 
def main() -> None:
    try:
        conn: Connection = get_connection()
    except sqlite3.Error as e:
        print(f"Could not connect to the database: {e}")
        return
 
    try:
        while True:
            user = login_screen(conn)
            if user is None:
                print("Goodbye.")
                break
 
            if user["user_type"] == "manager":
                manager_menu(conn, user)
            else:
                user_menu(conn, user)
            # loop back to login_screen after logout
    except (KeyboardInterrupt, EOFError):
        print("\n\nGoodbye.")
    except Exception as e:
        print(f"\nAn unexpected error occurred and the app needs to close: {e}")
    finally:
        conn.close()
 
 
if __name__ == "__main__":
    main()
