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
- Current queue from the current tip: `workledger queue <project> --target current`
- Lane and tip view: `workledger lanes <project> --target current`
- Recent scaffold path: `workledger trellis read --project <project> --latest 5`
- Direction restore from the scaffold: `workledger gradient detect --project <project> --latest 10`
- Queue view: `workledger list <project> --status open`
- Full WO: `workledger get <project> <id>`
- Rich WO view: `workledger detail <project> <id>`
- Duplicate check: `workledger search "<keywords>" --project <project>`
- Blockers: `workledger blocked <project>`
- Dependency tree: `workledger deps-tree <project> <id>`

Use `queue` and `lanes` first when the job is "what should we do from here?"
Those surfaces consume Workledger's current-tip planner truth:

- `queue` shows `now`, `next`, `later`, `blocked`, and deferred off-lane work
- `lanes` shows the current target, current tip, active lane, support lanes,
  blocker lanes, and deferred smoke or side work

Use raw `list` output when you need a full open backlog view, not when you need
execution order from the current tip.

## Scaffold review and continuation

Use these surfaces when the question is not only "what is next?" but also
"what is the agent standing on right now?"

```bash
workledger trellis read --project <project> --latest 5
workledger gradient detect --project <project> --latest 10
```

Use the recent trellis path to recover the decisions, constraints, and evidence
that still matter near the current tip. Use gradient detection to restore
direction for a fresh session without re-reading a giant transcript.

When a claim or proposed change needs review with context, build a review diff
instead of comparing prose by hand:

```bash
workledger trellis diff --base-file base.yaml --candidate-file candidate.yaml --context-file context.yaml --format markdown
```

That surface shows structural change, semantic target impact, and whether the
change is a drift signal or a real target refinement. Treat standing and
confidence as load-bearing when you decide what to trust next.

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

## Airgapped mirror and outbox transfer

When a machine must move mirror or queued mutation state by file copy:

```bash
workledger mirror export mirror.wlxfer
workledger outbox export queued-mutations.wlxfer
workledger outbox apply-bundle queued-mutations.wlxfer --receipt-out queued-mutations.receipt.wlxfer
workledger outbox import-receipt queued-mutations.receipt.wlxfer
```

Outbox request bundles carry an intended target fingerprint. Apply must stop if
the receiving shared store does not match that fingerprint.

## Planning and grouping

- Current-tip execution order: `workledger queue <project> --target current`
- Lane graph from the current tip: `workledger lanes <project> --target current`
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
- For the full operator handoff journey, read `docs/operator-workflow.md` in
  the Hiveram distribution. It is the canonical sequence for WO-based,
  bundle-based, and checkpoint-based rehydration plus return-path handling.
