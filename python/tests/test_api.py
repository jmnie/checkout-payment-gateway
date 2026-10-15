import json
import logging
from uuid import UUID, uuid4

import pytest
from conftest import ROOT

from payment_gateway_api.bank import BankError

CASES = json.loads((ROOT / "tests/invalid_requests.json").read_text())


def test_serves_shared_api_contract(client):
    assert client.get("/openapi.json").json() == json.loads(
        (ROOT / "docs/openapi.json").read_text()
    )


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["name"])
def test_rejected_request_never_calls_bank(client, bank, case):
    response = client.post("/payments", json=case["request"])
    assert response.status_code == 400
    assert response.json() == {"status": "Rejected", "message": "Invalid payment request"}
    bank.authorize.assert_not_called()


@pytest.mark.parametrize("authorized,status", [(True, "Authorized"), (False, "Declined")])
def test_create_and_get(client, bank, payload, authorized, status):
    bank.authorize.return_value = authorized
    response = client.post("/payments", json=payload)
    assert response.status_code == 201
    result = response.json()
    UUID(result["id"])
    assert result == {
        "id": result["id"],
        "status": status,
        "card_number_last_four": "0001",
        "expiry_month": 12,
        "expiry_year": 2099,
        "currency": "GBP",
        "amount": 100,
    }
    assert client.get(response.headers["location"]).json() == result
    bank.authorize.assert_awaited_once()


@pytest.mark.parametrize(
    "status,code", [(502, "BankInvalidResponse"), (503, "BankUnavailable"), (504, "BankTimeout")]
)
def test_bank_error_has_no_payment_status(client, bank, payload, status, code):
    bank.authorize.side_effect = BankError(status, code)
    response = client.post("/payments", json=payload)
    assert response.status_code == status
    assert response.json() == {"code": code}


def test_unknown_and_invalid_id(client):
    response = client.get(f"/payments/{uuid4()}")
    assert response.status_code == 404
    assert response.json() == {"code": "PaymentNotFound"}
    assert client.get("/payments/not-a-uuid").status_code == 400
    assert client.get("/not-a-route").status_code == 404
    assert client.post("/health").status_code == 405


@pytest.mark.parametrize("body", ["{", "null", "[]", "{} {}"])
def test_invalid_json(client, bank, body):
    assert (
        client.post(
            "/payments", content=body, headers={"Content-Type": "application/json"}
        ).status_code
        == 400
    )
    bank.authorize.assert_not_called()


def test_content_type(client, bank):
    assert client.post("/payments", content="{}").status_code == 415
    bank.authorize.assert_not_called()


def test_request_ids_and_safe_logs(client, payload, caplog):
    caplog.set_level(logging.INFO, logger="gateway")
    first = client.post("/payments", json=payload)
    second = client.post("/payments", json=payload | {"cvv": "secret"})
    assert first.headers["x-request-id"] != second.headers["x-request-id"]
    UUID(first.headers["x-request-id"])
    entries = [json.loads(record.message) for record in caplog.records if record.name == "gateway"]
    assert any(
        row["request_id"] == first.headers["x-request-id"] and row["status"] == 201
        for row in entries
    )
    assert all(row["duration_ms"] >= 0 for row in entries)
    assert payload["card_number"] not in caplog.text
    assert "secret" not in caplog.text
    assert '"cvv"' not in caplog.text
    assert client.get("/health").json() == {"status": "ok"}


@pytest.mark.parametrize("content_type", ["Application/JSON", "application/json; charset=UTF-8"])
def test_accepts_json_media_type_variants(client, payload, content_type):
    response = client.post(
        "/payments", content=json.dumps(payload), headers={"Content-Type": content_type}
    )
    assert response.status_code == 201


def test_invalid_body_encoding_is_rejected_before_bank(client, bank):
    response = client.post(
        "/payments", content=b"\xff", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 400
    assert response.json() == {"status": "Rejected", "message": "Invalid payment request"}
    bank.authorize.assert_not_called()
