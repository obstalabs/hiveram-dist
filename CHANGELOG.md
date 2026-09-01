# Changelog

Customer-facing release notes for Hiveram. Downloads for each version are on the [releases page](https://github.com/obstalabs/hiveram-dist/releases).

## [0.55.6] - 2026-09-01

### Added
- The Workledger Helm chart is published as a release asset. Deploy on Kubernetes against your own PostgreSQL, with a values schema, per-value documentation, an optional migration hook, and restricted Pod Security defaults.

### Changed
- The container image is published alongside the rest of the distribution, so it can be pulled from the same place you download everything else.

### Note
- This release supersedes 0.55.0 through 0.55.5, which were tagged but never published. Install 0.55.6.

## [0.55.5] - 2026-08-31

### Added
- The Workledger Helm chart is published as a release asset. Deploy on Kubernetes against your own PostgreSQL, with a values schema, per-value documentation, an optional migration hook, and restricted Pod Security defaults.

### Changed
- The container image is now published alongside the rest of the distribution, so it can be pulled from the same place you download everything else.

### Note
- This release supersedes 0.55.0 through 0.55.4, which were tagged but never published. Install 0.55.5.

## [0.55.4] - 2026-08-31

### Added
- The Workledger Helm chart is now published as a release asset. Deploy on Kubernetes against your own PostgreSQL, with a values schema, per-value documentation, an optional migration hook, and restricted Pod Security defaults.

### Fixed
- The container image no longer refuses a valid license after a key rotation. Both published architectures accept a valid license and are verified on their own hardware before release. Expired licenses are still refused.

### Note
- This release supersedes 0.55.0 through 0.55.3, which were tagged but never published. Install 0.55.4.

## [0.55.3] - 2026-08-30

### Note
- The OCI image index for this tag published. The final GitHub Release job failed during public-distribution validation, so no GitHub Release, binaries, or chart asset was published for this tag.

### Known issue
- The released arm64 image has not yet been runtime-proven with its release verifier. Treat it as unverified until exact-digest validation is published.

## [0.55.2] - 2026-08-30

### Added
- The Workledger Helm chart is now published as a release asset. Deploy on Kubernetes against your own PostgreSQL, with a values schema, per-value documentation, an optional migration hook, and restricted Pod Security defaults.

### Note
- The 0.55.0 and 0.55.1 tags had OCI image indexes but no GitHub Release or binary/chart assets. The 0.55.2 OCI image index also published, but its final GitHub Release and assets did not.

### Known issue
- The released arm64 image has not yet been runtime-proven with its release verifier. Treat it as unverified until exact-digest validation is published.

## [0.55.1] - 2026-08-30

### Added
- A Helm chart for deploying Workledger on Kubernetes against your own PostgreSQL, with a values schema, per-value documentation, an optional migration hook, and restricted Pod Security defaults.

### Note
- The 0.55.0 tag had an OCI image index but no GitHub Release or binary/chart assets. The 0.55.1 OCI image index also published, but its final GitHub Release and assets did not.

### Known issue
- The released arm64 image has not yet been runtime-proven with its release verifier. Treat it as unverified until exact-digest validation is published.

## [0.55.0] - 2026-08-29

### Added
- Self-hosted Kubernetes deployments can use a dependency-free Helm chart with immutable image selection, existing Secret references, fixed restricted Pod Security controls, external PostgreSQL, health and license-aware readiness checks, an optional migration preflight, and explicit retained-state cleanup.
- The public distribution now carries the maintained release history and the tested standard-library Python HTTP API quickstart, with a release-time drift check that fails before publication when those mechanical artifacts are stale.

## [0.54.2] - 2026-08-28

### Note
- This release supersedes 0.54.0 and 0.54.1, which were tagged but never published. Install 0.54.2 — it contains the same changes.

## [0.54.1] - 2026-08-28

### Note
- This release supersedes 0.54.0, which was tagged but never published. If you were waiting on 0.54.0, install 0.54.1 instead — it contains the same changes.

## [0.54.0] - 2026-08-28

### Added
- Releases can include an immutable multi-architecture container image designed for non-root, read-only operation under enforced Kubernetes restricted Pod Security. Operators can mirror the complete platform index and deploy its exact digest while keeping only the documented state and temporary paths writable.
- The authenticated HTTP API now exposes a machine-readable OpenAPI 3.1 contract and a dependency-free Python quickstart for safe create, get, claim, note, update, and close flows. The contract is checked against all 146 literal `/api/v1` registrations and validates the lifecycle responses used by integrations.

### Fixed
- The Python quickstart now protects both bearer tokens across redirects, inherited proxy settings, diagnostics, malformed responses, and unsafe plaintext origins while handling uncertain mutations without blind non-keyed retries. During the documented retry-retention window, restarting a completed example reuses the matching work order only to read its evidence; indefinite recovery uses the returned work-order ID.
- Webhook administration now checks administrator authority before exposing whether webhook storage is enabled.
- Container release verification now checks licensed readiness on both published architectures, proves restricted Pod Security enforcement, excludes nested operator credentials from the build context, and runs the exact-tag proof and public-release safety check before serialized immutable publication.

## [0.53.3] - 2026-08-26

### Fixed
- Webhook notifications that were already accepted are no longer lost when the server restarts. Previously a routine restart could drop deliveries that were mid-retry, so a subscriber would silently never receive them. Deliveries now complete their full retry schedule before shutdown finishes, and shutdown still returns within a bounded time rather than waiting indefinitely on an unreachable endpoint.

### Note
- This release supersedes 0.53.2, which was tagged but never published. If you were waiting on 0.53.2, install 0.53.3 instead — it contains the same fix.

## [0.53.2] - 2026-08-24

### Fixed
- Webhook notifications that were already accepted are no longer lost when the server restarts. Previously a routine restart could drop deliveries that were mid-retry, so a subscriber would silently never receive them. Deliveries now complete their full retry schedule before shutdown finishes, and shutdown still returns within a bounded time rather than waiting indefinitely on an unreachable endpoint.

## [0.53.1] - 2026-08-16

### Fixed
- Removing a project relationship now works when that relationship is actually in use. The safety check that confirms your work orders keep a valid project could fail on exactly the setups the correction was meant to fix, blocking the change. The check still refuses corrections that would leave work orders without a project.

## [0.53.0] - 2026-08-16

### Added
- Project identity can now be corrected, not only declared. If a project was set up with the wrong relationship to another — for example recorded as the same project when it is a separate customer-facing surface — you can now remove that relationship through the CLI instead of editing the database by hand. Removing one relationship leaves the others untouched.
- Corrections are refused when they would leave work orders without a repository, owner, or branch. The command tells you which work orders are affected rather than silently detaching them.

### Changed
- Identity changes are applied as a single transaction, so a failure part-way through no longer leaves a project half-updated.

## [0.52.0] - 2026-08-15

### Fixed
- Creating your first work order no longer looks like an error. A successful create previously led with an `[INVALID]` label, showed a cost estimate you did not ask for, and asked for a file list even when you were not working in a repository. It now reports success plainly.
- Upgrading is safe from older versions. Clients older than 0.51 could fail to read work orders, and — more seriously — could report a write as failed when it had actually been saved, so retrying created a duplicate. Older clients are now served a compatible response, and unknown fields from a newer server are ignored instead of breaking the read.
- Work orders read reliably over HTTP. Some records could fail verification on read through no fault of the data, and the same record could fail differently depending on which command you used. Records now verify consistently across every command.
- An invalid pricing override file now reports a clear error instead of crashing.

## [0.51.0] - 2026-08-12

### Changed
- When a work order cannot be read, the tools now tell you which one. An
  integrity mismatch previously reported only two long checksums, which said
  that something disagreed but not what — enough to know you had a problem,
  not enough to act on it. The mismatch now names the specific field that
  disagrees. Nothing about what is checked has changed; only what you are told
  when a check fails.
- One unreadable work order no longer blocks completion of unrelated work in
  the same project. A project-wide scan that meets a row it cannot read now
  reports that row by name, completes over the rest, and records on the
  completed work order exactly which rows were skipped — so a partial result
  can always be told apart from a full one afterwards. Genuine reasons to
  refuse completion still refuse.
- The health check reports unreadable work orders directly, so you find out
  before the condition blocks a release rather than at the moment you try to
  close something.

### Fixed
- The local pre-push check no longer lets a push through when it is
  interrupted. Stopping the check, or the check being stopped for you, now
  cancels the push instead of quietly allowing it. If the check runs out of
  time it still allows the push and now says so plainly, including the time
  limit it applied, because your continuous integration runs the same check
  again. The check is also bounded so it cannot occupy your machine
  indefinitely.
- A write that is refused no longer leaves the work order looking claimed. When
  a change was rejected after the system had briefly taken the work order on
  your behalf, that hold could survive the rejection — so the record showed
  someone working on it when nothing had happened. The hold is now released
  along with the change it belonged to. This matters because a work order held
  by an operation that never landed looks exactly like abandoned work, and
  sends whoever looks next in the wrong direction.
- A completed work order and its record of what was skipped are now written
  together, so the two can never disagree about the same completion.
- Alternate addresses for the same repository are verified before that
  repository is trusted, closing a case where a differently-configured address
  could satisfy a check it should not have.
- Provenance checks follow files that were renamed or moved, instead of
  reporting against a path that no longer exists.
- The health check and the completion process now agree on which states count
  as finished, so the same work order is not described differently depending on
  which one you ask.

### Compatibility
- No action required. Existing clients and stored records are unaffected.

## [0.50.1] - 2026-08-10

### Fixed
- Some work orders could not be read at all, and the same records blocked
  completion of unrelated work in the same project. A record could be stored
  perfectly and still fail its own integrity check, because the check depended
  on a detail of the machine that produced it rather than on the record alone.
  Anything holding such a record now reaches the same verdict, so those records
  read normally again and the work they were blocking can complete.
- No records were damaged and none were altered to fix this. The affected ones
  were intact the whole time; only the check disagreed with itself.

### Compatibility
- No action required, and no coordinated upgrade. Records that read correctly
  before are unaffected and produce an identical integrity value. Only the
  records that were already failing change, and they change to working.

## [0.50.0] - 2026-08-08

### Changed
- The grace period after a licence expires is now set deliberately rather than
  by accident. Paid keys already carry a short extension inside the key itself,
  which meant the real window was longer than either number suggested. A paid
  licence now has a seven-day total window from the end of your billing period
  before the service stops serving. Trial and free keys, which carry no such
  extension, keep the full seven days after their stated expiry date. Nothing
  about enforcement changes: the service still keeps running throughout the
  window and still tells you plainly that you are in it and when it ends. A key
  that was never valid gets no grace at any point, exactly as before.
- If your API key is scoped to a project that is also known by another name,
  you now see that project's work orders instead of an empty list. Projects can
  carry alternate names from renames or historical usage; a key scoped to one
  of those names previously returned nothing for work stored under the
  project's main name, which looked like missing data rather than a naming
  mismatch. The service resolves those names on its side, so a key can only
  ever see the projects it was already entitled to see.
- Complexity routing information returned to agent tooling now says where it
  came from — whether it was set explicitly on the work order, worked out from
  the work order's shape, or unavailable. A default value was previously
  indistinguishable from a genuine result, so tools could route work at the
  wrong size without any sign that the number was a placeholder. The
  classification an execution attempt ran under is also now recorded with that
  attempt, so a later reading reflects the routing decision as it was made.

### Compatibility
- No action required. The storage change is additive and applies itself on
  upgrade; existing records and older clients are unaffected.

## [0.49.0] - 2026-08-07

### Added
- An expired licence no longer cuts you off the moment it lapses. A licence
  that was valid and has just passed its expiry date now enters a bounded
  grace period during which the service keeps running normally, and the health
  endpoint says plainly that you are in that window and when it ends. That
  gives you time to install a new key without an interruption, and it makes the
  reason obvious instead of leaving you to guess at an outage. Enforcement is
  unchanged once the window closes, and a licence that was never valid — a
  corrupted, mistyped, or not-yet-active key — gets no grace at any point.
- You can now inspect and repair execution records from the command line,
  including across every project at once, without needing the API. Inspection
  reports counts and separates the two kinds of problem record, because they
  need different handling. Projects that cannot be read are named rather than
  quietly skipped, so a partial scan is never mistaken for a clean result.
  Repair is a separate, deliberate command that requires a reason, and it
  offers a preview mode that shows exactly what would change while writing
  nothing.

### Fixed
- One unreadable record no longer blocks unrelated work. Reviewing a change
  used to fail completely if it happened to reach a single record that could
  not be read, even when that record belonged to a different project and had
  nothing to do with the change. Such records are now reported by name and the
  rest of the review continues. A record that cannot be read is never treated
  as though it passed.
- Deployments no longer fail on a healthy release. A verification step compared
  the wrong thing and reported failure even when the deployment had succeeded
  and the service was running correctly — after the release had already gone
  out. Machines that are stopped are now skipped rather than misread, at least
  one running machine must still pass the check, and when the earlier setup
  step does fail it now says why instead of reporting a bare failure.
- Marking work as ready to land now explains what it needs. The refusal
  previously described where the system had looked rather than what you had to
  provide, which sent operators hunting in the wrong place. It now names the
  evidence that satisfies it, and accepts a commit you have already linked
  instead of asking you to supply the same details twice. The evidence
  requirement itself is unchanged.

## [0.48.0] - 2026-08-04

### Added
- Your deployment now tells you whether it can actually verify a licence. The
  health endpoint reports this directly, and a deploy stops rather than
  completing if the backend it just published cannot verify — including when a
  licence key was mistyped or truncated. Previously a deployment that could not
  verify looked identical to a healthy one from the outside.
- Deployments now confirm activation against the instance they just released,
  waiting for the rollout to finish before checking. A deploy can no longer
  report success by reaching a machine still running the previous licence.
- You can now list and repair execution records that were left in a
  contradictory state by an earlier defect — marked finished while still
  reporting as running. Listing them no longer fails, repair is explicit and
  audited, and records that completed correctly cannot be altered.

### Fixed
- An expired licence no longer takes the service down silently. It now reports
  the reason on its health endpoint instead of failing to start, and recovers on
  its own once a valid licence arrives — no restart needed. Refusing a licence
  also can no longer leave the service listening more openly than it would with
  a valid one.
- Work-execution records are now written completely or not at all. A record can
  no longer end up marked finished while still reporting as running, and the
  response you get back always matches what was stored.
- Bulk work-order updates now run through the same safety checks as single
  updates, so an update based on a stale read is refused rather than applied to
  a record that changed underneath it.
- Adding a note is now safe to retry. If the connection drops before you see a
  response, retrying returns the original note instead of creating a duplicate
  or losing the write.

## [0.47.1] - 2026-07-31

### Improved
- You can now see a work order's complexity level directly — not just the
  suggested model. The level shows up when you look up a work order, review its
  detail, check status, or plan, so it's clear at a glance how heavy a piece of
  work is before you assign it. When the level was inferred rather than set, that
  is shown honestly instead of being presented as a confirmed value.

### Fixed
- The local, offline-capable store is more robust when its license has lapsed and
  is later restored: it recovers cleanly, never leaves its data half-migrated if
  something is interrupted mid-recovery, and stays safe under concurrent shutdown.
  A restored license reconnects to exactly the file you were working on.

## [0.47.0] - 2026-07-28

### Added
- Automated work-order verification can now reopen a work order whose commit is
  no longer reachable, even when someone else holds it — through a single
  dedicated, separately-authorized path. Only a credential explicitly granted
  this permission can perform the reopen; an ordinary write or admin key cannot,
  and the permission survives key rotation. Every reopen records who did it, why,
  and the evidence behind it.

### Improved
- The automated completion pipeline is more reliable under failure: a reopen now
  either fully lands with its audit record in one step or fails cleanly and
  surfaces the error — it can no longer leave a work order half-changed if a
  network call is interrupted. The same safety rules apply identically across the
  command line, the HTTP API, and agent tools.

## [0.46.1] - 2026-07-24

### Fixed
- Closing or completing a work order now behaves identically whether you use the
  command line, the HTTP API, or an agent tool — the same safety checks, the same
  override rules, and the same audit record apply on every path. Overriding a
  blocked work order requires supplying the operator reason in the same action; a
  reason left over from an earlier edit can no longer stand in for it.
- When the shared backend is slow to respond, diff-time checks fall back to your
  validated local copy so you still see every finding, while genuine connection
  and authentication failures are still reported loudly instead of being masked.

## [0.46.0] - 2026-07-23

### Added
- Faster, more predictable reads during the working day. Listing clusters,
  looking up work orders by commit, discovering projects, and planning are now
  answered by the backend in one request instead of many round trips, so large
  workledgers stay responsive and results are never silently cut off at a page
  boundary. A scheduled health probe measures read and write latency during
  working hours and records the evidence, so "stable" is something you can see,
  not assume.

### Fixed
- Status and priority totals are now counted across your whole work-order set,
  not just the first page — so the numbers you see are the real totals.
- Reads no longer hang indefinitely on a slow backend; a stalled scan returns
  control instead of blocking other reads.
- When the backend is briefly unreachable, read-only commands can fall back to a
  local mirror for DNS/connection/timeout errors while still failing loudly on
  auth errors and never allowing a write against the mirror.
- Changing a work order's linked commit evidence is now atomic: the change and
  its audit record are saved together or not at all, and the commit that proves
  a work order's completion can no longer be removed. Looking up work orders by a
  short commit prefix returns a clear "too many matches, refine the prefix" error
  instead of an incomplete result.

## [0.45.3] - 2026-07-22

### Fixed
- A work order that is ready to land but still carries a hard block can now be
  closed with an operator override note, and clearing a hard block is recorded
  reliably — a work order whose blocks were legitimately cleared no longer gets
  stuck unable to reach done. The safeguards are unchanged: a real, unresolved
  block still blocks closure.

## [0.45.2] - 2026-07-22

### Added
- License enforcement is now consistent across every way you use Hiveram — the
  CLI, the MCP integration, the HTTP API, and the server all apply the same
  check in one place, so there are no gaps where a write could slip through
  unlicensed. When a license is missing, expired, or can't be verified, writes
  are refused with a clear, machine-readable reason and exit code — but reads
  and health checks keep working, so an expired license can never take your
  instance down.

### Fixed
- Wrapping the store with the license check no longer changes any unrelated
  backend behavior — status, history, batch updates, and search all behave
  exactly as before; only unlicensed writes are refused.
- The offline mirror now publishes its data and metadata together as one atomic
  switch, so an interrupted refresh can never leave you reading a new database
  paired with stale metadata.
- Read-only operations (including a dry-run link-commit) continue to work under
  an expired license, so you can still inspect your work orders while sorting
  out licensing.

The completion-integrity improvements (work orders reaching "done" on their own,
visibility into anything stuck) shipped in 0.45.1.

## [0.45.1] - 2026-07-21

### Added
- Finished work now reaches "done" on its own. When an agent completes a work
  order and the evidence is verified and landed, the work order is promoted
  automatically — on merge, on a schedule, and via a manual recovery run — so
  completed work no longer sits stranded in a holding state waiting for someone
  to run a command by hand. The automation only ever runs the authorized
  promoter; it never bypasses the checks that make "done" trustworthy.
- See what's stuck before it piles up. Status and stats now report how many work
  orders have been waiting in a holding state past a threshold, and how long the
  oldest has waited, so completion drift is visible early instead of
  accumulating silently.

### Fixed
- An out-of-date client can no longer overwrite server-computed fields.
  Readiness, blockers, and quality shown for a work order are held to the
  server's value when you're connected to a hosted backend, so a stale or
  version-skewed client cannot clobber them. Version and commit are now visible
  on the health endpoint so version skew is easy to spot.
- Automatic promotion is stricter about proof. A work order is only promoted
  when the verification result itself proves the commit is reachable and the
  identity is confirmed; a passing-but-incomplete result reopens the work order
  instead of closing it.
- Bulk status changes now honor the same rules as single updates. Updating many
  work orders at once against a local backend can no longer force an invalid
  status change that the normal, one-at-a-time path already rejects.

## [0.45.0] - 2026-07-20

### Added
- Find the next independent chunk of work in one command: `workledger clusters
  --in-flight <ids>` hides the group already being worked (and anything that
  overlaps or depends on it) and shows the next most important cluster that is
  safe to start in parallel.
- Close a work order on a green build without a manual override, even when the
  hosted backend can't reach your CI provider itself: a signed, identity-bound
  confirmation from your side is accepted and recorded with who confirmed it and
  the exact commit that landed. A backend that can verify on its own stays the
  authority, so nothing weakens the check — it just removes a needless override
  step when the backend has no line of sight to CI.

## [0.44.3] - 2026-07-20

### Fixed
- Faster search on the hosted backend: search and find-similar no longer make
  redundant follow-up requests for each result, so results come back with
  noticeably less latency and less load on the service.

## [0.44.2] - 2026-07-20

### Changed
- Work-order search is faster: a search that scans many candidates now completes
  in far fewer database round-trips, returning the same results with less load on
  your database.

### Fixed
- Steadier under load: the database connection pool is now sized for real
  concurrency (tunable with `WORKLEDGER_DB_MAX_CONNS`) and every query and request
  runs under a bounded timeout, so a busy backend no longer starves on a small
  fixed pool.
- No more cold-start failures: the first request after your database has been idle
  now waits for it to wake up instead of failing outright.
- More reliable over the network: a dropped connection on a read is retried
  automatically, and a backend that stays unreachable now reports a clear error
  and a non-zero exit code instead of silently returning nothing.
- Linking a commit to a work order you already hold no longer needs an override —
  your identity is resolved automatically, while a mismatched actor is still
  blocked with a clear message.
- Terminal sync rows that cannot be verified can now be cleared without a live
  backend connection, and the status output shows the exact recovery command.
- `workledger projects` now honors `--format json` and `--format tsv`, and
  rejects an unsupported format instead of quietly emitting plain text.

## [0.44.1] - 2026-07-18

### Changed
- Work orders are now validated more strictly at write time: an invalid work
  classification is rejected before it is stored, so bad data cannot enter the
  ledger through any interface (CLI, API, or offline sync).
- Work-order intent and history are preserved more durably across syncs,
  strengthening the long-term integrity and auditability of your records.
- Setting a work order's complexity now reliably persists the value you choose,
  and an explicit choice is kept instead of being overwritten.
- Status and closure errors now name the governing policy and the exact
  remediation, so a refused transition tells you how to proceed.

### Added
- You can now supply a note body from a file, making it easier to attach longer
  or pre-written notes to a work order.

### Fixed
- Recovering a blocked work order can clear its reason codes in a single atomic
  update, and a work order that needs rework is steered to an auditable held
  state instead of being marked complete.

## [0.44.0] - 2026-07-14

### Changed
- The work-order quality gate now reports a clear readiness state — `READY`,
  `READY_WITH_WARNINGS`, `NEEDS_UPSPEC`, or `INVALID` — instead of a single numeric
  score, so a spec with a serious gap can no longer average its way to green. Each
  issue is a typed finding that names what is wrong, where, and how to fix it.
- New advisory checks surface common gaps before a spec reaches a builder: vague or
  unverifiable acceptance wording, references to files or work orders the spec does
  not declare, and high-complexity work orders that lack decomposition. These are
  advisory-only in this release — they inform, they do not block.
- Parallel-planning output now highlights independent work-fronts you can run at the
  same time. It is advisory only and does not change what gets selected.

### Fixed
- Removing a single work-order relationship now works over the hosted API, matching
  local behavior.
- Work-order reads now consistently show claim state, cancellation reason, and
  relationships across the CLI, API, and tools — a work order that is claimed or
  cancelled no longer reads as unclaimed or reason-less depending on which surface
  you use.
- A batch work-order update over the tool interface no longer stalls for several
  minutes before responding.

## [0.43.2] - 2026-07-11

### Added
- A new `--no-outbox` flag skips the passive offline-queue status check for latency-sensitive and headless callers, so a slow or stale local queue no longer adds time to every command.

### Changed
- Work order changes over the command line, HTTP API, and MCP now go through one shared path, so claim, closure, and audit behavior is identical no matter which surface you use.

### Fixed
- Invalid requests — a missing project, a non-positive id, a missing claim actor, or bad relationship ids — now return a clear `400 Bad Request` instead of a `500` server error.
- Audit and closure notes that fail to save are now reported instead of being silently dropped, so a rejected note can no longer look like a clean success.

## [0.43.1] - 2026-07-09

### Fixed
- Listing work orders over the HTTP API with quality, complexity, or title filters now pages through large projects instead of stalling.

## [0.43.0] - 2026-07-09

### Added
- A new check can validate just the changed lines of a commit or diff across Go,
  Swift, TypeScript, Python, and shell — scoped to what actually changed, so it runs
  fast on large or mixed-language repositories and skips generated files
  automatically.
- `reaped` lists work orders that were auto-cancelled by TTL, with a stable age, so you can review and reopen them.

### Fixed
- TTL auto-cancel now measures from last meaningful activity, not creation time, and a reopened work order stays open instead of being swept again on the next tick.
- Reopening a work order out of a terminal state clears its old cancel reason, so it never carries a stale "why it was cancelled".
- Closure and transition errors now name the exact next command (inspect / retry / land) instead of a bare rejection.
- Outbox `status` and `list` honor `--format oneline|tsv` and keep their advisory banner on stderr, so read output stays parseable.

## [0.42.0] - 2026-07-08

### Added
- `next` and `context` now show parallel-dispatch lanes when two or more independent work orders are ready, so a safe parallel set is visible at a glance.
- `next-parallel` leads with the runnable clusters and summarizes the rest, with full detail behind `--verbose`; `--wos` explains pairwise write-path overlap for a set you supply.
- `guardrail worktree-clean`, with a sourced shell hook, detects and blocks a dirty branch switch in a marked shared checkout.

### Fixed
- `context` reports exact project, status, and priority totals while keeping output bounded.
- Outbox terminal-row pruning verifies the target write actually landed before dropping a row, so an unsynced change is never silently discarded.
- Creating a work order over MCP against the HTTP store now decodes correctly.

## [0.41.0] - 2026-07-07

### Added
- A new `status` command and `/status` API endpoint show velocity (closed in 7 and 30 days), remaining backlog by state, a runway estimate, and how long items have sat in holding states — so completion drift is visible instead of silent.
- `reconcile` finds and clears status-vs-git drift for work orders left in `ready_to_land` after a squash merge, so a merged item does not sit falsely open.
- `friction` records internal-tooling friction as tagged work orders and groups repeats by tool and error.
- `create` gains a strict contract mode that refuses work orders whose acceptance needs files missing from the write contract; the default stays advisory.
- `unlink-commit` removes or atomically replaces a stale linked commit with a required audit reason.

### Fixed
- `unlink-commit` refuses to strip the last linked commit from a done work order unless you pass an audited override, so a completion cannot be left with no evidence.
- Rocket-ready file matching accepts dot-prefixed directories and basename-only references when they unambiguously point at a contracted file.
- `target-plan` resolves an explicit work order by id even on large projects, and tells backend timeouts apart from empty results.

## [0.40.0] - 2026-07-04

### Fixed
- Over MCP, `add_relationship` now uses the `claim_actor` you pass. It was falling back to the connection's identity, so a note or edge could be recorded as `mcp` instead of the agent that made it; `claim_override` and its reason now reach the server too.
- An override with no reason is now rejected instead of being accepted with a filler reason. If you pass `claim_override` you must say why.
- Notes no longer have claim bookkeeping pasted into their text. The "who claimed this" record is kept as its own note, so the note you wrote is the note that's stored — over the command line, MCP, or the API.
- If a `create` or `link-commit` fails on a dropped connection or a 5xx, the command checks whether the write actually landed before it reports back. If it landed you get the existing item; if it didn't you get a clear "safe to retry" message instead of a guess. The landed check matches on the id or a create fingerprint, never on title alone.
- `target-plan --wo N` now finds a work order by its id even on large projects, where it previously reported "not found" past the default page size (while `detail N` found it).
- Readiness checks for "acceptance mentions tests/CHANGELOG/a file" now look at the work order's declared write paths when it has them, so a read-only or generated path doesn't get flagged as missing.

## [0.39.0] - 2026-07-03

### Added
- A blocked work order now says why it's blocked — waiting on a dependency, waiting for its commit to land, or manually held — in `get` and the compact list/search output.
- `workledger update --delete-section` removes a section explicitly. Deleting a section used to mean passing an empty `--section key=`, which was easy to trigger by accident (a shell-mangled value would wipe content). That empty form is now rejected; use the flag when you mean to delete.

### Changed
- Creating a work order with the same title as an existing active one is refused unless you pass `--force`. This catches accidental duplicates; when a duplicate is intentional, `--force` creates it and records why. Concurrent creates of the same title can't both slip through.

### Fixed
- Merging and updating work orders enforce ownership and removal rules in one atomic step, so a merge can't partially apply or bypass a protected work order under concurrency.
- Readiness checks no longer flag a work order for referencing a data or cross-project file it only reads — only files it's actually meant to edit.

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
