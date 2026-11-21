def test_home_page_loads(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"StockFlow AI is running!" in response.data


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


def test_products_page_loads(staff_client):
    response = staff_client.get("/products")

    assert response.status_code == 200
    assert b"Rice 25kg" in response.data


def test_low_stock_badge_shown(staff_client):
    response = staff_client.get("/products")

    assert b"Low stock" in response.data