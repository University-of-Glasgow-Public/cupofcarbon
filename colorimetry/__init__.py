""" Iinitialize app """
from flask import Flask
from pymongo import MongoClient
import certifi
from colorimetry.config import Config
from colorimetry.extensions import bcrypt, login_manager, mail


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # --- MongoDB setup (replaces flask-pymongo) ---
    mongo_uri = Config.MONGO_URL

    # client = MongoClient(
    #     mongo_uri,
    #     tls=True,
    #     tlsCAFile=certifi.where(),
    #     serverSelectionTimeoutMS=10000
    # )

    client = MongoClient(mongo_uri)

    # Attach to app (canonical Flask pattern)
    app.mongo = client
    app.db = client["colorimetry_db"]

    # Create indexes
    with app.app_context():
        app.db.samples.create_index([("geometry", "2dsphere")])
        app.db.sites.create_index([("geometry", "2dsphere")])

    # --- Flask extensions ---
    bcrypt.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "users.login"
    login_manager.login_message_category = "info"
    mail.init_app(app)

    # --- Blueprints ---
    from colorimetry.main.routes import main
    from colorimetry.users.routes import users
    from colorimetry.data.routes import data
    from colorimetry.image.routes import image

    app.register_blueprint(main)
    app.register_blueprint(users)
    app.register_blueprint(data)
    app.register_blueprint(image)

    return app