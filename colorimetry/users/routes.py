""" User routes"""
from math import ceil
from bson.objectid import ObjectId
from flask import current_app, request, render_template, url_for, Blueprint, flash, redirect
from flask_login import login_user, logout_user, current_user, login_required
from itsdangerous import URLSafeTimedSerializer
import requests
from colorimetry.users.forms import (RegistrationForm, LoginForm,
                                   RequestResetForm, ResetPasswordForm)
from colorimetry.services.user_service import register_user, authenticate_user, admin_required, update_password
from colorimetry.users.models import User
from colorimetry.services.query_service import (get_user_samples,
                                                paginated_deleted_sample_list,
                                                get_deleted_sample_count, retrieve_sites,
                                                delete_site)


users = Blueprint('users', __name__)

def serialize_doc(doc):
    doc["_id"] = str(doc["_id"])
    return doc


def generate_reset_token(user_id):
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return s.dumps(str(user_id), salt='password-reset')


def verify_reset_token(token, max_age=1800):  # 30 minutes
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        return s.loads(token, salt='password-reset', max_age=max_age)
    except Exception:
        return None


def send_reset_email(user, token):
    reset_url = url_for("users.reset_token", token=token, _external=True)

    payload = {
        "from": "Password Reset <no-reply@cupofcarbon.gla.ac.uk>",
        "to": [user["email"]],
        "subject": "Password Reset",
        "text": f"To reset your password,"
                f" click the link:\n{reset_url}\n\nIf you didn't request this, ignore this email."
    }
    #print("Loaded RESEND_API_KEY:", repr(current_app.config.get("RESEND_API_KEY")))

    r = requests.post(
        "https://api.resend.com/emails",
        json=payload,
        headers={"Authorization": f"Bearer {current_app.config['RESEND_API_KEY']}"}
    )

    print("Email response:", r.status_code, r.text)


@users.route("/register", methods=['GET', 'POST'])
def register():
    form = RegistrationForm()

    if request.method == "POST":
        recaptcha_response = request.form.get('g-recaptcha-response')

        if not recaptcha_response:
            flash("Please complete the reCAPTCHA.", "danger")
            return redirect(url_for("users.register"))

        if not verify_recaptcha(recaptcha_response):
            flash("reCAPTCHA validation failed.", "danger")
            return redirect(url_for("users.register"))

        if form.validate_on_submit():

            username = form.username.data
            email = form.email.data
            password = form.password.data

            result = register_user(username, email, password)

            if result["success"]:
                flash("Account created successfully! Please log in.", "success")
                return redirect(url_for("users.login"))

            flash(result["message"], "danger")

    return render_template("users/register.html",
                           title="Register",
                           form=form)



@users.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))  # adjust to your landing endpoint

    form = LoginForm()

    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        remember = form.remember.data

        result = authenticate_user(email, password)
        if result["success"]:
            # Fetch the full user doc to wrap for Flask-Login
            doc = current_app.db.users.find_one({"_id": ObjectId(result["user_id"])})
            user = User(doc)
            login_user(user, remember=remember)

            flash("Logged in successfully.", "success")

            # Handle ?next=/protected for redirects after login
            next_page = request.args.get("next")
            return redirect(next_page or url_for("main.home"))
        flash(result["message"], "danger")

    return render_template("users/login.html", title="Log In", form=form)



@users.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("users.login"))


@users.route("/account")
@login_required
def account():
    user_samples = get_user_samples(current_user.username)

    for s in user_samples:
        s["properties"]["link"] = url_for("data.sample", sample_id=s["_id"])

    user_samples = [serialize_doc(s) for s in user_samples]

    return render_template("users/account.html", title="My Account", user_samples=user_samples)



def verify_recaptcha(response_token):
    secret = current_app.config['RECAPTCHA_SECRET_KEY']
    verify_url = "https://www.google.com/recaptcha/api/siteverify"

    payload = {
        'secret': secret,
        'response': response_token
    }

    r = requests.post(verify_url, data=payload)
    result = r.json()

    return result.get('success', False)


@users.route("/admin")
@admin_required
def admin():
    try:
        page = max(int(request.args.get("page", 1)), 1)
    except ValueError:
        page = 1
    per_page = 10

    sample_count = get_deleted_sample_count()
    total_pages = max(ceil(sample_count/per_page), 1)

    if page > total_pages:
        page = total_pages

    samples = paginated_deleted_sample_list(page, per_page)

    sites = retrieve_sites()

    return render_template("users/admin.html",
                           samples=samples,
                           page=page,
                           per_page=per_page,
                           sample_count=sample_count,
                           total_pages=total_pages,
                           sites=sites)


@users.route("/reset_password", methods=["GET", "POST"])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    form = RequestResetForm()

    if form.validate_on_submit():
        email = form.email.data
        user = current_app.db.users.find_one({"email": email})

        flash("If that email exists, a reset link has been sent.", "info")

        if user:
            token = generate_reset_token(user["_id"])
            send_reset_email(user, token)

        return redirect(url_for("users.login"))

    return render_template("users/request.html",
                           title="Reset Password",
                           form=form)


@users.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for("main.home"))

    user_id = verify_reset_token(token)
    if user_id is None:
        flash("The reset link is invalid or expired.", "danger")
        return redirect(url_for("users.reset_request"))

    form = ResetPasswordForm()

    if form.validate_on_submit():
        update_password(user_id, form.password.data)

        flash("Your password has been updated!", "success")
        return redirect(url_for("users.login"))

    return render_template("users/reset.html",
                           title="Reset Password",
                           form=form)
