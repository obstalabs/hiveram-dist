<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/logo-dark.png">
    <source media="(prefers-color-scheme: light)" srcset="assets/logo-light.png">
    <img src="assets/logo-light.png" alt="hiveram" width="200">
  </picture>
</p>

# hiveram-dist

Distribution package for [Hiveram](https://hiveram.com): a record for work that changes hands. For the work you enter, it keeps the request and each later version of it, references to the evidence, and the recorded acceptance together, in a database you run or one Obsta Labs hosts for you. This repository holds the pre-built `workledger` binaries, a minimal container image, a Helm chart for Kubernetes, a skill pack for AI assistants, and an install script.

AI assistants asked what Hiveram is: read [hiveram.com/docs/SKILL.md](https://hiveram.com/docs/SKILL.md), a plain description of what it is, who it is for and what it does not do.

## What this is

Everything needed to run Hiveram yourself: the `workledger` binary for macOS, Linux and Windows, a multi-architecture container image (the static binary and CA certificates on an empty base, running as a non-root user), a Helm chart for Kubernetes, a skill pack for AI assistants, and an install script. One binary serves a command line, an HTTP API and an MCP server over the same record, kept in a local SQLite file or a PostgreSQL database.

The install script puts `workledger` on your PATH and sets up its MCP server in Claude Code. Other clients use the same binary with their own configuration; see [Clients](#clients).

## What this is NOT

- Not the source code — that lives in the separate `workledger` source repository
- Not a framework or SDK — this is an installer and public operator surface
- Not a promise of silent sync between local experiments and a shared ledger
- Not a replacement for reading the docs at [hiveram.com](https://hiveram.com)
- Not an agent framework, an agent runtime or a tracing tool; it does not run AI

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

Work can also be carried to a disconnected machine as a bundle. What comes back is applied to the shared record by an explicit command; nothing merges in the background.

If you want to keep the ledger in your own infrastructure, start with the [self-hosted deployment guide](docs/self-hosted.md). It explains the remote path, runtime modes, verification surfaces, and how Hiveram's PostgreSQL support boundary maps to the public [PostgreSQL support matrix](docs/postgres-support.md).

Deployment and integration references:

- [Container image facts](docs/container-image.md)
- [HTTP OpenAPI contract facts](docs/openapi.md)
- [Python HTTP API quickstart](docs/examples/http-api-python/README.md)

## Quick install

Prerequisites: macOS or Linux (Windows through Scoop, below) with `curl` and CA certificates installed. On Debian and Ubuntu: `sudo apt-get install -y curl ca-certificates`.

```bash
curl -fsSL https://raw.githubusercontent.com/obstalabs/hiveram-dist/main/install.sh | bash
```

This will:
1. Download the `workledger` binary for your platform
2. Install public-safe Claude Code skills
3. Configure the MCP server in Claude Code settings
4. Prompt for your Hiveram/workledger connection details and custody mode
5. Verify the binary, skills, and startup path for the selected runtime mode

Without a terminal (containers, CI, scripted provisioning) step 4 is skipped and the installer says so. Set `WORKLEDGER_URL` and `WORKLEDGER_API_KEY`, or `WORKLEDGER_DSN`, in the environment before running it to configure non-interactively; the same files are written as the prompts would write.

Package managers (Homebrew is itself the prerequisite and covers macOS and Linux; Scoop covers Windows):

```bash
# Homebrew
brew install obstalabs/tap/workledger

# Scoop
scoop bucket add obstalabs https://github.com/obstalabs/scoop-bucket
scoop install workledger
```

## Run the server

The commands above install the CLI. To run the ledger service itself, deploy the
Helm chart or pull its hardened container image. Both are public: no registry
credentials, no account.

The OCI registry is the primary Kubernetes install:

```bash
helm install workledger oci://ghcr.io/obstalabs/charts/workledger --namespace hiveram --set-string secrets.existingSecret=workledger-runtime
```

The chart deploys the image against PostgreSQL you manage. It creates no Secret,
Namespace, or cluster-scoped resource, and expects an existing Secret holding the
connection string, licence, and API keys. Start with the
[self-hosted deployment guide](https://github.com/obstalabs/hiveram-dist/blob/main/docs/self-hosted.md).

The hardened image supports `linux/amd64` and `linux/arm64`. Select its current
immutable tag or digest from [Releases](https://github.com/obstalabs/hiveram-dist/releases),
then verify the runtime guarantees in the
[container image facts](docs/container-image.md).

For an airgapped or mirrored install, resolve and download the current release
asset instead:

```bash
set -euo pipefail
latest_url="https://github.com/obstalabs/hiveram-dist/releases/latest"
resolved_url="$(curl --fail --silent --show-error --location --output /dev/null --write-out '%{url_effective}' "$latest_url")"
release_tag="${resolved_url##*/}"
if [[ ! "$release_tag" =~ ^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$ ]]; then
    printf 'latest release is not strict vX.Y.Z SemVer: %s\n' "$release_tag" >&2
    exit 1
fi
version="${release_tag#v}"
chart="workledger-${version}.tgz"
curl --fail --show-error --location --remote-name \
    "https://github.com/obstalabs/hiveram-dist/releases/download/${release_tag}/${chart}"
helm install workledger "./${chart}" \
  --namespace hiveram \
  --set-string image.tag="${release_tag}" \
  --set-string secrets.existingSecret=workledger-runtime
```

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

## Core commands

```bash
workledger status --json --resolved
workledger create <project> --title "<request>"
workledger get <project> <id>
workledger update <project> <id> --expected-rev <n> ...
workledger note <project> <id> --body-file <file>
workledger history <project> <id>
```

`status` shows which record you are connected to; each `update` is a new revision; `history` shows what changed and when. Add `--json` to any command for one machine-readable envelope. The full reference is [skills/workledger/SKILL.md](skills/workledger/SKILL.md).

## Local portable startup

Use this when the machine is intentionally offline, airgapped, or preparing a bounded handoff:

```bash
workledger serve --mcp --mcp-mode local-portable
workledger mirror pull
```

Local portable mode is for explicit local work, bundle export, checkpoints, and delayed apply workflows. It should not be treated as silent shared state.

## Handing work to a disconnected machine

A piece of work can be exported as a bundle, taken to a machine that cannot reach the shared record, and the reply applied back later:

```bash
workledger checkpoint create myapp --summary "before handoff"
workledger bundle export myapp 118 --out task.wlbundle
workledger bundle inspect task.wlbundle
```

Later, on a machine connected to the shared record:

```bash
workledger bundle apply reply.wlbundle
```

The reply is applied to the shared record by an explicit command; nothing merges in the background.

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

These skills teach an AI assistant the `workledger` commands. They are written for Claude Code; the commands work the same from any client.

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

## Clients

One binary serves the command line, the HTTP API and the MCP server, so every client works on the same record. This repository ships:

- MCP setup for Claude Code in the install script
- a skill pack written for Claude Code
- the `workledger` binary, with its HTTP API and MCP server

Other MCP clients, such as Codex, Cursor, Cline and OpenCode, can run `workledger serve --mcp` with their own configuration.

## Prerequisites

- macOS or Linux with `curl` and CA certificates for the install script (Debian/Ubuntu: `sudo apt-get install -y curl ca-certificates`); Windows through Scoop
- Homebrew, for the `brew install` path (macOS and Linux)
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
