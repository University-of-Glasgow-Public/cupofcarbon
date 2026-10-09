""" User models """
from bson.objectid import ObjectId
from flask_login import UserMixin
from flask import current_app
from colorimetry.extensions import login_manager

class User(UserMixin):
    def __init__(self, doc):
        self.doc = doc

    @property
    def id(self):
        return str(self.doc["_id"])

    @property
    def username(self):
        return self.doc.get("username")

    @property
    def email(self):
        return self.doc.get("email")

    @property
    def role(self):
        # Default to "user" if missing (backwards compatible)
        return self.doc.get("role", "user")

    def is_admin(self):
        return self.role == "admin"


@login_manager.user_loader
def load_user(user_id):
    """Load user from MongoDB using the session user_id."""
    try:
        doc = current_app.db.users.find_one({"_id": ObjectId(user_id)})
        return User(doc) if doc else None
    except Exception:
        return None
