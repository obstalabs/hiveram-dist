---
name: wrapup
description: Close out completed work orders, record delivery evidence, and finish a session cleanly.
argument-hint: "[commit message]"
---

Use this skill when implementation is finished and the session needs to be
closed out cleanly.

## Workflow

1. Identify which WOs were completed.
2. Verify the relevant tests or checks ran.
3. Hand completed WOs over for acceptance; do not close your own work:
   - `workledger note <project> <id> "Completed in <sha>: short summary"`
   - `workledger update <project> <id> --expected-rev <n> --status pending_verification`
   - A different identity closes it: `workledger close <project> <id> --squashed-as <sha> --reviewer <accepting-identity>`
4. Commit the code with a concise conventional commit message.
5. Push only if the user asked for it or the current workflow explicitly expects it.

## Rules

- Do not mark your own WO done; leave it at pending_verification with delivery evidence for the accepting identity.
- Keep the note short and factual: commit SHA plus what landed.
- If work is only partial, leave the WO open and add a progress note instead.
