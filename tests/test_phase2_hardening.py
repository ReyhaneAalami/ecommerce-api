import pytest

from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from fastapi.testclient import TestClient

from src.app import app
from src.data.models import Wallet, WalletTransaction


client = TestClient(app)


def _fund_customer(db, customer, amount=10_000_000):
    wallet = db.scalar(
        select(Wallet).where(Wallet.user_id == customer.id)
    )
    wallet.balance = amount
    db.flush()
    return wallet


def test_order_idempotency_reuses_existing_order(
    db, customer, customer_headers, product
):
    wallet = _fund_customer(db, customer)
    initial_stock = product.stock_quantity

    payload = {
        "items": [{"product_id": product.id, "quantity": 1}]
    }
    headers = {
        **customer_headers,
        "Idempotency-Key": "order-test-key-0001",
    }

    first = client.post("/api/v1/orders", json=payload, headers=headers)
    second = client.post("/api/v1/orders", json=payload, headers=headers)

    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["id"] == second.json()["id"]

    db.refresh(wallet)
    db.refresh(product)
    assert wallet.balance == 9_000_000
    assert product.stock_quantity == initial_stock - 1


def test_order_idempotency_rejects_different_payload(
    customer_headers, customer, db, product
):
    _fund_customer(db, customer)

    headers = {
        **customer_headers,
        "Idempotency-Key": "order-test-key-0002",
    }

    first = client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": product.id, "quantity": 1}]},
        headers=headers,
    )
    second = client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": product.id, "quantity": 2}]},
        headers=headers,
    )

    assert first.status_code == 201, first.text
    assert second.status_code == 409, second.text


def test_checkout_creates_order_and_clears_cart(
    db, customer, customer_headers, product
):
    wallet = _fund_customer(db, customer)

    add_response = client.post(
        "/api/v1/carts/items",
        json={"product_id": product.id, "quantity": 2},
        headers=customer_headers,
    )
    assert add_response.status_code == 201, add_response.text

    response = client.post(
        "/api/v1/carts/checkout",
        headers={
            **customer_headers,
            "Idempotency-Key": "checkout-test-key-01",
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["payment_status"] == "paid"

    cart_response = client.get(
        "/api/v1/carts/me",
        headers=customer_headers,
    )
    assert cart_response.status_code == 200
    assert cart_response.json()["items"] == []

    db.refresh(wallet)
    assert wallet.balance == 8_000_000


def test_wallet_ledger_rejects_update_and_delete(db, customer):
    wallet = db.scalar(
        select(Wallet).where(Wallet.user_id == customer.id)
    )
    transaction = WalletTransaction(
        wallet_id=wallet.id,
        transaction_type="manual_test",
        amount=100,
        balance_after=0,
        description="immutability test",
    )
    db.add(transaction)
    db.flush()

    db.execute(
        text(
            """
            CREATE OR REPLACE FUNCTION prevent_wallet_transaction_mutation()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'wallet_transactions are immutable'
                    USING ERRCODE = '55000';
            END;
            $$ LANGUAGE plpgsql
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TRIGGER trg_wallet_transactions_immutable
            BEFORE UPDATE OR DELETE ON wallet_transactions
            FOR EACH ROW
            EXECUTE FUNCTION prevent_wallet_transaction_mutation()
            """
        )
    )

    with pytest.raises(DBAPIError):
        db.execute(
            text(
                "UPDATE wallet_transactions SET amount = 200 WHERE id = :id"
            ),
            {"id": transaction.id},
        )
    db.rollback()
