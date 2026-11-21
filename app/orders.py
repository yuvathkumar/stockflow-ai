from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm import selectinload

from . import db
from .auth import admin_required
from .models import Order, Product, StockMovement
from .services import OrderError, place_order


def active_products():
    query = db.select(Product).where(Product.is_active.is_(True)).order_by(Product.name)
    return db.session.execute(query).scalars().all()


def parse_order_form(form, products):
    quantities = {}
    errors = []
    for product in products:
        raw = form.get(f"qty_{product.id}", "").strip()
        if not raw:
            continue
        try:
            quantity = int(raw)
        except ValueError:
            errors.append(f"Quantity for {product.name} must be a whole number.")
            continue
        if quantity < 0:
            errors.append(f"Quantity for {product.name} cannot be negative.")
        elif quantity > 0:
            quantities[product.id] = quantity
    return quantities, errors


def register_order_routes(app):

    @app.route("/orders")
    @login_required
    def orders():
        query = (
            db.select(Order)
            .options(selectinload(Order.items), selectinload(Order.created_by))
            .order_by(Order.created_at.desc(), Order.id.desc())
        )
        order_list = db.session.execute(query).scalars().all()
        return render_template("orders.html", orders=order_list)

    @app.route("/orders/new", methods=["GET", "POST"])
    @login_required
    def new_order():
        products = active_products()

        if request.method == "POST":
            quantities, errors = parse_order_form(request.form, products)
            if not errors:
                try:
                    order = place_order(current_user._get_current_object(), quantities)
                except OrderError as error:
                    errors.append(str(error))

            if errors:
                for error in errors:
                    flash(error, "danger")
                return render_template(
                    "order_form.html", products=products, values=request.form
                ), 400

            flash(f"Order #{order.id} placed.", "success")
            return redirect(url_for("order_detail", order_id=order.id))

        return render_template("order_form.html", products=products, values={})

    @app.route("/orders/<int:order_id>")
    @login_required
    def order_detail(order_id):
        order = db.get_or_404(Order, order_id)
        return render_template("order_detail.html", order=order)

    @app.route("/stock-history")
    @admin_required
    def stock_history():
        query = (
            db.select(StockMovement)
            .options(selectinload(StockMovement.product), selectinload(StockMovement.user))
            .order_by(StockMovement.created_at.desc(), StockMovement.id.desc())
            .limit(200)
        )
        movements = db.session.execute(query).scalars().all()
        return render_template("stock_history.html", movements=movements)