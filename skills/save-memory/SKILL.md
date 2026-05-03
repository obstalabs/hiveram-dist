---
name: save-memory
description: Save durable project context through workledger memory and context surfaces without leaking secrets.
argument-hint: "[project]"
---

Use this skill when the user wants to preserve stable project context that
should survive beyond the current session.

## Save only durable context

Good candidates:

- stable architecture notes
- durable operating constraints
- important repo-specific conventions
- long-lived investigation findings

Do not save:

- secrets
- raw credentials
- one-off debugging chatter
- ephemeral session state that belongs in a short-lived note instead

## Suggested flow

1. Write or update a local context file with the durable facts.
2. Push it into workledger using memory or context surfaces:

```bash
workledger memory put <project> <key> --file <path>
workledger context-put <project> --file <path>
```

3. Confirm the stored artifact can be listed or read back if needed.

## Rules

- Never print secret-bearing files while saving context.
- Keep saved context concise and durable.
- Prefer a WO note instead when the information only matters to one delivery slice.
