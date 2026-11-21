from functools import wraps

from flask import current_app, jsonify, request
from flask_login import current_user
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from . import db
from .ai import AIError, ask_llm
from .ask import AskError, answer_question
from .models import Product
from .reports import inventory_summary


def api_login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify(error="Authentication required."), 401
        return view(*args, **kwargs)

    return wrapped


def api_admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify(error="Authentication required."), 401
        if not current_user.is_admin:
            return jsonify(error="Admin access required."), 403
        return view(*args, **kwargs)

    return wrapped


def product_to_dict(product):
    return {
        "id": product.id,
        "name": product.name,
        "quantity": product.quantity,
        "price": product.price,
        "reorder_level": product.reorder_level,
        "is_low_stock": product.is_low_stock,
    }


def register_api_routes(app):

    @app.route("/health")
    def health():
        try:
            db.session.execute(text("SELECT 1"))
        except SQLAlchemyError:
            return jsonify(status="error", database="unreachable"), 503
        return jsonify(status="ok", database="ok")

    @app.route("/api/products")
    @api_login_required
    def api_products():
        query = db.select(Product).where(Product.is_active.is_(True)).order_by(Product.name)
        products = db.session.execute(query).scalars().all()

        if request.args.get("low_stock") == "true":
            products = [product for product in products if product.is_low_stock]

        return jsonify(count=len(products), products=[product_to_dict(p) for p in products])

    @app.route("/api/products/<int:product_id>")
    @api_login_required
    def api_product_detail(product_id):
        product = db.session.get(Product, product_id)
        if product is None or not product.is_active:
            return jsonify(error="Product not found."), 404
        return jsonify(product_to_dict(product))

    @app.route("/api/reports/summary")
    @api_admin_required
    def api_summary():
        return jsonify(inventory_summary())

    @app.route("/api/ask", methods=["POST"])
    @api_admin_required
    def api_ask():
        payload = request.get_json(silent=True) or {}
        question = payload.get("question", "")
        llm = current_app.config.get("LLM_CLIENT") or ask_llm

        try:
            result = answer_question(question, llm)
        except AIError as error:
            return jsonify(error=str(error)), 503
        except AskError as error:
            return jsonify(error=str(error)), 400
        return jsonify(result)