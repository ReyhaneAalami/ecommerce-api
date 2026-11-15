from uuid import uuid4

from fastapi.testclient import TestClient

from src.app import app


client = TestClient(app)

suffix = uuid4().hex[:8]

# Login as second vendor
login_response = client.post(
    "/api/v1/auth/login",
    json={
        "email": "customer_0beb1173@example.com",
        "password": "TestPassword123!",
    },
)

assert login_response.status_code == 200, login_response.text

token = login_response.json()["access_token"]

headers = {
    "Authorization": f"Bearer {token}"
}

# Create product
product_data = {
    "name": f"Second Vendor Product {suffix}",
    "description": "Product for multi-vendor order testing",
    "price": "75000.00",
    "stock_quantity": 15,
    "category_id": 1,
    "slug": f"second-vendor-product-{suffix}",
    "sku": f"SV-{suffix}",
}

response = client.post(
    "/api/v1/products",
    headers=headers,
    json=product_data,
)

assert response.status_code == 201, response.text

product = response.json()

print("Second vendor product created successfully")
print("Product ID:", product["id"])
print("Vendor ID:", product["vendor_id"])
print("Price:", product["price"])
print("Stock:", product["stock_quantity"])

assert product["vendor_id"] == 2
assert product["stock_quantity"] == 15

print("\nSECOND VENDOR PRODUCT TEST PASSED")