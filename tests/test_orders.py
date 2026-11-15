
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient

from src.app import app
from src.data.models import User, Vendor, Product
from src.utils.security import create_access_token


client = TestClient(app)


def test_customer_can_create_order_and_stock_decreases(
    customer_headers,
    product,
):
    initial_stock = product.stock_quantity

    response = client.post(
        "/api/v1/orders",
        headers=customer_headers,
        json={
            "items": [
                {
                    "product_id": product.id,
                    "quantity": 2,
                }
            ]
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["id"] > 0
    assert data["status"] == "pending"
    assert Decimal(data["total_amount"]) == Decimal("200.00")

    assert len(data["vendor_orders"]) == 1
    assert data["vendor_orders"][0]["items"][0]["quantity"] == 2

    assert product.stock_quantity == initial_stock - 2


def test_order_rejects_insufficient_stock(
    customer_headers,
    product,
):
    initial_stock = product.stock_quantity

    response = client.post(
        "/api/v1/orders",
        headers=customer_headers,
        json={
            "items": [
                {
                    "product_id": product.id,
                    "quantity": initial_stock + 1,
                }
            ]
        },
    )

    assert response.status_code == 400
    assert product.stock_quantity == initial_stock


def test_customer_can_get_order_history(
    customer_headers,
    product,
):
    create_response = client.post(
        "/api/v1/orders",
        headers=customer_headers,
        json={
            "items": [
                {
                    "product_id": product.id,
                    "quantity": 1,
                }
            ]
        },
    )

    assert create_response.status_code == 201

    response = client.get(
        "/api/v1/orders/me",
        headers=customer_headers,
    )

    assert response.status_code == 200
    assert len(response.json()) == 1


def test_customer_can_get_order_details(
    customer_headers,
    product,
):
    create_response = client.post(
        "/api/v1/orders",
        headers=customer_headers,
        json={
            "items": [
                {
                    "product_id": product.id,
                    "quantity": 1,
                }
            ]
        },
    )

    order_id = create_response.json()["id"]

    response = client.get(
        f"/api/v1/orders/{order_id}",
        headers=customer_headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == order_id


def test_customer_cannot_access_another_customers_order(
    customer_headers,
    product,
    db,
):
    create_response = client.post(
        "/api/v1/orders",
        headers=customer_headers,
        json={
            "items": [
                {
                    "product_id": product.id,
                    "quantity": 1,
                }
            ]
        },
    )

    order_id = create_response.json()["id"]

    other_customer = User(
        full_name="Other Customer",
        email=f"other_{uuid4().hex[:10]}@example.com",
        password_hash="test-password-hash",
        role="customer",
        is_active=True,
    )

    db.add(other_customer)
    db.flush()

    other_token = create_access_token(other_customer.id)

    response = client.get(
        f"/api/v1/orders/{order_id}",
        headers={
            "Authorization": f"Bearer {other_token}"
        },
    )

    assert response.status_code == 404


def test_order_is_split_between_multiple_vendors(
    customer_headers,
    product,
    approved_vendor,
    category,
    db,
):
    suffix = uuid4().hex[:10]

    second_user = User(
        full_name="Second Vendor",
        email=f"vendor_{suffix}@example.com",
        password_hash="test-password-hash",
        role="vendor",
        is_active=True,
    )

    db.add(second_user)
    db.flush()

    second_vendor = Vendor(
        user_id=second_user.id,
        store_name=f"Second Store {suffix}",
        description="Second test vendor",
        status="approved",
        is_active=True,
    )

    db.add(second_vendor)
    db.flush()

    second_product = Product(
        vendor_id=second_vendor.id,
        category_id=category.id,
        name=f"Second Product {suffix}",
        slug=f"second-product-{suffix}",
        sku=f"SECOND-SKU-{suffix}",
        price=Decimal("100.00"),
        stock_quantity=20,
        is_active=True,
    )

    db.add(second_product)
    db.flush()

    response = client.post(
        "/api/v1/orders",
        headers=customer_headers,
        json={
            "items": [
                {
                    "product_id": product.id,
                    "quantity": 2,
                },
                {
                    "product_id": second_product.id,
                    "quantity": 3,
                },
            ]
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert len(data["vendor_orders"]) == 2
    assert Decimal(data["total_amount"]) == Decimal("500.00")

    vendor_ids = {
        item["vendor_id"]
        for item in data["vendor_orders"]
    }

    assert vendor_ids == {
        approved_vendor.id,
        second_vendor.id,
    }


def test_vendor_can_update_order_status(
    customer_headers,
    vendor_headers,
    product,
):
    create_response = client.post(
        "/api/v1/orders",
        headers=customer_headers,
        json={
            "items": [
                {
                    "product_id": product.id,
                    "quantity": 1,
                }
            ]
        },
    )

    assert create_response.status_code == 201

    order = create_response.json()
    vendor_order_id = order["vendor_orders"][0]["id"]

    for new_status in ["processing", "shipped", "delivered"]:
        response = client.patch(
            f"/api/v1/vendor-orders/{vendor_order_id}/status",
            headers=vendor_headers,
            json={"status": new_status},
        )

        assert response.status_code == 200
        assert response.json()["status"] == new_status

    order_response = client.get(
        f"/api/v1/orders/{order['id']}",
        headers=customer_headers,
    )

    assert order_response.status_code == 200
    assert order_response.json()["status"] == "delivered"


def test_vendor_cannot_access_another_vendors_order(
    customer_headers,
    vendor_headers,
    product,
    approved_vendor,
    category,
    db,
):
    suffix = uuid4().hex[:10]

    second_user = User(
        full_name="Second Vendor",
        email=f"vendor_{suffix}@example.com",
        password_hash="test-password-hash",
        role="vendor",
        is_active=True,
    )

    db.add(second_user)
    db.flush()

    second_vendor = Vendor(
        user_id=second_user.id,
        store_name=f"Second Store {suffix}",
        status="approved",
        is_active=True,
    )

    db.add(second_vendor)
    db.flush()

    second_token = create_access_token(second_user.id)

    second_product = Product(
        vendor_id=second_vendor.id,
        category_id=category.id,
        name=f"Second Product {suffix}",
        slug=f"second-product-{suffix}",
        sku=f"SECOND-SKU-{suffix}",
        price=Decimal("100.00"),
        stock_quantity=20,
        is_active=True,
    )

    db.add(second_product)
    db.flush()

    order_response = client.post(
        "/api/v1/orders",
        headers=customer_headers,
        json={
            "items": [
                {
                    "product_id": product.id,
                    "quantity": 1,
                },
                {
                    "product_id": second_product.id,
                    "quantity": 1,
                },
            ]
        },
    )

    assert order_response.status_code == 201

    first_vendor_order = next(
        item
        for item in order_response.json()["vendor_orders"]
        if item["vendor_id"] == approved_vendor.id
    )

    response = client.get(
        f"/api/v1/vendor-orders/{first_vendor_order['id']}",
        headers={
            "Authorization": f"Bearer {second_token}"
        },
    )

    assert response.status_code == 404


def test_unauthenticated_user_cannot_create_order(product):
    response = client.post(
        "/api/v1/orders",
        json={
            "items": [
                {
                    "product_id": product.id,
                    "quantity": 1,
                }
            ]
        },
    )

    assert response.status_code == 401


def test_order_rejects_empty_items(customer_headers):
    response = client.post(
        "/api/v1/orders",
        headers=customer_headers,
        json={"items": []},
    )

    assert response.status_code == 422
