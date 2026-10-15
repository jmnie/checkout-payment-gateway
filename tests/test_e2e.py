"""Black-box contract tests: no application imports or mocked bank decisions."""
import concurrent.futures
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parent
BASE = json.loads((ROOT / "payment.json").read_text())
INVALID = json.loads((ROOT / "invalid_requests.json").read_text())
SPEC = json.loads((ROOT.parent / "docs/openapi.json").read_text())
PAYMENT_SCHEMA = Draft202012Validator(SPEC["components"]["schemas"]["Payment"], format_checker=FormatChecker())
URLS = os.environ.get("GATEWAY_URLS", "http://127.0.0.1:8090,http://127.0.0.1:8091").split(",")
BANK_ADMIN = os.environ.get("BANK_ADMIN_URL", "http://127.0.0.1:2525")
BANK = os.environ.get("BANK_URL", "http://127.0.0.1:8080")


@pytest.fixture(params=URLS)
def api(request):
    with httpx.Client(base_url=request.param, timeout=5, trust_env=False) as client:
        yield client


def bank_count():
    response = httpx.get(f"{BANK_ADMIN}/imposters/8080", trust_env=False)
    response.raise_for_status()
    return response.json()["numberOfRequests"]


@pytest.mark.parametrize("last", list("123456789"))
def test_payment_and_retrieval(api, last):
    payload = BASE | {"card_number": "222240534324000" + last}
    response = api.post("/payments", json=payload)
    assert response.status_code == 201, response.text
    body = response.json()
    PAYMENT_SCHEMA.validate(body)
    UUID(body["id"])
    assert body == {
        "id": body["id"], "status": "Authorized" if int(last) % 2 else "Declined",
        "card_number_last_four": "000" + last,
        "expiry_month": 12, "expiry_year": 2099, "currency": "GBP", "amount": 100,
    }
    assert response.headers["location"] == "/payments/" + body["id"]
    retrieved = api.get(response.headers["location"])
    assert retrieved.status_code == 200
    assert retrieved.json() == body
    UUID(response.headers["x-request-id"])
    assert response.headers["x-request-id"] != retrieved.headers["x-request-id"]


@pytest.mark.parametrize("case", INVALID, ids=lambda row: row["name"])
def test_invalid_input_does_not_reach_bank(api, case):
    before = bank_count()
    response = api.post("/payments", json=case["request"])
    assert response.status_code == 400, response.text
    assert response.json() == {"status": "Rejected", "message": "Invalid payment request"}
    assert bank_count() == before


@pytest.mark.parametrize("changes", [
    {"card_number": "0" * 13 + "1"}, {"card_number": "1" * 19},
    {"cvv": "0000"}, {"currency": "USD"}, {"currency": "EUR"},
    {"amount": 1}, {"amount": 9223372036854775807}, {"expiry_month": 1},
])
def test_valid_boundaries(api, changes):
    response = api.post("/payments", json=BASE | changes)
    assert response.status_code == 201, response.text
    assert response.json()["amount"] == changes.get("amount", BASE["amount"])


def test_month_boundary(api):
    now = datetime.now(timezone.utc)
    before = bank_count()
    response = api.post("/payments", json=BASE | {"expiry_month": now.month, "expiry_year": now.year})
    assert response.status_code == 400
    assert bank_count() == before
    year, month_index = divmod(now.year * 12 + now.month, 12)
    assert api.post("/payments", json=BASE | {"expiry_month": month_index + 1, "expiry_year": year}).status_code == 201


def test_bank_503_is_not_a_decline(api):
    before = bank_count()
    response = api.post("/payments", json=BASE | {"card_number": "2222405343240000"})
    assert response.status_code == 503
    assert response.json() == {"code": "BankUnavailable"}
    assert bank_count() == before + 1
    assert "location" not in response.headers


def test_lookup_and_health(api):
    response = api.get(f"/payments/{uuid4()}")
    assert response.status_code == 404
    assert response.json() == {"code": "PaymentNotFound"}
    assert api.get("/payments/not-a-uuid").status_code == 400
    assert api.get("/health").json() == {"status": "ok"}
    assert api.get("/openapi.json").json() == SPEC


@pytest.mark.parametrize("body", [b"", b"{", b"null", b"[]", b"{} {}", b"\xff"])
def test_bad_json_never_calls_bank(api, body):
    before = bank_count()
    response = api.post("/payments", content=body, headers={"Content-Type": "application/json"})
    assert response.status_code == 400
    assert response.json() == {"status": "Rejected", "message": "Invalid payment request"}
    assert bank_count() == before


@pytest.mark.parametrize("content_type", ["Application/JSON", "application/json; charset=UTF-8"])
def test_json_media_type_variants(api, content_type):
    response = api.post("/payments", content=json.dumps(BASE), headers={"Content-Type": content_type})
    assert response.status_code == 201
    PAYMENT_SCHEMA.validate(response.json())


def test_content_type(api):
    before = bank_count()
    assert api.post("/payments", content="{}").status_code == 415
    assert bank_count() == before


def test_concurrent_requests(api):
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        responses = list(pool.map(lambda _: api.post("/payments", json=BASE), range(12)))
    assert all(response.status_code == 201 for response in responses)
    assert len({response.json()["id"] for response in responses}) == 12
    for response in responses:
        assert api.get(response.headers["location"]).json() == response.json()


def test_simulator_missing_fields():
    response = httpx.post(f"{BANK}/payments", json={}, trust_env=False)
    assert response.status_code == 400


def test_runtime_logs():
    directory = os.environ.get("GATEWAY_LOG_DIR")
    if not directory:
        pytest.skip("Log files supplied by local runner; container logs checked separately in CI")
    for name in ("java", "python"):
        text = (Path(directory) / f"{name}.log").read_text()
        assert BASE["card_number"] not in text
        assert '"cvv"' not in text
        rows = [json.loads(line) for line in text.splitlines() if line.startswith('{"event"')]
        bank_rows = [row for row in rows if row["event"] == "bank_call"]
        http_rows = [row for row in rows if row["event"] == "http_request"]
        assert {"Authorized", "Declined", "BankUnavailable"} <= {row["outcome"] for row in bank_rows}
        request_ids = {row["request_id"] for row in http_rows}
        assert all(row["request_id"] in request_ids for row in bank_rows)
        assert all(row["duration_ms"] >= 0 for row in rows)
