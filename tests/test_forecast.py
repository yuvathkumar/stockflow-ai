from datetime import datetime, timedelta, timezone

from app import db
from app.forecast import forecast_products
from app.models import Order, Product, StockMovement
from app.seed import generate_demo_sales

NOW = datetime(2026, 11, 22, 12, 0, tzinfo=timezone.utc)


def get_product(name):
    db.session.expire_all()
    return db.session.execute(db.select(Product).filter_by(name=name)).scalar_one()


def add_sale(product, quantity, days_ago):
    db.session.add(StockMovement(
        product=product,
        change=-quantity,
        quantity_before=product.quantity + quantity,
        quantity_after=product.quantity,
        reason="order",
        created_at=NOW - timedelta(days=days_ago),
    ))
    db.session.commit()


def forecast_for(name):
    return next(row for row in forecast_products(now=NOW) if row["product"].name == name)


def test_no_sales_means_no_prediction(app):
    row = forecast_for("Rice 25kg")

    assert row["status"] == "no data"
    assert row["days_left"] is None
    assert row["suggested_order"] == 0


def test_daily_demand_and_days_left(app):
    rice = get_product("Rice 25kg")
    add_sale(rice, 30, days_ago=20)
    add_sale(rice, 30, days_ago=10)

    row = forecast_for("Rice 25kg")

    assert row["daily_demand"] == 3.0
    assert row["days_left"] == 13.3
    assert row["status"] == "warning"
    assert row["suggested_order"] == 3 * 21 - 40


def test_recent_product_uses_days_since_first_sale(app):
    sugar = get_product("Sugar 5kg")
    add_sale(sugar, 10, days_ago=5)

    row = forecast_for("Sugar 5kg")

    assert row["daily_demand"] == 2.0
    assert row["days_left"] == 4.0
    assert row["status"] == "critical"
    assert row["suggested_order"] == 2 * 21 - 8


def test_healthy_stock_is_ok(app):
    oil = get_product("Cooking Oil 1L")
    add_sale(oil, 5, days_ago=10)

    row = forecast_for("Cooking Oil 1L")

    assert row["daily_demand"] == 0.5
    assert row["days_left"] == 50.0
    assert row["status"] == "ok"
    assert row["suggested_order"] == 0


def test_sales_outside_window_are_ignored(app):
    tea = get_product("Tea Powder 500g")
    add_sale(tea, 3, days_ago=40)

    assert forecast_for("Tea Powder 500g")["status"] == "no data"


def test_forecast_sorted_most_urgent_first(app):
    add_sale(get_product("Rice 25kg"), 60, days_ago=20)
    add_sale(get_product("Sugar 5kg"), 10, days_ago=5)
    add_sale(get_product("Cooking Oil 1L"), 5, days_ago=10)

    names = [row["product"].name for row in forecast_products(now=NOW)]

    assert names == ["Sugar 5kg", "Rice 25kg", "Cooking Oil 1L", "Tea Powder 500g"]


def test_forecast_page(staff_client):
    response = staff_client.get("/forecast")

    assert response.status_code == 200
    assert b"Days until stockout" in response.data


def test_demo_sales_creates_history(app):
    generate_demo_sales(days=10)

    order_count = db.session.execute(db.select(db.func.count(Order.id))).scalar_one()
    assert order_count > 0
    assert any(row["daily_demand"] > 0 for row in forecast_products())