from src.app import app
from src.connections.database import SessionLocal
from src.data.models import Product, Cart, CartItem
from src.utils.security import create_access_token
from fastapi.testclient import TestClient


client = TestClient(app)

# Existing test data
customer_id = 1
product_id = 1

customer_headers = {
    "Authorization": f"Bearer {create_access_token(customer_id)}"
}

# Read initial stock
db = SessionLocal()

try:
    product = db.get(Product, product_id)

    assert product is not None
    initial_stock = product.stock_quantity

finally:
    db.close()

print("Initial stock:", initial_stock)

# 1. Clear cart before test
response = client.delete(
    "/api/v1/carts/clear",
    headers=customer_headers,
)

assert response.status_code == 200, response.text

print("Cart cleared before test: OK")

# 2. Get empty cart
response = client.get(
    "/api/v1/carts/me",
    headers=customer_headers,
)

assert response.status_code == 200, response.text

cart_data = response.json()

assert cart_data["customer_id"] == customer_id
assert len(cart_data["items"]) == 0

cart_id = cart_data["id"]

print("Empty cart retrieved: OK")

# 3. Add product with quantity 2
response = client.post(
    "/api/v1/carts/items",
    headers=customer_headers,
    json={
        "product_id": product_id,
        "quantity": 2,
    },
)

assert response.status_code == 201, response.text

cart_data = response.json()

assert len(cart_data["items"]) == 1
assert cart_data["items"][0]["quantity"] == 2

print("Add product: OK")

# 4. Add same product again
response = client.post(
    "/api/v1/carts/items",
    headers=customer_headers,
    json={
        "product_id": product_id,
        "quantity": 3,
    },
)

assert response.status_code == 201, response.text

cart_data = response.json()

assert len(cart_data["items"]) == 1
assert cart_data["items"][0]["quantity"] == 5

print("Duplicate product quantity increased: OK")

# 5. Update quantity
response = client.patch(
    f"/api/v1/carts/items/{product_id}",
    headers=customer_headers,
    json={
        "quantity": 4,
    },
)

assert response.status_code == 200, response.text

cart_data = response.json()

assert cart_data["items"][0]["quantity"] == 4

print("Update quantity: OK")

# 6. Verify stock has not changed
db = SessionLocal()

try:
    product = db.get(Product, product_id)

    assert product.stock_quantity == initial_stock

finally:
    db.close()

print("Cart operations did not change product stock: OK")

# 7. Remove product
response = client.delete(
    f"/api/v1/carts/items/{product_id}",
    headers=customer_headers,
)

assert response.status_code == 200, response.text

cart_data = response.json()

assert len(cart_data["items"]) == 0

print("Remove product: OK")

# 8. Add product again and clear cart
response = client.post(
    "/api/v1/carts/items",
    headers=customer_headers,
    json={
        "product_id": product_id,
        "quantity": 1,
    },
)

assert response.status_code == 201, response.text

response = client.delete(
    "/api/v1/carts/clear",
    headers=customer_headers,
)

assert response.status_code == 200, response.text

cart_data = response.json()

assert len(cart_data["items"]) == 0

print("Clear cart: OK")

# 9. Verify database
db = SessionLocal()

try:
    cart = db.query(Cart).filter(
        Cart.customer_id == customer_id
    ).first()

    assert cart is not None

    items = db.query(CartItem).filter(
        CartItem.cart_id == cart.id
    ).all()

    assert len(items) == 0

    product = db.get(Product, product_id)

    assert product.stock_quantity == initial_stock

finally:
    db.close()

print("Database verification: OK")

print("\nALL CART TESTS PASSED")