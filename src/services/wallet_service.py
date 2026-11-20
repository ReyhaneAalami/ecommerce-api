from sqlalchemy.orm import Session

from src.repositories.wallet_repository import WalletRepository


class WalletService:

    @staticmethod
    def get_wallet(
        db: Session,
        user_id: int,
    ):
        wallet = WalletRepository.get_by_user_id(
            db,
            user_id,
        )

        if not wallet:
            raise ValueError("Wallet not found.")

        return wallet

    @staticmethod
    def get_transactions(
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> dict:
        if skip < 0:
            raise ValueError("Skip cannot be negative.")

        if limit < 1 or limit > 100:
            raise ValueError("Limit must be between 1 and 100.")

        wallet = WalletService.get_wallet(
            db,
            user_id,
        )

        transactions = WalletRepository.get_transactions(
            db,
            wallet.id,
            skip,
            limit,
        )

        total = WalletRepository.count_transactions(
            db,
            wallet.id,
        )

        return {
            "items": transactions,
            "total": total,
            "skip": skip,
            "limit": limit,
        }
