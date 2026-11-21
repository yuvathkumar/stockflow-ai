from flask import Response, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from . import db
from .ai import AIError, ask_llm
from .ask import AskError, answer_question
from .auth import admin_required
from .csv_io import parse_products_csv, products_to_csv
from .forecast import COVER_DAYS, LEAD_TIME_DAYS, WINDOW_DAYS, forecast_products
from .models import Product
from .reports import inventory_summary, low_stock_products, monthly_sales, top_selling_products
from .services import import_products

MAX_ERRORS_SHOWN = 20


def register_tool_routes(app):

    @app.route("/reports")
    @admin_required
    def reports():
        return render_template(
            "reports.html",
            summary=inventory_summary(),
            top_products=top_selling_products(),
            months=monthly_sales(),
            low_stock=low_stock_products(),
        )

    @app.route("/forecast")
    @login_required
    def forecast():
        return render_template(
            "forecast.html",
            rows=forecast_products(),
            window_days=WINDOW_DAYS,
            lead_time_days=LEAD_TIME_DAYS,
            cover_days=COVER_DAYS,
        )

    @app.route("/ask", methods=["GET", "POST"])
    @admin_required
    def ask():
        if request.method == "POST":
            question = request.form.get("question", "")
            llm = current_app.config.get("LLM_CLIENT") or ask_llm
            try:
                result = answer_question(question, llm)
            except AIError as error:
                flash(str(error), "warning")
                return render_template("ask.html", question=question, result=None), 503
            except AskError as error:
                flash(str(error), "danger")
                return render_template("ask.html", question=question, result=None), 400
            return render_template("ask.html", question=question, result=result)

        return render_template("ask.html", question="", result=None)

    @app.route("/products/export.csv")
    @login_required
    def export_products():
        query = db.select(Product).where(Product.is_active.is_(True)).order_by(Product.name)
        products = db.session.execute(query).scalars().all()
        return Response(
            products_to_csv(products),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=products.csv"},
        )

    @app.route("/products/import", methods=["GET", "POST"], endpoint="import_products")
    @admin_required
    def import_products_page():
        if request.method == "POST":
            upload = request.files.get("file")

            if upload is None or upload.filename == "":
                flash("Choose a CSV file to upload.", "danger")
                return render_template("import_products.html"), 400

            if not upload.filename.lower().endswith(".csv"):
                flash("Only .csv files are supported.", "danger")
                return render_template("import_products.html"), 400

            try:
                text = upload.read().decode("utf-8-sig")
            except UnicodeDecodeError:
                flash("The file must be saved as UTF-8 CSV.", "danger")
                return render_template("import_products.html"), 400

            rows, errors = parse_products_csv(text)
            if errors:
                for error in errors[:MAX_ERRORS_SHOWN]:
                    flash(error, "danger")
                if len(errors) > MAX_ERRORS_SHOWN:
                    flash(f"...and {len(errors) - MAX_ERRORS_SHOWN} more errors.", "danger")
                flash("Nothing was imported. Fix the errors and try again.", "warning")
                return render_template("import_products.html"), 400

            created, updated = import_products(rows, current_user._get_current_object())
            flash(f"Import complete: {created} created, {updated} updated.", "success")
            return redirect(url_for("products"))

        return render_template("import_products.html")