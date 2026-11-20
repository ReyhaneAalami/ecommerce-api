from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class WalletTopUpCreate(BaseModel):
    amount_rial: int = Field(gt=0, le=500_000_000)


class PaymentResponse(BaseModel):
    id: int
    amount_rial: int
    provider: str
    status: Literal["pending", "succeeded", "failed", "cancelled", "expired"]
    authority: str | None
    reference_id: str | None
    created_at: datetime
    expires_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaymentStartResponse(BaseModel):
    payment: PaymentResponse
    redirect_url: str


class PaymentCallbackResponse(BaseModel):
    payment_id: int
    status: str
    wallet_credited: bool
    reference_id: str | None = None
    message: str
