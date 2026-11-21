from sqlalchemy import update

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