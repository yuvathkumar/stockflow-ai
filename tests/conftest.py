import pytest

from app import create_app, db
from app.seed import seed_products, seed_users


@pytest.fixture
def app():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
        "AI_PROVIDER": "",
        "LLM_CLIENT": None,
    })
    with app.app_context():
        db.create_all()
        seed_products()
        seed_users()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def log_in(client, username, password):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


@pytest.fixture
def admin_client(client):
    log_in(client, "admin", "admin123")
    return client


@pytest.fixture
def staff_client(client):
    log_in(client, "staff", "staff123")
    return client