"""
main.py
 
Console entry point for the Competency Tracking Tool.
Run with: pipenv run python main.py
 
Handles the login loop, then branches into a user menu or a manager
menu based on users.user_type. 
"""
 
from db import get_connection
from auth import authenticate, create_user, hash_password

import csv
import sqlite3
from datetime import date

# ---------------------------------------------------------------------------
# Small input helpers
# ---------------------------------------------------------------------------
 
def prompt(label: str) -> str:
    return input(f"{label}: ").strip()
 
 
def prompt_choice(label: str, valid_choices) -> str:
    while True:
        choice = prompt(label)
        if choice in valid_choices:
            return choice
        print(f"  Please enter one of: {', '.join(valid_choices)}")

 
# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
 
def login_screen(conn):
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
        user = authenticate(conn, email, password)
 
        if user is None:
            print("Login failed. Check your email/password (or the account may be inactive).")
            continue
 
        print(f"\nWelcome, {user['first_name']} {user['last_name']}!")
        return user


# ---------------------------------------------------------------------------
# Shared / "user" features -- both user_type='user' and 'manager' can do these
# ---------------------------------------------------------------------------
 
def view_own_profile(conn, user):
    print("\n--- Your Profile ---")
    print(f"Name:        {user['first_name']} {user['last_name']}")
    print(f"Email:       {user['email']}")
    print(f"Phone:       {user['phone']}")
    print(f"User type:   {user['user_type']}")
    print(f"Hire date:   {user['hire_date']}")
    print(f"Active:      {'Yes' if user['active'] else 'No'}")
 
 
def change_own_password(conn, user):
    print("\n--- Change Password ---")
    new_password = prompt("New password")
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

def get_latest_result(conn, user_id, competency_id):
    """Most recent assessment_result for a given user + competency, or 
    None if that user has never been assessed on that competency."""
    return conn.execute(
                        """
                        SELECT ar.score, asmt.name AS assessment_name, ar.date_taken
                        FROM assessment_results ar
                        JOIN assessments asmt ON ar.assessment_id = asmt.assessment_id
                        WHERE ar.user_id = ? AND asmt.competency_id = ?
                        ORDER BY ar.date_taken DESC, ar.assessment_result_id DESC
                        LIMIT 1
                        """,
                        (user_id, competency_id),
    ).fetchone()


def print_user_competency_summary(conn, target_user):
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


def view_own_competency_summary(conn, user):
    print_user_competency_summary(conn, user)
 
def user_menu(conn, user):
    while True:
        print("\n--- User Menu ---")
        print("1) View my profile")
        print("2) Change my password")
        print("3) View my competency summary")
        print("4) Log out")
        choice = prompt_choice("Choose an option", {"1", "2", "3", "4"})
 
        if choice == "1":
            view_own_profile(conn, user)
        elif choice == "2":
            change_own_password(conn, user)
        elif choice == "3":
            view_own_competency_summary(conn, user)
        elif choice == "4":
            print("Logging out...")
            return


 
# ---------------------------------------------------------------------------
# Manager-only features
# ---------------------------------------------------------------------------
 
def view_all_users(conn, user):
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
 
 
def search_users(conn, user):
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
 
 
def add_user(conn, user):
    print("\n--- Add User ---")
    first_name = prompt("First name")
    last_name = prompt("Last name")
    phone = prompt("Phone")
    email = prompt("Email")
    password = prompt("Temporary password")
    hire_date = prompt("Hire date (YYYY-MM-DD)")
    user_type = prompt_choice("User type (user/manager)", {"user", "manager"})
 
    try:
        new_id = create_user(
            conn, first_name, last_name, phone, email, password, hire_date, user_type
        )
        print(f"Created user_id={new_id}.")
    except Exception as e:
        print(f"Could not create user: {e}")


# ---------------------------------------------------------------------------
# Competencies -- view / add / edit only. The requirements only list
# "delete an assessment result" under Delete, so competencies don't get
# a delete option here.
# ---------------------------------------------------------------------------
 
def list_competencies(conn):
    return conn.execute(
        "SELECT competency_id, name, date_created FROM competencies ORDER BY name"
    ).fetchall()
 
 
def view_competencies(conn, user):
    print("\n--- Competencies ---")
    rows = list_competencies(conn)
    if not rows:
        print("No competencies yet.")
        return
    for row in rows:
        print(f"  [{row['competency_id']}] {row['name']} (added {row['date_created']})")
 
 
def add_competency(conn, user):
    print("\n--- Add Competency ---")
    name = prompt("Competency name")
    if not name:
        print("Name can't be blank. Nothing was added.")
        return
 
    today = date.today().isoformat()
    cursor = conn.execute(
        "INSERT INTO competencies (name, date_created) VALUES (?, ?)",
        (name, today),
    )
    conn.commit()
    print(f"Added competency_id={cursor.lastrowid} ({name}).")
 
 
def edit_competency(conn, user):
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
 
 
def manage_competencies(conn, user):
    while True:
        print("\n--- Manage Competencies ---")
        print("1) View competencies")
        print("2) Add a competency")
        print("3) Edit a competency")
        print("4) Back to manager menu")
        choice = prompt_choice("Choose an option", {"1", "2", "3", "4"})
 
        if choice == "1":
            view_competencies(conn, user)
        elif choice == "2":
            add_competency(conn, user)
        elif choice == "3":
            edit_competency(conn, user)
        elif choice == "4":
            return


#
#
#
 
def manager_menu(conn, user):
    while True:
        print("\n--- Manager Menu ---")
        print("1) View my profile")
        print("2) Change my password")
        print("3) View all users")
        print("4) Search users")
        print("5) Add a user")
        print("6) View a user's competency report")
        print("7) Manage competencies")
        print("8) Manage assessments")
        print("9) Manage assessment results")
        print("10) View competency results summary (all users)")
        print("11) Export CSV")
        print("12) Import CSV")
        print("13) Log out")
 
        choice = prompt_choice(
            "Choose an option",
            {str(n) for n in range(1, 14)},
        )
 
        if choice == "1":
            view_own_profile(conn, user)
        elif choice == "2":
            change_own_password(conn, user)
        elif choice == "3":
            view_all_users(conn, user)
        elif choice == "4":
            search_users(conn, user)
        elif choice == "5":
            add_user(conn, user)
        elif choice == "6":
            view_user_competency_report(conn, user)
        elif choice == "7":
            manage_competencies(conn, user)
        elif choice == "8":
            manage_assessments(conn, user)
        elif choice == "9":
            manage_assessment_results(conn, user)
        elif choice == "10":
            view_competency_results_summary(conn, user)
        elif choice == "11":
            csv_export_menu(conn, user)
        elif choice == "12":
            csv_import_menu(conn, user)
        elif choice == "13":
            print("Logging out...")
            return
 
 
# ---------------------------------------------------------------------------
# App loop
# ---------------------------------------------------------------------------
 
def main():
    conn = get_connection()
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
    finally:
        conn.close()
 
 
if __name__ == "__main__":
    main()
