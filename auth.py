from werkzeug.security import generate_password_hash, check_password_hash
from flask import session
from models import User
from database import db

def register_user(username, password, role="teacher"):
    """
    Registers a new user securely with a hashed password.
    Returns (success_boolean, message_string).
    """
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        return False, "Username already exists."
    
    hashed_pw = generate_password_hash(password)
    new_user = User(username=username, password_hash=hashed_pw, role=role)
    
    try:
        db.session.add(new_user)
        db.session.commit()
        return True, "User registered successfully."
    except Exception as e:
        db.session.rollback()
        return False, f"Database error: {str(e)}"

def verify_and_login(username, password):
    """
    Verifies stored hashes. If matched, injects authentication signatures directly into the Flask session block.
    Returns (success_boolean, message_string).
    """
    user = User.query.filter_by(username=username).first()
    
    if not user or not check_password_hash(user.password_hash, password):
        return False, "Invalid username or password."
    
    # Track critical authentication identifiers cleanly inside Flask Sessions
    session['user_id'] = user.id
    session['username'] = user.username
    session['role'] = user.role
    
    return True, "Login successful."

def logout_user():
    """
    Wipes the active user's Flask session destroying their authentication context natively.
    """
    session.clear()
