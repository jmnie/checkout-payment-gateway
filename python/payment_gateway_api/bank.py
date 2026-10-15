import json
import logging
from contextvars import ContextVar
from time import monotonic

import httpx

from payment_gateway_api.models import PaymentRequest

request_id = ContextVar("request_id", default="")
logger = logging.getLogger("gateway")


class BankError(Exception):
    def __init__(self, status_code: int, code: str):
        super().__init__(code)
        self.status_code = status_code
        self.code = code


class BankClient:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    async def authorize(self, payment: PaymentRequest) -> bool:
        started = monotonic()
        outcome = "error"
        try:
            try:
                response = await self.client.post(
                    "/payments",
                    json={
                        "card_number": payment.card_number,
                        "expiry_date": f"{payment.expiry_month:02}/{payment.expiry_year:04}",
                        "currency": payment.currency,
                        "amount": payment.amount,
                        "cvv": payment.cvv,
                    },
                )
            except httpx.TimeoutException as exc:
                raise BankError(504, "BankTimeout") from exc
            except httpx.RequestError as exc:
                raise BankError(503, "BankUnavailable") from exc
            if response.status_code == 503:
                raise BankError(503, "BankUnavailable")
            if response.status_code != 200:
                raise BankError(502, "BankInvalidResponse")
            try:
                data = response.json()
            except ValueError as exc:
                raise BankError(502, "BankInvalidResponse") from exc
            if not isinstance(data, dict) or type(data.get("authorized")) is not bool:
                raise BankError(502, "BankInvalidResponse")
            outcome = "Authorized" if data["authorized"] else "Declined"
            return data["authorized"]
        except BankError as exc:
            outcome = exc.code
            raise
        finally:
            logger.info(
                json.dumps(
                    {
                        "event": "bank_call",
                        "request_id": request_id.get(),
                        "outcome": outcome,
                        "duration_ms": round((monotonic() - started) * 1000, 2),
                    }
                )
            )
