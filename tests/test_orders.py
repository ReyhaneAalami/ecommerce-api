
from uuid import uuid4

from fastapi.testclient import TestClient

from src.app import app
from src.data.models import (
    User,
    Vendor,
    Product,
    Wallet,
    WalletTransaction,
)
from src.utils.security import create_access_token


client = TestClient(app)


def fund_customer(db, customer, amount):
    wallet = (
        db.query(Wallet)
        .filter(Wallet.user_id == customer.id)
        .one()
    )

    wallet.balance += amount
    db.flush()

    return wallet


def test_customer_can_create_order_and_wallet_is_debited(
    db,
    customer,
    customer_headers,
    product,
):
    initial_stock = product.stock_quantity
    wallet = fund_customer(db, customer, 3000000)
    initial_balance = wallet.balance

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
    assert data["payment_status"] == "paid"
    assert data["total_amount"] == 2000000

    assert len(data["vendor_orders"]) == 1
    assert data["vendor_orders"][0]["items"][0]["quantity"] == 2

    assert product.stock_quantity == initial_stock - 2

    wallet_after = (
        db.query(Wallet)
        .filter(Wallet.user_id == customer.id)
        .one()
    )

    assert wallet_after.balance == initial_balance - 2000000

    transactions = (
        db.query(WalletTransaction)
        .filter(
            WalletTransaction.wallet_id == wallet.id,
            WalletTransaction.transaction_type == "order_payment",
            WalletTransaction.reference_type == "order",
            WalletTransaction.reference_id == data["id"],
        )
        .all()
    )

    assert len(transactions) == 1
    assert transactions[0].amount == 2000000
    assert transactions[0].balance_after == 1000000


def test_order_rejects_insufficient_wallet_balance(
    db,
    customer,
    customer_headers,
    product,
):
    initial_stock = product.stock_quantity
    wallet = fund_customer(db, customer, 500000)
    initial_balance = wallet.balance

    response = client.post(
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

    assert response.status_code == 400
    assert "Insufficient wallet balance" in response.json()["detail"]

    assert product.stock_quantity == initial_stock

    wallet_after = (
        db.query(Wallet)
        .filter(Wallet.user_id == customer.id)
        .one()
    )

    assert wallet_after.balance == initial_balance

    assert (
        db.query(WalletTransaction)
        .filter(
            WalletTransaction.wallet_id == wallet_after.id,
            WalletTransaction.transaction_type == "order_payment",
        )
        .count()
        == 0
    )


def test_order_rejects_insufficient_stock(
    db,
    customer,
    customer_headers,
    product,
):
    initial_stock = product.stock_quantity

    fund_customer(db, customer, 50000000)

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
    db,
    customer,
    customer_headers,
    product,
):
    fund_customer(db, customer, 2000000)

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
    db,
    customer,
    customer_headers,
    product,
):
    fund_customer(db, customer, 2000000)

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

    order_id = create_response.json()["id"]

    response = client.get(
        f"/api/v1/orders/{order_id}",
        headers=customer_headers,
    )

    assert response.status_code == 200
    assert response.json()["id"] == order_id
    assert response.json()["payment_status"] == "paid"


def test_customer_cannot_access_another_customers_order(
    db,
    customer,
    customer_headers,
    product,
):
    fund_customer(db, customer, 2000000)

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
    db,
    customer,
    customer_headers,
    product,
    approved_vendor,
    category,
):
    suffix = uuid4().hex[:10]

    fund_customer(db, customer, 6000000)

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
        price=1000000,
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
    assert data["total_amount"] == 5000000
    assert data["payment_status"] == "paid"

    vendor_ids = {
        item["vendor_id"]
        for item in data["vendor_orders"]
    }

    assert vendor_ids == {
        approved_vendor.id,
        second_vendor.id,
    }

    wallet_after = (
        db.query(Wallet)
        .filter(Wallet.user_id == customer.id)
        .one()
    )

    assert wallet_after.balance == 1000000


def test_vendor_can_update_order_status(
    db,
    customer,
    customer_headers,
    vendor_headers,
    product,
):
    fund_customer(db, customer, 2000000)

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
    assert order_response.json()["payment_status"] == "paid"


def test_vendor_cannot_access_another_vendors_order(
    db,
    customer,
    customer_headers,
    product,
    approved_vendor,
    category,
):
    suffix = uuid4().hex[:10]

    fund_customer(db, customer, 3000000)

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
        price=1000000,
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


