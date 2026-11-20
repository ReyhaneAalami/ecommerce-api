from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.data.models import Wallet, WalletTransaction


class WalletRepository:

    @staticmethod
    def get_by_user_id(
        db: Session,
        user_id: int,
    ) -> Wallet | None:
        statement = (
            select(Wallet)
            .where(Wallet.user_id == user_id)
        )
        return db.scalar(statement)

    @staticmethod
    def get_by_user_id_for_update(
        db: Session,
        user_id: int,
    ) -> Wallet | None:
        statement = (
            select(Wallet)
            .where(Wallet.user_id == user_id)
            .with_for_update()
        )
        return db.scalar(statement)

    @staticmethod
    def create(
        db: Session,
        user_id: int,
    ) -> Wallet:
        wallet = Wallet(
            user_id=user_id,
            balance=0,
        )

        db.add(wallet)
        db.flush()

        return wallet

    @staticmethod
    def update_balance(
        db: Session,
        wallet: Wallet,
        new_balance: int,
    ) -> Wallet:
        wallet.balance = new_balance
        db.flush()

        return wallet

    @staticmethod
    def create_transaction(
        db: Session,
        transaction_data: dict,
    ) -> WalletTransaction:
        transaction = WalletTransaction(**transaction_data)

        db.add(transaction)
        db.flush()

        return transaction

    @staticmethod
    def get_transactions(
        db: Session,
        wallet_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> list[WalletTransaction]:
        statement = (
            select(WalletTransaction)
            .where(WalletTransaction.wallet_id == wallet_id)
            .order_by(
                WalletTransaction.created_at.desc(),
                WalletTransaction.id.desc(),
            )
            .offset(skip)
            .limit(limit)
        )

        return list(db.scalars(statement).all())

    @staticmethod
    def count_transactions(
        db: Session,
        wallet_id: int,
    ) -> int:
        statement = (
            select(func.count())
            .select_from(WalletTransaction)
            .where(WalletTransaction.wallet_id == wallet_id)
        )

        return db.scalar(statement) or 0

