from src.payments.base import PaymentRequestResult, PaymentVerifyResult


def test_provider_result_contract_is_provider_neutral():
    request = PaymentRequestResult(authority="A000000000000000000000000000000001", redirect_url="https://gateway.test/pay")
    verify = PaymentVerifyResult(
        success=True, already_verified=False, reference_id="123456", code=100
    )
    assert request.authority.startswith("A")
    assert request.redirect_url.startswith("https://")
    assert verify.success is True
    assert verify.reference_id == "123456"
