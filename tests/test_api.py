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