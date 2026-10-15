import asyncio
import json

import httpx
import pytest

from payment_gateway_api.bank import BankClient, BankError
from payment_gateway_api.models import PaymentRequest


def call_bank(payload, handler):
    async def run():
        async with httpx.AsyncClient(
            base_url="http://bank",
            transport=httpx.MockTransport(handler),
        ) as client:
            return await BankClient(client).authorize(PaymentRequest.model_validate(payload))

    return asyncio.run(run())


@pytest.mark.parametrize("authorized", [True, False])
def test_bank_contract(payload, authorized):
    def handler(request):
        assert request.method == "POST"
        assert request.url.path == "/payments"
        assert json.loads(request.content) == {
            "card_number": payload["card_number"],
            "expiry_date": "12/2099",
            "currency": "GBP",
            "amount": 100,
            "cvv": "012",
        }
        return httpx.Response(200, json={"authorized": authorized})

    assert call_bank(payload, handler) is authorized


@pytest.mark.parametrize(
    "status,body,expected,code",
    [
        (503, "{}", 503, "BankUnavailable"),
        (400, "{}", 502, "BankInvalidResponse"),
        (500, "{}", 502, "BankInvalidResponse"),
        (302, "{}", 502, "BankInvalidResponse"),
        (200, "broken", 502, "BankInvalidResponse"),
        (200, '{"authorized": true} {}', 502, "BankInvalidResponse"),
        (200, "{}", 502, "BankInvalidResponse"),
        (200, "null", 502, "BankInvalidResponse"),
        (200, "[]", 502, "BankInvalidResponse"),
        (200, '{"authorized": "false"}', 502, "BankInvalidResponse"),
        (200, '{"authorized": 1}', 502, "BankInvalidResponse"),
    ],
)
def test_invalid_response(payload, status, body, expected, code):
    with pytest.raises(BankError) as error:
        call_bank(payload, lambda request: httpx.Response(status, text=body))
    assert (error.value.status_code, error.value.code) == (expected, code)


@pytest.mark.parametrize(
    "exception,status,code",
    [
        (httpx.ReadTimeout, 504, "BankTimeout"),
        (httpx.ConnectTimeout, 504, "BankTimeout"),
        (httpx.ConnectError, 503, "BankUnavailable"),
    ],
)
def test_network_failure(payload, exception, status, code):
    def handler(request):
        raise exception("network failed", request=request)

    with pytest.raises(BankError) as error:
        call_bank(payload, handler)
    assert (error.value.status_code, error.value.code) == (status, code)
