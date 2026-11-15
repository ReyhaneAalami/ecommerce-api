from sqlalchemy.orm import Session

from src.data.models import Category
from src.repositories.category_repository import CategoryRepository


class CategoryService:

    @staticmethod
    def get_categories(db: Session) -> list[Category]:
        return CategoryRepository.get_all_active(db)

    @staticmethod
    def get_category(db: Session, category_id: int) -> Category:
        category = CategoryRepository.get_by_id(db, category_id)

        if category is None or not category.is_active:
            raise ValueError("Category not found.")

        return category

    @staticmethod
    def create_category(db: Session, category_data: dict) -> Category:
        slug = category_data["slug"].strip().lower()
        name = category_data["name"].strip()

        if not name or not slug:
            raise ValueError("Category name and slug are required.")

        if CategoryRepository.get_by_slug(db, slug):
            raise ValueError("This category slug is already registered.")

        category_data["name"] = name
        category_data["slug"] = slug

        return CategoryRepository.create(db, category_data)

    @staticmethod
    def update_category(
        db: Session,
        category_id: int,
        update_data: dict,
    ) -> Category:
        category = CategoryRepository.get_by_id(db, category_id)

        if category is None:
            raise ValueError("Category not found.")

        if "name" in update_data and update_data["name"] is not None:
            update_data["name"] = update_data["name"].strip()

        if "slug" in update_data and update_data["slug"] is not None:
            new_slug = update_data["slug"].strip().lower()
            existing = CategoryRepository.get_by_slug(db, new_slug)

            if existing is not None and existing.id != category_id:
                raise ValueError("This category slug is already registered.")

            update_data["slug"] = new_slug

        if "name" in update_data and update_data["name"] is None:
            update_data.pop("name")

        if "slug" in update_data and update_data["slug"] is None:
            update_data.pop("slug")

        return CategoryRepository.update(db, category, update_data)