from app import db
from app.models import Product, User
from app.reports import inventory_summary, monthly_sales, top_selling_products
from app.services import place_order


def get_product(name):
    db.session.expire_all()
    return db.session.execute(db.select(Product).filter_by(name=name)).scalar_one()


def get_admin():
    return db.session.execute(db.select(User).filter_by(username="admin")).scalar_one()


def test_inventory_summary_values(app):
    summary = inventory_summary()

    assert summary["total_products"] == 4
    assert summary["stock_value"] == 40 * 1200 + 8 * 250 + 25 * 180 + 5 * 220
    assert summary["low_stock_count"] == 2
    assert summary["order_count"] == 0
    assert summary["revenue"] == 0


def test_archived_products_excluded_from_summary(app):
    tea = get_product("Tea Powder 500g")
    tea.is_active = False
    db.session.commit()

    summary = inventory_summary()

    assert summary["total_products"] == 3
    assert summary["low_stock_count"] == 1


def test_top_selling_products(app):
    admin = get_admin()
    rice = get_product("Rice 25kg")
    sugar = get_product("Sugar 5kg")
    place_order(admin, {rice.id: 5, sugar.id: 2})
    place_order(admin, {rice.id: 3})

    top = top_selling_products()

    assert top[0] == {"name": "Rice 25kg", "quantity_sold": 8, "revenue": 9600.0}
    assert top[1] == {"name": "Sugar 5kg", "quantity_sold": 2, "revenue": 500.0}


def test_monthly_sales(app):
    admin = get_admin()
    rice = get_product("Rice 25kg")
    sugar = get_product("Sugar 5kg")
    place_order(admin, {rice.id: 1, sugar.id: 1})
    place_order(admin, {rice.id: 1})

    months = monthly_sales()

    assert len(months) == 1
    assert months[0]["orders"] == 2
    assert months[0]["revenue"] == 1200 + 250 + 1200


def test_reports_page_for_admin(admin_client):
    response = admin_client.get("/reports")

    assert response.status_code == 200
    assert b"55600.00" in response.data
    assert b"Top-selling products" in response.data


def test_reports_page_forbidden_for_staff(staff_client):
    response = staff_client.get("/reports")

    assert response.status_code == 403