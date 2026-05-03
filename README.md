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

Pre-built binaries, a small public-safe skill pack, and an install script that bootstraps a workstation with a working Hiveram/workledger setup: binary on PATH, MCP server configured for Claude Code, and optional remote API connectivity.

## What this is NOT

- Not the source code — that lives in the separate `workledger` source repository
- Not a framework or SDK — this is an installer
- Not a replacement for reading the docs at [hiveram.com](https://hiveram.com)

## Quick install

```bash
curl -fsSL https://raw.githubusercontent.com/obstalabs/hiveram-dist/main/install.sh | bash
```

This will:
1. Download the `workledger` binary for your platform
2. Install 5 public-safe Claude Code skills
3. Configure the MCP server in Claude Code settings
4. Prompt for your Hiveram/workledger connection details
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

# 5. Configure secrets
mkdir -p ~/.workledger
cat > ~/.workledger/api-key.env << 'EOF'
export WORKLEDGER_DSN='postgresql://...'
export WORKLEDGER_API_KEY='wl_...'
EOF
chmod 600 ~/.workledger/api-key.env
echo '[ -f ~/.workledger/api-key.env ] && source ~/.workledger/api-key.env' >> ~/.zshrc
```

## Included skills

These shipped skills are intentionally public-safe. They teach how to use the
product surfaces without exposing Obsta's internal operating workflow.

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

## Prerequisites

- [Claude Code](https://claude.ai/claude-code) installed
- A Hiveram Pro trial or license key for commercial CLI use
- A Hiveram/workledger API endpoint and API key for remote shared state

## Verify installation

After install, open a new terminal and run:

```bash
workledger version
```

Then activate your trial or license key:

```bash
workledger activate <your-license-key>
```

Start Claude Code in any project and run `/load-context` to verify the full stack.

The canonical public product skill for `workledger` is also published in the
source repository at [docs/SKILL.md](https://github.com/obstalabs/workledger/blob/main/docs/SKILL.md).

## License

[Business Source License 1.1](LICENSE) — use freely for internal and self-hosted deployments. See LICENSE for details.
