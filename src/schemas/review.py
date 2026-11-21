from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class ReviewCreate(BaseModel):
    product_id: int = Field(gt=0)
    order_item_id: int = Field(gt=0)
    rating: int = Field(ge=1, le=5)
    title: str | None = Field(default=None, max_length=120)
    body: str = Field(min_length=10, max_length=3000)


class ReviewModeration(BaseModel):
    status: Literal["approved", "rejected"]
    moderation_note: str | None = Field(default=None, max_length=500)


class ReviewResponse(BaseModel):
    id: int
    product_id: int
    order_item_id: int
    rating: int
    title: str | None
    body: str
    status: str
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ReviewAdminResponse(ReviewResponse):
    customer_id: int
    moderation_note: str | None = None
    moderated_by: int | None = None


class ReviewAdminListResponse(BaseModel):
    items: list[ReviewAdminResponse]
    total: int = Field(ge=0)
    skip: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)


class RatingSummary(BaseModel):
    product_id: int
    average_rating: float
    review_count: int


class ReviewListResponse(BaseModel):
    items: list[ReviewResponse]
    total: int = Field(ge=0)
    skip: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
