import hmac
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.config import settings
from src.data.models import Payment, Wallet, WalletTransaction
from src.payments.factory import get_payment_provider
from src.repositories.payment_repository import PaymentRepository
from src.payments.providers.zarinpal import ZarinpalError


class PaymentConflictError(ValueError):
    pass


class PaymentService:
    @staticmethod
    def create_wallet_top_up(
        db: Session, *, user_id: int, amount_rial: int, idempotency_key: str
    ) -> tuple[Payment, str]:
        if amount_rial < settings.PAYMENT_MIN_AMOUNT_RIAL:
            raise ValueError("Amount is below the minimum top-up amount.")
        if amount_rial > settings.PAYMENT_MAX_AMOUNT_RIAL:
            raise ValueError("Amount exceeds the maximum top-up amount.")
        if not idempotency_key or len(idempotency_key) < 8:
            raise ValueError("A valid Idempotency-Key header is required.")

        existing = PaymentRepository.get_by_idempotency(db, user_id, idempotency_key)
        if existing:
            if existing.amount_rial != amount_rial:
                raise PaymentConflictError(
                    "Idempotency key was already used with a different amount."
                )
            if existing.status == "pending" and existing.authority:
                provider = get_payment_provider(existing.provider)
                return existing, PaymentService._redirect_url(provider, existing.authority)
            if existing.status != "pending":
                raise PaymentConflictError(
                    f"This idempotency key already belongs to a {existing.status} payment."
                )
            raise PaymentConflictError(
                "The previous payment request is still being initialized. Retry shortly."
            )

        payment = Payment(
            user_id=user_id,
            amount_rial=amount_rial,
            provider=settings.PAYMENT_PROVIDER.lower(),
            status="pending",
            idempotency_key=idempotency_key,
            callback_token=secrets.token_urlsafe(32),
            expires_at=datetime.now(timezone.utc)
            + timedelta(minutes=settings.PAYMENT_EXPIRY_MINUTES),
        )
        db.add(payment)
        try:
            db.commit()
        except IntegrityError as exc:
            db.rollback()
            raise PaymentConflictError("Duplicate payment request.") from exc
        db.refresh(payment)

        callback_url = (
            settings.PAYMENT_CALLBACK_BASE_URL.rstrip("/")
            + "?"
            + urlencode({"payment_id": payment.id, "token": payment.callback_token})
        )
        try:
            provider = get_payment_provider(payment.provider)
            result = provider.create_payment(
                amount_rial=payment.amount_rial,
                callback_url=callback_url,
                description=f"Wallet top-up payment #{payment.id}",
            )
            payment.authority = result.authority
            db.commit()
            db.refresh(payment)
            return payment, result.redirect_url
        except Exception as exc:
            db.rollback()
            failed = PaymentRepository.get_by_id_for_update(db, payment.id)
            if failed and failed.status == "pending":
                failed.status = "failed"
                failed.failure_message = "Payment gateway request could not be initialized."
                db.commit()
            raise ValueError("Could not initialize payment with the gateway.") from exc

    @staticmethod
    def _redirect_url(provider, authority: str) -> str:
        # The provider owns its URL format; this path is only used for idempotent retries.
        if hasattr(provider, "startpay_base"):
            return f"{provider.startpay_base}/{authority}"
        raise ValueError("Provider cannot reconstruct its payment URL.")

    @staticmethod
    def handle_zarinpal_callback(
        db: Session, *, payment_id: int, token: str,
        authority: str | None, status: str | None,
    ) -> dict:
        payment = PaymentRepository.get_by_id(db, payment_id)
        if payment is None or not hmac.compare_digest(payment.callback_token, token):
            raise ValueError("Invalid payment callback.")
        if not authority or not payment.authority or not hmac.compare_digest(
            payment.authority, authority
        ):
            raise ValueError("Payment authority does not match.")
        if payment.status == "succeeded":
            return {
                "payment_id": payment.id,
                "status": "succeeded",
                "wallet_credited": False,
                "reference_id": payment.reference_id,
                "message": "Payment was already credited.",
            }
        if payment.status != "pending":
            return {
                "payment_id": payment.id,
                "status": payment.status,
                "wallet_credited": False,
                "reference_id": payment.reference_id,
                "message": "Payment is not pending.",
            }
        # A late "OK" callback must still be verified: the customer may have
        # completed the bank payment just before the local expiry boundary.
        # Never discard a potentially paid transaction based only on our clock.
        if (status or "").upper() != "OK":
            locked = PaymentRepository.get_by_id_for_update(db, payment.id)
            if locked and locked.status == "pending":
                locked.status = (
                    "expired"
                    if payment.expires_at <= datetime.now(timezone.utc)
                    else "cancelled"
                )
                db.commit()
            return {
                "payment_id": payment.id, "status": "cancelled",
                "wallet_credited": False, "message": "Payment was cancelled by the user.",
            }

        provider = get_payment_provider(payment.provider)
        try:
            verification = provider.verify_payment(
                authority=payment.authority,
                amount_rial=payment.amount_rial,
            )
        except Exception as exc:
            raise ValueError("Could not verify payment with the gateway. Retry callback.") from exc

        if not verification.success:
            locked = PaymentRepository.get_by_id_for_update(db, payment.id)
            if locked and locked.status == "pending":
                locked.status = "failed"
                locked.failure_code = str(verification.code) if verification.code is not None else None
                locked.failure_message = "Gateway verification failed."
                db.commit()
            return {
                "payment_id": payment.id, "status": "failed",
                "wallet_credited": False, "message": "Gateway verification failed.",
            }

        # Lock and re-check after the external network call: concurrent callbacks
        # can both verify, but only one may credit the wallet.
        locked = PaymentRepository.get_by_id_for_update(db, payment.id)
        if locked is None:
            raise ValueError("Payment not found.")
        if locked.status == "succeeded":
            return {
                "payment_id": locked.id, "status": "succeeded",
                "wallet_credited": False, "reference_id": locked.reference_id,
                "message": "Payment was already credited.",
            }
        if locked.status != "pending":
            raise PaymentConflictError("Payment is no longer pending.")

        wallet = db.scalar(
            select(Wallet).where(Wallet.user_id == locked.user_id).with_for_update()
        )
        if wallet is None:
            raise ValueError("Wallet not found.")
        new_balance = wallet.balance + locked.amount_rial
        wallet.balance = new_balance
        db.add(
            WalletTransaction(
                wallet_id=wallet.id,
                transaction_type="top_up",
                amount=locked.amount_rial,
                balance_after=new_balance,
                reference_type="payment",
                reference_id=locked.id,
                description=f"Wallet top-up payment #{locked.id}",
            )
        )
        locked.status = "succeeded"
        locked.reference_id = verification.reference_id
        locked.verified_at = datetime.now(timezone.utc)
        db.commit()
        return {
            "payment_id": locked.id,
            "status": "succeeded",
            "wallet_credited": True,
            "reference_id": locked.reference_id,
            "message": "Wallet was credited successfully.",
        }

    @staticmethod
    def get_user_payment(db: Session, payment_id: int, user_id: int):
        payment = PaymentRepository.get_by_id(db, payment_id, user_id)
        if payment is None:
            raise ValueError("Payment not found.")
        return payment
