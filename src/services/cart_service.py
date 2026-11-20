from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from src.data.models import Cart, Product, Vendor
from src.repositories.cart_repository import CartRepository


class CartService:

    @staticmethod
    def _get_or_create_locked_cart(db: Session, customer_id: int) -> Cart:
        cart = CartRepository.get_by_customer_id_for_update(db, customer_id)
        if cart is None:
            db.execute(
                pg_insert(Cart)
                .values(customer_id=customer_id)
                .on_conflict_do_nothing(index_elements=["customer_id"])
            )
            cart = CartRepository.get_by_customer_id_for_update(
                db, customer_id
            )
        if cart is None:
            raise RuntimeError("Could not create or lock customer cart.")
        return cart

    @staticmethod
    def get_or_create_cart(db: Session, customer_id: int) -> Cart:
        try:
            cart = CartRepository.get_by_customer_id(db, customer_id)
            if cart is not None:
                return cart
            CartService._get_or_create_locked_cart(db, customer_id)
            db.commit()
            return CartRepository.get_by_customer_id(db, customer_id)
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def get_cart(db: Session, customer_id: int) -> Cart:
        return CartService.get_or_create_cart(db, customer_id)

    @staticmethod
    def _get_valid_locked_product(db: Session, product_id: int) -> Product:
        product = db.scalar(
            select(Product)
            .where(Product.id == product_id)
            .with_for_update()
        )
        if product is None or not product.is_active:
            raise ValueError("Product not found or inactive.")

        vendor = db.scalar(
            select(Vendor).where(Vendor.id == product.vendor_id)
        )
        if not vendor or not vendor.is_active or vendor.status != "approved":
            raise ValueError("Product vendor is not active.")

        return product

    @staticmethod
    def add_item(
        db: Session,
        customer_id: int,
        product_id: int,
        quantity: int,
    ) -> Cart:
        try:
            if quantity < 1 or quantity > 1000:
                raise ValueError("Quantity must be between 1 and 1000.")

            cart = CartService._get_or_create_locked_cart(db, customer_id)
            product = CartService._get_valid_locked_product(db, product_id)
            item = CartRepository.get_item(db, cart.id, product_id)

            new_quantity = quantity + (item.quantity if item else 0)
            if new_quantity > 1000:
                raise ValueError("Maximum quantity per product is 1000.")
            if product.stock_quantity < new_quantity:
                raise ValueError("Insufficient product stock.")

            if item:
                item.quantity = new_quantity
            else:
                CartRepository.add_item(db, cart.id, product_id, quantity)

            db.commit()
            return CartRepository.get_by_customer_id(db, customer_id)
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
                raise ValueError("Quantity must be between 1 and 1000.")

            cart = CartRepository.get_by_customer_id_for_update(
                db, customer_id
            )
            if cart is None:
                raise ValueError("Cart not found.")

            item = CartRepository.get_item(db, cart.id, product_id)
            if item is None:
                raise ValueError("Product not found in cart.")

            product = CartService._get_valid_locked_product(db, product_id)
            if product.stock_quantity < quantity:
                raise ValueError("Insufficient product stock.")

            item.quantity = quantity
            db.commit()
            return CartRepository.get_by_customer_id(db, customer_id)
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def remove_item(db: Session, customer_id: int, product_id: int) -> Cart:
        try:
            cart = CartRepository.get_by_customer_id_for_update(
                db, customer_id
            )
            if cart is None:
                raise ValueError("Cart not found.")

            item = CartRepository.get_item(db, cart.id, product_id)
            if item is None:
                raise ValueError("Product not found in cart.")

            CartRepository.delete_item(db, item)
            db.commit()
            return CartRepository.get_by_customer_id(db, customer_id)
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def clear_cart(db: Session, customer_id: int) -> Cart:
        try:
            cart = CartService._get_or_create_locked_cart(db, customer_id)
            CartRepository.clear(db, cart)
            db.commit()
            return CartRepository.get_by_customer_id(db, customer_id)
        except Exception:
            db.rollback()
            raise
