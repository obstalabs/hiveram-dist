# Changelog

Customer-facing release notes for Hiveram. For the full internal development history, see the workledger repository changelog.

## [0.38.0] - 2026-07-02

### Added
- Reads tell you how much you're seeing. `list` and `search` now report the total, how many were returned, and whether more exist — so a capped page (the MCP default of 50 was the common surprise) is distinguishable from a complete result. A short notice prints when results were truncated.
- The status check reports "waking" as well as up/down. A backend that is serving reads but whose health endpoint briefly stutters (cold start) is no longer reported as unavailable; a genuinely-down backend still is.
- `serve` refuses to run an unauthenticated API on a non-loopback address unless you pass `--insecure-no-auth` explicitly. Local (loopback) development is unaffected.

### Changed
- Reads fail loud on backend trouble. `list`/`search`/`get`/`projects`/`stats` now return an error and a non-zero exit when the backend is unreachable, instead of an empty result that looks like "nothing found". If you relied on falling back to a local mirror on read failure, opt in with `WORKLEDGER_ALLOW_READ_MIRROR_FALLBACK=1`.
- Changing a work order's status either applies or tells you why not (with the allowed transitions and a command to run) — it no longer quietly does nothing.
- Errors now include the command to fix them.

### Fixed
- Delete and merge honor a work order's removal policy at the storage layer, so a protected work order can't be deleted from any surface. Merge and bulk updates are all-or-nothing, and can't sneak a work order to "done" without its close checks.
- Over a hosted connection, an override and its reason (and close proof) reach the server instead of being dropped.
- Connection errors no longer echo the raw database connection string. Queued offline changes surface instead of sitting unseen, and replay on reconnect without dropping anything that failed.

## [0.37.0] - 2026-06-30

### Added
- `workledger close` for work orders that were squash-merged. It records the landed commit on the default branch as the close proof, refuses to let the person who did the work close it themselves, and keeps the original pre-squash branch SHA. If it can't determine who executed the work, it stops rather than closing — pass `--allow-unverified-executor` to override with an audit note.
- `workledger reconcile` compares each work order's status against git. It reports the ones where the code already landed but the status was never advanced, the ones marked ready with no commit behind them, and stalled claims. It can close the unambiguous landed ones for you, through the same close-proof check as a normal close.

### Fixed
- A dependency that was auto-expired by the time-to-live sweep no longer counts as a completed prerequisite. Before this, a work order could start as though its groundwork was done when that work had only been abandoned. Cancellations now carry why they happened (intentional, superseded, or swept), and a dependency only counts as met when it was finished or deliberately superseded.
- `done` and `cancelled` now require a recorded reason. No more terminal work orders with no explanation of how they got there.
- Readiness rejects a work order whose acceptance criteria are empty or just a restatement of the problem. An under-specified work order no longer reads as ready to dispatch.

## [0.36.0] - 2026-06-28

### Added
- Much better search recall on large projects. Search now down-weights the common words that appear in almost every work order, so the distinctive terms that actually identify what you're looking for carry the result. On a realistic self-retrieval benchmark this roughly doubled the rank quality of the correct match. Search stays fully deterministic — no model call, no per-query network request.

### Operator action
- This is a server-side improvement, and it takes effect only after a one-time backfill. After updating, run `workledger reembed` once (whole corpus, no project filter) to rebuild the search index with the new weighting. Until you do, search keeps working exactly as before — no regression, but you won't see the recall gain. You can turn the semantic layer off entirely with `WORKLEDGER_EMBEDDINGS_DISABLED=1`.

## [0.35.0] - 2026-06-27

### Added
- Safe in-session MCP upgrades. A new supervised mode keeps your editor or agent connected to a stable process while the work order server behind it is refreshed, so you can pick up a newer install without restarting your whole session. It only refreshes when the installed version is genuinely newer and the available tools are unchanged; if the tool set changed, it tells the client to reconnect instead of swapping silently. An in-flight request always finishes first, and if a refresh fails the existing connection keeps working.

### Operator action
- Optional and off by default. Start it with `workledger mcp-shim`; enable automatic refresh with `--allow-worker-restart` once you want hands-off upgrades. Existing `workledger serve --mcp` usage is unchanged.

## [0.34.2] - 2026-06-26

### Added
- Smarter search: search now blends keyword matching with meaning-based recall, so a work order that is the right match but uses different words is more likely to surface — reducing "no results for something that clearly exists." Each result shows how it was matched. Meaning-based recall is computed locally at write time (no external service is called per search) and can be turned off to fall back to keyword-only. A new `reembed` step backfills existing work orders, including for teams connected over the network. Existing keyword searches are unaffected.

## [0.34.1] - 2026-06-25

