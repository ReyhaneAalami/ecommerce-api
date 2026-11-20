from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.app import app
from src.data.models import Wallet


client = TestClient(app)


def test_register_and_login(db: Session):
    suffix = uuid4().hex[:10]

    email = f"test_{suffix}@example.com"
    password = "TestPassword123!"

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Automated Test User",
            "email": email,
            "password": password,
        },
    )

    assert register_response.status_code == 201

    register_data = register_response.json()
    user_id = register_data["user"]["id"]

    assert register_data["access_token"]
    assert register_data["user"]["email"] == email
    assert register_data["user"]["role"] == "customer"

    wallet = db.scalar(
        select(Wallet).where(Wallet.user_id == user_id)
    )

    assert wallet is not None
    assert wallet.balance == 0

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert login_response.status_code == 200

    login_data = login_response.json()

    assert login_data["access_token"]
    assert login_data["user"]["id"] == user_id
    assert login_data["user"]["email"] == email
