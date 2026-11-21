from sqlalchemy import func, select

from . import db
from .models import Order, OrderItem, Product


def inventory_summary():
    active = Product.is_active.is_(True)

    total_products = db.session.execute(
        select(func.count(Product.id)).where(active)
    ).scalar_one()

    stock_value = db.session.execute(
        select(func.coalesce(func.sum(Product.quantity * Product.price), 0)).where(active)
    ).scalar_one()

    low_stock_count = db.session.execute(
        select(func.count(Product.id)).where(active, Product.quantity < Product.reorder_level)
    ).scalar_one()

    order_count = db.session.execute(select(func.count(Order.id))).scalar_one()

    revenue = db.session.execute(
        select(func.coalesce(func.sum(OrderItem.quantity * OrderItem.unit_price), 0))
    ).scalar_one()

    return {
        "total_products": total_products,
        "stock_value": float(stock_value),
        "low_stock_count": low_stock_count,
        "order_count": order_count,
        "revenue": float(revenue),
    }


def top_selling_products(limit=5):
    quantity_sold = func.sum(OrderItem.quantity).label("quantity_sold")
    revenue = func.sum(OrderItem.quantity * OrderItem.unit_price).label("revenue")

    query = (
        select(Product.name, quantity_sold, revenue)
        .join(OrderItem, OrderItem.product_id == Product.id)
        .group_by(Product.id, Product.name)
        .order_by(quantity_sold.desc(), Product.name)
        .limit(limit)
    )
    return [
        {"name": row.name, "quantity_sold": row.quantity_sold, "revenue": float(row.revenue)}
        for row in db.session.execute(query)
    ]


def monthly_sales():
    month = func.strftime("%Y-%m", Order.created_at).label("month")
    order_total = func.count(func.distinct(Order.id)).label("orders")
    revenue = func.sum(OrderItem.quantity * OrderItem.unit_price).label("revenue")

    query = (
        select(month, order_total, revenue)
        .join(OrderItem, OrderItem.order_id == Order.id)
        .group_by(month)
        .order_by(month.desc())
    )
    return [
        {"month": row.month, "orders": row.orders, "revenue": float(row.revenue)}
        for row in db.session.execute(query)
    ]


def low_stock_products():
    query = (
        select(Product)
        .where(Product.is_active.is_(True), Product.quantity < Product.reorder_level)
        .order_by(Product.quantity)
    )
    return db.session.execute(query).scalars().all()