import random
from datetime import datetime, timedelta, timezone

import click

from . import db
from .models import Product, StockMovement, User
from .services import OrderError, place_order, record_movement

SAMPLE_PRODUCTS = [
    {"name": "Rice 25kg", "quantity": 40, "price": 1200, "reorder_level": 10},
    {"name": "Sugar 5kg", "quantity": 8, "price": 250, "reorder_level": 10},
    {"name": "Cooking Oil 1L", "quantity": 25, "price": 180, "reorder_level": 10},
    {"name": "Tea Powder 500g", "quantity": 5, "price": 220, "reorder_level": 10},
]

SAMPLE_USERS = [
    {"username": "admin", "password": "admin123", "role": "admin"},
    {"username": "staff", "password": "staff123", "role": "staff"},
]


def seed_products():
    for data in SAMPLE_PRODUCTS:
        db.session.add(Product(**data))
    db.session.commit()


def seed_users():
    for data in SAMPLE_USERS:
        user = User(username=data["username"], role=data["role"])
        user.set_password(data["password"])
        db.session.add(user)
    db.session.commit()


def generate_demo_sales(days=45, seed=42):
    """Create realistic order history over the past `days` days."""
    rng = random.Random(seed)
    now = datetime.now(timezone.utc)
    admin = db.session.execute(db.select(User).filter_by(role="admin")).scalars().first()

    query = db.select(Product).where(Product.is_active.is_(True)).order_by(Product.name)
    products = db.session.execute(query).scalars().all()

    for product in products:
        before = product.quantity
        product.quantity = before + 100
        movement = record_movement(product, admin, before, product.quantity, "demo restock")
        movement.created_at = now - timedelta(days=days)
    db.session.commit()

    for day in range(days, 0, -1):
        moment = now - timedelta(days=day) + timedelta(hours=rng.randint(1, 8))
        quantities = {
            product.id: rng.randint(1, 4)
            for product in products
            if rng.random() < 0.7
        }
        if not quantities:
            continue

        try:
            order = place_order(admin, quantities)
        except OrderError:
            continue

        order.created_at = moment
        movements = db.session.execute(
            db.select(StockMovement).filter_by(order_id=order.id)
        ).scalars()
        for movement in movements:
            movement.created_at = moment
        db.session.commit()


def register_commands(app):
    @app.cli.command("init-db")
    def init_db():
        """Create fresh tables and load sample data."""
        db.drop_all()
        db.create_all()
        seed_products()
        seed_users()
        click.echo("Database created with sample products.")
        click.echo("Demo logins -> admin / admin123 (admin), staff / staff123 (staff)")

    @app.cli.command("demo-sales")
    @click.option("--days", default=45, show_default=True)
    def demo_sales(days):
        """Generate past orders so the forecast has data to work with."""
        generate_demo_sales(days=days)
        click.echo(f"Generated {days} days of demo sales.")

    @app.cli.command("create-user")
    @click.argument("username")
    @click.option("--role", type=click.Choice(["admin", "staff"]), default="staff")
    @click.password_option()
    def create_user(username, role, password):
        """Create a new user. Prompts for the password."""
        query = db.select(User).filter_by(username=username)
        if db.session.execute(query).first() is not None:
            raise click.ClickException(f"User '{username}' already exists.")

        user = User(username=username, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Created {role} user '{username}'.")