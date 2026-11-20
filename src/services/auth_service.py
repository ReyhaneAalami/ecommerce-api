from sqlalchemy.orm import Session

from src.repositories.user_repository import UserRepository
from src.repositories.wallet_repository import WalletRepository
from src.schemas.user import UserCreate
from src.utils.security import hash_password, verify_password


class AuthService:

    @staticmethod
    def register(
        db: Session,
        user_data: UserCreate,
    ):
        try:
            existing_user = UserRepository.get_by_email(
                db,
                user_data.email,
            )

            if existing_user:
                raise ValueError(
                    "این ایمیل قبلاً ثبت شده است."
                )

            user_dict = user_data.model_dump(
                exclude={"password"}
            )

            user_dict["password_hash"] = hash_password(
                user_data.password
            )

            user = UserRepository.create(
                db,
                user_dict,
            )

            WalletRepository.create(
                db,
                user.id,
            )

            db.commit()
            db.refresh(user)

            return user

        except Exception:
            db.rollback()
            raise

    @staticmethod
    def authenticate(
        db: Session,
        email: str,
        password: str,
    ):
        user = UserRepository.get_by_email(db, email)

        if not user:
            return None

        if not verify_password(
            password,
            user.password_hash,
        ):
            return None

        if not user.is_active:
            return None

        return user
