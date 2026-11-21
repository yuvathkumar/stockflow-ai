def test_health_check(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "database": "ok"}


def test_health_check_needs_no_login(client):
    response = client.get("/health")

    assert response.status_code != 302