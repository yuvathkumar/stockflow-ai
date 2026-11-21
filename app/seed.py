import click

from . import db
from .models import Product, User

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