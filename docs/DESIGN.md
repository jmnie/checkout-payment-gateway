# Design decisions

The request path is small: validate the API input, call the bank, map the decision, store a safe response, return it. GET reads that same response. The bank client owns HTTP serialization and upstream failures. The service owns payment IDs and storage. The HTTP layer owns request validation, status codes and correlation IDs.

## Contract choices

The brief defines business outcomes but leaves HTTP status codes and several edge cases open. These are the choices made here:

- POST returns 201 for both Authorized and Declined because a retrievable payment record was created. Rejected input returns 400 and creates no record.
- The public API uses snake_case and plural `/payments`. The starter Java path and mixed field names are not kept as aliases; this is a new exercise API with no existing clients.
- A response uses `card_number_last_four` as a string. This preserves values such as `0001`. Full card numbers and CVVs only exist while validating and sending the bank request; they are not retained by the payment store.
- Inputs must have their JSON types. Numeric strings, booleans used as numbers, and floats such as `1.0` are rejected. Unknown fields are rejected to surface misspellings.
- Amount is between 1 and 9223372036854775807. The brief only requires an integer in minor units. Positivity and the shared signed-64-bit limit are explicit exercise assumptions.
- Expiry must be strictly after the current UTC year/month. The current month is rejected to follow the wording “in the future.” Real card schemes often treat a card as valid through the end of its expiry month; that would be a different agreed rule. Year is bounded to 1–9999 so the bank representation remains MM/YYYY.
- Card number and CVV digits are ASCII. No Luhn check is added: it is not required by the brief, and the simulator uses synthetic cards.
- Currency must be exactly USD, GBP or EUR. No case normalization or conversion is performed.
- Validation errors use a fixed response rather than echoing rejected values. This keeps card data out of both responses and exception logs.

## Bank errors

The simulator's 503 and connection failures map to 503. Timeouts map to 504. Other non-200 responses, malformed JSON, and a missing/non-boolean `authorized` field map to 502. A string containing `false` must not become an authorization.

There is no automatic retry. A timeout can happen after a bank has processed a payment. Repeating it without an idempotency agreement could create another charge. This exercise cannot resolve that uncertainty: it returns a technical error and stores no successful/declined record. A real system needs a durable pending/unknown state plus reconciliation. This limitation is deliberate and is not an exactly-once guarantee.

Java uses JDK HttpClient and Python uses HTTPX. The configured timeout bounds Java's request and Python's individual network phases; they are not claimed to be identical end-to-end deadlines. Redirects are not followed. Test doubles live only in tests. The runtime bank dependency is the supplied Mountebank simulator.

## Storage and concurrency

Java uses ConcurrentHashMap and immutable payment records. Python uses an in-process dictionary of frozen models; within one asyncio worker, the insert follows the awaited bank call without another await. Each POST receives a new UUID. Concurrent tests verify that each result remains retrievable.

There is no duplicate detection, expiration, durable database or cross-process consistency. The store grows until the process exits. That is acceptable for this bounded exercise and unsuitable for a long-running public service.

## Observability

HTTP and bank calls emit JSON events with correlation ID and elapsed milliseconds. HTTP events use the framework's route template, not the raw path or query string. Clients receive a new generated ID; arbitrary client IDs are not copied into logs. Bank outcomes distinguish Authorized, Declined, BankUnavailable, BankTimeout and BankInvalidResponse.

These events support counts, error rates and latency calculations in a log backend. There is no metrics collector or tracing platform in the repository. `/health` is liveness only; bank failure does not make the process unhealthy. The integration tests check correlation, outcome coverage, and absence of card/CVV fields in logs.

## Keeping the implementation small

Validation belongs at the JSON and bank boundaries. Typed internal code does not repeat it. The store has one implementation, so there is no repository interface/factory hierarchy. The service and bank client are separate because their responsibilities and tests differ.

Java's request toString is redacted; Python excludes card/CVV fields from model repr. Expected network and decoding errors are caught locally. Unexpected programming errors are not converted into plausible bank declines.

Both versions have the same external behavior, with language-appropriate implementation. We do not force Python to copy Java's class structure or add a shared runtime library just to reuse a few mappings.
