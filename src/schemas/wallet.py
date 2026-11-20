from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WalletResponse(BaseModel):
    id: int
    user_id: int
    balance: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WalletTransactionResponse(BaseModel):
    id: int
    transaction_type: str
    amount: int
    balance_after: int
    reference_type: str | None
    reference_id: int | None
    description: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WalletTransactionListResponse(BaseModel):
    items: list[WalletTransactionResponse]
    total: int = Field(ge=0)
    skip: int = Field(ge=0)
    limit: int = Field(gt=0)
