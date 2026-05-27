# Changelog

Customer-facing release notes for Hiveram. For the full internal development history, see the workledger repository changelog.

## [0.25.9] - 2026-05-27

### Fixed
- Config file now reads API keys from `export VAR=value` format, not just bare keys. Existing `api-key.env` files work without changes.

## [0.25.8] - 2026-05-27

### Added
- **Config file support.** `~/.workledger/config.yaml` is now the single place to configure your backend, API key, and proxy. No more setting environment variables in every terminal session.
- **SOCKS5 and HTTP proxy.** Set `connection.proxy` in config.yaml to route all API traffic through a proxy. Instant fix for VPN environments where direct connections are unreliable.
- **Capture promotion.** `workledger artifact capture-promote` stores sanitized smoke-test captures as durable evidence with provenance links to work orders.

### Fixed
- Private key blocks are now redacted from capture evidence before storage.
- Closure proof enforcement requires branch evidence before marking work complete.

### Proxy quick start

```yaml
# ~/.workledger/config.yaml
connection:
  backend: http
  url: https://workledger.fly.dev
  api_key_file: ~/.workledger/api-key.env
  proxy: socks5://127.0.0.1:1080
```

See [docs/postgres-support.md](docs/postgres-support.md) for the full proxy guide.

## [0.25.7] - 2026-05-22

### Fixed
- Offline outbox recovery handles retryable failures, preserves receipt evidence, and counts failed bundle entries correctly.
- Project identity preservation prevents stale local mirrors from blanking shared repo guardrails.
- Completed-work safety checks tie closure evidence to the write that records completion.

## [0.25.6] - 2026-05-19

### Fixed
- Default convergence corpus bound lowered for responsive shared-backend queries.

## [0.25.5] - 2026-05-19

### Fixed
- HTTP-backed CLI respects server `Retry-After` for rate limiting.
