def test_home_page_loads(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"Never run out of stock again" in response.data


def test_home_page_shows_features(client):
    response = client.get("/")

    assert b"Stockout prediction" in response.data


def test_about_page_loads(client):
    response = client.get("/about")

    assert response.status_code == 200
    assert b"About StockFlow AI" in response.data


def test_unknown_page_returns_404(client):
    response = client.get("/xyz")

    assert response.status_code == 404


def test_dashboard_for_logged_in_user(staff_client):
    response = staff_client.get("/")

    assert response.status_code == 200
    assert b"Welcome back, staff" in response.data
    assert b"Needs attention" in response.data


def test_dashboard_lists_low_stock_products(staff_client):
    response = staff_client.get("/")

    assert b"Sugar 5kg" in response.data
    assert b"Tea Powder 500g" in response.data


def test_revenue_shown_to_admin_only(admin_client, app):
    assert b"Revenue" in admin_client.get("/").data

    admin_client.post("/logout")
    admin_client.post("/login", data={"username": "staff", "password": "staff123"})
    assert b"Revenue" not in admin_client.get("/").data


def test_assistant_shown_to_admin_only(admin_client):
    assert b"flo-toggle" in admin_client.get("/").data

    admin_client.post("/logout")
    admin_client.post("/login", data={"username": "staff", "password": "staff123"})
    assert b"flo-toggle" not in admin_client.get("/").data


def test_products_page_loads(staff_client):
    response = staff_client.get("/products")

    assert response.status_code == 200
    assert b"Rice 25kg" in response.data


def test_low_stock_badge_shown(staff_client):
    response = staff_client.get("/products")

    assert b"text-bg-danger\">Low stock" in response.data