from functools import wraps
from urllib.parse import urlparse

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from . import db, login_manager
from .models import User


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return login_manager.unauthorized()
        if not current_user.is_admin:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


def is_safe_next_url(target):
    if not target or not target.startswith("/") or target.startswith("//"):
        return False
    if "\\" in target:
        return False
    parsed = urlparse(target)
    return not parsed.scheme and not parsed.netloc


def register_auth_routes(app):

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("products"))

        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            query = db.select(User).filter_by(username=username)
            user = db.session.execute(query).scalar_one_or_none()

            if user is None or not user.check_password(password):
                flash("Invalid username or password.", "danger")
                return render_template("login.html", username=username), 401

            login_user(user)
            flash(f"Welcome back, {user.username}!", "success")

            next_url = request.args.get("next")
            if not is_safe_next_url(next_url):
                next_url = url_for("products")
            return redirect(next_url)

        return render_template("login.html", username="")

    @app.route("/logout", methods=["POST"])
    @login_required
    def logout():
        logout_user()
        flash("You have been logged out.", "success")
        return redirect(url_for("login"))