### Fixed
- Work-order creation now triggers its "created" event no matter how you create the item — command line, editor integration, or API — instead of only over the API. Local command-line creates deliver the event before the command returns.
- Safe retries: if a create is interrupted (timeout, dropped connection) and you retry it, you get the same work order back instead of an accidental duplicate — either by passing a stable retry key or automatically when the same item is created again within a short window.
- A completed item awaiting a single batch landing can no longer get stuck un-closable when its change was squash-merged; it can be closed with an audited override while normal completions keep their full verification.

### Changed
- Listing, creating, and the same operations across all interfaces now share one implementation, so they behave identically and return the same shapes — fewer surprises when switching between the command line, editor, and API.

### Added
- New create options: a stable retry key for safe send-and-forget creates, and a canonical complexity-tier flag. Listing uses a consistent default page size.

## [0.34.0] - 2026-06-22

### Added
- Lighter-weight output for scripts and agents: read commands can now return plain one-line or tab-separated rows (`--format oneline|tsv`, with an optional `--no-header`) instead of JSON, so tooling no longer has to parse JSON for simple lists. JSON remains the default and is unchanged.
- Attention cues on work clusters: the cluster view now flags clusters that look worth a second look (for example, very broad scope or mixed risk) under a REVIEW group. These are advisory only — they never change priorities, links, or what is allowed to run.
- Record where a work item was discussed: you can attach a short pointer and summary linking an item back to the conversation that produced or refined it.
- More forgiving search: multi-word searches no longer need quotes; a helpful hint is shown if it looks like you meant to filter by project.

### Fixed
- More reliable emergency recovery for the completion-evidence safeguard: if the safeguard is switched off or its settings cannot be read, completions are allowed through with an audit note rather than being blocked — the safeguard can never lock you out of closing work.
- More honest completion checks on hosted setups: completion proof supplied by the client is trusted when valid, and its source is recorded clearly instead of being reported as a configuration problem; completions with no proof still fail safely.
- Fixed a data-integrity issue where bulk status updates on the hosted database could mis-store some work-item fields.

## [0.33.1] - 2026-06-21

### Fixed
- Reliability: work orders that had been automatically claimed could become un-updatable in some cases; they can now be updated and closed normally.
- More trustworthy automatic completion: a work order is only marked done when its completion is genuinely verified, never on incomplete evidence.
- Audit clarity: memory and context writes now record who made the change separately from which machine it came from.

## [0.33.0] - 2026-06-20

### Added
- See which work to do next, by cluster: a new command ranks ready-to-start work clusters in priority order and shows, for each, its members, priority, risk class, and whether it is ready or blocked (and by what) — so you can pick the next shippable unit at a glance instead of hunting through individual items.
- Mark each work item's risk class (high / medium / low) so high-stakes changes are visible and treated differently from routine ones.
- Land a whole cluster at once: when a related set of work is complete and verified locally, land it together with a single step — closing the cluster as one unit with shared proof, instead of one item at a time.

### Changed
- More reliable verification: the test suite no longer depends on machine-specific state, so results are consistent across environments.

## [0.32.0] - 2026-06-19

### Added
- Reserve a work-order number before you create it: `reserve-id` returns the next free number and holds it briefly so two people (or agents) working at once never land on the same id, and `get-next-id` reads it without holding. This keeps branch names, commits, and the work order itself pointing at the same number.
- Wire dependencies as you create work: `create --depends-on` records a new work order's prerequisites in one step, instead of creating it and linking afterwards.
- A pre-dispatch readiness check confirms a work order is fully specified, its repository is in a clean (green) state, and a suitable runner is available before any work is handed off — so a dispatch that would fail is stopped up front instead of partway through.

### Changed
- Closing a work order now requires real evidence: a landed commit plus a passing build signal. Closing without that evidence requires an explicit, recorded acknowledgement, and an attempt to close without proof gets a clear, recoverable message rather than silently completing. Overriding the check requires a recorded reason.
- Under parallel branches, each work order remembers the exact code revision it was claimed against, so work is always verified against the right checkout.

### Fixed
- Work orders that merely describe credentials or security topics in plain prose are no longer mistaken for leaked secrets; only real secret values are blocked, and the message points to how to redact or reference them. Genuine secret detection is unchanged.

### Reliability
- Continuous-integration builds on our self-hosted runners are now stable; a cache conflict that intermittently produced false build failures has been resolved.

## [0.31.0] - 2026-06-15

### Added
- A new verify-pending command lets an operator confirm work orders awaiting verification: it promotes those whose implementing commit has landed on the canonical branch and reopens those that have not, each with a clear note. Runs once by default, with continuous and preview modes.

### Changed
- Work-order readiness now advises when a spec asks a worker to act for-each item of a category without listing the category's members, so the spec can be pinned before it is handed off. This is advisory and does not block creation.

