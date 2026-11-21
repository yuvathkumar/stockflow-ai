from flask import Flask, render_template


def create_app():
    app = Flask(__name__)

    @app.route("/")
    def home():
        features = [
            "Product and stock management",
            "Orders with automatic stock updates",
            "Stockout prediction",
            "Ask questions in plain English",
        ]
        return render_template("home.html", user_name="Yuvath", features=features)

    @app.route("/about")
    def about():
        return render_template("about.html")

    return app