def test_customer_can_cancel_order_and_receive_refund(
    db,
    customer,
    customer_headers,
    product,
):
    initial_stock = product.stock_quantity
    fund_customer(db, customer, 3000000)

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

    order_id = response.json()["id"]

    wallet = (
        db.query(Wallet)
        .filter(Wallet.user_id == customer.id)
        .one()
    )

    assert wallet.balance == 1000000
    assert product.stock_quantity == initial_stock - 2

    cancel_response = client.post(
        f"/api/v1/orders/{order_id}/cancel",
        headers=customer_headers,
    )

    assert cancel_response.status_code == 200

    data = cancel_response.json()

    assert data["id"] == order_id
    assert data["status"] == "cancelled"
    assert data["payment_status"] == "refunded"

    assert all(
        vendor_order["status"] == "cancelled"
        for vendor_order in data["vendor_orders"]
    )

    db.refresh(wallet)
    db.refresh(product)

    assert wallet.balance == 3000000
    assert product.stock_quantity == initial_stock

    refund_count = (
        db.query(WalletTransaction)
        .filter(
            WalletTransaction.wallet_id == wallet.id,
            WalletTransaction.transaction_type == "refund",
            WalletTransaction.reference_type == "order",
            WalletTransaction.reference_id == order_id,
        )
        .count()
    )

    assert refund_count == 1


def test_repeated_order_cancellation_does_not_duplicate_refund(
    db,
    customer,
    customer_headers,
    product,
):
    initial_stock = product.stock_quantity
    fund_customer(db, customer, 3000000)

    response = client.post(
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

    assert response.status_code == 201

    order_id = response.json()["id"]

    wallet = (
        db.query(Wallet)
        .filter(Wallet.user_id == customer.id)
        .one()
    )

    first_cancel = client.post(
        f"/api/v1/orders/{order_id}/cancel",
        headers=customer_headers,
    )

    assert first_cancel.status_code == 200

    db.refresh(wallet)
    balance_after_first_cancel = wallet.balance

    db.refresh(product)
    stock_after_first_cancel = product.stock_quantity

    second_cancel = client.post(
        f"/api/v1/orders/{order_id}/cancel",
        headers=customer_headers,
    )

    assert second_cancel.status_code == 200

    db.refresh(wallet)
    db.refresh(product)

    assert wallet.balance == balance_after_first_cancel
    assert product.stock_quantity == stock_after_first_cancel
    assert product.stock_quantity == initial_stock

    refund_count = (
        db.query(WalletTransaction)
        .filter(
            WalletTransaction.wallet_id == wallet.id,
            WalletTransaction.transaction_type == "refund",
            WalletTransaction.reference_type == "order",
            WalletTransaction.reference_id == order_id,
        )
        .count()
    )

    assert refund_count == 1


def test_customer_cannot_cancel_order_after_vendor_starts_processing(
    db,
    customer,
    customer_headers,
    vendor_headers,
    product,
):
    initial_stock = product.stock_quantity
    fund_customer(db, customer, 3000000)

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
    order_id = order["id"]
    vendor_order_id = order["vendor_orders"][0]["id"]

    status_response = client.patch(
        f"/api/v1/vendor-orders/{vendor_order_id}/status",
        headers=vendor_headers,
        json={"status": "processing"},
    )

    assert status_response.status_code == 200
    assert status_response.json()["status"] == "processing"

    cancel_response = client.post(
        f"/api/v1/orders/{order_id}/cancel",
        headers=customer_headers,
    )

    assert cancel_response.status_code == 400

    wallet = (
        db.query(Wallet)
        .filter(Wallet.user_id == customer.id)
        .one()
    )

    db.refresh(wallet)
    db.refresh(product)

    assert wallet.balance == 2000000
    assert product.stock_quantity == initial_stock - 1

    refund_count = (
        db.query(WalletTransaction)
        .filter(
            WalletTransaction.wallet_id == wallet.id,
            WalletTransaction.transaction_type == "refund",
            WalletTransaction.reference_type == "order",
            WalletTransaction.reference_id == order_id,
        )
        .count()
    )

    assert refund_count == 0


def test_customer_cannot_cancel_another_customers_order(
    db,
    customer,
    customer_headers,
    product,
):
    fund_customer(db, customer, 3000000)

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

    cancel_response = client.post(
        f"/api/v1/orders/{order_id}/cancel",
        headers={
            "Authorization": f"Bearer {other_token}"
        },
    )

    assert cancel_response.status_code == 404


def test_unauthenticated_user_cannot_cancel_order():
    response = client.post(
        "/api/v1/orders/1/cancel",
    )

    assert response.status_code == 401
