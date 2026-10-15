import asyncio
from uuid import uuid4

import pytest

from payment_gateway_api.bank import BankError
from payment_gateway_api.models import PaymentRequest


@pytest.mark.parametrize("authorized,status", [(True, "Authorized"), (False, "Declined")])
def test_create_and_retrieve(service, bank, payload, authorized, status):
    bank.authorize.return_value = authorized
    request = PaymentRequest.model_validate(payload)
    payment = asyncio.run(service.create(request))
    assert payment.status == status
    assert payment.card_number_last_four == "0001"
    assert service.get(payment.id) == payment
    assert service.get(uuid4()) is None
    bank.authorize.assert_awaited_once_with(request)
    assert set(payment.model_dump()) == {
        "id",
        "status",
        "card_number_last_four",
        "expiry_month",
        "expiry_year",
        "currency",
        "amount",
    }


def test_failed_bank_call_does_not_store_payment(service, bank, payload):
    bank.authorize.side_effect = BankError(503, "BankUnavailable")
    with pytest.raises(BankError):
        asyncio.run(service.create(PaymentRequest.model_validate(payload)))
    assert service.payments == {}
    bank.authorize.assert_awaited_once()


def test_concurrent_creates_are_retrievable(service, payload):
    async def run():
        return await asyncio.gather(
            *[service.create(PaymentRequest.model_validate(payload)) for _ in range(20)]
        )

    payments = asyncio.run(run())
    assert len({payment.id for payment in payments}) == 20
    assert all(service.get(payment.id) == payment for payment in payments)
