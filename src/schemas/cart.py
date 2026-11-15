from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CartItemCreate(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0, le=1000)


class CartItemUpdate(BaseModel):
    quantity: int = Field(gt=0, le=1000)


class CartProductResponse(BaseModel):
    id: int
    name: str
    slug: str
    sku: str | None
    price: Decimal
    stock_quantity: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class CartItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    product: CartProductResponse
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CartResponse(BaseModel):
    id: int
    customer_id: int
    items: list[CartItemResponse]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)