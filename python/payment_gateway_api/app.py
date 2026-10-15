import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from time import monotonic
from typing import Annotated
from uuid import UUID, uuid4

import httpx
from fastapi import Depends, FastAPI, Request, Response
from fastapi.exception_handlers import http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from payment_gateway_api.bank import BankClient, BankError, logger, request_id
from payment_gateway_api.models import Payment, PaymentRequest
from payment_gateway_api.service import PaymentService


def get_service(request: Request) -> PaymentService:
    return request.app.state.service


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with httpx.AsyncClient(
        base_url=os.environ.get("BANK_URL", "http://localhost:8080"),
        timeout=float(os.environ.get("BANK_TIMEOUT_SECONDS", "2")),
        trust_env=False,
    ) as client:
        app.state.service = PaymentService(BankClient(client))
        yield


app = FastAPI(title="Payment Gateway", version="1.0.0", lifespan=lifespan)
api_contract = json.loads((Path(__file__).resolve().parents[2] / "docs/openapi.json").read_text())
app.openapi = lambda: api_contract
logging.basicConfig(level=logging.INFO, format="%(message)s")


@app.middleware("http")
async def observe(request: Request, call_next):
    correlation_id = str(uuid4())
    token = request_id.set(correlation_id)
    started = monotonic()
    status = 500
    try:
        if (
            request.method == "POST"
            and request.url.path == "/payments"
            and (
                request.headers.get("content-type", "").split(";")[0].strip().lower()
                != "application/json"
            )
        ):
            response = JSONResponse(status_code=415, content={"code": "UnsupportedMediaType"})
        else:
            response = await call_next(request)
        status = response.status_code
        response.headers["X-Request-Id"] = correlation_id
        return response
    finally:
        # Route templates keep arbitrary path/query data out of logs.
        route = request.scope.get("route")
        logger.info(
            json.dumps(
                {
                    "event": "http_request",
                    "request_id": correlation_id,
                    "method": request.method,
                    "route": route.path if route else "unmatched",
                    "status": status,
                    "duration_ms": round((monotonic() - started) * 1000, 2),
                }
            )
        )
        request_id.reset(token)


@app.exception_handler(RequestValidationError)
@app.exception_handler(HTTPException)
async def invalid_request(request: Request, exc: RequestValidationError | HTTPException):
    if isinstance(exc, HTTPException) and exc.status_code != 400:
        return await http_exception_handler(request, exc)
    if request.method == "POST":
        return JSONResponse(
            status_code=400,
            content={
                "status": "Rejected",
                "message": "Invalid payment request",
            },
        )
    return JSONResponse(status_code=400, content={"code": "InvalidRequest"})


@app.exception_handler(BankError)
async def bank_failure(request: Request, exc: BankError):
    return JSONResponse(status_code=exc.status_code, content={"code": exc.code})


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/payments", status_code=201, response_model=Payment)
async def create_payment(
    payment: PaymentRequest,
    response: Response,
    service: Annotated[PaymentService, Depends(get_service)],
):
    result = await service.create(payment)
    response.headers["Location"] = f"/payments/{result.id}"
    return result


@app.get("/payments/{payment_id}", response_model=Payment)
async def get_payment(payment_id: UUID, service: Annotated[PaymentService, Depends(get_service)]):
    payment = service.get(payment_id)
    if payment is None:
        return JSONResponse(status_code=404, content={"code": "PaymentNotFound"})
    return payment
