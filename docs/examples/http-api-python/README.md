# Python HTTP API quickstart

Python 3.10 or newer is required. The runnable standard-library example
performs one complete authenticated lifecycle with two distinct `write`
credentials:

1. the agent creates a keyed WO, claims it, moves it to `in_progress`, and
   appends keyed evidence;
2. a separately authenticated reviewer closes the no-code WO; and
3. the reviewer reads the notes, history, and exact note-idempotency binding.

Provision the agent key with an ID that exactly matches
`WORKLEDGER_AGENT_ID`. Provision a second key with a different ID for the
reviewer: the closure gate compares the authenticated reviewer key ID with the
recorded executor, so changing `claim_actor` in JSON cannot disguise a
self-close. Keep both one-time tokens in a secret manager and pass them only by
environment variable; the example validates them before constructing a request
and redacts both credentials from every diagnostic. It ignores inherited proxy
settings so the process environment cannot reroute a bearer-bearing request.
Plaintext HTTP is accepted only for the loopback hosts `localhost`,
`127.0.0.1`, and `::1`. Use an HTTPS origin for every remote tenant; the
example rejects remote HTTP, URL userinfo, queries, fragments, and base paths
before sending a bearer credential.

```bash
export WORKLEDGER_URL='http://localhost:8080'
export WORKLEDGER_PROJECT='chainwatch'
export WORKLEDGER_AGENT_ID='quickstart-agent'
export WORKLEDGER_AGENT_API_KEY='<agent write token>'
export WORKLEDGER_REVIEWER_API_KEY='<reviewer write token>'
export WORKLEDGER_RUN_ID='customer-sandbox-001'

python3 docs/examples/http-api-python/quickstart.py --help
python3 docs/examples/http-api-python/quickstart.py
python3 -m unittest docs/examples/http-api-python/quickstart_test.py
```

`WORKLEDGER_RUN_ID` becomes the bounded create and note retry identity. Reuse it
promptly to recover the same attempted lifecycle; choose a new run ID for an
intentional new WO, and persist the returned WO ID when recovery must outlive
the server's terminal-retention window. The example refuses every redirect
status before parsing its destination or forwarding a bearer credential. It
treats mutation redirects, transport failures, response-framing failures, HTTP
5xx responses, and invalid successful acknowledgements as ambiguous outcomes.
Only the keyed create and dedicated
`/note/idempotent` write receive one byte-equivalent replay; a non-keyed claim
or PATCH instead reads the WO and accepts only the already-observed target
state. If a prompt keyed replay returns an existing `done` WO, the example
performs evidence GETs without another claim, PATCH, or note.

Successful output contains identifiers and counts, but no credentials:

```json
{
  "created": true,
  "deduplicated": false,
  "history_entries": 4,
  "note_binding_verified": true,
  "note_id": 17,
  "notes_returned": 1,
  "status": "done",
  "wo_id": 42
}
```
