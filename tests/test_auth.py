
from uuid import uuid4

from fastapi.testclient import TestClient

from src.app import app


client = TestClient(app)


def test_register_and_login():
    suffix = uuid4().hex[:10]

    email = f"test_{suffix}@example.com"
    password = "TestPassword123!"

    # 1. Register a new customer
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

    assert register_data["access_token"]
    assert register_data["user"]["email"] == email
    assert register_data["user"]["role"] == "customer"

    # 2. Login with the same credentials
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
    assert login_data["user"]["id"] == register_data["user"]["id"]
    assert login_data["user"]["email"] == email
