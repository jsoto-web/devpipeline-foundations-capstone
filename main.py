"""
main.py
 
Console entry point for the Competency Tracking Tool.
Run with: pipenv run python main.py
 
Handles the login loop, then branches into a user menu or a manager
menu based on users.user_type. 
"""
 
from db import get_connection
from auth import authenticate, create_user, hash_password
 
