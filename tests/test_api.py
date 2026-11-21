from app import db
from app.models import Product


def get_product(name):
    db.session.expire_all()
    return db.session.execute(db.select(Product).filter_by(name=name)).scalar_one()


def test_api_requires_login(client):
    response = client.get("/api/products")

    assert response.status_code == 401
    assert response.get_json() == {"error": "Authentication required."}


def test_api_lists_products(staff_client):
    data = staff_client.get("/api/products").get_json()

    assert data["count"] == 4
    names = [product["name"] for product in data["products"]]
    assert "Rice 25kg" in names
    assert set(data["products"][0]) == {
        "id", "name", "quantity", "price", "reorder_level", "is_low_stock"
    }


def test_api_low_stock_filter(staff_client):
    data = staff_client.get("/api/products?low_stock=true").get_json()

    names = {product["name"] for product in data["products"]}
    assert names == {"Sugar 5kg", "Tea Powder 500g"}


def test_api_product_detail(staff_client):
    rice = get_product("Rice 25kg")

    data = staff_client.get(f"/api/products/{rice.id}").get_json()

    assert data["name"] == "Rice 25kg"
    assert data["quantity"] == 40
    assert data["is_low_stock"] is False


def test_api_missing_product_returns_404(staff_client):
    response = staff_client.get("/api/products/999")

    assert response.status_code == 404
    assert response.get_json() == {"error": "Product not found."}


def test_api_summary_for_admin(admin_client):
    data = admin_client.get("/api/reports/summary").get_json()

    assert data["stock_value"] == 55600.0
    assert data["low_stock_count"] == 2


def test_api_summary_forbidden_for_staff(staff_client):
    response = staff_client.get("/api/reports/summary")

    assert response.status_code == 403
    assert response.get_json() == {"error": "Admin access required."}


def test_api_ask_answers_question(app, admin_client):
    app.config["LLM_CLIENT"] = lambda prompt: (
        "SELECT name FROM product WHERE quantity < reorder_level ORDER BY name"
    )

    response = admin_client.post("/api/ask", json={"question": "Which products are low?"})

    assert response.status_code == 200
    data = response.get_json()
    assert data["columns"] == ["name"]
    assert data["rows"] == [["Sugar 5kg"], ["Tea Powder 500g"]]
    assert "SELECT" in data["sql"]


def test_api_ask_blocks_users_table(app, admin_client):
    app.config["LLM_CLIENT"] = lambda prompt: "SELECT username, password_hash FROM users"

    response = admin_client.post("/api/ask", json={"question": "Show passwords"})

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_api_ask_without_ai_configured(admin_client):
    response = admin_client.post("/api/ask", json={"question": "How many products?"})

    assert response.status_code == 503


def test_api_ask_forbidden_for_staff(staff_client):
    response = staff_client.post("/api/ask", json={"question": "Anything"})

    assert response.status_code == 403


def test_api_ask_requires_login(client):
    response = client.post("/api/ask", json={"question": "Anything"})

    assert response.status_code == 401