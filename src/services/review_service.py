from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.data.models import Product, ProductReview, Order, OrderItem, VendorOrder


class ReviewService:
    @staticmethod
    def create(db: Session, *, customer_id: int, data):
        product = db.get(Product, data.product_id)
        if product is None:
            raise LookupError("Product not found.")
        item = db.scalar(
            select(OrderItem)
            .join(VendorOrder, VendorOrder.id == OrderItem.vendor_order_id)
            .join(Order, Order.id == VendorOrder.order_id)
            .where(
                OrderItem.id == data.order_item_id,
                OrderItem.product_id == data.product_id,
                Order.customer_id == customer_id,
                VendorOrder.status == "delivered",
                Order.payment_status == "paid",
            )
        )
        if item is None:
            raise ValueError("A review can only be submitted for a product in your delivered order.")
        existing = db.scalar(select(ProductReview).where(
            ProductReview.product_id == data.product_id,
            ProductReview.customer_id == customer_id,
        ))
        if existing:
            raise ValueError("You have already reviewed this product.")
        review = ProductReview(
            product_id=data.product_id,
            customer_id=customer_id,
            order_item_id=item.id,
            rating=data.rating,
            title=data.title,
            body=data.body.strip(),
            status="pending",
        )
        db.add(review)
        db.commit()
        db.refresh(review)
        return review

    @staticmethod
    def list_public(db: Session, product_id: int, skip: int, limit: int):
        if db.get(Product, product_id) is None:
            raise LookupError("Product not found.")
        filters = (ProductReview.product_id == product_id, ProductReview.status == "approved")
        total = db.scalar(select(func.count(ProductReview.id)).where(*filters)) or 0
        items = list(db.scalars(
            select(ProductReview).where(*filters)
            .order_by(ProductReview.created_at.desc(), ProductReview.id.desc())
            .offset(skip).limit(limit)
        ).all())
        return {"items": items, "total": total, "skip": skip, "limit": limit}

    @staticmethod
    def summary(db: Session, product_id: int):
        if db.get(Product, product_id) is None:
            raise LookupError("Product not found.")
        average, count = db.execute(
            select(func.coalesce(func.avg(ProductReview.rating), 0.0), func.count(ProductReview.id))
            .where(ProductReview.product_id == product_id, ProductReview.status == "approved")
        ).one()
        return {"product_id": product_id, "average_rating": round(float(average), 2), "review_count": int(count)}

    @staticmethod
    def list_mine(db: Session, customer_id: int, skip: int, limit: int):
        filters = (ProductReview.customer_id == customer_id,)
        total = db.scalar(select(func.count(ProductReview.id)).where(*filters)) or 0
        items = list(db.scalars(select(ProductReview).where(*filters)
            .order_by(ProductReview.created_at.desc(), ProductReview.id.desc())
            .offset(skip).limit(limit)).all())
        return {"items": items, "total": total, "skip": skip, "limit": limit}

    @staticmethod
    def list_pending(db: Session, skip: int, limit: int):
        filters = (ProductReview.status == "pending",)
        total = db.scalar(select(func.count(ProductReview.id)).where(*filters)) or 0
        items = list(db.scalars(select(ProductReview).where(*filters)
            .order_by(ProductReview.created_at.asc(), ProductReview.id.asc())
            .offset(skip).limit(limit)).all())
        return {"items": items, "total": total, "skip": skip, "limit": limit}

    @staticmethod
    def moderate(db: Session, review_id: int, admin_id: int, status: str, note: str | None):
        review = db.scalar(select(ProductReview).where(ProductReview.id == review_id).with_for_update())
        if review is None:
            raise LookupError("Review not found.")
        if review.status != "pending":
            raise ValueError("Only pending reviews can be moderated.")
        review.status = status
        review.moderation_note = note
        review.moderated_by = admin_id
        db.commit()
        db.refresh(review)
        return review
