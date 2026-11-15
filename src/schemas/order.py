
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field
from typing import Literal


# ورودی هر محصول در سفارش
class OrderItemCreate(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0, le=1000)


# ورودی ثبت سفارش
class OrderCreate(BaseModel):
    items: list[OrderItemCreate] = Field(min_length=1, max_length=100)


# خروجی هر قلم سفارش
class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    sku: str | None
    quantity: int
    unit_price: Decimal
    subtotal: Decimal

    model_config = ConfigDict(from_attributes=True)


# خروجی زیرسفارش فروشنده
class VendorOrderResponse(BaseModel):
    id: int
    vendor_id: int
    vendor_name: str
    status: str
    subtotal: Decimal
    shipping_fee: Decimal
    total_amount: Decimal
    items: list[OrderItemResponse]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# خروجی سفارش اصلی
class OrderResponse(BaseModel):
    id: int
    customer_id: int
    status: str
    total_amount: Decimal
    vendor_orders: list[VendorOrderResponse]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VendorOrderStatusUpdate(BaseModel):
    status: Literal["processing", "shipped", "delivered"]