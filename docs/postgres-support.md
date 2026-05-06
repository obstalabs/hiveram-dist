# PostgreSQL Support Matrix

Hiveram runs on standard PostgreSQL in your environment or ours. This document defines the support floor, what we officially support, what is best-effort, and how to validate a deployment before promising compatibility.

## Support floor

Hiveram expects:

- PostgreSQL 15 or newer
- A standard PostgreSQL DSN using `postgres://` or `postgresql://`
- Normal TLS modes such as `disable`, `require`, `verify-ca`, or `verify-full`
- Standard PostgreSQL semantics for DDL, `JSONB`, `ON CONFLICT`, arrays, and `timestamptz`
- Reachability from the machine running the API or the administrative CLI path

If an environment does not meet that floor, it is not a supported Hiveram deployment target.

## Officially supported targets

These environments are inside the product contract when they present standard PostgreSQL behavior:

- Customer-managed PostgreSQL 15+ on a VM, container, Kubernetes cluster, or bare metal host
- AWS RDS for PostgreSQL and Aurora PostgreSQL
- GCP Cloud SQL for PostgreSQL
- Azure Database for PostgreSQL
- Neon
- Obsta-managed Hiveram deployments backed by PostgreSQL 15+

Official support means we expect the core product to work without provider-specific code paths when the deployment passes the smoke kit below.

## Tested targets

These are the concrete deployment shapes we use as the compatibility gate before we call a customer rollout ready:

- Direct DSN validation against a standard PostgreSQL 15+ instance
- Deployed Workledger/Hiveram API backed by PostgreSQL 15+
- Provider-family validation for managed PostgreSQL on AWS, GCP, Azure, Neon, or a plain self-hosted deployment by running the smoke kit against the actual customer DSN or API

The key point is deliberate: we do not promise a provider family in the abstract. We require the actual customer deployment to pass `scripts/pg_smoke.sh`.

## Best-effort targets

These environments may work, but they are not part of the default product contract unless they pass customer-specific validation:

- Connection proxies or poolers with non-default behavior, such as PgBouncer in transaction-pooling mode or cloud proxy layers that change session behavior
- PostgreSQL-compatible services or forks that diverge in DDL, locking, or `JSONB` behavior
- Custom TLS stacks, private CA chains, or unusual network topologies that require provider-specific tuning

Best-effort support means we will help investigate, but we do not market these environments as first-class targets without explicit validation evidence.

## Non-goals

These are outside the support contract:

- Non-PostgreSQL databases that only mimic the wire protocol
- Compatibility layers that do not support standard PostgreSQL DDL and JSONB semantics
- Provider-specific automation for every cloud or every managed service variant

## Smoke kit

Use the `scripts/pg_smoke.sh` smoke kit before calling a deployment supported. Obsta-managed evaluations can run this for you; self-hosted teams should run the current smoke kit that ships with their release binary or deployment package.

### Direct DSN mode

Use DSN mode when you want to validate the direct PostgreSQL path, including schema bootstrap and migration behavior:

```bash
scripts/pg_smoke.sh --dsn "$WORKLEDGER_DSN"
```

This mode checks:

- direct store open against PostgreSQL
- create
- get
- list
- search
- update
- cleanup by deleting the smoke WO

### Deployed API mode

Use API mode when you want to validate a remote Hiveram deployment without connecting to the database directly:

```bash
scripts/pg_smoke.sh       --api-url https://workledger.example.com       --api-key "$WORKLEDGER_API_KEY"
```

This mode checks:

- `/healthz`
- create
- get
- list
- search
- update

API mode validates the deployed service path. It also gives you the identity fields that matter for shared authoritative work, such as `store_kind`, `mode`, `store_label`, and `store_fingerprint`. It does not run startup migrations from the client side. That is why DSN mode remains the authoritative migration and bootstrap check.

### Output contract

The smoke kit emits one of three result classes:

- `PASS` - the check succeeded
- `FAIL` - the environment should be treated as broken until fixed
- `UNSUPPORTED` - the input or environment falls outside the support contract

Exit codes:

- `0` - pass
- `1` - fail
- `2` - usage error
- `3` - unsupported environment
