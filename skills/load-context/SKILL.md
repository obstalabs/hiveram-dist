---
name: load-context
description: Orient a new agent session on the repo and the current open work without changing anything.
argument-hint: "[project]"
---

Use this skill at the start of a session to understand the repo and the current
workledger state before making changes.

## Read-only orientation flow

1. Read the project README and any relevant local docs.
2. Inspect the current work queue:
   - `workledger next <project>`
   - `workledger list <project> --status open`
   - `workledger blocked <project>`
3. Open the most relevant WO details:
   - `workledger get <project> <id>`
   - `workledger detail <project> <id>`
4. Summarize:
   - what the project is
   - what is currently open
   - what is blocked
   - what looks like the best next step

## Rules

- This skill is read-only.
- Do not create, update, or claim WOs during orientation.
- Ask the user which WO or objective should be handled next once the summary is ready.
