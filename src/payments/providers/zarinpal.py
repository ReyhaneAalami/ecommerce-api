import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.config import settings
from src.payments.base import PaymentRequestResult, PaymentVerifyResult


class ZarinpalError(RuntimeError):
    pass


class ZarinpalProvider:
    name = "zarinpal"

    def __init__(self):
        if not settings.ZARINPAL_MERCHANT_ID:
            raise ZarinpalError("ZARINPAL_MERCHANT_ID is not configured.")
        if settings.ZARINPAL_SANDBOX:
            self.api_base = "https://sandbox.zarinpal.com/pg/v4/payment"
            self.startpay_base = "https://sandbox.zarinpal.com/pg/StartPay"
        else:
            self.api_base = "https://api.zarinpal.com/pg/v4/payment"
            self.startpay_base = "https://www.zarinpal.com/pg/StartPay"

    @staticmethod
    def _post(url: str, payload: dict) -> dict:
        body = json.dumps(payload).encode("utf-8")
        request = Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "EcommerceAPI/1.0",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=settings.PAYMENT_HTTP_TIMEOUT_SECONDS) as response:
                raw = response.read()
        except (HTTPError, URLError, TimeoutError) as exc:
            raise ZarinpalError("Could not communicate with Zarinpal.") from exc

        try:
            result = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ZarinpalError("Invalid response from Zarinpal.") from exc
        if not isinstance(result, dict):
            raise ZarinpalError("Invalid response from Zarinpal.")
        return result

    def create_payment(
        self, *, amount_rial: int, callback_url: str, description: str,
        mobile: str | None = None, email: str | None = None,
    ) -> PaymentRequestResult:
        payload = {
            "merchant_id": settings.ZARINPAL_MERCHANT_ID,
            "amount": amount_rial,
            "callback_url": callback_url,
            "description": description[:500],
            "metadata": {},
        }
        if mobile:
            payload["metadata"]["mobile"] = mobile
        if email:
            payload["metadata"]["email"] = email

        result = self._post(f"{self.api_base}/request.json", payload)
        data = result.get("data") or {}
        code = data.get("code")
        authority = data.get("authority")
        if code != 100 or not authority:
            errors = result.get("errors") or {}
            raise ZarinpalError(
                f"Zarinpal request failed (code={code or errors.get('code', 'unknown')})."
            )
        return PaymentRequestResult(
            authority=str(authority),
            redirect_url=f"{self.startpay_base}/{authority}",
        )

    def verify_payment(
        self, *, authority: str, amount_rial: int,
    ) -> PaymentVerifyResult:
        result = self._post(
            f"{self.api_base}/verify.json",
            {
                "merchant_id": settings.ZARINPAL_MERCHANT_ID,
                "amount": amount_rial,
                "authority": authority,
            },
        )
        data = result.get("data") or {}
        code = data.get("code")
        # 100 = newly verified; 101 = this transaction was verified before.
        return PaymentVerifyResult(
            success=code in (100, 101),
            already_verified=(code == 101),
            reference_id=str(data["ref_id"]) if data.get("ref_id") is not None else None,
            code=code if isinstance(code, int) else None,
            message=(result.get("errors") or {}).get("message"),
        )
