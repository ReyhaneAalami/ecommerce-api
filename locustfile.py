import os
from locust import HttpUser, task, between
from locust.exception import StopUser

CUSTOMER_TOKEN = os.getenv("CUSTOMER_TOKEN", "").strip()
VENDOR_TOKEN = os.getenv("VENDOR_TOKEN", "").strip()


class PublicShopper(HttpUser):
    """Public read-only workload; safe for baseline and load tests."""
    weight = 6
    wait_time = between(1, 3)

    @task(5)
    def list_products(self):
        self.client.get(
            "/api/v1/products?skip=0&limit=20",
            name="GET /api/v1/products",
        )

    @task(2)
    def list_categories(self):
        self.client.get(
            "/api/v1/categories",
            name="GET /api/v1/categories",
        )

    @task(1)
    def health(self):
        self.client.get("/health", name="GET /health")


class AuthenticatedCustomer(HttpUser):
    """Customer read workload; enabled only when CUSTOMER_TOKEN is set."""
    weight = 3
    wait_time = between(1, 3)

    def on_start(self):
        if not CUSTOMER_TOKEN:
            raise StopUser()
        self.client.headers.update(
            {"Authorization": f"Bearer {CUSTOMER_TOKEN}"}
        )

    @task(3)
    def get_cart(self):
        self.client.get("/api/v1/carts/me", name="GET /api/v1/carts/me")

    @task(2)
    def get_orders(self):
        self.client.get("/api/v1/orders/me", name="GET /api/v1/orders/me")

    @task(1)
    def get_wallet(self):
        self.client.get("/api/v1/wallets/me", name="GET /api/v1/wallets/me")


class AuthenticatedVendor(HttpUser):
    """Vendor read workload; enabled only when VENDOR_TOKEN is set."""
    weight = 1
    wait_time = between(1, 3)

    def on_start(self):
        if not VENDOR_TOKEN:
            raise StopUser()
        self.client.headers.update(
            {"Authorization": f"Bearer {VENDOR_TOKEN}"}
        )

    @task(3)
    def get_vendor_orders(self):
        self.client.get(
            "/api/v1/vendor-orders/me",
            name="GET /api/v1/vendor-orders/me",
        )

    @task(2)
    def get_vendor_products(self):
        self.client.get(
            "/api/v1/products/vendor/me",
            name="GET /api/v1/products/vendor/me",
        )

    @task(1)
    def get_wallet(self):
        self.client.get("/api/v1/wallets/me", name="GET /api/v1/wallets/me")
