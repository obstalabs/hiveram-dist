# HTTP OpenAPI contract facts

- Endpoint: authenticated `GET /v1/openapi.yaml`.
- Format: OpenAPI `3.1.0` YAML served from the same bytes committed with the server.
- Path items: `118`.
- Literal server registrations: `148` — `76 GET`, `46 POST`, `12 PUT`, `10 PATCH`, and `4 DELETE`.
- Effective HTTP operations: `224`, including the `76 HEAD` operations supplied by Go HTTP routing for registered `GET` routes.
- Lifecycle-verified operations: `11`; their request and response schemas are exercised against real handlers.
- Route-only-unverified operations: `213`; literal paths and HTTP methods are registration-verified, while request and response bodies are not handler-verified.
- Read-only `POST` operations: `/api/v1/briefings/resolve`, `/api/v1/bundles/export`, `/api/v1/bundles/inspect`, and `/api/v1/projects/{project}/identity-mutation-receipts`.
- Explicit retry identities: notes require `idempotency_key`; creates accept a caller key and otherwise derive a request fingerprint; identity mutations use `operation_id`.
- No caller-provided deduplication key: claim, PATCH update or close, add relationship, link commit, and blob/memory PUT operations.
- Versioning boundary: the contract is versioned with the server release.
