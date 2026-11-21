from sqlalchemy import func, select
from sqlalchemy.orm import Session
from src.data.models import (
    User, Vendor, Product, Order, VendorOrder, OrderItem,
    Wallet, WalletTransaction, PayoutRequest, ProductReview,
)


class StatisticsService:
    @staticmethod
    def vendor(db: Session, vendor_id: int, user_id: int):
        product_count, active_count, stock = db.execute(select(
            func.count(Product.id),
            func.count(Product.id).filter(Product.is_active.is_(True)),
            func.coalesce(func.sum(Product.stock_quantity), 0),
        ).where(Product.vendor_id == vendor_id)).one()
        total_orders, pending_orders, delivered_orders, revenue = db.execute(select(
            func.count(VendorOrder.id),
            func.count(VendorOrder.id).filter(VendorOrder.status == "pending"),
            func.count(VendorOrder.id).filter(VendorOrder.status == "delivered"),
            func.coalesce(func.sum(VendorOrder.subtotal).filter(VendorOrder.status == "delivered"), 0),
        ).where(VendorOrder.vendor_id == vendor_id)).one()
        units = db.scalar(select(func.coalesce(func.sum(OrderItem.quantity), 0)).select_from(OrderItem).join(VendorOrder, VendorOrder.id == OrderItem.vendor_order_id)
            .where(VendorOrder.vendor_id == vendor_id, VendorOrder.status == "delivered")) or 0
        wallet_balance = db.scalar(select(Wallet.balance).where(Wallet.user_id == user_id)) or 0
        lifetime = db.scalar(select(func.coalesce(func.sum(WalletTransaction.amount), 0)).join(Wallet, Wallet.id == WalletTransaction.wallet_id)
            .where(Wallet.user_id == user_id, WalletTransaction.transaction_type == "vendor_earning")) or 0
        held = db.scalar(select(func.coalesce(func.sum(WalletTransaction.amount), 0)).join(Wallet, Wallet.id == WalletTransaction.wallet_id)
            .where(Wallet.user_id == user_id, WalletTransaction.transaction_type == "payout_hold")) or 0
        released = db.scalar(select(func.coalesce(func.sum(WalletTransaction.amount), 0)).join(Wallet, Wallet.id == WalletTransaction.wallet_id)
            .where(Wallet.user_id == user_id, WalletTransaction.transaction_type == "payout_reversal")) or 0
        available_for_payout = max(0, int(lifetime) - int(held) + int(released))
        reserved_paid = db.scalar(select(func.coalesce(func.sum(PayoutRequest.amount_rial), 0)).where(
            PayoutRequest.vendor_id == vendor_id, PayoutRequest.status.in_(["pending", "approved", "paid"]))) or 0
        return {
            "vendor_id": vendor_id, "product_count": int(product_count),
            "active_product_count": int(active_count), "inventory_units": int(stock),
            "total_vendor_orders": int(total_orders), "pending_vendor_orders": int(pending_orders),
            "delivered_vendor_orders": int(delivered_orders), "delivered_revenue_rial": int(revenue),
            "units_delivered": int(units), "wallet_balance_rial": int(wallet_balance),
            "available_for_payout_rial": available_for_payout,
            "lifetime_earnings_rial": int(lifetime), "payout_reserved_or_paid_rial": int(reserved_paid),
        }

    @staticmethod
    def admin(db: Session):
        count = lambda model: int(db.scalar(select(func.count()).select_from(model)) or 0)
        customer_count = db.scalar(select(func.count(User.id)).where(User.role == "customer")) or 0
        vendor_count = count(Vendor)
        product_count = count(Product)
        order_count = count(Order)
        paid_orders = db.scalar(select(func.count(Order.id)).where(Order.payment_status == "paid")) or 0
        delivered = db.scalar(select(func.count(VendorOrder.id)).where(VendorOrder.status == "delivered")) or 0
        gross = db.scalar(select(func.coalesce(func.sum(Order.total_amount), 0)).where(
            Order.payment_status == "paid", Order.status != "cancelled")) or 0
        pending_count = db.scalar(select(func.count(PayoutRequest.id)).where(PayoutRequest.status == "pending")) or 0
        pending_amount = db.scalar(select(func.coalesce(func.sum(PayoutRequest.amount_rial), 0)).where(PayoutRequest.status == "pending")) or 0
        pending_reviews = db.scalar(select(func.count(ProductReview.id)).where(ProductReview.status == "pending")) or 0
        return {
            "customer_count": int(customer_count), "vendor_count": vendor_count,
            "product_count": product_count, "order_count": order_count,
            "paid_order_count": int(paid_orders), "delivered_vendor_order_count": int(delivered),
            "gross_paid_order_value_rial": int(gross), "pending_payout_count": int(pending_count),
            "pending_payout_amount_rial": int(pending_amount), "pending_review_count": int(pending_reviews),
        }
