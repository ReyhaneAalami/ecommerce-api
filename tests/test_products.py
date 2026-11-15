
from fastapi.testclient import TestClient

from src.app import app


client = TestClient(app)


def test_public_products_list():
    response = client.get("/api/v1/products")

    assert response.status_code == 200
    assert isinstance(response.json(), list)

    for product in response.json():
        assert product["is_active"] is True
        assert product["id"] > 0
        assert product["vendor_id"] > 0
        assert product["price"] is not None


def test_public_products_pagination():
    response = client.get(
        "/api/v1/products",
        params={"skip": 0, "limit": 5},
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) <= 5


def test_public_products_reject_invalid_pagination():
    response = client.get(
        "/api/v1/products",
        params={"limit": 101},
    )

    assert response.status_code == 422


def test_nonexistent_product_returns_404():
    response = client.get("/api/v1/products/999999999")

    assert response.status_code == 404
