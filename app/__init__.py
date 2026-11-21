import os

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()

DEV_SECRET_KEY = "dev-only-change-me"


def create_app(test_config=None):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", DEV_SECRET_KEY)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///stockflow.db")
    app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["PASSWORD_HASH_METHOD"] = "scrypt"

    app.config["AI_PROVIDER"] = os.environ.get("AI_PROVIDER", "")
    app.config["GEMINI_API_KEY"] = os.environ.get("GEMINI_API_KEY", "")
    app.config["GEMINI_MODEL"] = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
    app.config["OLLAMA_URL"] = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    app.config["OLLAMA_MODEL"] = os.environ.get("OLLAMA_MODEL", "llama3.2")
    app.config["LLM_CLIENT"] = None

    if test_config:
        app.config.update(test_config)

    is_production = os.environ.get("APP_ENV") == "production"
    if is_production and app.config["SECRET_KEY"] == DEV_SECRET_KEY:
        raise RuntimeError("SECRET_KEY must be set in production.")

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = "login"
    login_manager.login_message_category = "warning"

    from .api import register_api_routes
    from .auth import register_auth_routes
    from .orders import register_order_routes
    from .routes import register_routes
    from .seed import register_commands
    from .tools import register_tool_routes

    register_auth_routes(app)
    register_routes(app)
    register_order_routes(app)
    register_tool_routes(app)
    register_api_routes(app)
    register_commands(app)

    return app