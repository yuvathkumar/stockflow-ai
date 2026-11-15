def test_home_page_loads(client):

    response = client.get("/")

    assert response.status_code == 200
    assert b"StockFlow AI is running!" in response.data

def test_checking_addition_page(client):

    response = client.get("/about")

    assert response.status_code == 200
    assert b"Addition Page" in response.data

def test_unknown_page_returns_404(client):

    response = client.get("/xyz")

    assert response.status_code == 404