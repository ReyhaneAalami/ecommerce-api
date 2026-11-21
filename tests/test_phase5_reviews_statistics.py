from uuid import uuid4
from fastapi.testclient import TestClient

from src.app import app
from src.data.models import User, Order, VendorOrder, OrderItem, Wallet
from src.utils.security import create_access_token

client = TestClient(app)


def _admin_headers(db):
    suffix = uuid4().hex[:10]
    admin = User(full_name="Test Admin", email=f"admin_{suffix}@example.com", password_hash="x", role="admin", is_active=True)
    db.add(admin)
    db.flush()
    return {"Authorization": f"Bearer {create_access_token(admin.id)}"}


def _delivered_purchase(db, customer, product, status="delivered"):
    order = Order(customer_id=customer.id, status=status, payment_status="paid", total_amount=product.price)
    db.add(order)
    db.flush()
    vendor_order = VendorOrder(order_id=order.id, vendor_id=product.vendor_id, vendor_name="Test Store", status=status, subtotal=product.price, shipping_fee=0, total_amount=product.price)
    db.add(vendor_order)
    db.flush()
    item = OrderItem(vendor_order_id=vendor_order.id, product_id=product.id, product_name=product.name, sku=product.sku, quantity=1, unit_price=product.price, subtotal=product.price)
    db.add(item)
    db.flush()
    return order, vendor_order, item


def test_review_requires_delivered_purchase(db, customer, product, customer_headers):
    _, _, item = _delivered_purchase(db, customer, product, status="shipped")
    response = client.post("/api/v1/reviews", headers=customer_headers, json={
        "product_id": product.id, "order_item_id": item.id, "rating": 5, "body": "Excellent product quality."
    })
    assert response.status_code == 409


def test_review_moderation_and_public_rating_summary(db, customer, product, customer_headers):
    _, _, item = _delivered_purchase(db, customer, product)
    created = client.post("/api/v1/reviews", headers=customer_headers, json={
        "product_id": product.id, "order_item_id": item.id, "rating": 5,
        "title": "Great", "body": "Excellent product quality and delivery."
    })
    assert created.status_code == 201, created.text
    review_id = created.json()["id"]

    public_before = client.get(f"/api/v1/reviews/products/{product.id}")
    assert public_before.status_code == 200
    assert public_before.json()["total"] == 0

    admin_headers = _admin_headers(db)
    moderated = client.patch(f"/api/v1/reviews/admin/{review_id}/moderate", headers=admin_headers, json={"status": "approved"})
    assert moderated.status_code == 200, moderated.text
    summary = client.get(f"/api/v1/reviews/products/{product.id}/summary")
    assert summary.status_code == 200
    assert summary.json()["average_rating"] == 5.0
    assert summary.json()["review_count"] == 1


def test_customer_cannot_review_same_product_twice(db, customer, product, customer_headers):
    _, _, item = _delivered_purchase(db, customer, product)
    payload = {"product_id": product.id, "order_item_id": item.id, "rating": 4, "body": "Good product, works well."}
    assert client.post("/api/v1/reviews", headers=customer_headers, json=payload).status_code == 201
    duplicate = client.post("/api/v1/reviews", headers=customer_headers, json=payload)
    assert duplicate.status_code == 409


def test_vendor_statistics_endpoint(db, approved_vendor, vendor_headers, product):
    response = client.get("/api/v1/statistics/vendors/me", headers=vendor_headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["vendor_id"] == approved_vendor.id
    assert data["product_count"] == 1
    assert data["inventory_units"] == product.stock_quantity


def test_delivered_vendor_order_credits_vendor_wallet_once(db, approved_vendor, vendor_headers, product):
    customer = User(full_name="Buyer", email=f"buyer_{uuid4().hex[:10]}@example.com", password_hash="x", role="customer", is_active=True)
    db.add(customer)
    db.flush()
    _, vendor_order, _ = _delivered_purchase(db, customer, product, status="shipped")
    response = client.patch(f"/api/v1/vendor-orders/{vendor_order.id}/status", headers=vendor_headers, json={"status": "delivered"})
    assert response.status_code == 200, response.text
    wallet = db.query(Wallet).filter(Wallet.user_id == approved_vendor.user_id).one()
    assert wallet.balance == vendor_order.subtotal


def test_admin_can_view_platform_statistics(db, customer, product):
    admin_headers = _admin_headers(db)
    response = client.get("/api/v1/statistics/admin", headers=admin_headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["customer_count"] >= 1
    assert data["product_count"] >= 1
    assert "pending_payout_count" in data
