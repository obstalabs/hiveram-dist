# Operator Workflow for Portable Reasoning

This document defines the practical Hiveram Pro operator journey for bounded
handoff, fresh-agent rehydration, and result return. It is the workflow
companion to [Context Mobility and Deployment Topologies](context-mobility.md).

Use this guide when you need to answer:

- how an agent or operator starts from a WO, bundle, or checkpoint
- what to do in shared authoritative mode vs local portable mode
- how results come back without brainsplit or silent mutation

## The workflow in one sentence

Architect once, freeze bounded truth, start a fresh focused run from a mission
briefing, and return explicit results to the canonical graph.

## The three entry points

Portable reasoning has three normal rehydration selectors. They are all
legitimate, and each is best at a different moment.

### 1. WO-based rehydration

Use this when the canonical work order is already the primary source of truth
and the next agent only needs the current task contract.

Typical path:

```bash
workledger status --json --resolved
workledger briefing wo myapp 118
```

This is the cleanest "start fresh without replay" path. The briefing carries
the active task, constraints, decisions, rejected approaches, likely files, and
reporting contract.

Use WO-based rehydration when:

- the shared ledger is reachable
- the work order already has the right scope and evidence
- you want the lightest-weight handoff

### 2. Bundle-based rehydration

Use this when work must move across agents, machines, teams, or environments as
an explicit bounded artifact.

Typical path:

```bash
workledger briefing wo myapp 118
workledger bundle export myapp 118 --out task.wlbundle
workledger bundle inspect task.wlbundle
```

On the receiving side:

```bash
workledger bundle import task.wlbundle --mode import_as_local_copy
workledger briefing bundle myapp bundle_...
```

Use bundle-based rehydration when:

- the next execution surface cannot see the same live ledger
- the handoff needs reviewable, portable packaging
- the operator wants a request/reply workflow instead of direct shared writes

### 3. Checkpoint-based rehydration

Use this when the state you need is not "the current WO" but a specific frozen
branch point or reasoning state.

Typical path:

```bash
workledger checkpoint create myapp --summary "before external handoff"
workledger briefing checkpoint myapp cp_...
```

Use checkpoint-based rehydration when:

- the operator wants a known branch point before a risky or external handoff
- the next run should begin from a named frozen state
- branch history matters more than the latest WO snapshot

## The runtime mode decision

Before doing anything else, the operator should know which mode they are in.

### Shared authoritative

Use this when the machine is expected to read and write the canonical ledger.

Check the authority surface first:

```bash
workledger status --json --resolved
workledger serve --mcp --mcp-mode shared-authoritative
```

Trust writes only after verifying:

- `mode`
- `store_kind`
- `store_label`
- `store_fingerprint`

In shared authoritative mode, the normal return path is:

- note
- update
- bundle apply
- checkpoint creation
- closure evidence

### Local portable

Use this when work is intentionally local, disconnected, restricted, or moving
through a bounded handoff instead of direct shared writes.

Typical startup:

```bash
workledger serve --mcp --mcp-mode local-portable
workledger mirror pull
```

Treat this mode as portable on purpose, not as secretly shared. The operator is
holding a bounded artifact or local state, not the canonical graph itself.

### Offline queued

Use this when a machine needs to record intended shared writes while direct
reachability is unavailable.

Typical path:

```bash
workledger update myapp 118 --status in_progress --queue-offline
workledger outbox list
workledger outbox export queued-mutations.wlxfer
```

This mode means:

- the local side has queued intent
- the shared ledger has not yet accepted the mutation
- the authoritative return signal will come later as a receipt

Operators should describe these results as queued, not committed.

## See the queue from the current tip

Before choosing a WO from raw backlog order, pull the current queue and lane
view that Workledger now computes from the current tip:

```bash
workledger queue myapp --target current
workledger lanes myapp --target current
```

Use these surfaces to answer different questions:

- `queue` answers what is ready now, what comes next, what is later, what is
  blocked, and what is intentionally deferred
- `lanes` answers what the current target is, where the active lane is, which
  support or safety lanes exist, and which old smoke-stage items are off-lane

This matters because importance is not the same thing as target reach. A real
bug can still be the wrong next move if it does not advance the current target.
The queue view keeps important-but-off-lane work visible without mixing it into
the execution lane.

For fresh-agent orientation, treat these as the first read surfaces. They are
lighter and truer than re-reading giant transcripts or inferring order from a
flat list of open WOs.

## The handoff sequence

The normal handoff sequence looks like this:

