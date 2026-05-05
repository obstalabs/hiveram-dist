---
name: workledger
description: Use workledger to inspect, plan, and update structured work orders through MCP, CLI, or HTTP API without relying on flat backlog files.
argument-hint: "[project] [goal]"
---

Use this skill when the user wants to inspect work orders, create or update
them, understand blockers or dependencies, or choose what to work on next.

## Pick the safest access path

1. Prefer MCP when it is available.
2. Otherwise use the `workledger` CLI.
3. Use the HTTP API only when CLI or MCP is unavailable.
4. Use flat backlog files only as a last-resort fallback.

## Authentication rules

- The commercial CLI uses a Hiveram license saved by `workledger activate`.
- The binary should read the saved license automatically from
  `~/.hiveram/license`.
- The HTTP API uses `WORKLEDGER_API_KEY`. Hosted bearer tokens may be `ol_`-prefixed, but they are still API credentials, not the saved CLI license from `~/.hiveram/license`.
- Never print, paste, summarize, or log full license keys or API keys.

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
workledger create <project> \
  --title "Short imperative title" \
  --priority P1 \
  --complexity C2 \
  --file internal/example/file.go \
  --target type=invariant,id=context-routing \
  --section problem="What is wrong and why it matters" \
  --section scope="What to change and what not to change" \
  --section acceptance="Concrete completion criteria" \
  --section expected_output=diff
```

- Update status or metadata:

```bash
workledger update <project> <id> --status done
workledger update <project> <id> --target type=file_cluster,id=internal/router/guard.go
workledger note <project> <id> "Completed in <sha>: short summary"
```

## Planning and grouping

- Full queue planning: `workledger queue-plan <project>`
- Target-centered cohort: `workledger target-plan <project> --wo WO-23`
- Session grouping: `workledger dispatch <project>`
- Best next executable group: `workledger next <project>`

Useful flags:

- `--json` for machine-readable output
- `--model sonnet|opus|codex|haiku` to filter by execution tier
- `--execute` on `dispatch` or `next` to write task files for execution

## HTTP API fallback

If CLI or MCP is unavailable and `WORKLEDGER_URL` plus `WORKLEDGER_API_KEY`
are already configured:

- `GET /api/v1/wo/{project}/{id}`
- `GET /api/v1/search?q=<query>&project=<project>`
- `GET /api/v1/projects/{project}/queue-plan`
- `GET /api/v1/projects/{project}/target-plan?wo_id=<id>`
- `POST /api/v1/wo`
- `PATCH /api/v1/wo/{project}/{id}`
- `POST /api/v1/wo/{project}/{id}/note`

Do not echo secret-bearing environment variables while checking API access.

`WORKLEDGER_URL` is the preferred remote-backend variable. For compatibility with older setups, the CLI and MCP server also accept `WORKLEDGER_HOST`; when present without a scheme it is treated as `https://<host>`.

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
- Treat `repo_warning` as a real signal that project metadata needs cleanup.
- Do not use `workledger import` for normal day-to-day WO authoring.
