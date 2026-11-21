from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from sqlalchemy import event, func, select
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from src.app import app
from src.data.models import (
    User,
    Vendor,
    Wallet,
    WalletTransaction,
    PayoutRequest,
)
from src.schemas.payout import PayoutCreate
from src.services.payout_service import PayoutService
from src.utils.security import create_access_token

client = TestClient(app)
IBAN = "IR" + "123456789012345678901234"


def _admin_headers(db):
    suffix = uuid4().hex[:10]
    admin = User(full_name="Payout Admin", email=f"payout_admin_{suffix}@example.com", password_hash="x", role="admin", is_active=True)
    db.add(admin)
    db.flush()
    return {"Authorization": f"Bearer {create_access_token(admin.id)}"}


def _fund_vendor_wallet(db, vendor, amount=500000):
    wallet = db.query(Wallet).filter(Wallet.user_id == vendor.user_id).one()
    wallet.balance = amount
    db.add(WalletTransaction(
        wallet_id=wallet.id, transaction_type="vendor_earning", amount=amount,
        balance_after=amount, reference_type="vendor_order",
        reference_id=abs(hash(uuid4().hex)) % 2_000_000_000,
        description="Test vendor earnings",
    ))
    db.flush()
    return wallet


def test_vendor_can_request_payout_and_funds_are_reserved(db, approved_vendor, vendor_headers):
    wallet = _fund_vendor_wallet(db, approved_vendor)
    response = client.post("/api/v1/payouts/me", headers={**vendor_headers, "Idempotency-Key": "payout-test-0001"}, json={
        "amount_rial": 200000, "iban": IBAN, "account_holder": "Test Vendor"
    })
    assert response.status_code == 201, response.text
    assert response.json()["status"] == "pending"
    assert wallet.balance == 300000
    hold = db.query(WalletTransaction).filter(WalletTransaction.transaction_type == "payout_hold").one()
    assert hold.amount == 200000


def test_vendor_cannot_request_more_than_wallet_balance(db, approved_vendor, vendor_headers):
    _fund_vendor_wallet(db, approved_vendor, 100000)
    response = client.post("/api/v1/payouts/me", headers={**vendor_headers, "Idempotency-Key": "payout-test-0002"}, json={
        "amount_rial": 200000, "iban": IBAN, "account_holder": "Test Vendor"
    })
    assert response.status_code == 400


def test_rejected_payout_releases_reserved_funds(db, approved_vendor, vendor_headers):
    wallet = _fund_vendor_wallet(db, approved_vendor)
    created = client.post("/api/v1/payouts/me", headers={**vendor_headers, "Idempotency-Key": "payout-test-0003"}, json={
        "amount_rial": 150000, "iban": IBAN, "account_holder": "Test Vendor"
    })
    request_id = created.json()["id"]
    admin_headers = _admin_headers(db)
    rejected = client.patch(f"/api/v1/payouts/admin/{request_id}/decision", headers=admin_headers, json={"decision": "rejected", "admin_note": "Bank details review failed"})
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["status"] == "rejected"
    assert wallet.balance == 500000
    assert db.query(WalletTransaction).filter(WalletTransaction.transaction_type == "payout_reversal").count() == 1


def test_approved_payout_can_be_marked_paid(db, approved_vendor, vendor_headers):
    _fund_vendor_wallet(db, approved_vendor)
    created = client.post("/api/v1/payouts/me", headers={**vendor_headers, "Idempotency-Key": "payout-test-0004"}, json={
        "amount_rial": 100000, "iban": IBAN, "account_holder": "Test Vendor"
    })
    request_id = created.json()["id"]
    admin_headers = _admin_headers(db)
    approved = client.patch(f"/api/v1/payouts/admin/{request_id}/decision", headers=admin_headers, json={"decision": "approved"})
    assert approved.status_code == 200, approved.text
    paid = client.patch(f"/api/v1/payouts/admin/{request_id}/decision", headers=admin_headers, json={"decision": "paid", "transfer_reference": "BANK-TRANSFER-123"})
    assert paid.status_code == 200, paid.text
    assert paid.json()["status"] == "paid"
    assert paid.json()["transfer_reference"] == "BANK-TRANSFER-123"


def test_payout_idempotency_rejects_different_amount(db, approved_vendor, vendor_headers):
    _fund_vendor_wallet(db, approved_vendor)
    headers = {**vendor_headers, "Idempotency-Key": "payout-test-0005"}
    first = client.post("/api/v1/payouts/me", headers=headers, json={"amount_rial": 100000, "iban": IBAN, "account_holder": "Test Vendor"})
    assert first.status_code == 201
    second = client.post("/api/v1/payouts/me", headers=headers, json={"amount_rial": 120000, "iban": IBAN, "account_holder": "Test Vendor"})
    assert second.status_code == 409


def test_vendor_cannot_withdraw_wallet_topups_as_earnings(db, approved_vendor, vendor_headers):
    wallet = db.query(Wallet).filter(Wallet.user_id == approved_vendor.user_id).one()
    wallet.balance = 500000
    db.add(WalletTransaction(
        wallet_id=wallet.id, transaction_type="top_up", amount=500000,
        balance_after=500000, reference_type="payment", reference_id=987654321,
        description="Wallet top-up, not vendor earnings",
    ))
    db.flush()
    response = client.post("/api/v1/payouts/me", headers={**vendor_headers, "Idempotency-Key": "payout-test-0006"}, json={
        "amount_rial": 100000, "iban": IBAN, "account_holder": "Test Vendor"
    })
    assert response.status_code == 400


