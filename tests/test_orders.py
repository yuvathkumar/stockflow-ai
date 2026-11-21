import pytest

from app import db
from app.models import Order, Product, StockMovement, User
from app.services import OrderError, place_order


def get_product(name):
    db.session.expire_all()
    query = db.select(Product).filter_by(name=name)
    return db.session.execute(query).scalar_one()


def order_count():
    return db.session.execute(db.select(db.func.count(Order.id))).scalar_one()


def test_new_order_form_lists_products(staff_client):
    response = staff_client.get("/orders/new")

    assert response.status_code == 200
    assert b"Rice 25kg" in response.data
    assert b"Place order" in response.data


def test_place_order_reduces_stock(staff_client):
    rice = get_product("Rice 25kg")

    response = staff_client.post(
        "/orders/new", data={f"qty_{rice.id}": "5"}, follow_redirects=True
    )

    assert response.status_code == 200
    assert b"Order #1 placed" in response.data
    assert get_product("Rice 25kg").quantity == 35


def test_order_records_items_and_total(staff_client):
    rice = get_product("Rice 25kg")
    sugar = get_product("Sugar 5kg")

    staff_client.post("/orders/new", data={f"qty_{rice.id}": "2", f"qty_{sugar.id}": "3"})

    db.session.expire_all()
    order = db.session.execute(db.select(Order)).scalar_one()
    assert len(order.items) == 2
    assert order.total == 2 * 1200 + 3 * 250
    assert order.created_by.username == "staff"


def test_order_rejected_when_stock_too_low(staff_client):
    tea = get_product("Tea Powder 500g")

    response = staff_client.post("/orders/new", data={f"qty_{tea.id}": "6"})

    assert response.status_code == 400
    assert b"Not enough stock for Tea Powder 500g" in response.data
    assert get_product("Tea Powder 500g").quantity == 5
    assert order_count() == 0


def test_order_is_all_or_nothing(staff_client):
    rice = get_product("Rice 25kg")
    tea = get_product("Tea Powder 500g")

    response = staff_client.post(
        "/orders/new", data={f"qty_{rice.id}": "5", f"qty_{tea.id}": "6"}
    )

    assert response.status_code == 400
    assert get_product("Rice 25kg").quantity == 40
    assert get_product("Tea Powder 500g").quantity == 5
    assert order_count() == 0


def test_empty_order_rejected(staff_client):
    response = staff_client.post("/orders/new", data={})

    assert response.status_code == 400
    assert b"Add at least one product" in response.data


def test_order_rejects_negative_quantity(staff_client):
    rice = get_product("Rice 25kg")

    response = staff_client.post("/orders/new", data={f"qty_{rice.id}": "-3"})

    assert response.status_code == 400
    assert b"cannot be negative" in response.data
    assert order_count() == 0


def test_order_rejects_text_quantity(staff_client):
    rice = get_product("Rice 25kg")

    response = staff_client.post("/orders/new", data={f"qty_{rice.id}": "abc"})

    assert response.status_code == 400
    assert b"must be a whole number" in response.data


def test_order_creates_stock_movement(staff_client):
    rice = get_product("Rice 25kg")

    staff_client.post("/orders/new", data={f"qty_{rice.id}": "5"})

    db.session.expire_all()
    movement = db.session.execute(db.select(StockMovement)).scalar_one()
    assert movement.change == -5
    assert movement.quantity_before == 40
    assert movement.quantity_after == 35
    assert movement.reason == "order"
    assert movement.user.username == "staff"
    assert movement.order_id is not None


def test_unit_price_is_saved_at_order_time(staff_client):
    rice = get_product("Rice 25kg")
    staff_client.post("/orders/new", data={f"qty_{rice.id}": "2"})

    rice = get_product("Rice 25kg")
    rice.price = 2000
    db.session.commit()

    db.session.expire_all()
    order = db.session.execute(db.select(Order)).scalar_one()
    assert order.total == 2400


def test_place_order_service_directly(app):
    user = db.session.execute(db.select(User).filter_by(username="admin")).scalar_one()
    sugar = get_product("Sugar 5kg")

    place_order(user, {sugar.id: 8})
    assert get_product("Sugar 5kg").quantity == 0

    with pytest.raises(OrderError):
        place_order(user, {sugar.id: 1})
    assert get_product("Sugar 5kg").quantity == 0


def test_orders_page_lists_order(staff_client):
    rice = get_product("Rice 25kg")
    staff_client.post("/orders/new", data={f"qty_{rice.id}": "2"})

    response = staff_client.get("/orders")

    assert response.status_code == 200
    assert b"2400.00" in response.data


def test_order_detail_page(staff_client):
    rice = get_product("Rice 25kg")
    staff_client.post("/orders/new", data={f"qty_{rice.id}": "2"})

    response = staff_client.get("/orders/1")

    assert response.status_code == 200
    assert b"Rice 25kg" in response.data
    assert b"2400.00" in response.data


def test_missing_order_returns_404(staff_client):
    response = staff_client.get("/orders/999")

    assert response.status_code == 404


def test_orders_require_login(client):
    response = client.get("/orders")

    assert response.status_code == 302


def test_staff_cannot_view_stock_history(staff_client):
    response = staff_client.get("/stock-history")

    assert response.status_code == 403


def test_admin_sees_stock_history(admin_client):
    rice = get_product("Rice 25kg")
    admin_client.post("/orders/new", data={f"qty_{rice.id}": "5"})

    response = admin_client.get("/stock-history")

    assert response.status_code == 200
    assert b"Rice 25kg" in response.data
    assert b"40 \xe2\x86\x92 35" in response.data


def test_manual_edit_is_logged(admin_client):
    sugar = get_product("Sugar 5kg")

    admin_client.post(
        f"/products/{sugar.id}/edit",
        data={"name": "Sugar 5kg", "quantity": "20", "price": "250", "reorder_level": "10"},
    )

    db.session.expire_all()
    movement = db.session.execute(db.select(StockMovement)).scalar_one()
    assert movement.change == 12
    assert movement.reason == "manual adjustment"
    assert movement.user.username == "admin"