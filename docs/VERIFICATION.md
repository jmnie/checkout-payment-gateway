# Verification

Checked on 2026-10-15 against the official assessment brief and Java/Python starters.

| Check | Result |
|---|---|
| Java validation, service, MVC and real-socket tests | 81 passed; zero failures, errors or skipped cases |
| Java clean build | `clean test bootJar` passed on JDK 17; all eight Gradle tasks executed |
| Python unit, API and real-socket tests | 157 passed |
| Shared live-process E2E with the original simulator | 166 passed, including the log check |
| Python lint and formatting | Ruff passed |
| Official fixtures | Both editor configs and the bank simulator passed SHA-256 checks; Java wrapper JAR matched upstream |
| Java source and test formatting | Two-space indentation; lines within the supplied 100-character limit |
| Documentation | Local links checked; architecture, POST/GET and deployment diagrams rendered and inspected |

Java line coverage is approximately 93%; Python is 99%. These figures exclude shared E2E coverage and do not prove every possible behavior. The uncovered Python default dependency is exercised by live E2E.

## Reproduce

From the repository root:

```sh
make test
make e2e
shasum -a 256 -c docs/SOURCE_CHECKSUMS.sha256
```

To force a clean Java build, run `cd java && ./gradlew clean test bootJar --no-daemon`.

The [Verify workflow](../.github/workflows/verify.yml) builds both Docker images, waits for healthy containers, runs 165 HTTP cases plus one log check, uploads reports, and stops the stack. Results are available in [GitHub Actions](https://github.com/jmnie/checkout-payment-gateway/actions).

## Scope

The local machine has no Docker installation. Local E2E runs the Java JAR, uvicorn and the original Mountebank process; container behavior is verified in CI.

Tests cover authorization/decline, all required fields, validation before bank calls, safe create/retrieve responses, unknown IDs, currency and date boundaries, concurrency, malformed JSON/media types, bank errors, timeouts and log redaction/correlation. Controlled HTTP servers are used only in tests for failure cases the official simulator cannot produce.

The old simulator dependency tree has npm audit findings; it is retained to match the supplied exercise and is isolated from gateway runtime images. TestClient and JVM instrumentation warnings do not indicate failed assertions.

No real bank, durable database, failover, merchant authentication, idempotency or reconciliation is implemented or claimed as tested.
