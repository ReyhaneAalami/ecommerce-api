from fastapi.testclient import TestClient

from src.app import app
from src.utils.security import create_access_token


client = TestClient(app)

customer_token = create_access_token(1)
vendor_token = create_access_token(3)

customer_headers = {
    "Authorization": f"Bearer {customer_token}"
}

vendor_headers = {
    "Authorization": f"Bearer {vendor_token}"
}


# 1. Customer can access their own order
response = client.get(
    "/api/v1/orders/1",
    headers=customer_headers,
)
assert response.status_code == 200, response.text
print("Customer can access own order: OK")


# 2. Vendor cannot access customer order endpoint
response = client.get(
    "/api/v1/orders/1",
    headers=vendor_headers,
)
assert response.status_code == 403, response.text
print("Vendor cannot access customer order: OK")


# 3. Customer cannot update vendor order status
response = client.patch(
    "/api/v1/vendor-orders/1/status",
    headers=customer_headers,
    json={"status": "processing"},
)
assert response.status_code == 403, response.text
print("Customer cannot update vendor order: OK")


# 4. Vendor can access their own vendor order
response = client.get(
    "/api/v1/vendor-orders/1",
    headers=vendor_headers,
)
assert response.status_code == 200, response.text
print("Vendor can access own vendor order: OK")


# 5. Unauthenticated user cannot access order
response = client.get("/api/v1/orders/1")
assert response.status_code == 401, response.text
print("Unauthenticated access rejected: OK")


print("\nALL ACCESS CONTROL TESTS PASSED")