# Multi-Vendor E-Commerce API

A RESTful multi-vendor e-commerce backend built with FastAPI, SQLAlchemy, PostgreSQL, Alembic, and Pydantic.

## Implemented features

### Authentication
- Customer registration and login.
- JWT access tokens.
- Argon2 password hashing.

### Vendors and products
- Vendor registration, profile management, and admin approval.
- Product and category management.
- Vendor ownership and approval checks.
- Product stock validation.

### Shopping cart
- View, add, update, remove, and clear cart items.
- Cart checkout through `POST /api/v1/carts/checkout`.
- Checkout locks the cart and validates current product availability.

### Orders
- Direct order creation through `POST /api/v1/orders`.
- Multi-vendor parent orders and vendor suborders.
- Customer order history and order details.
- Vendor order history and status transitions.
- Direct cancellation only while all suborders remain pending.
- Cancellation restores stock and refunds the customer's wallet.

### Wallet and payment
- One wallet per user.
- Order payment from the customer's wallet.
- Wallet transaction history.
- Payment and stock changes occur in the same database transaction.
- Refunds are recorded as separate ledger entries.
- PostgreSQL trigger prevents UPDATE and DELETE on `wallet_transactions`.
- Idempotency keys protect order creation and checkout from duplicate retries.

## Technology stack

- Python 3.11+
- FastAPI
- SQLAlchemy
- PostgreSQL
- Alembic
- Pydantic
- PyJWT
- Argon2
- uv
- pytest

## Installation

```powershell
git clone https://github.com/ReyhaneAalami/ecommerce-api.git
cd ecommerce-api
uv sync
Copy-Item .env.example .env
```

Configure the PostgreSQL connection and JWT secret in `.env`. Never commit `.env` or expose secret values.

## Database setup

```powershell
uv run alembic upgrade head
```

## Run the API

```powershell
uv run uvicorn src.app:app --reload
```

- API: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- Health: `http://127.0.0.1:8000/health`

## API endpoints

All routes below use the `/api/v1` prefix.

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/register` | Register customer |
| POST | `/auth/login` | Login |
| POST | `/vendors/register` | Register vendor |
| GET/PATCH | `/vendors/me` | View/update vendor profile |
| GET | `/vendors/admin/pending` | List pending vendors |
| PATCH | `/vendors/admin/{vendor_id}/review` | Approve/reject vendor |
| GET | `/products` | List public products |
| GET | `/products/{product_id}` | Product details |
| POST | `/products` | Create product |
| PATCH | `/products/{product_id}` | Update product |
| DELETE | `/products/{product_id}` | Delete product |
| GET | `/products/vendor/me` | Vendor's products |
| GET | `/categories` | List categories |
| GET | `/categories/{category_id}` | Category details |
| POST/PATCH | `/categories` | Admin category management |
| GET | `/carts/me` | Current cart |
| POST | `/carts/items` | Add cart item |
| PATCH | `/carts/items/{product_id}` | Update cart item |
| DELETE | `/carts/items/{product_id}` | Remove cart item |
| DELETE | `/carts/clear` | Clear cart |
| POST | `/carts/checkout` | Checkout and pay from wallet |
| GET | `/wallets/me` | Current wallet |
| GET | `/wallets/me/transactions` | Wallet transaction history |
| POST | `/orders` | Create and pay for an order |
| GET | `/orders/me` | Customer order history |
| GET | `/orders/{order_id}` | Customer order details |
| POST | `/orders/{order_id}/cancel` | Cancel eligible order and refund |
| GET | `/vendor-orders/me` | Vendor order history |
| GET | `/vendor-orders/{vendor_order_id}` | Vendor order details |
| PATCH | `/vendor-orders/{vendor_order_id}/status` | Update vendor order status |

## Idempotency

`POST /api/v1/orders` and `POST /api/v1/carts/checkout` accept an optional `Idempotency-Key` header.

Example:

```http
Idempotency-Key: checkout-session-2026-001
```

Use a new unique key for each logical purchase and reuse the same key only when retrying that same request. Reusing a key with different direct-order data returns HTTP 409.

The header is optional for backward compatibility with existing clients and tests. Production clients should always send it.

## Wallet amounts

All monetary values are stored as integer Rial values. The backend does not accept a client-provided order total; it calculates totals from current database product prices.

Wallet top-ups through a real payment gateway are not part of this phase.

## Create an admin user

```powershell
uv run python -m scripts.create_admin
```

## Run tests

Tests use the separate PostgreSQL database `ecommerce_test_db`.

```powershell
uv run pytest -v
```

Do not point the test suite at the development or production database.

## Database models

- User
- Vendor
- Category
- Product
- Cart
- CartItem
- Wallet
- WalletTransaction
- Order
- VendorOrder
- OrderItem
- IdempotencyRecord

## Project roadmap

- Phase 1: authentication, vendors, products, categories, and approval workflow.
- Phase 2: cart, wallet payments, orders, checkout, cancellation, and refunds.
- Phase 3: PostgreSQL product search and filtering.
- Phase 4: real payment gateway and wallet top-ups.
- Phase 5: ratings, reviews, views, and sales analytics.
- Phase 6: vendor payout requests and settlement workflow.

## License

Educational and mentoring project.
