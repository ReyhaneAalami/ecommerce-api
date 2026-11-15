# Multi-Vendor E-Commerce API

A RESTful multi-vendor e-commerce backend built with **FastAPI**, **SQLAlchemy**, and **PostgreSQL**.

The project supports customer authentication, vendor registration and approval, product and category management, shopping carts, and multi-vendor order processing.

## Features

### Authentication
- Customer registration and login.
- JWT-based authentication.
- Password hashing using Argon2.

### Vendor Management
- Register a vendor account.
- View and update vendor profile.
- Admin review and approval/rejection of vendor applications.
- Only approved vendors can manage products.

### Products
- Public product listing and product details.
- Create, update, and delete vendor-owned products.
- List products belonging to the authenticated vendor.
- Pagination support.

### Categories
- Public category listing and details.
- Admin-only category creation and updates.

### Shopping Cart
- View the customer's cart.
- Add products to the cart.
- Update product quantities.
- Remove individual products.
- Clear the cart.

### Orders
- Create customer orders.
- View customer order history and order details.
- Split orders into vendor-specific orders.
- Vendors can view their own orders.
- Vendors can update the status of their orders.
- Stock validation and inventory updates during order creation.
- Ownership checks for customer and vendor resources.

## Technology Stack

- Python 3.11+
- FastAPI
- SQLAlchemy
- PostgreSQL
- Alembic
- Pydantic
- JWT (PyJWT)
- Argon2
- uv
- pytest

## Project Structure

```text
ecommerce-api/
├── resources/
├── scripts/
│   └── create_admin.py
├── src/
│   ├── api/
│   │   ├── dependencies.py
│   │   └── endpoints/
│   │       └── v1/
│   ├── connections/
│   ├── data/
│   │   └── models/
│   ├── schemas/
│   ├── services/
│   ├── utils/
│   ├── config.py
│   └── app.py
├── tests/
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_carts.py
│   ├── test_orders.py
│   ├── test_products.py
│   └── test_vendors.py
├── alembic/
├── .env.example
├── .gitignore
├── alembic.ini
├── pyproject.toml
├── uv.lock
└── README.md
```

## Requirements

- Python 3.11 or newer
- PostgreSQL
- uv

## Installation

Clone the repository:

```bash
git clone https://github.com/ReyhaneAalami/ecommerce-api.git
cd ecommerce-api
```

Install dependencies:

```bash
uv sync
```

Create your local environment file:

```powershell
Copy-Item .env.example .env
```

Configure the required environment variables in `.env`, including your PostgreSQL database connection and JWT secret key.

**Never commit your `.env` file or expose secret keys.**

## Database Setup

Apply database migrations:

```bash
uv run alembic upgrade head
```

To create a new migration after changing models:

```bash
uv run alembic revision --autogenerate -m "describe your changes"
```

Apply the new migration:

```bash
uv run alembic upgrade head
```

## Create an Admin User

Run the admin creation script:

```bash
uv run python -m scripts.create_admin
```

Follow the prompts to create an administrator account.

## Run the Application

```bash
uv run uvicorn src.app:app --reload
```

The API will be available at:

- API base URL: `http://127.0.0.1:8000`
- Swagger documentation: `http://127.0.0.1:8000/docs`
- ReDoc documentation: `http://127.0.0.1:8000/redoc`
- Health check: `http://127.0.0.1:8000/health`

## API Endpoints

All version 1 endpoints use the `/api/v1` prefix.

### Authentication

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/register` | Register a customer |
| POST | `/auth/login` | Login |

### Vendors

| Method | Endpoint | Description |
|---|---|---|
| POST | `/vendors/register` | Register a vendor |
| GET | `/vendors/me` | Get own vendor profile |
| PATCH | `/vendors/me` | Update own vendor profile |
| GET | `/vendors/admin/pending` | List pending vendor applications |
| PATCH | `/vendors/admin/{vendor_id}/review` | Approve or reject a vendor |

### Products

| Method | Endpoint | Description |
|---|---|---|
| GET | `/products` | List public products |
| GET | `/products/{product_id}` | Get product details |
| POST | `/products` | Create a product |
| PATCH | `/products/{product_id}` | Update a product |
| DELETE | `/products/{product_id}` | Delete a product |
| GET | `/products/vendor/me` | List own products |

### Categories

| Method | Endpoint | Description |
|---|---|---|
| GET | `/categories` | List categories |
| GET | `/categories/{category_id}` | Get category details |
| POST | `/categories` | Create a category (admin) |
| PATCH | `/categories/{category_id}` | Update a category (admin) |

### Shopping Cart

| Method | Endpoint | Description |
|---|---|---|
| GET | `/carts/me` | Get current cart |
| POST | `/carts/items` | Add an item |
| PATCH | `/carts/items/{product_id}` | Update item quantity |
| DELETE | `/carts/items/{product_id}` | Remove an item |
| DELETE | `/carts/clear` | Clear the cart |

### Orders

| Method | Endpoint | Description |
|---|---|---|
| POST | `/orders` | Create an order |
| GET | `/orders/me` | List customer orders |
| GET | `/orders/{order_id}` | Get customer order details |
| GET | `/vendor-orders/me` | List vendor orders |
| GET | `/vendor-orders/{vendor_order_id}` | Get vendor order details |
| PATCH | `/vendor-orders/{vendor_order_id}/status` | Update vendor order status |

### Health

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Check application health |

**Note:** Endpoint paths in the tables are relative to `/api/v1`, except `/health`.

## Authentication

Protected endpoints require a JWT access token.

After registration or login, copy the returned `access_token` and provide it through the Swagger UI's **Authorize** option using Bearer authentication.

Example:

```text
Authorization: Bearer YOUR_ACCESS_TOKEN
```

Access permissions depend on the authenticated user's role and, for vendors, their approval status.

## Order Processing

A customer can create an order containing products from multiple vendors.

The system creates:
- One parent customer order.
- Separate vendor orders for each participating vendor.
- Order items associated with the corresponding vendor order.

Vendors can access and update only their own vendor orders.

## Running Tests

Run the complete test suite:

```bash
uv run pytest -v
```

The automated tests cover authentication, vendor management, products, shopping carts, and order processing.

Tests use a separate test database named `ecommerce_test_db` and should not use the development database.

Make sure the test database connection and PostgreSQL permissions are configured before running the tests.

## Database Models

The project currently includes these main entities:

- User
- Vendor
- Category
- Product
- Cart
- CartItem
- Order
- VendorOrder
- OrderItem

Database schema changes are managed with Alembic migrations.

## Scope

This project focuses on the core multi-vendor e-commerce workflow.

Payment gateways, wallets, product reviews, advanced search, vendor payouts, and analytics are not currently implemented.

## License

This project is developed for educational and mentoring purposes.