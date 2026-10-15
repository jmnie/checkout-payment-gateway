import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from payment_gateway_api.app import app, get_service
from payment_gateway_api.bank import BankClient
from payment_gateway_api.service import PaymentService

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def payload():
    return json.loads((ROOT / "tests/payment.json").read_text())


@pytest.fixture
def bank():
    result = AsyncMock(spec=BankClient)
    result.authorize.return_value = True
    return result


@pytest.fixture
def service(bank):
    return PaymentService(bank)


@pytest.fixture
def client(service):
    app.dependency_overrides[get_service] = lambda: service
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
