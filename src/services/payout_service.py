from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.data.models import PayoutRequest, Wallet, WalletTransaction


class PayoutConflictError(ValueError):
    pass


class PayoutService:

    @staticmethod
    def _matches_request(existing: PayoutRequest, data) -> bool:
        return (
            existing.amount_rial == data.amount_rial
            and existing.iban == data.iban
            and existing.account_holder == data.account_holder
        )

    @staticmethod
    def _get_existing_request(
        db: Session,
        vendor_id: int,
        idempotency_key: str,
    ) -> PayoutRequest | None:
        return db.scalar(
            select(PayoutRequest).where(
                PayoutRequest.vendor_id == vendor_id,
                PayoutRequest.idempotency_key == idempotency_key,
            )
        )

    @staticmethod
    def create(
        db: Session,
        *,
        vendor_id: int,
        user_id: int,
        data,
        idempotency_key: str,
    ):
        if not idempotency_key or len(idempotency_key) < 8:
            raise ValueError(
                "A valid Idempotency-Key header is required."
            )

        # Fast path: return an already-created request.
        existing = PayoutService._get_existing_request(
            db, vendor_id, idempotency_key
        )

        if existing is not None:
            if not PayoutService._matches_request(existing, data):
                raise PayoutConflictError(
                    "Idempotency key was reused with different payout details."
                )
            return existing

        # Serialize payout creation for this vendor's wallet.
        wallet = db.scalar(
            select(Wallet)
            .where(Wallet.user_id == user_id)
            .with_for_update()
        )

        if wallet is None:
            raise ValueError("Vendor wallet not found.")

        # Critical second check:
        # Another request with the same key may have completed while this
        # request was waiting for the wallet lock.
        existing = PayoutService._get_existing_request(
            db, vendor_id, idempotency_key
        )

        if existing is not None:
            if not PayoutService._matches_request(existing, data):
                raise PayoutConflictError(
                    "Idempotency key was reused with different payout details."
                )

            # Release the wallet lock/read transaction before returning.
            db.commit()
            db.refresh(existing)
            return existing

        earned = db.scalar(
            select(
                func.coalesce(func.sum(WalletTransaction.amount), 0)
            ).where(
                WalletTransaction.wallet_id == wallet.id,
                WalletTransaction.transaction_type == "vendor_earning",
            )
        ) or 0

        held = db.scalar(
            select(
                func.coalesce(func.sum(WalletTransaction.amount), 0)
            ).where(
                WalletTransaction.wallet_id == wallet.id,
                WalletTransaction.transaction_type == "payout_hold",
            )
        ) or 0

        released = db.scalar(
            select(
                func.coalesce(func.sum(WalletTransaction.amount), 0)
            ).where(
                WalletTransaction.wallet_id == wallet.id,
                WalletTransaction.transaction_type == "payout_reversal",
            )
        ) or 0

        payout_available = int(earned) - int(held) + int(released)

        if data.amount_rial > payout_available:
            raise ValueError(
                "Payout amount exceeds the vendor's available earned balance."
            )

        if wallet.balance < data.amount_rial:
            raise ValueError(
                "Payout amount exceeds the available wallet balance."
            )

        request = PayoutRequest(
            vendor_id=vendor_id,
            user_id=user_id,
            amount_rial=data.amount_rial,
            iban=data.iban,
            account_holder=data.account_holder,
            status="pending",
            idempotency_key=idempotency_key,
        )

        try:
            db.add(request)
            db.flush()

            wallet.balance -= data.amount_rial

            db.add(
                WalletTransaction(
                    wallet_id=wallet.id,
                    transaction_type="payout_hold",
                    amount=data.amount_rial,
                    balance_after=wallet.balance,
                    reference_type="payout_request",
                    reference_id=request.id,
                    description=(
                        f"Funds reserved for payout request #{request.id}"
                    ),
                )
            )

            db.commit()
            db.refresh(request)
            return request

        except IntegrityError as exc:
            db.rollback()

            # A concurrent request may have inserted the same key.
            existing = PayoutService._get_existing_request(
                db, vendor_id, idempotency_key
            )

            if existing is not None:
                if PayoutService._matches_request(existing, data):
                    return existing

                raise PayoutConflictError(
                    "Idempotency key was reused with different payout details."
                ) from exc

            raise PayoutConflictError(
                "Payout request conflicts with an existing database record."
            ) from exc

    @staticmethod
    def list_vendor(
        db: Session,
        vendor_id: int,
        skip: int,
        limit: int,
    ):
        filters = (PayoutRequest.vendor_id == vendor_id,)

        total = db.scalar(
            select(func.count(PayoutRequest.id)).where(*filters)
        ) or 0

        items = list(
            db.scalars(
                select(PayoutRequest)
                .where(*filters)
                .order_by(
                    PayoutRequest.created_at.desc(),
                    PayoutRequest.id.desc(),
                )
                .offset(skip)
                .limit(limit)
            ).all()
        )

        return {
            "items": items,
            "total": total,
            "skip": skip,
            "limit": limit,
        }

    @staticmethod
    def list_admin(
        db: Session,
        status: str | None,
        skip: int,
        limit: int,
    ):
        filters = []

        if status:
            filters.append(PayoutRequest.status == status)

        total = db.scalar(
            select(func.count(PayoutRequest.id)).where(*filters)
        ) or 0

        items = list(
            db.scalars(
                select(PayoutRequest)
                .where(*filters)
                .order_by(
                    PayoutRequest.created_at.asc(),
                    PayoutRequest.id.asc(),
                )
                .offset(skip)
                .limit(limit)
            ).all()
        )

        return {
            "items": items,
            "total": total,
            "skip": skip,
            "limit": limit,
        }

    @staticmethod
    def decide(
        db: Session,
        request_id: int,
        admin_id: int,
        decision: str,
        note: str | None,
        transfer_reference: str | None,
    ):
        request = db.scalar(
            select(PayoutRequest)
            .where(PayoutRequest.id == request_id)
            .with_for_update()
        )

        if request is None:
            raise LookupError("Payout request not found.")

        if request.status == decision:
            return request

        now = datetime.now(timezone.utc)

        if decision == "approved":
            if request.status != "pending":
                raise ValueError(
                    "Only pending payout requests can be approved."
                )

            request.status = "approved"
            request.admin_id = admin_id
            request.admin_note = note
            request.reviewed_at = now

        elif decision == "rejected":
            if request.status not in {"pending", "approved"}:
                raise ValueError(
                    "Only pending or approved unpaid requests can be rejected."
                )

            wallet = db.scalar(
                select(Wallet)
                .where(Wallet.user_id == request.user_id)
                .with_for_update()
            )

            if wallet is None:
                raise ValueError("Vendor wallet not found.")

            already_reversed = db.scalar(
                select(WalletTransaction.id).where(
                    WalletTransaction.transaction_type == "payout_reversal",
                    WalletTransaction.reference_type == "payout_request",
                    WalletTransaction.reference_id == request.id,
                )
            )

            if already_reversed is None:
                wallet.balance += request.amount_rial

                db.add(
                    WalletTransaction(
                        wallet_id=wallet.id,
                        transaction_type="payout_reversal",
                        amount=request.amount_rial,
                        balance_after=wallet.balance,
                        reference_type="payout_request",
                        reference_id=request.id,
                        description=(
                            f"Release reserved funds for rejected payout "
                            f"#{request.id}"
                        ),
                    )
                )

            request.status = "rejected"
            request.admin_id = admin_id
            request.admin_note = note
            request.reviewed_at = now

        elif decision == "paid":
            if request.status != "approved":
                raise ValueError(
                    "Only approved payout requests can be marked paid."
                )

            if (
                not transfer_reference
                or len(transfer_reference.strip()) < 3
            ):
                raise ValueError(
                    "A bank transfer reference is required to mark a payout paid."
                )

            request.status = "paid"
            request.admin_id = admin_id
            request.admin_note = note
            request.transfer_reference = transfer_reference.strip()
            request.paid_at = now

        else:
            raise ValueError("Unsupported payout decision.")

        db.commit()
        db.refresh(request)
        return request
