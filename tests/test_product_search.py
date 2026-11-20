from fastapi.testclient import TestClient

from src.app import app


client = TestClient(app)


def test_product_search_finds_product_by_name(product):
    query = product.name[:4]

    response = client.get(
        "/api/v1/products/search",
        params={"q": query},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] >= 1
    assert any(item["id"] == product.id for item in body["items"])


def test_product_search_filters_by_category_and_vendor(product):
    response = client.get(
        "/api/v1/products/search",
        params={
            "category_id": product.category_id,
            "vendor_id": product.vendor_id,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert any(item["id"] == product.id for item in body["items"])


def test_product_search_filters_by_price_range(product):
    response = client.get(
        "/api/v1/products/search",
        params={
            "min_price": product.price,
            "max_price": product.price,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert any(item["id"] == product.id for item in body["items"])


def test_product_search_supports_in_stock_filter(product):
    response = client.get(
        "/api/v1/products/search",
        params={"in_stock": "true"},
    )

    assert response.status_code == 200
    assert all(item["stock_quantity"] > 0 for item in response.json()["items"])


def test_product_search_pagination_metadata(product):
    response = client.get(
        "/api/v1/products/search",
        params={"skip": 0, "limit": 1},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["skip"] == 0
    assert body["limit"] == 1
    assert body["total"] >= 1
    assert len(body["items"]) <= 1


def test_product_search_rejects_invalid_price_range():
    response = client.get(
        "/api/v1/products/search",
        params={"min_price": 500, "max_price": 100},
    )

    assert response.status_code == 400
    assert "min_price" in response.json()["detail"]


def test_product_search_rejects_unknown_sort_option():
    response = client.get(
        "/api/v1/products/search",
        params={"sort_by": "popular"},
    )

    assert response.status_code == 422
