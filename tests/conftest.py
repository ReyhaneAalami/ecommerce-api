
import pytest
from uuid import uuid4

from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from src.app import app
from src.config import settings
from src.connections.database import get_db
from src.data.base import Base
from src.data import models
from src.data.models import (
    User,
    Vendor,
    Category,
    Product,
    Wallet,
)
from src.utils.security import create_access_token


@pytest.fixture(scope="session")
def test_engine():
    database_url = make_url(settings.DATABASE_URL)
    test_database_url = database_url.set(
        database="ecommerce_test_db"
    )

    if test_database_url.database != "ecommerce_test_db":
        raise RuntimeError(
            "Tests can only run against ecommerce_test_db."
        )

    engine = create_engine(
        test_database_url,
        pool_pre_ping=True,
    )

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    yield engine

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db(test_engine):
    connection = test_engine.connect()
    outer_transaction = connection.begin()

    session = Session(
        bind=connection,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )

    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, transaction):
        if (
            transaction.nested
            and transaction._parent is not None
            and not transaction._parent.nested
        ):
            session.expire_all()
            session.begin_nested()

    try:
        yield session
    finally:
        event.remove(
            session,
            "after_transaction_end",
            restart_savepoint,
        )

        session.close()

        if outer_transaction.is_active:
            outer_transaction.rollback()

        connection.close()


@pytest.fixture(autouse=True)
def override_database(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    try:
        yield
    finally:
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def customer(db):
    suffix = uuid4().hex[:10]

    user = User(
        full_name="Test Customer",
        email=f"customer_{suffix}@example.com",
        password_hash="test-password-hash",
        role="customer",
        is_active=True,
    )

    db.add(user)
    db.flush()

    wallet = Wallet(
        user_id=user.id,
        balance=0,
    )

    db.add(wallet)
    db.flush()

    return user


@pytest.fixture
def approved_vendor(db):
    suffix = uuid4().hex[:10]

    vendor_user = User(
        full_name="Test Vendor",
        email=f"vendor_{suffix}@example.com",
        password_hash="test-password-hash",
        role="vendor",
        is_active=True,
    )

    db.add(vendor_user)
    db.flush()

    wallet = Wallet(
        user_id=vendor_user.id,
        balance=0,
    )

    db.add(wallet)
    db.flush()

    vendor = Vendor(
        user_id=vendor_user.id,
        store_name=f"Test Store {suffix}",
        description="Automated test vendor",
        status="approved",
        is_active=True,
    )

    db.add(vendor)
    db.flush()

    return vendor


@pytest.fixture
def category(db):
    suffix = uuid4().hex[:10]

    item = Category(
        name=f"Test Category {suffix}",
        slug=f"test-category-{suffix}",
        description="Automated test category",
        is_active=True,
    )

    db.add(item)
    db.flush()

    return item


@pytest.fixture
def product(db, approved_vendor, category):
    suffix = uuid4().hex[:10]

    item = Product(
        vendor_id=approved_vendor.id,
        category_id=category.id,
        name=f"Test Product {suffix}",
        slug=f"test-product-{suffix}",
        sku=f"SKU-{suffix}",
        description="Automated test product",
        price=1000000,
        stock_quantity=20,
        is_active=True,
    )

    db.add(item)
    db.flush()

    return item


@pytest.fixture
def customer_headers(customer):
    token = create_access_token(customer.id)

    return {
        "Authorization": f"Bearer {token}"
    }


@pytest.fixture
def vendor_headers(approved_vendor):
    token = create_access_token(approved_vendor.user_id)

    return {
        "Authorization": f"Bearer {token}"
    }
