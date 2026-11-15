
from uuid import uuid4

from fastapi.testclient import TestClient

from src.app import app
from src.utils.security import create_access_token


client = TestClient(app)
suffix = uuid4().hex[:8]

# 1. Register customer
response = client.post(
    "/api/v1/auth/register",
    json={
        "full_name": "Test Vendor",
        "email": f"vendor.test.{suffix}@example.com",
        "password": "TestPassword123!",
    },
)
assert response.status_code == 201, response.text

vendor_token = response.json()["access_token"]
user_id = response.json()["user"]["id"]
vendor_headers = {"Authorization": f"Bearer {vendor_token}"}

print("1. Customer registration: OK | User:", user_id)

# 2. Register vendor
response = client.post(
    "/api/v1/vendors/register",
    headers=vendor_headers,
    json={
        "store_name": f"Test Store {suffix}",
        "description": "Integration test store",
    },
)
assert response.status_code == 201, response.text

vendor_id = response.json()["id"]
print("2. Vendor registration: OK | Vendor:", vendor_id)

# 3. Admin approval
admin_headers = {
    "Authorization": f"Bearer {create_access_token(2)}"
}

response = client.patch(
    f"/api/v1/vendors/admin/{vendor_id}/review",
    headers=admin_headers,
    json={"status": "approved"},
)
assert response.status_code == 200, response.text
print("3. Vendor approval: OK")

# 4. Create category
response = client.post(
    "/api/v1/categories",
    headers=admin_headers,
    json={
        "name": f"Test Category {suffix}",
        "slug": f"test-category-{suffix}",
        "description": "Integration test category",
    },
)
assert response.status_code == 201, response.text

category_id = response.json()["id"]
print("4. Category creation: OK | Category:", category_id)

# 5. Create product
response = client.post(
    "/api/v1/products",
    headers=vendor_headers,
    json={
        "name": f"Test Product {suffix}",
        "slug": f"test-product-{suffix}",
        "description": "Integration test product",
        "price": 125000,
        "stock_quantity": 20,
        "category_id": category_id,
        "sku": f"SKU-{suffix}",
    },
)
assert response.status_code == 201, response.text

product = response.json()

print("5. Product creation: OK")
print("   Product ID:", product["id"])
print("   Price:", product["price"])
print("   Stock:", product["stock_quantity"])

print("\nALL TESTS PASSED")
