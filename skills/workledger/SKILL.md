---
name: workledger
description: Use workledger to inspect, plan, and update structured work orders through MCP, CLI, or HTTP API without relying on flat backlog files.
---

# workledger

Use this skill when the user wants to inspect work orders, create or update them, understand blockers or dependencies, or choose what to work on next.

## Pick the safest access path

1. Prefer MCP when it is available.
2. Otherwise use the `workledger` CLI.
3. Use the HTTP API only when CLI or MCP is unavailable.
4. Use flat backlog files only as a last-resort fallback.

Before trusting any authoritative write or import, run:

- `workledger status --json --resolved`

Treat `failure_kind: "dns"` as a likely sandbox or outbound-network restriction. In that case, keep shared writes out of the loop until you are back on a network-enabled shell.

## Choose an explicit runtime mode

For MCP startup, choose one of two modes on purpose:

- shared authoritative:
  - `workledger serve --mcp --mcp-mode shared-authoritative`
  - use for canonical writes, imports, bundle apply, and closure evidence
  - refuses implicit SQLite fallback
- local portable:
  - `workledger serve --mcp --mcp-mode local-portable`
  - use for offline work, airgapped work, bounded handoff, and bundle preparation
  - not a substitute for shared authoritative state

Do not treat local portable mode as authoritative shared state.

## Identity checks

Before trusting a cross-surface comparison, compare backend identity:

- CLI: `workledger status --json --resolved`
- MCP: `workledger_backend_info`
- HTTP: `GET /healthz`

The fields that should agree are:

- `mode`
- `store_kind`
- `store_label`
- `store_fingerprint`

If those values differ, you are not on the same authority surface.

## Core read flows

- Project list: `workledger projects`
- Queue view: `workledger list <project> --status open`
- Full WO: `workledger get <project> <id>`
- Rich WO view: `workledger detail <project> <id>`
- Duplicate check: `workledger search "<keywords>" --project <project>`
- Blockers: `workledger blocked <project>`
- Dependency tree: `workledger deps-tree <project> <id>`

## Creation and updates

- Search before creating a new WO.
- Create with concrete scope:

```bash
workledger create <project>       --title "Short imperative title"       --priority P1       --complexity C2       --file internal/example/file.go       --section problem="What is wrong and why it matters"       --section scope="What to change and what not to change"       --section acceptance="Concrete completion criteria"       --section expected_output=diff
```

- Update status or metadata:

```bash
workledger update <project> <id> --status done
workledger note <project> <id> "Completed in <sha>: short summary"
```

## Portable reasoning handoff

Use bounded artifacts instead of replaying giant transcripts:

```bash
workledger briefing wo <project> <wo-id>
workledger checkpoint create <project> --summary "before handoff"
workledger bundle export <project> <wo-id> --out task.wlbundle
workledger bundle inspect task.wlbundle
```

Returned work can be reviewed and applied later:

```bash
workledger bundle apply reply.wlbundle
```

Portable reasoning is an explicit workflow. It is not hidden background sync.

## Planning and grouping

- Full queue planning: `workledger queue-plan <project>`
- Target-centered cohort: `workledger target-plan <project> --wo WO-23`
- Session grouping: `workledger dispatch <project>`
- Best next executable group: `workledger next <project>`

## HTTP API fallback

If CLI or MCP is unavailable and `WORKLEDGER_URL` plus `WORKLEDGER_API_KEY` are already configured:

- `GET /api/v1/wo/{project}/{id}`
- `GET /api/v1/search?q=<query>&project=<project>`
- `GET /api/v1/projects/{project}/queue-plan`
- `POST /api/v1/wo`
- `PATCH /api/v1/wo/{project}/{id}`
- `POST /api/v1/wo/{project}/{id}/note`
- `POST /api/v1/bundles/export`
- `POST /api/v1/bundles/import`
- `POST /api/v1/bundles/apply`
- `POST /api/v1/briefings/resolve`

`WORKLEDGER_URL` is the preferred remote-backend variable. For compatibility with older agent configs, the CLI and MCP server also accept `WORKLEDGER_HOST`; when present without a scheme it is treated as `https://<host>`.

## Verify backend identity before trusting a mismatch

When MCP, CLI, and HTTP disagree about whether a WO exists or whether a
relationship target is present, compare store identity before assuming the data
is wrong:

- MCP: `workledger_backend_info`
- CLI: `workledger status --json --resolved`
- HTTP: `GET /healthz`

Compare these fields:

- `store_fingerprint`
- `store_label`
- `store_kind`
- `mode`

If the fingerprints differ, you are looking at different stores. Treat a
relationship FK error as "missing in this store" first, not as proof that the
relationship handler is broken.

## Operator rules

- Search first, then create.
- Prefer structured fields over freeform notes when a field exists.
- When a WO is done, attach commit evidence in a note.
- Treat shared authoritative mode as the normal path for trusted writes.
- Treat local portable mode as an explicit offline or handoff mode.
- Do not use `workledger import` for normal day-to-day WO authoring.
- Do not describe portable reasoning as silent sync or automatic reconciliation.
