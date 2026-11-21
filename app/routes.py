from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from . import db
from .auth import admin_required
from .forecast import forecast_products
from .models import Product
from .reports import inventory_summary
from .services import record_movement

EMPTY_FORM = {"name": "", "quantity": "", "price": "", "reorder_level": 10}
ATTENTION_LIMIT = 5


def validate_product_form(form):
    errors = []
    name = form.get("name", "").strip()
    if not name:
        errors.append("Name is required.")

    try:
        quantity = int(form.get("quantity", ""))
        if quantity < 0:
            errors.append("Quantity cannot be negative.")
    except ValueError:
        quantity = None
        errors.append("Quantity must be a whole number.")

    try:
        price = float(form.get("price", ""))
        if price < 0:
            errors.append("Price cannot be negative.")
    except ValueError:
        price = None
        errors.append("Price must be a number.")

    try:
        reorder_level = int(form.get("reorder_level", ""))
        if reorder_level < 0:
            errors.append("Reorder level cannot be negative.")
    except ValueError:
        reorder_level = None
        errors.append("Reorder level must be a whole number.")

    data = {
        "name": name,
        "quantity": quantity,
        "price": price,
        "reorder_level": reorder_level,
    }
    return data, errors


def name_taken(name, exclude_id=None):
    query = db.select(Product).where(Product.name == name)
    if exclude_id is not None:
        query = query.where(Product.id != exclude_id)
    return db.session.execute(query).first() is not None


def get_active_product_or_404(product_id):
    product = db.session.get(Product, product_id)
    if product is None or not product.is_active:
        abort(404)
    return product


def needs_attention(row):
    if row["status"] in ("critical", "warning"):
        return True
    return row["status"] == "no data" and row["product"].is_low_stock


def register_routes(app):

    @app.route("/")
    def home():
        if not current_user.is_authenticated:
            return render_template("home.html")

        forecast_rows = forecast_products()
        attention = [row for row in forecast_rows if needs_attention(row)][:ATTENTION_LIMIT]
        critical_count = sum(1 for row in forecast_rows if row["status"] == "critical")
        return render_template(
            "home.html",
            summary=inventory_summary(),
            attention=attention,
            critical_count=critical_count,
        )

    @app.route("/about")
    def about():
        return render_template("about.html")

    @app.route("/products")
    @login_required
    def products():
        query = (
            db.select(Product)
            .where(Product.is_active.is_(True))
            .order_by(Product.name)
        )
        product_list = db.session.execute(query).scalars().all()
        return render_template("products.html", products=product_list)

    @app.route("/products/new", methods=["GET", "POST"])
    @admin_required
    def new_product():
        if request.method == "POST":
            data, errors = validate_product_form(request.form)
            if not errors and name_taken(data["name"]):
                errors.append("A product with this name already exists.")

            if errors:
                for error in errors:
                    flash(error, "danger")
                return render_template(
                    "product_form.html", title="Add product", values=request.form
                ), 400

            product = Product(**data)
            db.session.add(product)
            if product.quantity > 0:
                record_movement(
                    product,
                    current_user._get_current_object(),
                    quantity_before=0,
                    quantity_after=product.quantity,
                    reason="initial stock",
                )
            db.session.commit()
            flash(f"Added {product.name}.", "success")
            return redirect(url_for("products"))

        return render_template("product_form.html", title="Add product", values=EMPTY_FORM)

    @app.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
    @admin_required
    def edit_product(product_id):
        product = get_active_product_or_404(product_id)

        if request.method == "POST":
            data, errors = validate_product_form(request.form)
            if not errors and name_taken(data["name"], exclude_id=product.id):
                errors.append("A product with this name already exists.")

            if errors:
                for error in errors:
                    flash(error, "danger")
                return render_template(
                    "product_form.html", title="Edit product", values=request.form
                ), 400

            old_quantity = product.quantity
            for field, value in data.items():
                setattr(product, field, value)

            if product.quantity != old_quantity:
                record_movement(
                    product,
                    current_user._get_current_object(),
                    quantity_before=old_quantity,
                    quantity_after=product.quantity,
                    reason="manual adjustment",
                )
            db.session.commit()
            flash(f"Updated {product.name}.", "success")
            return redirect(url_for("products"))

        values = {
            "name": product.name,
            "quantity": product.quantity,
            "price": product.price,
            "reorder_level": product.reorder_level,
        }
        return render_template("product_form.html", title="Edit product", values=values)

    @app.route("/products/<int:product_id>/archive", methods=["POST"])
    @admin_required
    def archive_product(product_id):
        product = get_active_product_or_404(product_id)
        product.is_active = False
        db.session.commit()
        flash(f"Archived {product.name}.", "success")
        return redirect(url_for("products"))