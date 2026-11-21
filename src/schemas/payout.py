import re
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class PayoutCreate(BaseModel):
    amount_rial: int = Field(gt=0, le=500_000_000)
    iban: str = Field(min_length=26, max_length=26)
    account_holder: str = Field(min_length=3, max_length=150)

    @field_validator("iban")
    @classmethod
    def validate_iban(cls, value: str) -> str:
        normalized = value.replace(" ", "").upper()
        if not re.fullmatch(r"IR[0-9]{24}", normalized):
            raise ValueError("IBAN must be an Iranian IBAN in IR plus 24 digits format.")
        return normalized


class PayoutDecision(BaseModel):
    decision: Literal["approved", "rejected", "paid"]
    admin_note: str | None = Field(default=None, max_length=500)
    transfer_reference: str | None = Field(default=None, min_length=3, max_length=150)


class PayoutResponse(BaseModel):
    id: int
    vendor_id: int
    user_id: int
    amount_rial: int
    iban: str
    account_holder: str
    status: str
    idempotency_key: str
    admin_id: int | None
    admin_note: str | None
    transfer_reference: str | None
    requested_at: datetime
    reviewed_at: datetime | None
    paid_at: datetime | None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PayoutListResponse(BaseModel):
    items: list[PayoutResponse]
    total: int = Field(ge=0)
    skip: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
