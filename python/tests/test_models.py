import json
from datetime import UTC, datetime

import pytest
from conftest import ROOT
from pydantic import ValidationError

from payment_gateway_api.models import PaymentRequest

CASES = json.loads((ROOT / "tests/invalid_requests.json").read_text())


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
def test_invalid_fields(case):
    with pytest.raises(ValidationError):
        PaymentRequest.model_validate(case["request"])


@pytest.mark.parametrize(
    "changes",
    [
        {"card_number": "0" * 13 + "1"},
        {"card_number": "1" * 19},
        {"cvv": "0000"},
        {"cvv": "000"},
        {"currency": "USD"},
        {"currency": "EUR"},
        {"amount": 1},
        {"amount": 9223372036854775807},
        {"expiry_month": 1},
    ],
)
def test_valid_boundaries(payload, changes):
    model = PaymentRequest.model_validate(payload | changes)
    assert model.model_dump() == payload | changes


def test_current_month_is_rejected_and_next_month_accepted(payload):
    now = datetime.now(UTC)
    with pytest.raises(ValidationError):
        PaymentRequest.model_validate(
            payload | {"expiry_year": now.year, "expiry_month": now.month}
        )
    next_year, month_index = divmod(now.year * 12 + now.month, 12)
    PaymentRequest.model_validate(
        payload | {"expiry_year": next_year, "expiry_month": month_index + 1}
    )


def test_request_repr_does_not_expose_credentials(payload):
    model = PaymentRequest.model_validate(payload)
    assert payload["card_number"] not in repr(model)
    assert "cvv=" not in repr(model)
