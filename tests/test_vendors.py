
from uuid import uuid4

from fastapi.testclient import TestClient

from src.app import app


client = TestClient(app)


def create_customer():
    suffix = uuid4().hex[:10]

    response = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Vendor Test User",
            "email": f"vendor_{suffix}@example.com",
            "password": "TestPassword123!",
        },
    )

    assert response.status_code == 201

    data = response.json()

    return data["access_token"], data["user"]


def test_customer_can_register_vendor():
    token, user = create_customer()

    suffix = uuid4().hex[:8]

    response = client.post(
        "/api/v1/vendors/register",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "store_name": f"Test Store {suffix}",
            "description": "Automated vendor test",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["user_id"] == user["id"]
    assert data["status"] == "pending"
    assert data["is_active"] is True


def test_customer_cannot_register_two_vendors():
    token, _ = create_customer()

    headers = {"Authorization": f"Bearer {token}"}

    first_response = client.post(
        "/api/v1/vendors/register",
        headers=headers,
        json={"store_name": f"First Store {uuid4().hex[:8]}"},
    )

    assert first_response.status_code == 201

    second_response = client.post(
        "/api/v1/vendors/register",
        headers=headers,
        json={"store_name": f"Second Store {uuid4().hex[:8]}"},
    )

    assert second_response.status_code == 403


def test_customer_cannot_access_vendor_profile():
    token, _ = create_customer()

    response = client.get(
        "/api/v1/vendors/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_unauthenticated_user_cannot_access_vendor_profile():
    response = client.get("/api/v1/vendors/me")

    assert response.status_code == 401


def test_customer_cannot_access_admin_pending_vendors():
    token, _ = create_customer()

    response = client.get(
        "/api/v1/vendors/admin/pending",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
