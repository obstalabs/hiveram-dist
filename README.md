<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logo-dark.png">
    <source media="(prefers-color-scheme: light)" srcset="assets/logo-light.png">
    <img src="assets/logo-light.png" alt="hiveram" width="200">
  </picture>
</p>

# hiveram-dist

Distribution package for [Hiveram](https://hiveram.com) — agent coordination and execution intelligence. Pre-built `workledger` binaries, a public-safe skill pack, and an install script.

## What this is

Pre-built binaries, a public-safe skill pack, and an install script that bootstraps a workstation with a working Hiveram setup: the `workledger` binary on PATH, MCP server wiring for Claude Code by default, and the runtime surfaces needed for shared authoritative work or intentional portable handoff.

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

For the deeper product contract behind those operator surfaces, read
[Context Mobility and Deployment Topologies](docs/context-mobility.md). That
document explains the difference between NR-only, Hiveram-only, and hybrid
deployments, and it defines the authority-boundary promises each topology can
honestly make.

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

## Manual install

If you prefer not to pipe to bash:

```bash
# 1. Download the tarball for your platform
# macOS Apple Silicon
curl -LO https://github.com/obstalabs/hiveram-dist/releases/download/v0.15.0/workledger_0.15.0_darwin_arm64.tar.gz

# macOS Intel
curl -LO https://github.com/obstalabs/hiveram-dist/releases/download/v0.15.0/workledger_0.15.0_darwin_amd64.tar.gz

# Linux amd64
curl -LO https://github.com/obstalabs/hiveram-dist/releases/download/v0.15.0/workledger_0.15.0_linux_amd64.tar.gz

# 2. Verify checksum
sha256sum -c checksums.txt

# 3. Extract and install
tar -xzf workledger_*.tar.gz
sudo mv workledger /usr/local/bin/
chmod +x /usr/local/bin/workledger

# 4. Copy skills
for skill in workledger write-wo load-context wrapup save-memory; do
    mkdir -p ~/.claude/skills/$skill
    curl -fsSL -o ~/.claude/skills/$skill/SKILL.md             "https://raw.githubusercontent.com/obstalabs/hiveram-dist/main/skills/$skill/SKILL.md"
done

# 5. Configure connection details
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
