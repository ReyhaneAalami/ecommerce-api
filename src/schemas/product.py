from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProductBase(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str | None = None
    price: int = Field(gt=0)
    stock_quantity: int = Field(default=0, ge=0)
    category_id: int = Field(gt=0)


class ProductCreate(ProductBase):
    slug: str = Field(min_length=2, max_length=220)
    sku: str | None = Field(default=None, max_length=64)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = None
    price: int | None = Field(default=None, gt=0)
    stock_quantity: int | None = Field(default=None, ge=0)
    category_id: int | None = Field(default=None, gt=0)
    is_active: bool | None = None


class ProductResponse(ProductBase):
    id: int
    vendor_id: int
    slug: str
    sku: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductSearchResponse(BaseModel):
    items: list[ProductResponse]
    total: int = Field(ge=0)
    skip: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
