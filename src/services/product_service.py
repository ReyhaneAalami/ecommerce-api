from sqlalchemy.orm import Session

from src.repositories.product_repository import ProductRepository
from src.repositories.vendor_repository import VendorRepository
from src.repositories.category_repository import CategoryRepository
from src.schemas.product import ProductCreate, ProductUpdate


class ProductService:

    @staticmethod
    def get_product(db: Session, product_id: int):
        product = ProductRepository.get_by_id(db, product_id)

        if not product or not product.is_active:
            raise ValueError("Product not found.")

        return product

    @staticmethod
    def get_products(
        db: Session,
        skip: int = 0,
        limit: int = 20,
    ):
        if skip < 0:
            raise ValueError("skip must be greater than or equal to zero.")

        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100.")

        return ProductRepository.get_all(db, skip=skip, limit=limit)

    @staticmethod
    def search_products(
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
    ):
        if skip < 0:
            raise ValueError("skip must be greater than or equal to zero.")

        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100.")

        if min_price is not None and max_price is not None:
            if min_price > max_price:
                raise ValueError("min_price cannot be greater than max_price.")

        products, total = ProductRepository.search(
            db,
            q=q,
            category_id=category_id,
            vendor_id=vendor_id,
            min_price=min_price,
            max_price=max_price,
            in_stock=in_stock,
            sort_by=sort_by,
            skip=skip,
            limit=limit,
        )

        return {
            "items": products,
            "total": total,
            "skip": skip,
            "limit": limit,
        }

    @staticmethod
    def get_vendor_products(
        db: Session,
        vendor_id: int,
        skip: int = 0,
        limit: int = 20,
    ):
        if skip < 0 or limit < 1 or limit > 100:
            raise ValueError("Invalid pagination parameters.")

        vendor = VendorRepository.get_by_id(db, vendor_id)

        if not vendor:
            raise ValueError("Vendor not found.")

        return ProductRepository.get_by_vendor(
            db,
            vendor_id,
            skip=skip,
            limit=limit,
        )

    @staticmethod
    def create_product(
        db: Session,
        vendor_id: int,
        product_data: ProductCreate,
    ):
        vendor = VendorRepository.get_by_id(db, vendor_id)

        if not vendor or not vendor.is_active:
            raise ValueError("Vendor is not active.")

        if vendor.status != "approved":
            raise ValueError("Vendor account has not been approved.")

        category = CategoryRepository.get_by_id(
            db,
            product_data.category_id,
        )

        if not category or not category.is_active:
            raise ValueError("Category is not active.")

        if ProductRepository.get_by_slug(db, product_data.slug):
            raise ValueError("Product slug already exists.")

        if product_data.sku and ProductRepository.get_by_sku(
            db,
            product_data.sku,
        ):
            raise ValueError("Product SKU already exists.")

        return ProductRepository.create(
            db,
            vendor_id,
            product_data.model_dump(),
        )

    @staticmethod
    def update_product(
        db: Session,
        vendor_id: int,
        product_id: int,
        update_data: ProductUpdate,
    ):
        product = ProductRepository.get_by_id_for_vendor(
            db,
            product_id,
            vendor_id,
        )

        if not product:
            raise ValueError("Product not found or does not belong to this vendor.")

        update_dict = update_data.model_dump(exclude_unset=True)

        if (
            "category_id" in update_dict
            and update_dict["category_id"] is not None
        ):
            category = CategoryRepository.get_by_id(
                db,
                update_dict["category_id"],
            )
            if not category or not category.is_active:
                raise ValueError("Category is not active.")

        return ProductRepository.update(db, product, update_dict)

    @staticmethod
    def delete_product(
        db: Session,
        vendor_id: int,
        product_id: int,
    ):
        product = ProductRepository.get_by_id_for_vendor(
            db,
            product_id,
            vendor_id,
        )

        if not product:
            raise ValueError("Product not found or does not belong to this vendor.")

        if not product.is_active:
            raise ValueError("Product is already inactive.")

        # Soft-delete keeps historical order-item references intact.
        product.is_active = False
        db.commit()
        db.refresh(product)
        return product
