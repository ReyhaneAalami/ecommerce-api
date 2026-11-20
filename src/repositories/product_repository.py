from sqlalchemy import func, or_, select
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
            .order_by(Product.created_at.desc(), Product.id.desc())
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
            .order_by(Product.created_at.desc(), Product.id.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(db.scalars(statement).all())

    @staticmethod
    def search(
        db: Session,
        *,
        q: str | None = None,
        category_id: int | None = None,
        vendor_id: int | None = None,
        min_price: int | None = None,
        max_price: int | None = None,
        in_stock: bool | None = None,
        sort_by: str = "newest",
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Product], int]:
        filters = [Product.is_active.is_(True)]

        if category_id is not None:
            filters.append(Product.category_id == category_id)

        if vendor_id is not None:
            filters.append(Product.vendor_id == vendor_id)

        if min_price is not None:
            filters.append(Product.price >= min_price)

        if max_price is not None:
            filters.append(Product.price <= max_price)

        if in_stock is True:
            filters.append(Product.stock_quantity > 0)
        elif in_stock is False:
            filters.append(Product.stock_quantity == 0)

        # Each search word must occur in either the product name or description.
        # PostgreSQL ILIKE supports case-insensitive matching; pg_trgm indexes
        # added by the migration accelerate substring searches.
        if q and q.strip():
            terms = q.strip().split()
            for term in terms:
                pattern = f"%{term}%"
                filters.append(
                    or_(
                        Product.name.ilike(pattern),
                        Product.description.ilike(pattern),
                    )
                )

        total_statement = (
            select(func.count(Product.id))
            .where(*filters)
        )
        total = db.scalar(total_statement) or 0

        statement = select(Product).where(*filters)

        if sort_by == "price_asc":
            statement = statement.order_by(Product.price.asc(), Product.id.asc())
        elif sort_by == "price_desc":
            statement = statement.order_by(Product.price.desc(), Product.id.desc())
        elif sort_by == "name_asc":
            statement = statement.order_by(Product.name.asc(), Product.id.asc())
        else:
            statement = statement.order_by(
                Product.created_at.desc(),
                Product.id.desc(),
            )

        products = list(
            db.scalars(statement.offset(skip).limit(limit)).all()
        )
        return products, total

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
