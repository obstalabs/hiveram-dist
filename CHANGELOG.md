# Changelog

Customer-facing release notes for Hiveram. For the full internal development history, see the workledger repository changelog.

## [0.29.1] - 2026-06-09

### Fixed
- Work orders with `removal-policy: prohibited` now reach rocket-ready even when
  their planning prose contains removal verbs naming functionality objects (flags,
  endpoints, commands). The signal is surfaced as an advisory note rather than a
  hard blocker, so additive work no longer requires prose rewrites or no-op
  workarounds to pass readiness checks.

## [0.26.1] - 2026-06-01

### Added
- `link-commit` links a commit directly to a work order, so closing work no longer depends on commit-message conventions — useful for audit-closing already-shipped work with proper evidence.
- `find-similar` surfaces related work orders before you create a new one, reducing duplicates.
- Two-stage closure: work orders can move through a pending-verification state before done, with the queue and stats accounting for it.

### Fixed
- Direct commit links are preserved end-to-end over the hosted API, including ownership checks and author identity.
- Closure checks no longer mistake internal backend identifiers for commit references.
- Similarity search runs reliably against the hosted API.
- Destructive operations over the API require explicit confirmation.
- Bulk and empty results return consistent, predictable output.

## [0.25.13] - 2026-05-28

### Added
- `search --summary` returns a compact one-line-per-result view with complexity and readiness badges, matching `list --summary`.

### Fixed
- Saving shared memory and context no longer requires anchoring to a work order. Memory writes are audited automatically (who, which machine, when) and sync to the shared store directly. Other canonical writes are unchanged.

## [0.25.12] - 2026-05-28

### Added
- The CLI and MCP server now work fully against the hosted HTTP API backend. Batch updates, similar-WO search, blocked-WO and dependency queries, and the execution-object surface all work over HTTP — no direct database connection required.

### Fixed
- Operator memory and context saves can be authorized with an audited override when no specific work order applies, instead of being blocked.
- Work order updates preserve claim ownership and closure evidence when applied over HTTP or through the agent tools.

## [0.25.11] - 2026-05-27

### Fixed
- Status line no longer shows permanent `wl:!` when an unrelated backend probe fails. Readiness computed from resolved backend only.
- Rate limit raised to 300 requests per minute; admin keys are exempt.

## [0.25.10] - 2026-05-27

### Fixed
- Proxy from config.yaml now applies to all outbound connections including healthcheck and status probes.

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
