"""
main.py
 
Console entry point for the Competency Tracking Tool.
Run with: pipenv run python main.py
 
Handles the login loop, then branches into a user menu or a manager
menu based on users.user_type. 
"""
 
from db import get_connection
from auth import authenticate, create_user, hash_password

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