## [0.30.0] - 2026-06-11

### Added
- A new `doctor` command reports which backends the tool can reach (hosted API, database, or local file) and, when one is unreachable, names the setting to check — without ever printing a credential. Useful for diagnosing setup from an automation environment.

### Changed
- The command-line tool now authenticates from its own configuration in a fresh shell, so automated agents no longer need a hand-sourced environment to read and write work orders.
- Routine writes (notes, updates, relationships) no longer require a manual override flag; the tool resolves who is making the change from its configuration, while still protecting work actively claimed by someone else.
- Choosing the local database or a specific backend explicitly is now honored exactly, instead of quietly falling back to a configured remote; degraded local reads are clearly marked.
- Common command mistakes now produce an actionable error that shows the correct usage and valid values rather than a bare usage dump.

## [0.29.1] - 2026-06-09

### Fixed
- Work orders with `removal-policy: prohibited` now reach rocket-ready even when
  their planning prose contains removal verbs naming functionality objects (flags,
  endpoints, commands). The signal is surfaced as an advisory note rather than a
  hard blocker, so additive work no longer requires prose rewrites or no-op
  workarounds to pass readiness checks.

## [0.26.1] - 2026-06-01

### Added
- `link-commit` links a commit directly to a work order, so closing work no longer depends on commit-message conventions — useful for audit-closing already-shipped work with proper evidence.
- `find-similar` surfaces related work orders before you create a new one, reducing duplicates.
- Two-stage closure: work orders can move through a pending-verification state before done, with the queue and stats accounting for it.

### Fixed
- Direct commit links are preserved end-to-end over the hosted API, including ownership checks and author identity.
- Closure checks no longer mistake internal backend identifiers for commit references.
- Similarity search runs reliably against the hosted API.
- Destructive operations over the API require explicit confirmation.
- Bulk and empty results return consistent, predictable output.

## [0.25.13] - 2026-05-28

### Added
- `search --summary` returns a compact one-line-per-result view with complexity and readiness badges, matching `list --summary`.

### Fixed
- Saving shared memory and context no longer requires anchoring to a work order. Memory writes are audited automatically (who, which machine, when) and sync to the shared store directly. Other canonical writes are unchanged.

## [0.25.12] - 2026-05-28

### Added
- The CLI and MCP server now work fully against the hosted HTTP API backend. Batch updates, similar-WO search, blocked-WO and dependency queries, and the execution-object surface all work over HTTP — no direct database connection required.

### Fixed
- Operator memory and context saves can be authorized with an audited override when no specific work order applies, instead of being blocked.
- Work order updates preserve claim ownership and closure evidence when applied over HTTP or through the agent tools.

## [0.25.11] - 2026-05-27

### Fixed
- Status line no longer shows permanent `wl:!` when an unrelated backend probe fails. Readiness computed from resolved backend only.
- Rate limit raised to 300 requests per minute; admin keys are exempt.

## [0.25.10] - 2026-05-27

### Fixed
- Proxy from config.yaml now applies to all outbound connections including healthcheck and status probes.

## [0.25.9] - 2026-05-27

### Fixed
- Config file now reads API keys from `export VAR=value` format, not just bare keys. Existing `api-key.env` files work without changes.

## [0.25.8] - 2026-05-27

### Added
- **Config file support.** `~/.workledger/config.yaml` is now the single place to configure your backend, API key, and proxy. No more setting environment variables in every terminal session.
- **SOCKS5 and HTTP proxy.** Set `connection.proxy` in config.yaml to route all API traffic through a proxy. Instant fix for VPN environments where direct connections are unreliable.
- **Capture promotion.** `workledger artifact capture-promote` stores sanitized smoke-test captures as durable evidence with provenance links to work orders.

### Fixed
- Private key blocks are now redacted from capture evidence before storage.
- Closure proof enforcement requires branch evidence before marking work complete.

### Proxy quick start

```yaml
# ~/.workledger/config.yaml
connection:
  backend: http
  url: https://workledger.fly.dev
  api_key_file: ~/.workledger/api-key.env
  proxy: socks5://127.0.0.1:1080
```

See [docs/postgres-support.md](docs/postgres-support.md) for the full proxy guide.

## [0.25.7] - 2026-05-22

### Fixed
- Offline outbox recovery handles retryable failures, preserves receipt evidence, and counts failed bundle entries correctly.
- Project identity preservation prevents stale local mirrors from blanking shared repo guardrails.
- Completed-work safety checks tie closure evidence to the write that records completion.

## [0.25.6] - 2026-05-19

### Fixed
- Default convergence corpus bound lowered for responsive shared-backend queries.

## [0.25.5] - 2026-05-19

### Fixed
- HTTP-backed CLI respects server `Retry-After` for rate limiting.
