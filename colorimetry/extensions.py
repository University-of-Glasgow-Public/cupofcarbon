from pymongo import MongoClient
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail

mongo: MongoClient | None = None
bcrypt = Bcrypt()
login_manager = LoginManager()
mail = Mail()
