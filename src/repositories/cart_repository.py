from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from src.data.models import Cart, CartItem


class CartRepository:

    @staticmethod
    def get_by_customer_id(
        db: Session,
        customer_id: int,
    ) -> Cart | None:
        statement = (
            select(Cart)
            .where(Cart.customer_id == customer_id)
            .options(
                selectinload(Cart.items).selectinload(CartItem.product)
            )
            .execution_options(populate_existing=True)
        )

        return db.scalar(statement)

    @staticmethod
    def get_by_customer_id_for_update(
        db: Session,
        customer_id: int,
    ) -> Cart | None:
        statement = (
            select(Cart)
            .where(Cart.customer_id == customer_id)
            .options(
                selectinload(Cart.items).selectinload(CartItem.product)
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )

        return db.scalar(statement)
    @staticmethod
    def create(
        db: Session,
        customer_id: int,
    ) -> Cart:
        cart = Cart(customer_id=customer_id)

        db.add(cart)
        db.flush()

        return cart

    @staticmethod
    def get_item(
        db: Session,
        cart_id: int,
        product_id: int,
    ) -> CartItem | None:
        statement = select(CartItem).where(
            CartItem.cart_id == cart_id,
            CartItem.product_id == product_id,
        )

        return db.scalar(statement)

    @staticmethod
    def add_item(
        db: Session,
        cart_id: int,
        product_id: int,
        quantity: int,
    ) -> CartItem:
        item = CartItem(
            cart_id=cart_id,
            product_id=product_id,
            quantity=quantity,
        )

        db.add(item)
        db.flush()

        return item

    @staticmethod
    def delete_item(
        db: Session,
        item: CartItem,
    ) -> None:
        db.delete(item)
        db.flush()

    @staticmethod
    def clear(
        db: Session,
        cart: Cart,
    ) -> None:
        cart.items.clear()
        db.flush()