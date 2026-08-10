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
