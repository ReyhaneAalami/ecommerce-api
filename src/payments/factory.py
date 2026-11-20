from src.config import settings
from src.payments.base import PaymentProvider
from src.payments.providers.zarinpal import ZarinpalProvider


def get_payment_provider(provider_name: str | None = None) -> PaymentProvider:
    name = (provider_name or settings.PAYMENT_PROVIDER).strip().lower()
    if name == "zarinpal":
        return ZarinpalProvider()
    # Future integration: add ZibalProvider here without changing PaymentService.
    raise ValueError(f"Unsupported payment provider: {name}")
