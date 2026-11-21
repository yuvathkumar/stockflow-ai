import os

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


def create_app(test_config=None):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-only-change-me")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///stockflow.db"
    app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024

    if test_config:
        app.config.update(test_config)

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