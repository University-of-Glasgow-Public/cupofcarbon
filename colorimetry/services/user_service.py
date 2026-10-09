""" Service for user based functions """
from functools import wraps
from bson.objectid import ObjectId
from flask import current_app, abort
from flask_login import current_user, login_required
from colorimetry.extensions import bcrypt


def get_user_collection():
    return current_app.db.users


def register_user(username, email, password):
    users = get_user_collection()

    if users.find_one({"email": email}):
        return {"success": False, "message": "Email already exists"}

    if users.find_one({"username": username}):
        return {"success": False, "message": "Username already taken"}

    hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")

    user = {
        "username": username,
        "email": email,
        "password": hashed_pw,
        "role": "user"
    }

    result = users.insert_one(user)

    return {
        "success": True,
        "user_id": str(result.inserted_id),
        "message": "User registered successfully"
    }


def authenticate_user(email, password):
    users = get_user_collection()

    user = users.find_one({"email": email})

    if not user:
        return {"success": False, "message": "User not found"}

    if not bcrypt.check_password_hash(user["password"], password):
        return {"success": False, "message": "Incorrect password"}

    return {
        "success": True,
        "user_id": str(user["_id"]),
        "message": "Authenticated successfully"
    }


def set_user_role(user_id, role):
    """Promote/demote user by setting their role."""
    users = get_user_collection()
    result = users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"role": role}}
    )
    return result.modified_count > 0


def roles_required(*roles):
    """Restrict a route to users with one of the given roles."""
    def decorator(f):
        @wraps(f)
        @login_required
        def wrapper(*args, **kwargs):
            if current_user.role not in roles:
                return abort(403)
            return f(*args, **kwargs)
        return wrapper
    return decorator


def update_password(user_id, password):
    users = get_user_collection()

    hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")

    result = users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"password": hashed_pw}}
    )

    return result.modified_count > 0


def admin_required(f):
    """Shortcut for @roles_required('admin')"""
    return roles_required("admin")(f)