def test_admin_can_list_pending_payouts(db, approved_vendor, vendor_headers):
    _fund_vendor_wallet(db, approved_vendor)
    created = client.post("/api/v1/payouts/me", headers={**vendor_headers, "Idempotency-Key": "payout-test-0007"}, json={
        "amount_rial": 100000, "iban": IBAN, "account_holder": "Test Vendor"
    })
    assert created.status_code == 201
    admin_headers = _admin_headers(db)
    response = client.get("/api/v1/payouts/admin?status=pending", headers=admin_headers)
    assert response.status_code == 200, response.text
    assert response.json()["total"] >= 1
    assert any(item["id"] == created.json()["id"] for item in response.json()["items"])

def test_payout_idempotency_same_payload_returns_existing_request(
    db, approved_vendor, vendor_headers
):
    wallet = _fund_vendor_wallet(db, approved_vendor)
    headers = {
        **vendor_headers,
        "Idempotency-Key": "payout-same-payload-001",
    }
    payload = {
        "amount_rial": 100000,
        "iban": IBAN,
        "account_holder": "Test Vendor",
    }

    first = client.post(
        "/api/v1/payouts/me",
        headers=headers,
        json=payload,
    )
    assert first.status_code == 201, first.text

    second = client.post(
        "/api/v1/payouts/me",
        headers=headers,
        json=payload,
    )
    assert second.status_code == 201, second.text

    assert second.json()["id"] == first.json()["id"]
    assert wallet.balance == 400000

    holds = (
        db.query(WalletTransaction)
        .filter(
            WalletTransaction.transaction_type == "payout_hold",
            WalletTransaction.reference_type == "payout_request",
            WalletTransaction.reference_id == first.json()["id"],
        )
        .count()
    )
    assert holds == 1


def test_concurrent_same_payout_idempotency_key_creates_one_request(
    test_engine,
):
    suffix = uuid4().hex
    idempotency_key = f"payout-concurrent-{suffix}"

    # Create committed records visible to both independent connections.
    with Session(test_engine) as seed:
        user = User(
            full_name="Concurrent Payout Vendor",
            email=f"concurrent_payout_{suffix}@example.com",
            password_hash="test-password-hash",
            role="vendor",
            is_active=True,
        )
        seed.add(user)
        seed.flush()

        vendor = Vendor(
            user_id=user.id,
            store_name=f"Concurrent Payout Store {suffix}",
            status="approved",
            is_active=True,
        )

        wallet = Wallet(
            user_id=user.id,
            balance=500000,
        )

        seed.add_all([vendor, wallet])
        seed.flush()

        seed.add(
            WalletTransaction(
                wallet_id=wallet.id,
                transaction_type="vendor_earning",
                amount=500000,
                balance_after=500000,
                reference_type="vendor_order",
                reference_id=abs(hash(suffix)) % 2_000_000_000,
                description="Concurrent payout test earnings",
            )
        )

        seed.commit()

        vendor_id = vendor.id
        user_id = user.id
        wallet_id = wallet.id

    payload = PayoutCreate(
        amount_rial=100000,
        iban=IBAN,
        account_holder="Concurrent Vendor",
    )

    # Force both threads to finish their initial idempotency lookup
    # before either thread continues to acquire the wallet lock.
    initial_lookup_barrier = Barrier(2)

    def synchronize_initial_lookup(
        connection,
        cursor,
        statement,
        parameters,
        context,
        executemany,
    ):
        normalized_statement = statement.lower()

        is_idempotency_lookup = (
            "payout_requests" in normalized_statement
            and "idempotency_key" in normalized_statement
        )

        if (
            is_idempotency_lookup
            and not connection.info.get(
                "payout_initial_lookup_synchronized"
            )
        ):
            connection.info[
                "payout_initial_lookup_synchronized"
            ] = True

            initial_lookup_barrier.wait(timeout=20)

    def submit_payout():
        # Each thread owns its own independent SQLAlchemy Session.
        with Session(test_engine) as session:
            request = PayoutService.create(
                session,
                vendor_id=vendor_id,
                user_id=user_id,
                data=payload,
                idempotency_key=idempotency_key,
            )
            return request.id

    event.listen(
        test_engine,
        "after_cursor_execute",
        synchronize_initial_lookup,
    )

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            first_future = executor.submit(submit_payout)
            second_future = executor.submit(submit_payout)

            first_id = first_future.result(timeout=30)
            second_id = second_future.result(timeout=30)

    finally:
        event.remove(
            test_engine,
            "after_cursor_execute",
            synchronize_initial_lookup,
        )

    # Both concurrent requests must return the same payout request.
    assert first_id == second_id

    # Verify the persisted database state using a fresh session.
    with Session(test_engine) as verification:
        request_count = verification.scalar(
            select(func.count())
            .select_from(PayoutRequest)
            .where(
                PayoutRequest.vendor_id == vendor_id,
                PayoutRequest.idempotency_key == idempotency_key,
            )
        )

        hold_count = verification.scalar(
            select(func.count())
            .select_from(WalletTransaction)
            .where(
                WalletTransaction.wallet_id == wallet_id,
                WalletTransaction.transaction_type == "payout_hold",
                WalletTransaction.reference_type == "payout_request",
                WalletTransaction.reference_id == first_id,
            )
        )

        updated_wallet = verification.get(Wallet, wallet_id)

        assert request_count == 1
        assert hold_count == 1
        assert updated_wallet.balance == 400000
