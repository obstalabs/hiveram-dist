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
   - `workledger queue <project> --target current`
   - `workledger lanes <project> --target current`
   - `workledger next <project>`
   - `workledger list <project> --status open`
   - `workledger blocked <project>`
3. Restore the recent scaffold path around the current tip:
   - `workledger trellis read --project <project> --latest 5`
   - `workledger gradient detect --project <project> --latest 10`
4. Open the most relevant WO details:
   - `workledger get <project> <id>`
   - `workledger detail <project> <id>`
5. Summarize:
   - what the project is
   - what the current target and active lane are
   - what is ready now, next, later, and blocked
   - what is important but off-lane
   - what the recent scaffold path says still matters
   - what looks like the best next step from the current tip

## Rules

- This skill is read-only.
- Do not create, update, or claim WOs during orientation.
- Prefer `queue` and `lanes` over raw backlog order when those surfaces are
  available.
- Prefer `trellis read` plus `gradient detect` over transcript replay when those
  surfaces are available.
- Ask the user which WO or objective should be handled next once the summary is ready.
