
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.data.models import Product


class ProductRepository:

    @staticmethod
    def get_by_id(db: Session, product_id: int) -> Product | None:
        statement = select(Product).where(Product.id == product_id)
        return db.scalar(statement)

    @staticmethod
    def get_by_id_for_vendor(
        db: Session,
        product_id: int,
        vendor_id: int,
    ) -> Product | None:
        statement = select(Product).where(
            Product.id == product_id,
            Product.vendor_id == vendor_id,
        )
        return db.scalar(statement)

    @staticmethod
    def get_by_slug(db: Session, slug: str) -> Product | None:
        statement = select(Product).where(Product.slug == slug)
        return db.scalar(statement)

    @staticmethod
    def get_by_sku(db: Session, sku: str) -> Product | None:
        statement = select(Product).where(Product.sku == sku)
        return db.scalar(statement)

    @staticmethod
    def get_all(
        db: Session,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Product]:
        statement = (
            select(Product)
            .where(Product.is_active.is_(True))
            .offset(skip)
            .limit(limit)
        )
        return list(db.scalars(statement).all())

    @staticmethod
    def get_by_vendor(
        db: Session,
        vendor_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Product]:
        statement = (
            select(Product)
            .where(Product.vendor_id == vendor_id)
            .offset(skip)
            .limit(limit)
        )
        return list(db.scalars(statement).all())

    @staticmethod
    def create(
        db: Session,
        vendor_id: int,
        product_data: dict,
    ) -> Product:
        product = Product(
            **product_data,
            vendor_id=vendor_id,
        )

        db.add(product)
        db.commit()
        db.refresh(product)

        return product

    @staticmethod
    def update(
        db: Session,
        product: Product,
        update_data: dict,
    ) -> Product:
        for field, value in update_data.items():
            if value is not None or field == "description":
                setattr(product, field, value)

        db.commit()
        db.refresh(product)

        return product

    @staticmethod
    def delete(
        db: Session,
        product: Product,
    ) -> None:
        db.delete(product)
        db.commit()