1. verify authority mode
2. inspect the source WO
3. create a checkpoint if the handoff needs a named branch point
4. build the mission briefing or bundle
5. start the fresh execution surface from that bounded truth
6. return results as apply, reply, or receipt
7. update the canonical graph with evidence

### Minimal shared-ledger handoff

```bash
workledger status --json --resolved
workledger queue myapp --target current
workledger lanes myapp --target current
workledger briefing wo myapp 118
```

This is enough when the next run stays on the same shared ledger and only needs
a fresh, bounded task contract.

### Portable request/reply handoff

```bash
workledger checkpoint create myapp --summary "before external handoff"
workledger bundle export myapp 118 --out task.wlbundle
```

The receiving side works from the imported bundle, then returns a reply bundle:

```bash
workledger bundle apply reply.wlbundle
```

The important rule is that returned work comes back as an explicit artifact. The
shared graph is not mutated by implication.

### Airgapped request/receipt handoff

When the machine is truly disconnected, move queued mutations and receipts by
file copy:

```bash
workledger outbox export queued-mutations.wlxfer

# connected side
workledger outbox apply-bundle queued-mutations.wlxfer --receipt-out queued-mutations.receipt.wlxfer

# disconnected side
workledger outbox import-receipt queued-mutations.receipt.wlxfer
```

This path matters because the operator needs to know what kind of result they
are holding:

- a local edit
- a queued intent
- an authoritative receipt

Those are not interchangeable.

## How results flow back

There are three normal return shapes.

### 1. Direct apply back

Use this in shared authoritative mode when the returned artifact is ready to be
applied against the canonical graph.

Example:

```bash
workledger bundle apply reply.wlbundle
```

This is the strongest return path because the ledger itself records the result
and its provenance.

### 2. Receipt return

Use this in offline queued workflows when the disconnected side needs proof that
the shared system accepted or rejected the intended mutations.

Example:

```bash
workledger outbox import-receipt queued-mutations.receipt.wlxfer
```

The receipt tells the operator which actions were accepted, which were rejected,
and which server-side WO IDs were assigned.

### 3. Branch-history continuation

Use this when the handoff creates a meaningful fork in reasoning history rather
than a straight request/reply cycle.

Typical path:

```bash
workledger checkpoint create myapp --summary "fork after external review" --parent cp_... --lineage-event branched_from
```

or

```bash
workledger checkpoint create myapp --summary "resume earlier branch" --parent cp_... --lineage-event rewound_to
```

This keeps the branch history explicit instead of making alternative paths
disappear into notes or memory.

## The mission briefing contract

Fresh agents should begin from the mission briefing, not from a giant chat.

The bounded contract should answer:

- what is the active task
- what constraints still matter
- what decisions are already made
- which approaches are explicitly rejected
- what files or surfaces are likely in scope
- what evidence or reporting contract is expected on return

If an operator cannot explain the next run from that contract, the handoff is
not ready yet.

## What to say in demos and onboarding

Use these phrases:

- "fresh agent from a bounded mission briefing"
- "portable request/reply workflow"
- "shared authoritative vs local portable"
- "receipt proves what the shared system accepted"
- "checkpoint keeps the branch point visible"

Avoid these phrases:

- "it just remembers everything"
- "background sync"
- "the systems silently merge"
- "local is basically the same as shared"

## Failure and ambiguity rules

When something looks missing or inconsistent, the first question is not "did we
lose the work?" It is "which authority surface answered?"

Before trusting a mismatch:

```bash
workledger status --json --resolved
```

Compare:

- `mode`
- `store_kind`
- `store_label`
- `store_fingerprint`

If a result came from local portable mode or from a queued outbox state, do not
describe it as authoritative shared truth.

## Recommended onboarding sequence

For a new team or customer:

1. teach the shared authoritative vs local portable distinction
2. show WO-based rehydration first
3. show portable bundle handoff second
4. show airgapped receipt flow only if the deployment needs it
5. show checkpoints when branching or external review matters

That order keeps the simplest trustworthy path first and adds portability only
when the operator already understands the authority boundary.

## Relationship to other docs

Use this doc with:

- [Context Mobility and Deployment Topologies](context-mobility.md) for the
  product promise and topology matrix
- [Self-hosted Hiveram](self-hosted.md) for custody and deployment mechanics
- the README for install and quick-start operator entry points

If a public workflow explanation drifts from this sequence, bring it back to
the bounded handoff and explicit-return model instead of layering on vaguer
language.
