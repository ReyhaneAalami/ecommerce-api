from fastapi.testclient import TestClient

from src.app import app
from src.utils.security import create_access_token


client = TestClient(app)

vendor_1_headers = {
    "Authorization": f"Bearer {create_access_token(3)}"
}

vendor_2_headers = {
    "Authorization": f"Bearer {create_access_token(4)}"
}


# Vendor 1 can access own order
response = client.get(
    "/api/v1/vendor-orders/2",
    headers=vendor_1_headers,
)
assert response.status_code == 200, response.text
print("Vendor 1 can access own order: OK")


# Vendor 1 cannot access Vendor 2 order
response = client.get(
    "/api/v1/vendor-orders/3",
    headers=vendor_1_headers,
)
assert response.status_code == 404, response.text
print("Vendor 1 cannot access Vendor 2 order: OK")


# Vendor 2 can access own order
response = client.get(
    "/api/v1/vendor-orders/3",
    headers=vendor_2_headers,
)
assert response.status_code == 200, response.text
print("Vendor 2 can access own order: OK")


# Vendor 2 cannot access Vendor 1 order
response = client.get(
    "/api/v1/vendor-orders/2",
    headers=vendor_2_headers,
)
assert response.status_code == 404, response.text
print("Vendor 2 cannot access Vendor 1 order: OK")


# Vendor 1 cannot update Vendor 2 order
response = client.patch(
    "/api/v1/vendor-orders/3/status",
    headers=vendor_1_headers,
    json={"status": "processing"},
)
assert response.status_code == 404, response.text
print("Vendor 1 cannot update Vendor 2 order: OK")


# Vendor 2 cannot update Vendor 1 order
response = client.patch(
    "/api/v1/vendor-orders/2/status",
    headers=vendor_2_headers,
    json={"status": "processing"},
)
assert response.status_code == 404, response.text
print("Vendor 2 cannot update Vendor 1 order: OK")


print("\nALL VENDOR ISOLATION TESTS PASSED")