
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from src.app import app
from src.connections.database import SessionLocal
from src.data.models import Product, Order, VendorOrder, OrderItem
from src.utils.security import create_access_token


client = TestClient(app)

# Existing test data
customer_id = 1
product_id = 1
vendor_id = 1
quantity = 2

customer_headers = {
    "Authorization": f"Bearer {create_access_token(customer_id)}"
}

# 1. Read initial stock
db = SessionLocal()

try:
    product = db.get(Product, product_id)

    assert product is not None, "Product not found"

    initial_stock = product.stock_quantity
    unit_price = Decimal(product.price)

finally:
    db.close()

print("Initial stock:", initial_stock)

# 2. Create order
response = client.post(
    "/api/v1/orders",
    headers=customer_headers,
    json={
        "items": [
            {
                "product_id": product_id,
                "quantity": quantity,
            }
        ]
    },
)

assert response.status_code == 201, response.text

order_data = response.json()
order_id = order_data["id"]

print("Order created:", order_id)
print("Order status:", order_data["status"])
print("Order total:", order_data["total_amount"])

# 3. Verify order structure
assert order_data["customer_id"] == customer_id
assert len(order_data["vendor_orders"]) == 1

vendor_order_data = order_data["vendor_orders"][0]

assert vendor_order_data["vendor_id"] == vendor_id
assert len(vendor_order_data["items"]) == 1

item_data = vendor_order_data["items"][0]

assert item_data["product_id"] == product_id
assert item_data["quantity"] == quantity

expected_subtotal = unit_price * quantity

assert Decimal(str(item_data["subtotal"])) == expected_subtotal
assert Decimal(str(order_data["total_amount"])) == expected_subtotal

print("Order structure and totals: OK")

# 4. Verify database records and stock
db = SessionLocal()

try:
    product = db.get(Product, product_id)
    order = db.get(Order, order_id)

    vendor_orders = list(
        db.scalars(
            select(VendorOrder).where(
                VendorOrder.order_id == order_id
            )
        ).all()
    )

    assert order is not None
    assert len(vendor_orders) == 1

    order_items = list(
        db.scalars(
            select(OrderItem).where(
                OrderItem.vendor_order_id == vendor_orders[0].id
            )
        ).all()
    )

    assert len(order_items) == 1
    assert product.stock_quantity == initial_stock - quantity

    print("Parent order in database: OK")
    print("Vendor suborder in database: OK")
    print("Order item in database: OK")
    print("Stock before:", initial_stock)
    print("Stock after:", product.stock_quantity)

finally:
    db.close()

print("\nALL ORDER TESTS PASSED")
