from sqlalchemy import select
from sqlalchemy.orm import Session

from src.data.models import User


class UserRepository:

    @staticmethod
    def get_by_id(db: Session, user_id: int) -> User | None:
        statement = select(User).where(User.id == user_id)
        return db.scalar(statement)

    @staticmethod
    def get_by_email(db: Session, email: str) -> User | None:
        statement = select(User).where(User.email == email)
        return db.scalar(statement)

    @staticmethod
    def create(db: Session, user_data: dict) -> User:
        user = User(**user_data)

        db.add(user)
        db.flush()

        return user

    @staticmethod
    def update(
        db: Session,
        user: User,
        update_data: dict,
    ) -> User:
        for field, value in update_data.items():
            setattr(user, field, value)

        db.commit()
        db.refresh(user)

        return user

    @staticmethod
    def delete(db: Session, user: User) -> None:
        db.delete(user)
        db.commit()
