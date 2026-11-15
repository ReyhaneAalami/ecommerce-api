from uuid import uuid4

from fastapi.testclient import TestClient

from src.app import app
from src.utils.security import create_access_token


client = TestClient(app)

# Admin account ID
admin_token = create_access_token(2)

admin_headers = {
    "Authorization": f"Bearer {admin_token}"
}

# Generate unique test data
suffix = uuid4().hex[:8]

customer_data = {
    "full_name": "Second Test Customer",
    "email": f"customer_{suffix}@example.com",
    "phone": None,
    "password": "TestPassword123!"
}

# 1. Register second customer
response = client.post(
    "/api/v1/auth/register",
    json=customer_data,
)

assert response.status_code == 201, response.text

customer_result = response.json()
customer_id = customer_result["user"]["id"]
customer_token = customer_result["access_token"]

print("Second customer created:", customer_id)

customer_headers = {
    "Authorization": f"Bearer {customer_token}"
}

# 2. Register second vendor
vendor_data = {
    "store_name": f"Second Test Store {suffix}",
    "description": "Second vendor for access control testing"
}

response = client.post(
    "/api/v1/vendors/register",
    headers=customer_headers,
    json=vendor_data,
)

assert response.status_code == 201, response.text

vendor_result = response.json()
vendor_id = vendor_result["id"]

print("Second vendor created:", vendor_id)
assert vendor_result["status"] == "pending"

# 3. Admin approves second vendor
response = client.patch(
    f"/api/v1/vendors/admin/{vendor_id}/review",
    headers=admin_headers,
    json={"status": "approved"},
)

assert response.status_code == 200, response.text

approved_vendor = response.json()

assert approved_vendor["status"] == "approved"
assert approved_vendor["is_active"] is True

print("Second vendor approved:", vendor_id)

print("\nSECOND VENDOR SETUP PASSED")
print("Customer ID:", customer_id)
print("Vendor ID:", vendor_id)