# Upstream sources

Read and retrieved on 2026-10-14:

- [Assessment brief](https://github.com/cko-recruitment/.github/blob/5f1ce249179665b1d8a97202acfc9990fcc4c779/profile/README.md), commit `5f1ce249179665b1d8a97202acfc9990fcc4c779`.
- [Java starter](https://github.com/cko-recruitment/payment-gateway-challenge-java/tree/78be4c696c7d49bb3c242363cccc86a632c93aca), commit `78be4c696c7d49bb3c242363cccc86a632c93aca`.
- [Python starter](https://github.com/cko-recruitment/payment-gateway-challenge-python/tree/9ffcd486c25ce5d51aad182c0e3c5d4b9d89523b), commit `9ffcd486c25ce5d51aad182c0e3c5d4b9d89523b`.

The two `.editorconfig` files and `imposters/bank_simulator.ejs` are copied unchanged. Both upstream simulators were byte-identical. The Java Gradle wrapper comes from the starter; its distribution was updated to 8.14.3. The implementations replace the starter application code while retaining Spring Boot and FastAPI as their respective frameworks.

The simulator remains Mountebank 2.8.1 to match the supplied Compose configuration. Its old transitive npm dependencies have audit findings. It is confined to the development/test environment, the admin endpoint is localhost-only, and no real card data should be used. These dependencies are not part of either gateway's runtime image.

The brief's example expiry 04/2025 is now in the past. Examples here use 12/2099 to stay executable; validation uses the actual current UTC month.

The three upstream HEAD commits were rechecked on 2026-10-15 and still matched these SHAs.
