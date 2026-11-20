from sqlalchemy import select
from sqlalchemy.orm import Session

from src.data.models import Payment


class PaymentRepository:
    @staticmethod
    def get_by_id(db: Session, payment_id: int, user_id: int | None = None):
        statement = select(Payment).where(Payment.id == payment_id)
        if user_id is not None:
            statement = statement.where(Payment.user_id == user_id)
        return db.scalar(statement)

    @staticmethod
    def get_by_id_for_update(db: Session, payment_id: int):
        return db.scalar(
            select(Payment).where(Payment.id == payment_id).with_for_update()
        )

    @staticmethod
    def get_by_idempotency(db: Session, user_id: int, key: str):
        return db.scalar(
            select(Payment).where(
                Payment.user_id == user_id,
                Payment.idempotency_key == key,
            )
        )

    @staticmethod
    def get_by_authority(db: Session, authority: str):
        return db.scalar(select(Payment).where(Payment.authority == authority))
