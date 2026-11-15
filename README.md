# Multi-Vendor E-Commerce API

A multi-vendor e-commerce REST API built with FastAPI and PostgreSQL.

## Project Overview

This project is being developed as part of a backend development course.

The platform allows customers to register, create vendor stores, and view products from different vendors.

## Implementation Progress

### Phase 1 — Minimum Requirements

- Customer registration and authentication
- Vendor store registration
- Public product listing
- Public product details

### Phase 2 — Additional Features

- Shopping cart management
- Order creation
- Multi-vendor order management

### Additional Implemented Features

- Vendor profile management
- Admin review and approval of vendor applications
- Product creation, updating, and soft deletion
- Category management

## Tech Stack

- Python 3.11+
- FastAPI
- PostgreSQL
- SQLAlchemy
- Alembic
- Pydantic
- JWT Authentication
- Argon2 password hashing
- Pytest

## Project Structure

```text
ecommerce-api/
├── scripts/
│   └── create_admin.py
├── src/
│   ├── api/
│   ├── connections/
│   ├── data/
│   │   ├── migrations/
│   │   └── models/
│   ├── repositories/
│   ├── schemas/
│   ├── services/
│   ├── utils/
│   ├── app.py
│   └── config.py
├── tests/
├── alembic.ini
├── pyproject.toml
├── uv.lock
├── .env.example
├── .gitignore
└── README.md
```

## Requirements

- Python 3.11 or higher
- PostgreSQL
- uv

## Installation

Clone the repository:

```bash
git clone YOUR_REPOSITORY_URL
cd ecommerce-api
```

Install dependencies:

```powershell
uv sync
```

## Environment Configuration

Create a local environment file:

```powershell
Copy-Item .env.example .env
```

Update `.env` with your PostgreSQL connection string and a secure JWT secret.

Never commit `.env` or real credentials.

## Database Setup

Make sure PostgreSQL is running and the database specified in `DATABASE_URL` exists.

Apply migrations:

```powershell
uv run alembic upgrade head
```

## Create Administrator

Run:

```powershell
uv run python -m scripts.create_admin
```

Follow the prompts to create the administrator account.

## Run the Application

```powershell
uv run uvicorn src.app:app --reload
```

API documentation:

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc
- Health Check: http://127.0.0.1:8000/health

## Main API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/auth/register` | Customer registration |
| POST | `/api/v1/auth/login` | User login |
| POST | `/api/v1/vendors/register` | Register a vendor store |
| GET | `/api/v1/products` | Public product listing |
| GET | `/api/v1/products/{product_id}` | Public product details |
| POST | `/api/v1/products` | Create a product (vendor) |

For the complete list of endpoints, run the application and open Swagger UI.

## Authentication

Protected endpoints use Bearer token authentication.

After registration or login, copy the returned `access_token` and use it in Swagger UI's Authorize section.

## Running Tests

```powershell
uv run pytest
```

## Security

- Passwords are hashed using Argon2.
- Authentication uses JWT access tokens.
- Sensitive configuration is loaded from environment variables.
- The actual `.env` file must never be committed.

## License

This project is developed as an educational software project.
