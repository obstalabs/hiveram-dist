<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logo-dark.png">
    <source media="(prefers-color-scheme: light)" srcset="assets/logo-light.png">
    <img src="assets/logo-light.png" alt="hiveram" width="200">
  </picture>
</p>

# hiveram-dist

Distribution package for [Hiveram](https://hiveram.com) — agent coordination and execution intelligence. Pre-built `workledger` binaries, a hardened container image, a Helm chart for Kubernetes, a public-safe skill pack, and an install script.

## What this is

Pre-built binaries, a hardened multi-architecture container image, a Helm chart for Kubernetes, a public-safe skill pack, and an install script that bootstraps a workstation with a working Hiveram setup: the `workledger` binary on PATH, MCP server wiring for Claude Code by default, and the runtime surfaces needed for shared authoritative work or intentional portable handoff.

Hiveram/workledger is not Claude-only. The same CLI, HTTP API, and MCP server are usable from any compatible agent surface, including Claude Code, Codex, OpenCode, Cursor, Cline, Qwen, and other MCP-capable clients. The installer automates Claude Code first because it is the safest default bootstrap path today.

## What this is NOT

- Not the source code — that lives in the separate `workledger` source repository
- Not a framework or SDK — this is an installer and public operator surface
- Not a promise of silent sync between local experiments and a shared ledger
- Not a replacement for reading the docs at [hiveram.com](https://hiveram.com)

## Deployment modes

Hiveram can run in three common custody modes:

- **Local** — SQLite on your own machine, no remote ledger service required
- **Customer-hosted** — you run the Hiveram/workledger API and PostgreSQL in your own environment, then connect operators with `WORKLEDGER_URL` and `WORKLEDGER_API_KEY`
- **Obsta-managed** — Obsta runs the remote service for you, and you connect to that endpoint with `WORKLEDGER_URL` and `WORKLEDGER_API_KEY`

Direct `WORKLEDGER_DSN` access is supported for self-hosted and admin workflows, but it is not the normal operator path for commercial use.

## Runtime modes

Deployment mode answers where the ledger lives. Runtime mode answers which authority surface an operator is using right now.

- **Shared authoritative** — the normal mode for canonical writes, imports, notes, and closure evidence. Operators and agents point at the shared ledger and verify that they are on the expected authority surface before trusting results.
- **Local portable** — explicit local or disconnected operation for bounded handoff, airgapped work, or temporary offline execution. Useful on purpose, but not the same thing as shared state.

Hiveram supports portable reasoning and disconnected transfer as an explicit workflow. That means bounded bundles, checkpoints, and mission briefings can move across agents or environments, but returned results are still reviewed or applied against the canonical ledger instead of silently merging in the background. A senior agent can architect once, then many cheaper or specialized agents can execute from the same bounded truth without rediscovering the project.

If you want to keep the ledger in your own infrastructure, start with the [self-hosted deployment guide](docs/self-hosted.md). It explains the remote path, runtime modes, verification surfaces, and how Hiveram's PostgreSQL support boundary maps to the public [PostgreSQL support matrix](docs/postgres-support.md).

Deployment and integration references:

- [Container image facts](docs/container-image.md)
- [HTTP OpenAPI contract facts](docs/openapi.md)
- [Python HTTP API quickstart](docs/examples/http-api-python/README.md)

For the deeper product contract behind those operator surfaces, read
[Context Mobility and Deployment Topologies](docs/context-mobility.md). That
document explains the difference between NR-only, Hiveram-only, and hybrid
deployments, and it defines the authority-boundary promises each topology can
honestly make.

For the concrete handoff journey, read
[Operator Workflow for Portable Reasoning](docs/operator-workflow.md). That
guide covers WO-based, bundle-based, and checkpoint-based rehydration plus the
direct-apply, receipt, and branch-history return paths.

## Quick install

```bash
curl -fsSL https://raw.githubusercontent.com/obstalabs/hiveram-dist/main/install.sh | bash
```

This will:
1. Download the `workledger` binary for your platform
2. Install public-safe Claude Code skills
3. Configure the MCP server in Claude Code settings
4. Prompt for your Hiveram/workledger connection details and custody mode
5. Verify the binary, skills, and startup path for the selected runtime mode

Package managers:

```bash
# Homebrew
brew install obstalabs/tap/workledger

# Scoop
scoop bucket add obstalabs https://github.com/obstalabs/scoop-bucket
scoop install workledger
```

## Run the server

The commands above install the CLI. To run the ledger service itself, pull the
container image or deploy the Helm chart. Both are public: no registry
credentials, no account.

```bash
# Hardened container image, linux/amd64 and linux/arm64
docker pull ghcr.io/obstalabs/hiveram-dist:v0.55.6
```

The image is distroless, runs as a non-root user with a read-only root
filesystem, and is admitted under restricted Pod Security Standards. See
[container image facts](docs/container-image.md).

```bash
# Helm chart, attached to every release
curl -fsSLO https://github.com/obstalabs/hiveram-dist/releases/download/v0.55.6/workledger-0.55.6.tgz

helm install workledger ./workledger-0.55.6.tgz \
  --namespace hiveram \
  --set-string image.tag=v0.55.6 \
  --set-string secrets.existingSecret=workledger-runtime
```

The chart deploys the same image against PostgreSQL you manage. It creates no
Secret, Namespace, or cluster-scoped resource, and expects an existing Secret
holding the connection string, licence, and API keys. Start with the
[self-hosted deployment guide](docs/self-hosted.md).

## Manual install

If you prefer not to pipe to bash:

```bash
set -euo pipefail

# 1. Resolve the current strict-SemVer release and this machine's archive.
latest_url="https://github.com/obstalabs/hiveram-dist/releases/latest"
resolved_url="$(curl --fail --silent --show-error --location --output /dev/null --write-out '%{url_effective}' "$latest_url")"
release_tag="${resolved_url##*/}"
if [[ ! "$release_tag" =~ ^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$ ]]; then
    printf 'latest release is not strict vX.Y.Z SemVer: %s\n' "$release_tag" >&2
    exit 1
fi
version="${release_tag#v}"

case "$(uname -s):$(uname -m)" in
    Darwin:arm64) platform="darwin_arm64" ;;
    Darwin:x86_64) platform="darwin_amd64" ;;
    Linux:arm64|Linux:aarch64) platform="linux_arm64" ;;
    Linux:x86_64|Linux:amd64) platform="linux_amd64" ;;
    *) printf 'unsupported platform: %s\n' "$(uname -s):$(uname -m)" >&2; exit 1 ;;
esac

archive="workledger_${version}_${platform}.tar.gz"
download_url="https://github.com/obstalabs/hiveram-dist/releases/download/${release_tag}"

# 2. Download exactly the selected archive and its checksum manifest.
curl --fail --show-error --location --remote-name "${download_url}/${archive}"
curl --fail --show-error --location --remote-name "${download_url}/checksums.txt"

# 3. Select one exact lowercase SHA-256 row and verify it with the host tool.
if ! checksum_row="$(awk -v archive="$archive" '
    NF == 2 && $2 == archive && length($1) == 64 && $1 !~ /[^0-9a-f]/ { matches++; row=$0 }
    END { if (matches != 1) exit 1; print row }
' checksums.txt)"; then
    printf 'checksums.txt must contain one exact SHA-256 row for %s\n' "$archive" >&2
    exit 1
fi

if command -v sha256sum >/dev/null 2>&1; then
    printf '%s\n' "$checksum_row" | sha256sum --check -
elif command -v shasum >/dev/null 2>&1; then
    printf '%s\n' "$checksum_row" | shasum --algorithm 256 --check -
else
    printf 'install sha256sum or shasum to verify the release\n' >&2
    exit 1
fi

# 4. Extract into a temporary directory and install the verified binary.
extract_dir="$(mktemp -d)"
trap 'rm -rf "$extract_dir"' EXIT
tar -xzf "$archive" -C "$extract_dir"
sudo install -m 0755 "$extract_dir/workledger" /usr/local/bin/workledger
workledger version

# 5. Copy skills
for skill in workledger write-wo load-context wrapup save-memory; do
    mkdir -p ~/.claude/skills/$skill
    curl -fsSL -o ~/.claude/skills/$skill/SKILL.md             "https://raw.githubusercontent.com/obstalabs/hiveram-dist/main/skills/$skill/SKILL.md"
done

# 6. Configure connection details
mkdir -p ~/.workledger
cat > ~/.workledger/api-key.env << 'EOF'
export WORKLEDGER_URL='https://workledger.example.com'
# Legacy compatibility: WORKLEDGER_HOST also works for CLI and MCP, but URL is preferred.
export WORKLEDGER_API_KEY='ol_sk_...'
EOF
chmod 600 ~/.workledger/api-key.env
echo '[ -f ~/.workledger/api-key.env ] && source ~/.workledger/api-key.env' >> ~/.zshrc
```

## Shared authoritative startup

Use this when the machine should talk to the canonical connected ledger:

```bash
workledger status --json --resolved
workledger serve --mcp --mcp-mode shared-authoritative
```

Look for a shared `mode`, `store_label`, and `store_fingerprint` before trusting writes, imports, or bundle apply operations.

## Current queue from the tip

When the question is "what should we do from here?" use the current-tip queue
and lane surfaces before falling back to raw backlog order:

```bash
workledger queue myapp --target current
workledger lanes myapp --target current
```

`queue` gives the operator the actionable `now`, `next`, `later`, `blocked`,
and deferred buckets. `lanes` shows the active lane, current tip, and the work
that is real but off-lane. That keeps fresh sessions from reconstructing
execution order from a giant open-WO list.

## Scaffold review and continuation

Once the current tip is visible, inspect the recent scaffold path that supports
it before starting a fresh agent session:

```bash
workledger trellis read --project myapp --latest 5
workledger gradient detect --project myapp --latest 10
```

Those surfaces recover the recent decisions, constraints, evidence, and
direction that still matter around the tip. If a proposed change needs review
with backing context instead of prose-only comparison, use:

```bash
workledger trellis diff --base-file base.yaml --candidate-file candidate.yaml --context-file context.yaml --format markdown
```

This is the product surface for continuation without transcript replay: current
tip, attached scaffold path, reviewable changes with context, and enough claim
weight to tell canonical guidance from tentative ideas.

## Local portable startup

Use this when the machine is intentionally offline, airgapped, or preparing a bounded handoff:

```bash
workledger serve --mcp --mcp-mode local-portable
workledger mirror pull
```

Local portable mode is for explicit local work, bundle export, checkpoints, and delayed apply workflows. It should not be treated as silent shared state.

## Portable reasoning handoff

Hiveram can move bounded reasoning instead of replaying a giant transcript:

```bash
workledger briefing wo myapp 118
workledger checkpoint create myapp --summary "before external handoff"
workledger bundle export myapp 118 --out task.wlbundle
workledger bundle inspect task.wlbundle
```

A reply bundle can come back later and be applied against the canonical ledger under review:

```bash
workledger bundle apply reply.wlbundle
```

That workflow is explicit by design. Portable reasoning is a controlled handoff path, not background merge magic.

## Topology fit

Hiveram supports three legitimate product shapes:

- **NR-only** for live-window shaping and bounded execution hygiene
- **Hiveram-only / workledger-only** for durable shared truth, portable
  bundles, checkpoints, and mission briefings
- **Hybrid** for teams that want both a canonical work graph and a cleaner live
  execution window

The topology matrix, trust-floor rules, and demo/roadmap guidance live in
[docs/context-mobility.md](docs/context-mobility.md).

The step-by-step operator journey for handoff and rehydration lives in
[docs/operator-workflow.md](docs/operator-workflow.md).

## Airgapped mirror and outbox transfer

When a machine is fully disconnected, Hiveram now has an explicit file-copy
transport for mirror snapshots and queued shared mutations:

```bash
workledger mirror export mirror.wlxfer
workledger outbox export queued-mutations.wlxfer

# on a connected machine pointed at the authoritative shared ledger
workledger outbox apply-bundle queued-mutations.wlxfer --receipt-out queued-mutations.receipt.wlxfer

# back on the disconnected machine
workledger outbox import-receipt queued-mutations.receipt.wlxfer
```

These `.wlxfer` bundles carry:

- a manifest,
- per-file SHA-256 checksums,
- an intended target fingerprint for outbox requests,
- authoritative replay receipts with returned `server_wo_id` values for create operations.

That keeps airgapped workflows explicit and reviewable instead of pretending a
background sync channel exists.

## Included skills

These shipped skills are intentionally public-safe. They teach how to use the product surfaces without exposing internal Obsta operating workflow.

The bundled skill files are optimized for Claude Code installation. The command surface they describe is agent-neutral, and the same `workledger` CLI, API, and MCP flows work from other agent environments.

| Skill | Command | What it does |
|-------|---------|--------------|
| workledger | `/workledger` | Query, create, update, group, inspect, and hand off work with mode-aware guidance |
| write-wo | `/write-wo` | Turn a feature brief into one or more well-scoped work orders |
| load-context | `/load-context` | Orient an agent on the current repo and open work orders |
| wrapup | `/wrapup` | Close out completed work orders and record delivery evidence |
| save-memory | `/save-memory` | Save durable project context through workledger memory surfaces |

## Platforms

| OS | Architecture | Status |
|----|-------------|--------|
| macOS | Apple Silicon (arm64) | Supported |
| macOS | Intel (amd64) | Supported |
| Linux | amd64 | Supported |
| Linux | arm64 | Supported |
| Windows | amd64 | Supported via Scoop |
| Windows | arm64 | Supported via Scoop |

## Agent support

Hiveram/workledger is designed for multi-agent use:

- Claude Code
- Codex
- OpenCode
- Cursor
- Cline
- Qwen
- other MCP-capable agent clients

Today this repo ships:

- automatic Claude Code MCP setup
- a public-safe Claude skill pack
- the canonical `workledger` binary and API/MCP surface used by all agents

Other agent clients can use the same binary and MCP server with their own local configuration.

## Prerequisites

- [Claude Code](https://claude.ai/claude-code) installed for the automated setup path
- A Hiveram Pro trial or license key for commercial CLI use
- Either a Hiveram/workledger API endpoint plus API key for shared authoritative work, or a local SQLite path for portable/offline work
- Direct `WORKLEDGER_DSN` access only for self-hosted and admin setups

## Verify installation

After install, open a new terminal and run:

```bash
workledger version
workledger status --json --resolved
```

Then activate your trial or license key:

```bash
workledger activate <your-license-key>
```

If you are connecting to a shared remote ledger, verify that your surfaces are
pointed at the same store before debugging missing WOs or relationship errors:

```bash
# CLI
workledger status --json --resolved

# HTTP
curl -fsS "$WORKLEDGER_URL/healthz"
```

If your agent uses MCP, compare those results with the MCP
`workledger_backend_info` tool. The important fields are:
`store_fingerprint`, `store_label`, `store_kind`, and `mode`. Different
fingerprints mean you are looking at different stores.

Start your preferred agent client and verify that it can:

1. run `workledger version`
2. connect to `workledger serve --mcp` in the intended mode
3. report the expected `mode`, `store_label`, and `store_fingerprint`
4. read project state through CLI, API, or MCP

The canonical public product skill for `workledger` is bundled in this distribution at [skills/workledger/SKILL.md](skills/workledger/SKILL.md).

## License

Proprietary. This repository distributes Hiveram binaries, installer assets, and public-safe skills only. The Hiveram/workledger source code is private and is not distributed from this repository. See [LICENSE](LICENSE) for the distribution terms.
