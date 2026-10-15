# Payment gateway

Java 17 / Spring Boot and Python 3.12 / FastAPI implementations of the Checkout.com exercise. Both use the same API contract and official bank simulator. Each has its own in-memory store.

## Architecture

![Payment gateway architecture](docs/diagrams/architecture.png)

Python runs independently on port 8091 with the same request flow. Neither application calls the other. [Java code map, template choices and deployment](docs/JAVA.md).

## Payment flow

![Payment processing flow](docs/diagrams/payment-flow.png)

Every handled response includes `X-Request-Id`; request logging records the status and duration. The architecture diagram shows logging, liveness and API documentation routes. Technical failures do not imply a decline. The application does not retry bank calls: a timeout may happen after the bank has processed the payment.

## Run

With Docker Engine/Desktop and Compose v2:

```sh
docker compose up --build --wait
curl http://localhost:8090/health
```

Java: `8090`. Python: `8091`. Bank: `8080`. Simulator admin: `2525`. Published ports bind to localhost. Stop with `docker compose down`.

Create a payment:

```sh
curl -i http://localhost:8090/payments \
  -H 'Content-Type: application/json' \
  --data @tests/payment.json
```

Use the returned `Location` to retrieve it from the same application. The sample card is authorized. [Other requests](demo/): `declined.json` returns 201 Declined, `rejected.json` returns 400, and `bank-unavailable.json` returns 503.

### Without Docker

Requires JDK 17 and Node.js/npm. Set `JAVA_HOME` if Java 17 is not the default. From the repository root, start the simulator:

```sh
npm ci --ignore-scripts
npm run bank
```

In a second terminal, start Java:

```sh
cd java
./gradlew bootRun
```

For Python, use Python 3.12 and uv 0.11.28 in a separate terminal:

```sh
cd python
uv sync --locked
uv run uvicorn payment_gateway_api.app:app --host 127.0.0.1 --port 8091 --no-access-log
```

`BANK_URL` defaults to `http://localhost:8080`; `BANK_TIMEOUT_SECONDS` to `2`. Java uses `PORT` (default `8090`); Python uses uvicorn's `--port`. Run Python with one worker because storage is process-local.

## API

[OpenAPI](docs/openapi.json) is served at `/openapi.json` by both applications. Python also serves Swagger UI at `/docs`.

| Request or outcome | Response |
|---|---|
| POST, bank authorized or declined | 201, payment details and Location |
| Invalid payment or malformed JSON | 400 Rejected; no bank call |
| Unsupported Content-Type | 415 |
| GET /payments/{id} | 200; unknown ID 404; invalid UUID 400 |
| Bank unavailable / timeout / invalid response | 503 / 504 / 502 |
| GET /health | 200; application liveness only |

Card numbers and CVVs are strings. Amounts are positive integers in minor units. Supported currencies: USD, GBP, EUR. Expiry must be after the current UTC month. Responses contain only the last four card digits, never the full card number or CVV. [Design choices and assumptions](docs/DESIGN.md).

## Tests

Requires JDK 17, Python 3.12, uv and Node.js/npm.

```sh
make test   # Unit, API and socket tests; builds the Java JAR
make e2e    # Includes make test; starts both apps and the official simulator
```

E2E needs ports 8080, 2525, 8090 and 8091 free. It checks HTTP behavior and logs, then stops the processes it started. CI also builds both containers and runs E2E against them.

Verified on 2026-10-15: Java **81**, Python **157**, shared E2E **166** passed. See [test evidence](docs/VERIFICATION.md) and [requirements coverage](docs/REQUIREMENTS.md).

## Limits and logs

Handled HTTP responses carry an `X-Request-Id`. API and bank logs include that ID, outcome/status and duration. Application logs omit request bodies, full card numbers, CVVs and query strings.

Storage is in memory: restarts lose data; instances do not share it. Authentication, idempotency and reconciliation are not implemented. Containers run as non-root. The bank simulator is for testing only; keep its admin port local and use synthetic card data.
