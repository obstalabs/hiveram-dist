# Container image facts

- Registry: `ghcr.io/obstalabs/hiveram-dist`.
- Release selectors: immutable semantic-version tags and OCI manifest digests.
- Release artifact: each release publishes one multi-platform OCI index for `linux/amd64` and `linux/arm64`.
- Digest-pinned reference: `ghcr.io/obstalabs/hiveram-dist@sha256:<manifest-digest>`.
- Runtime base: `scratch` with CA certificates and the statically linked `workledger` binary.
- Runtime identity: numeric UID and GID `65532:65532`.
- Entrypoint: `/workledger`.
- Default arguments: `--no-outbox serve --http --addr :8080`.
- HTTP port: `8080`.
- Writable runtime paths: `/var/lib/workledger/.workledger` and `/tmp`.
- Declared image volumes: none.
- Supported customer-hosted production configuration: external PostgreSQL DSN, Hiveram license, and API-key configuration.
- Health endpoint: `/healthz`.
- Readiness endpoint: `/readyz`; an expired license returns HTTP `503`.
- Restricted Pod Security fields: non-root execution, read-only root filesystem, privilege escalation disabled, all Linux capabilities dropped, and `RuntimeDefault` seccomp.
