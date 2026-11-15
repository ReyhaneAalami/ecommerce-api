
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.data.models import Category


class CategoryRepository:

    @staticmethod
    def get_by_id(db: Session, category_id: int) -> Category | None:
        statement = select(Category).where(
            Category.id == category_id
        )
        return db.scalar(statement)

    @staticmethod
    def get_by_slug(db: Session, slug: str) -> Category | None:
        statement = select(Category).where(Category.slug == slug)
        return db.scalar(statement)

    @staticmethod
    def get_all_active(db: Session) -> list[Category]:
        statement = select(Category).where(
            Category.is_active.is_(True)
        )
        return list(db.scalars(statement).all())

    @staticmethod
    def create(db: Session, category_data: dict) -> Category:
        category = Category(**category_data)

        db.add(category)
        db.commit()
        db.refresh(category)

        return category

    @staticmethod
    def update(
        db: Session,
        category: Category,
        update_data: dict,
    ) -> Category:
        for field, value in update_data.items():
            setattr(category, field, value)

        db.commit()
        db.refresh(category)

        return category
