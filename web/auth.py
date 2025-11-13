"""
Authentication module for D&D Dungeon Manager
Handles user registration, login, and session management
"""

import hashlib
from functools import wraps
from flask import session, jsonify
from core.db import db, utcnow


def hash_password(password: str) -> str:
    """Hash a password using SHA-256 (simple hashing for demo purposes)."""
    return hashlib.sha256(password.encode()).hexdigest()


def create_user(username: str, password: str) -> dict:
    """Create a new user account."""
    users_coll = db().users
    
    # Check if user already exists
    existing = users_coll.find_one({"username": username})
    if existing:
        return {"status": "error", "message": "Username already exists"}
    
    # Create new user
    user_doc = {
        "username": username,
        "password_hash": hash_password(password),
        "created_at": utcnow(),
    }
    users_coll.insert_one(user_doc)
    
    return {"status": "ok", "user_id": str(user_doc["_id"])}


def verify_user(username: str, password: str) -> dict:
    """Verify user credentials and return user info."""
    users_coll = db().users
    user = users_coll.find_one({"username": username})
    
    if not user:
        return {"status": "error", "message": "Invalid username or password"}
    
    password_hash = hash_password(password)
    if user["password_hash"] != password_hash:
        return {"status": "error", "message": "Invalid username or password"}
    
    return {
        "status": "ok",
        "user_id": str(user["_id"]),
        "username": user["username"]
    }


def get_current_user_id():
    """Get the current logged-in user ID from session."""
    return session.get("user_id")


def get_current_username():
    """Get the current logged-in username from session."""
    return session.get("username")


def require_auth(f):
    """Decorator to require authentication for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = get_current_user_id()
        if not user_id:
            return jsonify({"status": "error", "message": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated_function


def ensure_users_index():
    """Ensure unique index on username."""
    try:
        db().users.create_index("username", unique=True)
    except Exception as e:
        # Index might already exist, that's okay
        pass

