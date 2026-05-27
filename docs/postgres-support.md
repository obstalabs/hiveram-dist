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

## Network proxies (SOCKS5, HTTP)

When a VPN or firewall makes direct PostgreSQL connections unreliable, route traffic through the HTTP API behind a SOCKS5 or HTTP proxy instead. The Workledger CLI and HTTPStore respect the standard Go proxy environment variables.

### HTTP API through a proxy (recommended)

Set `ALL_PROXY` to route all HTTP API traffic through a local SOCKS5 proxy:

```bash
export WORKLEDGER_URL=https://workledger.example.com
export WORKLEDGER_API_KEY=wlk_...
export ALL_PROXY=socks5://127.0.0.1:1080
workledger list myproject
```

This works because Hiveram's HTTPStore uses Go's default HTTP transport, which honors `ALL_PROXY`, `HTTPS_PROXY`, and `HTTP_PROXY` automatically. No code changes or special configuration required.

Supported proxy schemes:

- `socks5://host:port` — SOCKS5 proxy (most VPN setups)
- `http://host:port` — HTTP CONNECT proxy
- `https://host:port` — HTTPS CONNECT proxy

### Direct DSN through a proxy

PostgreSQL DSN connections (`WORKLEDGER_DSN`) do not honor HTTP proxy environment variables because they use TCP directly, not HTTP. If your VPN blocks direct Postgres but allows SOCKS, two options:

1. **Switch to HTTP API mode.** Set `WORKLEDGER_URL` instead of `WORKLEDGER_DSN` and use the proxy as shown above. This is the recommended path.

2. **Local TCP tunnel.** Forward a local port through the SOCKS proxy to the Postgres host:

   ```bash
   # Forward local:15432 → neon-host:5432 through SOCKS5
   ssh -D 1080 -N jumpbox &
   socat TCP-LISTEN:15432,fork SOCKS4A:127.0.0.1:neon-host:5432,socksport=1080 &
   # Then point WORKLEDGER_DSN at localhost:15432 instead of the remote host
   ```

   This is a workaround, not a product feature. Prefer the HTTP API path.

### When to use a proxy

- VPN setup routes general traffic through SOCKS but blocks direct Postgres ports
- Corporate firewall allows HTTPS outbound but not arbitrary TCP
- Connecting from a restricted network where only a proxy is available
- Latency or reliability issues with direct Postgres that disappear through the proxy path

### MCP and CLI

The MCP server runs as a local stdio process and does not need a proxy for its own transport. However, if the MCP server's backend is HTTPStore, the proxy environment variables apply to the MCP server's outbound HTTP calls to the Workledger API. Set the proxy variables in the MCP server's environment (typically in `claude_desktop_config.json` or `settings.json` env block).

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
