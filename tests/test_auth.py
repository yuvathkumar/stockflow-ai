from app import db
from app.models import Product, User


def test_login_page_loads(client):
    response = client.get("/login")

    assert response.status_code == 200
    assert b"Log in" in response.data


def test_login_with_valid_credentials(client):
    response = client.post(
        "/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Welcome back, admin!" in response.data


def test_login_with_wrong_password_fails(client):
    response = client.post("/login", data={"username": "admin", "password": "wrong"})

    assert response.status_code == 401
    assert b"Invalid username or password" in response.data


def test_login_with_unknown_user_gives_same_message(client):
    response = client.post("/login", data={"username": "nobody", "password": "x"})

    assert response.status_code == 401
    assert b"Invalid username or password" in response.data


def test_products_require_login(client):
    response = client.get("/products")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_staff_can_view_products(staff_client):
    response = staff_client.get("/products")

    assert response.status_code == 200


def test_staff_cannot_open_add_form(staff_client):
    response = staff_client.get("/products/new")

    assert response.status_code == 403


def test_staff_cannot_delete_product(staff_client):
    response = staff_client.post("/products/1/delete")

    assert response.status_code == 403
    assert db.session.get(Product, 1) is not None


def test_staff_does_not_see_admin_buttons(staff_client):
    response = staff_client.get("/products")

    assert b"+ Add product" not in response.data


def test_logout(admin_client):
    response = admin_client.post("/logout", follow_redirects=True)

    assert b"You have been logged out" in response.data
    assert admin_client.get("/products").status_code == 302


def test_passwords_are_stored_hashed(app):
    query = db.select(User).filter_by(username="admin")
    user = db.session.execute(query).scalar_one()

    assert user.password_hash != "admin123"
    assert user.check_password("admin123")


def test_login_blocks_external_redirect(client):
    response = client.post(
        "/login?next=https://evil.example.com",
        data={"username": "admin", "password": "admin123"},
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/products")