# Development / Tooling

Global development tooling that spans the whole repo (backend and frontend alike). Backend-specific instructions live in `backend/README.md`.

## CodeGraph

[CodeGraph](https://codegraph.ai) builds a local code-intelligence index (symbols, call graphs, and dynamic-dispatch hops) that both AI agents and humans can query against. The index is stored in a `.codegraph/` directory at the repo root and covers every indexed language in the project, so it is **not** backend- or frontend-specific.

### What gets indexed

| Data | Value |
|---|---|
| Index location | `.codegraph/codegraph.db` (SQLite, gitignored — see `.codegraph/.gitignore`) |
| Status | `codegraph status` — should end with `✓ Index is up to date` |
| Coverage | All indexed source files under the repo root (`backend/`, `frontend/`, ...) |

### Setup

1. **Install** — `codegraph init` at the repo root builds the initial index. Upgrades happen via `codegraph upgrade` (versioned under `~/.codegraph/versions/`).
2. **PATH** — the launcher symlink lives at `~/.local/bin/codegraph`. Do **not** move the binary — it is a symlink managed by the versioned installer. Every shell that launches opencode must have `~/.local/bin` on `PATH`:
   ```sh
   export PATH="$HOME/.local/bin:$PATH"
   ```
   This line is already in `~/.zshenv` (sourced by **every** zsh — interactive, login, and non-interactive) and in `~/.zshrc`. Verify with `which codegraph`. Note that PATH is captured when a shell *starts*: after editing a dotfile, open a **new** shell/terminal — an existing shell keeps its stale PATH.
3. **opencode** — the repo root `opencode.jsonc` wires up the MCP server:
   ```jsonc
   "mcp": {
     "codegraph": {
       "type": "local",
       "command": ["codegraph", "serve", "--mcp"],
       "enabled": true
     }
   }
   ```
   Launch opencode from a **fresh** shell that has `~/.local/bin` on `PATH` so the relative `codegraph` command resolves when opencode spawns the MCP server. An opencode started before the PATH export existed (or launched from a long-lived shell) will keep failing until it is relaunched from a new shell.

### Using it

- **In opencode** — ask a question that names a symbol or an area ("how does the ingestion pipeline work", "who calls `GLiNERGraph`") and opencode's `codegraph_explore` MCP tool answers with the verbatim source plus call paths.
- **From the CLI** — `codegraph explore "<symbol or question>"` prints the same output. Also useful: `codegraph query <search>`, `codegraph callers <symbol>`, `codegraph impact <symbol>`.

### Keeping the index fresh

- `codegraph sync` — incremental, picks up changes since the last index.
- `codegraph index` — full rebuild from scratch (same result as a fresh `init`).
- `codegraph status` — check whether the index is up to date and complete.

!!! note "Indexing is the developer's decision"
    The `.codegraph/` directory is machine-local and gitignored on purpose. If you see a repo without `.codegraph/`, that just means no one has indexed it — nothing is broken.

### Troubleshooting

| Symptom | Fix |
|---|---|
| `codegraph: command not found` | Make sure `~/.local/bin` is in `PATH`; verify with `which codegraph`. If missing, ensure the `export PATH="$HOME/.local/bin:$PATH"` line is in `~/.zshenv` (and `~/.zshrc`), then open a **new** shell. |
| opencode MCP shows CodeGraph as unavailable | The relative `codegraph` command couldn't be resolved when opencode spawned it — opencode inherited a stale `PATH` (e.g. from a long-lived shell started before the export was added). Relaunch opencode from a **new** shell/terminal. |
| `codegraph status` reports a stale/incomplete index | Run `codegraph sync`; if that doesn't help, `codegraph index`. |
| A stale lock blocks indexing | `codegraph unlock` |
