from app import db
from app.models import Product


def get_product(name):
    db.session.expire_all()
    query = db.select(Product).filter_by(name=name)
    return db.session.execute(query).scalar_one_or_none()


def valid_form(**overrides):
    form = {"name": "Salt 1kg", "quantity": "30", "price": "25", "reorder_level": "10"}
    form.update(overrides)
    return form


def test_products_listed_from_database(admin_client):
    response = admin_client.get("/products")

    assert response.status_code == 200
    assert b"Rice 25kg" in response.data
    assert b"Tea Powder 500g" in response.data


def test_create_product(admin_client):
    response = admin_client.post("/products/new", data=valid_form(), follow_redirects=True)

    assert response.status_code == 200
    assert b"Added Salt 1kg" in response.data
    assert get_product("Salt 1kg").quantity == 30


def test_create_product_rejects_negative_quantity(admin_client):
    response = admin_client.post("/products/new", data=valid_form(quantity="-5"))

    assert response.status_code == 400
    assert b"Quantity cannot be negative" in response.data
    assert get_product("Salt 1kg") is None


def test_create_product_rejects_text_price(admin_client):
    response = admin_client.post("/products/new", data=valid_form(price="abc"))

    assert response.status_code == 400
    assert b"Price must be a number" in response.data


def test_create_product_rejects_duplicate_name(admin_client):
    response = admin_client.post("/products/new", data=valid_form(name="Rice 25kg"))

    assert response.status_code == 400
    assert b"already exists" in response.data


def test_edit_product(admin_client):
    product = get_product("Sugar 5kg")

    response = admin_client.post(
        f"/products/{product.id}/edit",
        data=valid_form(name="Sugar 5kg", quantity="50"),
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert get_product("Sugar 5kg").quantity == 50


def test_archive_product(admin_client):
    product = get_product("Tea Powder 500g")

    response = admin_client.post(f"/products/{product.id}/archive", follow_redirects=True)

    assert response.status_code == 200
    assert b"Archived Tea Powder 500g" in response.data
    assert get_product("Tea Powder 500g").is_active is False

    listing = admin_client.get("/products")
    assert b"Tea Powder 500g" not in listing.data


def test_archived_product_cannot_be_edited(admin_client):
    product = get_product("Tea Powder 500g")
    admin_client.post(f"/products/{product.id}/archive")

    response = admin_client.get(f"/products/{product.id}/edit")

    assert response.status_code == 404


def test_edit_missing_product_returns_404(admin_client):
    response = admin_client.get("/products/999/edit")

    assert response.status_code == 404