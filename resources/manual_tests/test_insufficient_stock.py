
from fastapi.testclient import TestClient
from sqlalchemy import select, func

from src.app import app
from src.connections.database import SessionLocal
from src.data.models import Product, Order
from src.utils.security import create_access_token


client = TestClient(app)

customer_headers = {
    "Authorization": f"Bearer {create_access_token(1)}"
}

db = SessionLocal()

try:
    product = db.get(Product, 1)
    assert product is not None

    initial_stock = product.stock_quantity
    initial_order_count = db.scalar(
        select(func.count()).select_from(Order)
    )

finally:
    db.close()

# Request more than available stock
response = client.post(
    "/api/v1/orders",
    headers=customer_headers,
    json={
        "items": [
            {
                "product_id": 1,
                "quantity": initial_stock + 1,
            }
        ]
    },
)

assert response.status_code == 400, response.text

db = SessionLocal()

try:
    product = db.get(Product, 1)

    final_order_count = db.scalar(
        select(func.count()).select_from(Order)
    )

    assert product.stock_quantity == initial_stock
    assert final_order_count == initial_order_count

    print("Insufficient stock rejected: OK")
    print("Stock unchanged:", product.stock_quantity)
    print("No new order created: OK")

finally:
    db.close()

print("\nALL NEGATIVE TESTS PASSED")
