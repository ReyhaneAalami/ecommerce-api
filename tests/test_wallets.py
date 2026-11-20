
from uuid import uuid4

from fastapi.testclient import TestClient

from src.app import app
from src.data.models import Wallet, WalletTransaction


client = TestClient(app)


def test_customer_can_view_wallet(customer_headers):
    response = client.get(
        "/api/v1/wallets/me",
        headers=customer_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["balance"] == 0
    assert data["user_id"] > 0


def test_vendor_can_view_wallet(vendor_headers):
    response = client.get(
        "/api/v1/wallets/me",
        headers=vendor_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["balance"] == 0
    assert data["user_id"] > 0


def test_unauthenticated_user_cannot_view_wallet():
    response = client.get(
        "/api/v1/wallets/me",
    )

    assert response.status_code == 401


def test_unauthenticated_user_cannot_view_transactions():
    response = client.get(
        "/api/v1/wallets/me/transactions",
    )

    assert response.status_code == 401


def test_customer_can_view_empty_transaction_history(
    customer_headers,
):
    response = client.get(
        "/api/v1/wallets/me/transactions",
        headers=customer_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["items"] == []
    assert data["total"] == 0
    assert data["skip"] == 0
    assert data["limit"] == 20


def test_transaction_pagination_validation(customer_headers):
    response = client.get(
        "/api/v1/wallets/me/transactions?skip=-1",
        headers=customer_headers,
    )

    assert response.status_code == 422

    response = client.get(
        "/api/v1/wallets/me/transactions?limit=101",
        headers=customer_headers,
    )

    assert response.status_code == 422


def test_customer_can_view_wallet_transactions(
    db,
    customer,
    customer_headers,
):
    wallet = db.query(Wallet).filter(
        Wallet.user_id == customer.id
    ).one()

    transaction = WalletTransaction(
        wallet_id=wallet.id,
        transaction_type="deposit",
        amount=500000,
        balance_after=500000,
        description="Test deposit",
    )

    db.add(transaction)
    wallet.balance = 500000
    db.flush()

    response = client.get(
        "/api/v1/wallets/me/transactions",
        headers=customer_headers,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["transaction_type"] == "deposit"
    assert data["items"][0]["amount"] == 500000
    assert data["items"][0]["balance_after"] == 500000


def test_customer_cannot_access_another_wallet(
    db,
    customer,
    customer_headers,
):
    another_user = type(customer)(
        full_name="Another Customer",
        email=f"another_{uuid4().hex[:10]}@example.com",
        password_hash="test-password-hash",
        role="customer",
        is_active=True,
    )

    db.add(another_user)
    db.flush()

    another_wallet = Wallet(
        user_id=another_user.id,
        balance=1000000,
    )

    db.add(another_wallet)
    db.flush()

    # Wallet API only exposes the authenticated user's wallet.
    response = client.get(
        "/api/v1/wallets/me",
        headers=customer_headers,
    )

    assert response.status_code == 200
    assert response.json()["user_id"] == customer.id
    assert response.json()["user_id"] != another_user.id
