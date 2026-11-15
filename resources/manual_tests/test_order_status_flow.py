
from fastapi.testclient import TestClient

from src.app import app
from src.utils.security import create_access_token


client = TestClient(app)

# Customer ID 1, Vendor user ID 3
customer_headers = {
    "Authorization": f"Bearer {create_access_token(1)}"
}

vendor_headers = {
    "Authorization": f"Bearer {create_access_token(3)}"
}

order_id = 1
vendor_order_id = 1

# 1. Verify that skipping a status is rejected
response = client.patch(
    f"/api/v1/vendor-orders/{vendor_order_id}/status",
    headers=vendor_headers,
    json={"status": "shipped"},
)

assert response.status_code == 400, response.text
print("Invalid transition rejected: OK")

# 2. Test valid transitions
transitions = [
    ("processing", "processing"),
    ("shipped", "shipped"),
    ("delivered", "delivered"),
]

for new_status, expected_parent_status in transitions:

    response = client.patch(
        f"/api/v1/vendor-orders/{vendor_order_id}/status",
        headers=vendor_headers,
        json={"status": new_status},
    )

    assert response.status_code == 200, response.text

    vendor_order = response.json()
    assert vendor_order["status"] == new_status

    # Check parent order status
    parent_response = client.get(
        f"/api/v1/orders/{order_id}",
        headers=customer_headers,
    )

    assert parent_response.status_code == 200, parent_response.text

    parent_order = parent_response.json()

    assert parent_order["status"] == expected_parent_status

    print(
        f"Vendor status: {new_status} | "
        f"Parent status: {parent_order['status']} | OK"
    )

print("\nALL STATUS TESTS PASSED")
