from sqlalchemy import select, update

from . import db
from .models import Order, OrderItem, Product, StockMovement


class OrderError(Exception):
    """Raised when an order cannot be placed."""


def record_movement(product, user, quantity_before, quantity_after, reason, order=None):
    movement = StockMovement(
        product=product,
        user=user,
        change=quantity_after - quantity_before,
        quantity_before=quantity_before,
        quantity_after=quantity_after,
        reason=reason,
        order=order,
    )
    db.session.add(movement)
    return movement


def place_order(user, quantities):
    """Create an order and reduce stock. All items succeed, or nothing changes.

    quantities: {product_id: quantity_to_order}
    """
    if not quantities:
        raise OrderError("Add at least one product to the order.")

    order = Order(created_by=user)
    db.session.add(order)

    try:
        for product_id in sorted(quantities):
            quantity = quantities[product_id]
            if quantity <= 0:
                raise OrderError("Quantities must be greater than zero.")

            product = db.session.get(Product, product_id)
            if product is None or not product.is_active:
                raise OrderError("One of the selected products is not available.")

            result = db.session.execute(
                update(Product)
                .where(Product.id == product_id, Product.quantity >= quantity)
                .values(quantity=Product.quantity - quantity)
            )
            if result.rowcount == 0:
                raise OrderError(
                    f"Not enough stock for {product.name} "
                    f"(available: {product.quantity}, requested: {quantity})."
                )

            db.session.refresh(product)
            order.items.append(
                OrderItem(product=product, quantity=quantity, unit_price=product.price)
            )
            record_movement(
                product,
                user,
                quantity_before=product.quantity + quantity,
                quantity_after=product.quantity,
                reason="order",
                order=order,
            )

        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return order


def import_products(rows, user):
    """Create new products or update existing ones. All rows succeed, or nothing changes.

    Returns (created_count, updated_count).
    """
    created = 0
    updated = 0

    try:
        for data in rows:
            query = select(Product).filter_by(name=data["name"])
            product = db.session.execute(query).scalar_one_or_none()

            if product is None:
                product = Product(**data)
                db.session.add(product)
                if product.quantity > 0:
                    record_movement(product, user, 0, product.quantity, "csv import")
                created += 1
            else:
                old_quantity = product.quantity
                for field, value in data.items():
                    setattr(product, field, value)
                product.is_active = True
                if product.quantity != old_quantity:
                    record_movement(
                        product, user, old_quantity, product.quantity, "csv import"
                    )
                updated += 1

        db.session.commit()
    except Exception:
        db.session.rollback()
        raise

    return created, updated