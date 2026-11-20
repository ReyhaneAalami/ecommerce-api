from datetime import datetime, timedelta, timezone

import pytest

from src.data.models import Payment, Wallet, WalletTransaction
from src.payments.base import PaymentRequestResult, PaymentVerifyResult
from src.services import payment_service
from src.services.payment_service import PaymentService, PaymentConflictError


class FakeProvider:
    name = "zarinpal"
    startpay_base = "https://sandbox.zarinpal.com/pg/StartPay"

    def create_payment(self, **kwargs):
        self.requested_amount = kwargs["amount_rial"]
        return PaymentRequestResult(
            authority="A000000000000000000000000000000001",
            redirect_url=self.startpay_base + "/A000000000000000000000000000000001",
        )

    def verify_payment(self, **kwargs):
        assert kwargs["amount_rial"] == self.requested_amount
        return PaymentVerifyResult(
            success=True, already_verified=False, reference_id="987654321", code=100
        )


def test_wallet_top_up_credits_exactly_once(db, customer, monkeypatch):
    provider = FakeProvider()
    monkeypatch.setattr(payment_service, "get_payment_provider", lambda name=None: provider)

    payment, redirect_url = PaymentService.create_wallet_top_up(
        db, user_id=customer.id, amount_rial=150000, idempotency_key="topup-test-0001"
    )
    assert redirect_url.endswith(payment.authority)

    result = PaymentService.handle_zarinpal_callback(
        db,
        payment_id=payment.id,
        token=payment.callback_token,
        authority=payment.authority,
        status="OK",
    )
    assert result["wallet_credited"] is True

    wallet = db.query(Wallet).filter_by(user_id=customer.id).one()
    assert wallet.balance == 150000
    transactions = db.query(WalletTransaction).filter_by(
        reference_type="payment", reference_id=payment.id
    ).all()
    assert len(transactions) == 1
    assert transactions[0].transaction_type == "top_up"

    repeated = PaymentService.handle_zarinpal_callback(
        db,
        payment_id=payment.id,
        token=payment.callback_token,
        authority=payment.authority,
        status="OK",
    )
    assert repeated["wallet_credited"] is False
    assert wallet.balance == 150000


def test_idempotency_key_cannot_be_reused_for_different_amount(db, customer, monkeypatch):
    provider = FakeProvider()
    monkeypatch.setattr(payment_service, "get_payment_provider", lambda name=None: provider)
    PaymentService.create_wallet_top_up(
        db, user_id=customer.id, amount_rial=150000, idempotency_key="topup-test-0002"
    )
    with pytest.raises(PaymentConflictError):
        PaymentService.create_wallet_top_up(
            db, user_id=customer.id, amount_rial=250000, idempotency_key="topup-test-0002"
        )


def test_invalid_callback_token_does_not_credit_wallet(db, customer, monkeypatch):
    provider = FakeProvider()
    monkeypatch.setattr(payment_service, "get_payment_provider", lambda name=None: provider)
    payment, _ = PaymentService.create_wallet_top_up(
        db, user_id=customer.id, amount_rial=150000, idempotency_key="topup-test-0003"
    )
    with pytest.raises(ValueError, match="Invalid payment callback"):
        PaymentService.handle_zarinpal_callback(
            db, payment_id=payment.id, token="wrong-token-value-that-is-long-enough",
            authority=payment.authority, status="OK"
        )
    wallet = db.query(Wallet).filter_by(user_id=customer.id).one()
    assert wallet.balance == 0
