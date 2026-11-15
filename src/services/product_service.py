
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
            raise ValueError("محصول موردنظر پیدا نشد.")

        return product

    @staticmethod
    def get_products(
        db: Session,
        skip: int = 0,
        limit: int = 20,
    ):
        if skip < 0:
            raise ValueError("مقدار skip نمی‌تواند منفی باشد.")

        if limit < 1 or limit > 100:
            raise ValueError("limit باید بین 1 تا 100 باشد.")

        return ProductRepository.get_all(
            db,
            skip=skip,
            limit=limit,
        )

    @staticmethod
    def get_vendor_products(
        db: Session,
        vendor_id: int,
        skip: int = 0,
        limit: int = 20,
    ):
        if skip < 0 or limit < 1 or limit > 100:
            raise ValueError("محدوده صفحه‌بندی نامعتبر است.")

        vendor = VendorRepository.get_by_id(db, vendor_id)

        if not vendor:
            raise ValueError("فروشنده موردنظر پیدا نشد.")

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
            raise ValueError("فروشنده معتبر یا فعال نیست.")

        if vendor.status != "approved":
            raise ValueError("حساب فروشنده هنوز تأیید نشده است.")

        category = CategoryRepository.get_by_id(
            db,
            product_data.category_id,
        )

        if not category or not category.is_active:
            raise ValueError("دسته‌بندی معتبر یا فعال نیست.")

        if ProductRepository.get_by_slug(db, product_data.slug):
            raise ValueError("این slug قبلاً استفاده شده است.")

        if product_data.sku and ProductRepository.get_by_sku(
            db,
            product_data.sku,
        ):
            raise ValueError("این SKU قبلاً استفاده شده است.")

        product_dict = product_data.model_dump()

        return ProductRepository.create(
            db,
            vendor_id,
            product_dict,
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
            raise ValueError(
                "محصول پیدا نشد یا متعلق به این فروشنده نیست."
            )

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
                raise ValueError("دسته‌بندی معتبر یا فعال نیست.")

        return ProductRepository.update(
            db,
            product,
            update_dict,
        )

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
            raise ValueError(
                "محصول پیدا نشد یا متعلق به این فروشنده نیست."
            )

        if not product.is_active:
            raise ValueError("این محصول قبلاً غیرفعال شده است.")

        # حذف نرم: حفظ سوابق سفارش‌های قبلی
        product.is_active = False

        db.commit()
        db.refresh(product)

        return product
