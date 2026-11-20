from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PaymentRequestResult:
    authority: str
    redirect_url: str


@dataclass(frozen=True)
class PaymentVerifyResult:
    success: bool
    already_verified: bool
    reference_id: str | None
    code: int | None
    message: str | None = None


class PaymentProvider(Protocol):
    name: str

    def create_payment(
        self, *, amount_rial: int, callback_url: str, description: str,
        mobile: str | None = None, email: str | None = None,
    ) -> PaymentRequestResult: ...

    def verify_payment(
        self, *, authority: str, amount_rial: int,
    ) -> PaymentVerifyResult: ...
