# Requirements and test coverage

The official brief and starter READMEs were read in full, including the bank simulator implementation. This table separates mandatory behavior from implementation decisions.

| Requirement | Implementation | Evidence |
|---|---|---|
| Process payment through gateway | POST /payments, actual bank HTTP call | Both service/API suites; shared test_payment_and_retrieval |
| Authorized and Declined | Map bank authorized boolean | Bank client tests; E2E covers all nonzero final digits |
| Rejected before bank | Strict request validation, 400 | API suites verify no calls; E2E compares simulator request count |
| Card required, numeric, 14–19 chars | String constraints | Shared invalid_requests.json, boundary tests |
| Month required, 1–12 | Integer constraints | Shared cases and valid month boundaries |
| Expiry year and month in future | UTC year/month check | Current/next/past month tests |
| Currency required, 3 chars, up to three codes | USD/GBP/EUR | All allowed codes and invalid cases |
| Amount required, integer minor units | Strict integer; positive signed 64-bit assumption | Decimal/string/bool/zero/negative/overflow/max tests |
| CVV required, numeric, 3–4 chars | String constraints | Shared cases and leading-zero tests |
| Payment ID and status | UUID and exact status strings | Create/GET response comparisons |
| Return only last four digits | String last-four field | Full response assertions, log tests |
| Response contains expiry, currency, amount | Immutable safe payment object | Exact response comparison in shared E2E |
| Retrieve existing payment by ID | GET /payments/{id} | API and E2E tests, missing and invalid ID |
| Storage may be in memory | Per-process store | Service tests and concurrent E2E |
| Document considerations and assumptions | DESIGN.md | Amount/expiry/errors/scale limitations stated explicitly |
| Build and automated tests | uv lock, Gradle wrapper, CI | Unit/API/socket/E2E and container checks |
| Simple and maintainable | Four Python modules; focused Java classes | No retry framework, compatibility layer or unused persistence abstraction |
| Preserve simulator and editor configs | Copied unchanged from pinned upstream | SOURCE_CHECKSUMS.sha256 |
| Do not PR upstream | Standalone personal repository | Own origin only |

## Test layers

Python tests separate request validation, service behavior, the bank adapter, FastAPI routing and real-socket HTTP behavior. Java tests separate Bean Validation, service behavior, JDK HTTP transport and the Spring MVC boundary. API tests replace only the bank dependency; they still run framework parsing and validation. Java’s invalid-input cases run individually through MVC, and bank transport tests use the application’s Jackson configuration.

Shared E2E tests import no application code. They run against both live servers and the original Mountebank configuration. They verify all final card digits, safe create/GET responses, validation before bank calls, malformed JSON and byte encoding, JSON media-type variants, current-month expiry, valid bounds, concurrency and bank 503. Log assertions verify correlation and redaction.

Timeouts, malformed bank responses and connection failures use controlled test-only HTTP servers because the official simulator has no such scenarios. Its configuration is not edited to manufacture them.

Tests are not a claim of production readiness. We do not test a real acquiring bank, card scheme, persistent database, failover or authentication because none is implemented here.

## Engineering review

| Area | Implementation and evidence |
|---|---|
| Observability | Correlated HTTP/bank JSON events, status/outcome and duration; redaction assertions; liveness endpoint. No metrics/tracing service. |
| Packaging/Hosting | Java JAR, non-root Docker images, Compose dependency health checks, localhost bindings; container E2E in CI. [Deployment commands](JAVA.md#deploy-and-verify). |
| Technical Documentation | README diagrams and quickstart; [Java code map](JAVA.md); OpenAPI; design assumptions, source record and verification results. |
| API Design | POST and GET contracts, exact safe response fields, documented validation and technical errors; shared black-box checks. |
| Code Design | Validation at boundaries; controller, service and bank adapter have separate responsibilities; immutable safe records and one memory store. |
| Testing Mindset | Unit, MVC/API, real-socket and live-process/container tests; invalid input must not reach the bank; failures are not treated as declines. |

The official brief requires automated tests but specifies neither a coverage percentage nor a test count. Current-month expiry rejection, positive amounts, strict JSON types and a signed-64-bit amount limit are documented choices, not additional official requirements.
