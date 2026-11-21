import math
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from . import db
from .models import Product, StockMovement

WINDOW_DAYS = 30
LEAD_TIME_DAYS = 7
COVER_DAYS = 14


def as_utc(value):
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def sales_by_product(now, window_days):
    since = now - timedelta(days=window_days)
    units = func.sum(-StockMovement.change).label("units")
    first_sale = func.min(StockMovement.created_at).label("first_sale")

    query = (
        select(StockMovement.product_id, units, first_sale)
        .where(StockMovement.reason == "order", StockMovement.created_at >= since)
        .group_by(StockMovement.product_id)
    )
    return {
        row.product_id: (row.units, as_utc(row.first_sale))
        for row in db.session.execute(query)
    }


def classify(days_left, lead_time_days):
    if days_left <= lead_time_days:
        return "critical"
    if days_left <= lead_time_days * 2:
        return "warning"
    return "ok"


def forecast_products(
    now=None,
    window_days=WINDOW_DAYS,
    lead_time_days=LEAD_TIME_DAYS,
    cover_days=COVER_DAYS,
):
    now = now or datetime.now(timezone.utc)
    sales = sales_by_product(now, window_days)

    query = select(Product).where(Product.is_active.is_(True)).order_by(Product.name)
    products = db.session.execute(query).scalars().all()

    results = []
    for product in products:
        units, first_sale = sales.get(product.id, (0, None))

        if units and units > 0:
            observed_days = (now - first_sale).total_seconds() / 86400
            observed_days = min(window_days, max(1.0, observed_days))
            daily_demand = units / observed_days
            days_left = product.quantity / daily_demand
            target_stock = math.ceil(daily_demand * (lead_time_days + cover_days))
            results.append({
                "product": product,
                "daily_demand": round(daily_demand, 2),
                "days_left": round(days_left, 1),
                "stockout_date": (now + timedelta(days=days_left)).date(),
                "suggested_order": max(0, target_stock - product.quantity),
                "status": classify(days_left, lead_time_days),
            })
        else:
            results.append({
                "product": product,
                "daily_demand": 0.0,
                "days_left": None,
                "stockout_date": None,
                "suggested_order": 0,
                "status": "no data",
            })

    results.sort(key=lambda row: (
        row["days_left"] is None,
        row["days_left"] or 0,
        row["product"].name,
    ))
    return results