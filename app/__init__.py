from flask import Flask

def create_app():
    app = Flask(__name__)

    @app.route("/")
    def home():
        return "StockFlow AI is running!"

    @app.route("/about")
    def about():
        return "Addition Page"

    return app