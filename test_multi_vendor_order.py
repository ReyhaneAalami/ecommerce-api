from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select

from src.app import app
from src.connections.database import SessionLocal
from src.data.models import Product, Order, VendorOrder, OrderItem
from src.utils.security import create_access_token


client = TestClient(app)

customer_id = 1

product_quantities = {
    1: 2,
    2: 3,
}

headers = {
    "Authorization": f"Bearer {create_access_token(customer_id)}"
}


# 1. Read initial stock and prices
db = SessionLocal()

try:
    products = {}

    for product_id, quantity in product_quantities.items():
        product = db.get(Product, product_id)

        assert product is not None, f"Product {product_id} not found"

        products[product_id] = {
            "stock": product.stock_quantity,
            "price": Decimal(product.price),
            "vendor_id": product.vendor_id,
        }

        assert product.stock_quantity >= quantity

finally:
    db.close()

print("Initial product data:", products)


# 2. Create one order with products from two vendors
response = client.post(
    "/api/v1/orders",
    headers=headers,
    json={
        "items": [
            {"product_id": 1, "quantity": 2},
            {"product_id": 2, "quantity": 3},
        ]
    },
)

assert response.status_code == 201, response.text

order_data = response.json()
order_id = order_data["id"]

print("Parent order created:", order_id)
print("Parent total:", order_data["total_amount"])

assert order_data["customer_id"] == customer_id
assert len(order_data["vendor_orders"]) == 2


# 3. Verify vendor suborders and totals
vendor_ids = set()
expected_total = Decimal("0.00")
suborder_ids = {}

for vendor_order in order_data["vendor_orders"]:
    vendor_id = vendor_order["vendor_id"]
    vendor_ids.add(vendor_id)

    assert len(vendor_order["items"]) == 1

    item = vendor_order["items"][0]
    product_id = item["product_id"]
    quantity = product_quantities[product_id]

    assert item["quantity"] == quantity
    assert vendor_id == products[product_id]["vendor_id"]

    expected_subtotal = products[product_id]["price"] * quantity

    assert Decimal(str(item["subtotal"])) == expected_subtotal
    assert Decimal(str(vendor_order["subtotal"])) == expected_subtotal

    expected_total += expected_subtotal
    suborder_ids[vendor_id] = vendor_order["id"]

assert vendor_ids == {1, 2}
assert Decimal(str(order_data["total_amount"])) == expected_total

print("Two separate vendor orders: OK")
print("Order totals: OK")


# 4. Verify database records and stock
db = SessionLocal()

try:
    order = db.get(Order, order_id)

    assert order is not None

    vendor_orders = list(
        db.scalars(
            select(VendorOrder).where(
                VendorOrder.order_id == order_id
            )
        ).all()
    )

    assert len(vendor_orders) == 2

    for vendor_order in vendor_orders:
        items = list(
            db.scalars(
                select(OrderItem).where(
                    OrderItem.vendor_order_id == vendor_order.id
                )
            ).all()
        )

        assert len(items) == 1

    for product_id, quantity in product_quantities.items():
        product = db.get(Product, product_id)

        expected_stock = products[product_id]["stock"] - quantity

        assert product.stock_quantity == expected_stock

        print(
            f"Product {product_id} stock:",
            products[product_id]["stock"],
            "->",
            product.stock_quantity,
        )

    print("Parent order in database: OK")
    print("Both vendor orders in database: OK")
    print("Order items in database: OK")

finally:
    db.close()


print("\nALL MULTI-VENDOR ORDER TESTS PASSED")
print("Order ID:", order_id)
print("Vendor suborder IDs:", suborder_ids)