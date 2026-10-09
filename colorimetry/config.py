import os
from dotenv import load_dotenv

load_dotenv()


class Config():

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret")
    MONGO_URL = os.getenv("MONGO_URI", "mongodb://localhost:27017/colorimetry_db")
    UPLOAD_FOLDER = "static\\upload_images"
    RECAPTCHA_SITE_KEY = os.environ.get("RECAPTCHA_SITE_KEY", "")
    RECAPTCHA_SECRET_KEY = os.environ.get("RECAPTCHA_SECRET_KEY", "")
    RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")