from pydantic import BaseModel, Field


class VendorStatisticsResponse(BaseModel):
    vendor_id: int
    product_count: int
    active_product_count: int
    inventory_units: int
    total_vendor_orders: int
    pending_vendor_orders: int
    delivered_vendor_orders: int
    delivered_revenue_rial: int
    units_delivered: int
    wallet_balance_rial: int
    available_for_payout_rial: int
    lifetime_earnings_rial: int
    payout_reserved_or_paid_rial: int


class AdminStatisticsResponse(BaseModel):
    customer_count: int
    vendor_count: int
    product_count: int
    order_count: int
    paid_order_count: int
    delivered_vendor_order_count: int
    gross_paid_order_value_rial: int
    pending_payout_count: int
    pending_payout_amount_rial: int
    pending_review_count: int
