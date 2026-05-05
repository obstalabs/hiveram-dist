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

Pre-built binaries, a small public-safe skill pack, and an install script that bootstraps a workstation with a working Hiveram/workledger setup: binary on PATH, MCP server configured for Claude Code by default, and optional remote API connectivity to either a customer-hosted or Obsta-managed deployment.

Hiveram/workledger itself is not Claude-only. The same MCP server and CLI are
usable from any compatible agent surface, including Claude Code, Codex,
OpenCode, Cursor, Cline, Qwen, and other MCP-capable clients. The installer
automates Claude Code first because it is the safest default bootstrap path
today.

## What this is NOT

- Not the source code — that lives in the separate `workledger` source repository
- Not a framework or SDK — this is an installer
- Not a replacement for reading the docs at [hiveram.com](https://hiveram.com)

## Deployment modes

Hiveram can run in three common custody modes:

- **Local** — SQLite on your own machine, no remote ledger service required
- **Customer-hosted** — you run the Hiveram/workledger API and PostgreSQL in your own environment, then connect operators with `WORKLEDGER_URL` and `WORKLEDGER_API_KEY`
- **Obsta-managed** — Obsta runs the remote service for you, and you connect to that endpoint with `WORKLEDGER_URL` and `WORKLEDGER_API_KEY`

Direct `WORKLEDGER_DSN` access is supported for self-hosted and admin workflows, but it is not the normal operator path for commercial use.

If you want to keep the ledger in your own infrastructure, start with the
[self-hosted deployment guide](docs/self-hosted.md). It explains the normal
remote path, backup expectations, and how Hiveram's PostgreSQL support boundary
maps to the public [PostgreSQL support matrix](docs/postgres-support.md).

## Quick install

```bash
curl -fsSL https://raw.githubusercontent.com/obstalabs/hiveram-dist/main/install.sh | bash
```

This will:
1. Download the `workledger` binary for your platform
2. Install 5 public-safe Claude Code skills
3. Configure the MCP server in Claude Code settings
4. Prompt for your Hiveram/workledger connection details and custody mode
5. Verify the binary, skills, and MCP wiring

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
curl -LO https://github.com/obstalabs/hiveram-dist/releases/download/v0.10.2/workledger_0.10.2_darwin_arm64.tar.gz

# macOS Intel
curl -LO https://github.com/obstalabs/hiveram-dist/releases/download/v0.10.2/workledger_0.10.2_darwin_amd64.tar.gz

# Linux amd64
curl -LO https://github.com/obstalabs/hiveram-dist/releases/download/v0.10.2/workledger_0.10.2_linux_amd64.tar.gz

# 2. Verify checksum
sha256sum -c checksums.txt

# 3. Extract and install
tar -xzf workledger_*.tar.gz
sudo mv workledger /usr/local/bin/
chmod +x /usr/local/bin/workledger

# 4. Copy skills
for skill in workledger write-wo load-context wrapup save-memory; do
    mkdir -p ~/.claude/skills/$skill
    curl -fsSL -o ~/.claude/skills/$skill/SKILL.md \
        "https://raw.githubusercontent.com/obstalabs/hiveram-dist/main/skills/$skill/SKILL.md"
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

# Optional: direct Postgres access for self-hosted or admin workflows only
# export WORKLEDGER_DSN='postgresql://...'
```

## Included skills

These shipped skills are intentionally public-safe. They teach how to use the
product surfaces without exposing Obsta's internal operating workflow.

The bundled skill files are optimized for Claude Code installation. The command
surface they describe is agent-neutral, and the same `workledger` MCP/CLI/API
flows work from other agent environments.

| Skill | Command | What it does |
|-------|---------|--------------|
| workledger | `/workledger` | Query, create, update, group, and inspect work orders |
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

Other agent clients can use the same binary and MCP server with their own local
configuration.

## Prerequisites

- [Claude Code](https://claude.ai/claude-code) installed for the automated setup path
- A Hiveram Pro trial or license key for commercial CLI use
- Either a Hiveram/workledger API endpoint plus API key for shared remote state, or a local-only SQLite evaluation flow
- Direct `WORKLEDGER_DSN` access only for self-hosted and admin setups

## Verify installation

After install, open a new terminal and run:

```bash
workledger version
```

Then activate your trial or license key:

```bash
workledger activate <your-license-key>
```

Start Claude Code in any project and run `/load-context` to verify the default
installed skill pack.

If you use another agent client, verify that it can:

1. run `workledger version`
2. connect to the `workledger serve --mcp` server
3. read project state through CLI or MCP

The canonical public product skill for `workledger` is bundled in this distribution at [skills/workledger/SKILL.md](skills/workledger/SKILL.md).

## License

Proprietary. This repository distributes Hiveram binaries, installer assets, and public-safe skills only. The Hiveram/workledger source code is private and is not distributed from this repository. See [LICENSE](LICENSE) for the distribution terms.
