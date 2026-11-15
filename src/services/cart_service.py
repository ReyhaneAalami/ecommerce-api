from sqlalchemy.orm import Session

from src.data.models import Cart
from src.repositories.cart_repository import CartRepository
from src.repositories.product_repository import ProductRepository
from src.repositories.vendor_repository import VendorRepository


class CartService:

    @staticmethod
    def get_or_create_cart(
        db: Session,
        customer_id: int,
    ) -> Cart:
        try:
            cart = CartRepository.get_by_customer_id(
                db,
                customer_id,
            )

            if cart:
                return cart

            cart = CartRepository.create(
                db,
                customer_id,
            )

            db.commit()

            return CartRepository.get_by_customer_id(
                db,
                customer_id,
            )

        except Exception:
            db.rollback()
            raise

    @staticmethod
    def get_cart(
        db: Session,
        customer_id: int,
    ) -> Cart:
        return CartService.get_or_create_cart(
            db,
            customer_id,
        )

    @staticmethod
    def add_item(
        db: Session,
        customer_id: int,
        product_id: int,
        quantity: int,
    ) -> Cart:
        try:
            if quantity < 1 or quantity > 1000:
                raise ValueError(
                    "Quantity must be between 1 and 1000."
                )

            product = ProductRepository.get_by_id(
                db,
                product_id,
            )

            if not product or not product.is_active:
                raise ValueError("Product not found or inactive.")

            vendor = VendorRepository.get_by_id(
                db,
                product.vendor_id,
            )

            if (
                not vendor
                or not vendor.is_active
                or vendor.status != "approved"
            ):
                raise ValueError("Product vendor is not active.")

            if product.stock_quantity < quantity:
                raise ValueError("Insufficient product stock.")

            cart = CartRepository.get_by_customer_id(
                db,
                customer_id,
            )

            if not cart:
                cart = CartRepository.create(
                    db,
                    customer_id,
                )

            item = CartRepository.get_item(
                db,
                cart.id,
                product_id,
            )

            new_quantity = quantity

            if item:
                new_quantity += item.quantity

                if new_quantity > 1000:
                    raise ValueError(
                        "Maximum quantity per product is 1000."
                    )

                if product.stock_quantity < new_quantity:
                    raise ValueError("Insufficient product stock.")

                item.quantity = new_quantity

            else:
                CartRepository.add_item(
                    db,
                    cart.id,
                    product_id,
                    quantity,
                )

            db.commit()

            return CartRepository.get_by_customer_id(
                db,
                customer_id,
            )

        except Exception:
            db.rollback()
            raise

    @staticmethod
    def update_item(
        db: Session,
        customer_id: int,
        product_id: int,
        quantity: int,
    ) -> Cart:
        try:
            if quantity < 1 or quantity > 1000:
                raise ValueError(
                    "Quantity must be between 1 and 1000."
                )

            cart = CartRepository.get_by_customer_id(
                db,
                customer_id,
            )

            if not cart:
                raise ValueError("Cart not found.")

            item = CartRepository.get_item(
                db,
                cart.id,
                product_id,
            )

            if not item:
                raise ValueError("Product not found in cart.")

            product = ProductRepository.get_by_id(
                db,
                product_id,
            )

            if not product or not product.is_active:
                raise ValueError("Product not found or inactive.")

            if product.stock_quantity < quantity:
                raise ValueError("Insufficient product stock.")

            item.quantity = quantity

            db.commit()

            return CartRepository.get_by_customer_id(
                db,
                customer_id,
            )

        except Exception:
            db.rollback()
            raise

    @staticmethod
    def remove_item(
        db: Session,
        customer_id: int,
        product_id: int,
    ) -> Cart:
        try:
            cart = CartRepository.get_by_customer_id(
                db,
                customer_id,
            )

            if not cart:
                raise ValueError("Cart not found.")

            item = CartRepository.get_item(
                db,
                cart.id,
                product_id,
            )

            if not item:
                raise ValueError("Product not found in cart.")

            CartRepository.delete_item(
                db,
                item,
            )

            db.commit()

            return CartRepository.get_by_customer_id(
                db,
                customer_id,
            )

        except Exception:
            db.rollback()
            raise

    @staticmethod
    def clear_cart(
        db: Session,
        customer_id: int,
    ) -> Cart:
        try:
            cart = CartRepository.get_by_customer_id(
                db,
                customer_id,
            )

            if not cart:
                return CartRepository.create(
                    db,
                    customer_id,
                )

            CartRepository.clear(
                db,
                cart,
            )

            db.commit()

            return CartRepository.get_by_customer_id(
                db,
                customer_id,
            )

        except Exception:
            db.rollback()
            raise