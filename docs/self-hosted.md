# Self-hosted Hiveram

Use this guide when you want to keep the Hiveram ledger in your own
infrastructure instead of relying on an Obsta-managed deployment.

## Custody modes

Hiveram supports three practical deployment modes:

- **Local** — SQLite on one machine for solo evaluation or private work
- **Customer-hosted** — you run the Workledger/Hiveram HTTP API and PostgreSQL
  in your own environment
- **Obsta-managed** — Obsta runs the remote service for you, while your agents
  connect over HTTPS

Hiveram Pro is a product tier, not a custody requirement. Customer-hosted
deployments are a normal supported path.

## Support boundary

Hiveram supports standard PostgreSQL. The public support contract for customer-hosted deployments is here:

- [PostgreSQL support matrix](postgres-support.md)

Use that support matrix to distinguish officially supported, tested,
best-effort, and unsupported environments before you promise compatibility.

## Recommended architecture

The normal team path is:

1. PostgreSQL 15+ in your environment
2. `workledger serve --http` running against that database
3. Agent clients configured with `WORKLEDGER_URL` and `WORKLEDGER_API_KEY` (the bearer token may be `ol_`-prefixed)

Keep raw `WORKLEDGER_DSN` access for setup, migrations, smoke validation, and
admin operations. Most operators should never need a database connection string.

## Minimum setup

### 1. Prepare PostgreSQL

Start with a standard PostgreSQL 15+ deployment that meets the support matrix:

- normal PostgreSQL DSN using `postgres://` or `postgresql://`
- normal TLS mode such as `require`, `verify-ca`, or `verify-full` when the
  database is remote
- network reachability from the machine that will run the Hiveram API

Example DSN shape:

```bash
export WORKLEDGER_DSN='postgresql://user:pass@db.example.com/workledger?sslmode=require'
```

### 2. Run the API service

Start the service with the DSN and an API key file:

```bash
workledger serve --http --addr :8080 --dsn "$WORKLEDGER_DSN" --api-keys ~/.workledger/api-keys.json
```

Generate an API key if you do not already have one:

```bash
workledger keygen --id your-team --role write --projects '*'
```

### 3. Configure operators for the normal remote path

Operators and agent clients should use the HTTPS API path, not the raw DSN:

```bash
export WORKLEDGER_URL='https://workledger.example.com'
# Legacy compatibility: WORKLEDGER_HOST also works for CLI and MCP, but URL is preferred.
export WORKLEDGER_API_KEY='ol_sk_...'
```

Direct DSN access is still valid for admin tasks such as first bootstrap,
deployment checks, and explicit maintenance.

## Health verification

Before onboarding a team, verify both the service path and the PostgreSQL path.

### API health

```bash
curl -fsS https://workledger.example.com/healthz
```

Expected response:

```json
{"status":"ok","db":"reachable","store_kind":"postgres","mode":"live_shared","store_label":"shared-postgres","store_fingerprint":"wl:postgres:..."}
```

The extra store-identity fields are not decoration. They let you prove that CLI,
HTTP, and MCP are all pointed at the same ledger before you trust a missing WO,
an FK failure, or a relationship mismatch.

### End-to-end smoke

Use the deterministic smoke kit from the Workledger source repository:

```bash
# Direct PostgreSQL path: bootstrap + CRUD/search
scripts/pg_smoke.sh --dsn "$WORKLEDGER_DSN"

# Deployed service path: health + CRUD/search through the API
scripts/pg_smoke.sh --api-url "$WORKLEDGER_URL" --api-key "$WORKLEDGER_API_KEY"
```

That script returns explicit `PASS`, `FAIL`, or `UNSUPPORTED` results so you can
separate a broken deployment from an out-of-contract environment.

### Cross-surface identity check

For agent-heavy setups, compare backend identity across every surface you use:

```bash
# CLI
workledger status --json --resolved

# HTTP
curl -fsS "$WORKLEDGER_URL/healthz"
```

If your agent uses MCP, also inspect `workledger_backend_info`. The values that
should agree are:

- `store_fingerprint`
- `store_label`
- `store_kind`
- `mode`

If those fingerprints differ, treat the mismatch as "different stores" before
assuming a handler bug or missing data.

## Backup expectations

Treat PostgreSQL as the ledger of record for customer-hosted Hiveram. At a
minimum:

- enable scheduled backups or managed snapshots
- use point-in-time recovery if your platform supports it
- test a restore path before trusting the deployment with real work
- preserve the API key configuration used by your operators

SQLite is a good local evaluation mode, but it is not the backup strategy for a
shared customer-hosted deployment.

## What this guide does not promise

This guide intentionally does not promise that every PostgreSQL-adjacent proxy,
fork, or cloud quirk is equally supported. If your environment uses unusual
connection pooling, custom TLS, or a PostgreSQL-compatible service with
non-standard behavior, validate it against the support matrix and smoke kit
first.
