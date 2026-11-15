from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class VendorCreate(BaseModel):
    store_name: str = Field(
        min_length=2,
        max_length=150,
    )
    description: str | None = None


class VendorUpdate(BaseModel):
    store_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=150,
    )
    description: str | None = None


class VendorAdminStatusUpdate(BaseModel):
    status: Literal["approved", "rejected"]


class VendorResponse(BaseModel):
    id: int
    user_id: int
    store_name: str
    description: str | None
    status: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )