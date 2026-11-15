
from fastapi.testclient import TestClient

from src.app import app


client = TestClient(app)


def test_customer_can_get_empty_cart(customer_headers):
    response = client.get(
        "/api/v1/carts/me",
        headers=customer_headers,
    )

    assert response.status_code == 200

    data = response.json()
    assert data["customer_id"] > 0
    assert data["items"] == []


def test_customer_can_add_product_to_cart(
    customer_headers,
    product,
):
    response = client.post(
        "/api/v1/carts/items",
        headers=customer_headers,
        json={
            "product_id": product.id,
            "quantity": 2,
        },
    )

    assert response.status_code == 201

    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["product_id"] == product.id
    assert data["items"][0]["quantity"] == 2
    assert data["items"][0]["product"]["id"] == product.id


def test_adding_same_product_increases_quantity(
    customer_headers,
    product,
):
    first_response = client.post(
        "/api/v1/carts/items",
        headers=customer_headers,
        json={
            "product_id": product.id,
            "quantity": 2,
        },
    )

    assert first_response.status_code == 201

    second_response = client.post(
        "/api/v1/carts/items",
        headers=customer_headers,
        json={
            "product_id": product.id,
            "quantity": 3,
        },
    )

    assert second_response.status_code == 201

    items = second_response.json()["items"]

    assert len(items) == 1
    assert items[0]["quantity"] == 5


def test_customer_can_update_cart_item_quantity(
    customer_headers,
    product,
):
    client.post(
        "/api/v1/carts/items",
        headers=customer_headers,
        json={
            "product_id": product.id,
            "quantity": 2,
        },
    )

    response = client.patch(
        f"/api/v1/carts/items/{product.id}",
        headers=customer_headers,
        json={"quantity": 4},
    )

    assert response.status_code == 200

    items = response.json()["items"]

    assert len(items) == 1
    assert items[0]["quantity"] == 4


def test_customer_can_remove_cart_item(
    customer_headers,
    product,
):
    client.post(
        "/api/v1/carts/items",
        headers=customer_headers,
        json={
            "product_id": product.id,
            "quantity": 2,
        },
    )

    response = client.delete(
        f"/api/v1/carts/items/{product.id}",
        headers=customer_headers,
    )

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_customer_can_clear_cart(
    customer_headers,
    product,
):
    client.post(
        "/api/v1/carts/items",
        headers=customer_headers,
        json={
            "product_id": product.id,
            "quantity": 2,
        },
    )

    response = client.delete(
        "/api/v1/carts/clear",
        headers=customer_headers,
    )

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_cart_operations_do_not_change_product_stock(
    customer_headers,
    product,
):
    initial_stock = product.stock_quantity

    client.post(
        "/api/v1/carts/items",
        headers=customer_headers,
        json={
            "product_id": product.id,
            "quantity": 2,
        },
    )

    client.patch(
        f"/api/v1/carts/items/{product.id}",
        headers=customer_headers,
        json={"quantity": 4},
    )

    client.delete(
        f"/api/v1/carts/items/{product.id}",
        headers=customer_headers,
    )

    assert product.stock_quantity == initial_stock


def test_cart_rejects_invalid_quantity(
    customer_headers,
    product,
):
    response = client.post(
        "/api/v1/carts/items",
        headers=customer_headers,
        json={
            "product_id": product.id,
            "quantity": 0,
        },
    )

    assert response.status_code == 422


def test_unauthenticated_user_cannot_access_cart():
    response = client.get("/api/v1/carts/me")

    assert response.status_code == 401
