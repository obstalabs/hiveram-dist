---
name: write-wo
description: Turn a feature brief, bug report, or operator request into one or more well-scoped work orders.
argument-hint: "[project] [brief]"
---

Use this skill when the user wants new work orders written from a feature brief,
bug report, or investigation result.

## Workflow

1. Read the project README and nearby source structure if they matter for scope.
2. Inspect current work orders before creating anything:
   - `workledger search "<keywords>" --project <project>`
   - `workledger list <project> --status open`
3. Split the brief into session-sized work orders.
4. Create only the WOs that are genuinely distinct.

## WO shape

Every WO should include:

- a short imperative title
- priority
- complexity tier when it is clear
- specific files or modules when known
- `problem`
- `scope`
- `acceptance`
- `expected_output`

When multiple WOs share the same underlying target, add structured targets such
as:

```bash
--target type=invariant,id=context-routing
--target type=file_cluster,id=internal/router/guard.go
```

## Creation pattern

```bash
workledger create <project> \
  --title "Short imperative title" \
  --priority P1 \
  --complexity C2 \
  --file internal/example/file.go \
  --section problem="What is wrong and why it matters" \
  --section scope="What to change and what not to change" \
  --section acceptance="Concrete completion criteria" \
  --section expected_output=diff
```

## Rules

- Search first to avoid duplicates.
- Prefer one WO per distinct deliverable or research question.
- Reopen an existing WO when the same acceptance is still unresolved.
- Create a new sibling WO only when the surface is truly distinct.
- Do not use `workledger import` for normal WO authoring.
