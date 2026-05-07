# Context Mobility and Deployment Topologies

This document defines the Hiveram Pro product story for context mobility. It is
not public hype copy and it is not a runtime spec. Its job is to keep the
product promise honest across docs, demos, roadmap work, and operator guidance.

## Core framing

Hiveram is not "chat memory" and it is not just "long context."

Hiveram is the canonical work graph plus the bounded handoff layer that lets
work move between agents, machines, and time without making truth ambiguous.

That means:

- the authoritative work graph stays singular
- reasoning moves as a bounded artifact, not as transcript folklore
- fresh agents start from a mission briefing, not a giant replay
- returned work is reviewed or applied back to the canonical ledger explicitly

The shortest product distinction is:

- **Hiveram is the shared truth**
- **NeuroRouter is the moving focus window**
- **portable bundles are the bridge**

## What this is not

This product story does **not** promise:

- silent sync between local work and shared work
- replay of entire chat transcripts as the default continuity mechanism
- that every topology has the same capabilities
- that one long-lived session is the ideal operating model

The trust boundary is part of the product. If authority is ambiguous, the
system should say so instead of pretending continuity exists.

## The workflow shape

The core workflow is:

1. architect the work once
2. freeze the bounded truth
3. start a fresh focused execution surface
4. execute from the mission briefing
5. return results for review or apply-back

That flow is valuable because a senior agent can do the expensive architectural
work once, while cheaper or more specialized agents can execute from the same
bounded truth without rediscovering the project.

## Product promises

The Hiveram Pro promise is not "infinite memory." It is a more disciplined set
of guarantees:

1. **No forced giant session**
   Work can move into a fresh session without starting from zero.
2. **No silent authority drift**
   Shared authoritative and local portable modes stay explicit.
3. **No transcript dependency**
   Fresh agents work from a mission briefing, checkpoint, or bundle instead of
   guessing from a replay.
4. **No ambiguous return path**
   Results come back as explicit reply or receipt artifacts and are reviewed or
   applied against the canonical ledger.

## Deployment topology matrix

Hiveram Pro supports three legitimate product shapes. None of them should be
described as a degraded fake version of the others.

| Topology | What it has | Primary value | Honest promise | Not promised yet |
| --- | --- | --- | --- | --- |
| **NR-only** | NeuroRouter shaping, local session control, context window hygiene | Better live execution economics and session quality | Improve the current model window and keep bounded runs cleaner | Shared durable work graph, portable bundle lifecycle, canonical apply-back |
| **Hiveram-only / workledger-only** | Canonical work graph, portable reasoning bundles, checkpoints, provenance, mission briefings | Durable work continuity across agents and environments | Keep truth explicit and make handoff portable without transcript replay | Provider-side focus shaping, paging heuristics, or automatic live-window optimization |
| **Hybrid** | Hiveram substrate plus NeuroRouter projection/retrieval surfaces | Architect once, rehydrate fresh execution sessions, apply results back to one shared graph | Full context mobility with explicit authority boundaries and bounded handoff | Hidden reconciliation magic or provider-agnostic perfection across every surface |

## Runtime modes inside those topologies

Regardless of topology, runtime mode must stay visible:

- **Shared authoritative**
  - use when writing to the canonical ledger
  - verify `mode`, `store_kind`, `store_label`, and `store_fingerprint`
- **Local portable**
  - use for bounded offline work, airgapped transfer, or deliberate local-only
    exploration
  - valuable on purpose, but not the same as shared state

This distinction is load-bearing. "Portable" should never be described as a
synonym for "implicitly synchronized."

## What each topology is good for

### NR-only

Best when the main pain is cost, cap pressure, or stale-session drift inside one
agent surface.

Use this story:

- better bounded execution
- cleaner fresh sessions
- context shaping without pretending a shared work graph already exists

Do **not** use this story:

- durable shared truth across agents
- authoritative recall or apply-back

### Hiveram-only / workledger-only

Best when the main pain is coordination, portability, reviewable handoff, or
durable state across teams, machines, and time.

Use this story:

- canonical work graph
- portable reasoning bundles
- checkpoints
- provenance
- mission briefings

Do **not** use this story:

- provider-window optimization
- automatic shaping of what enters a live model context

### Hybrid

Best when the team wants both:

- a durable system of record for work
- and a cleaner live execution window

Use this story:

- architect once
- rehydrate a fresh focused run
- execute on the cheapest capable surface
- apply back without making authority ambiguous

This is the flagship context-mobility story, but it must still stay honest: the
bridge is bounded and explicit, not magical.

## Demo guidance

When demonstrating Hiveram Pro, show the workflow as a bounded contract:

1. inspect one WO as the system of record
2. produce a mission briefing or portable bundle
3. start a fresh execution surface from that bounded truth
4. return a receipt, reply, or apply step to the canonical ledger

Good demos emphasize:

- authority verification
- bounded handoff
- fresh-session execution
- explicit apply-back

Bad demos imply:

- hidden background merge
- transcript teleportation
- "it just remembered everything"

## Roadmap guidance

This document should steer product choices:

- work that makes authority explicit is on-strategy
- work that improves bounded handoff is on-strategy
- work that clarifies topology-specific promises is on-strategy
- work that relies on silent sync, fuzzy memory claims, or provider-specific
  magic as the core story is off-strategy

The roadmap sequence should keep the layers legible:

1. trust floor and authority modes
2. durable bundles, checkpoints, and mission briefings
3. clean dispatch and rehydration flows
4. richer focus-window and recall behavior in the hybrid stack

## Relationship to public docs

Use this document as the internal product spine behind:

- the public README
- self-hosted guidance
- site copy
- demo scripts
- roadmap framing

If public wording drifts from this contract, the fix is not louder copy. The
fix is to bring the public surface back to the real topology and authority
story.
