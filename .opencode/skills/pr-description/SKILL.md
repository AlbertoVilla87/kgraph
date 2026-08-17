---
name: pr-description
description: Generate a pull request description for the current branch using the repo's Summary/What Changed/Testing/Breaking Changes format, and optionally push the branch and open the PR on GitHub. Use when the user says "PR", "pull request", "descripción de PR", "github", "create a PR", or asks for a release note in that format. Always write in English.
---

# PR description & GitHub PR creation

Create professional PR descriptions for the current branch, following this repo's
standard format, and (when asked) push the branch and open the PR on GitHub.

Always write the description in **English**. If anything is ambiguous, ask the
user before writing.

## The format

Exactly four sections using `##` headings:

```
## Summary
A one or two sentence overview of what the change accomplishes and why.

## What Changed
A bullet list of concrete changes (files, modules, configs, deps). Be specific:
name the actual files and symbols, not just areas.

## Testing
A bullet list of how it was verified (commands run, expected output).

## Breaking Changes
A bullet list of anything that breaks existing usage: renames, moved paths,
removed keys, changed commands. Use "None" if there are none.
```

Example (from this repo):

```
## Summary
Implemented KeyBERT keyword extraction as a new pipeline stage and exposed it
through a CLI entry point.

## What Changed
- Added a new key_bert_demo.py CLI script that loads documents, extracts
  keyphrases with KeyBERT, and prints the scored keywords.
- Registered a new kbert-demo entry point in backend/pyproject.toml.
- Added keybert and sentence-transformers (via KeyBERT) to the project
  dependencies.
- Extended backend/configs/params.yaml with a new keyword_extractor section.
- Added the ExtractorConfig Pydantic model in kgraph/graph/config.py.
- Renamed ModelConfig to NERConfig and the model config key to ner.

## Testing
- Verified dependency installation with uv sync.
- Verified the new kbert-demo entry point runs and prints extracted keywords.

## Breaking Changes
- The model key in backend/configs/params.yaml has been renamed to ner.
- The ModelConfig class in kgraph.graph.config was renamed to NERConfig.
```

## Commit messages with gitmoji

Before pushing or creating the PR, all changes **must be committed**. Use
[gitmoji](https://gitmoji.dev/) prefixed commit messages to enable automatic
versioning. Pick the emoji that best matches the change type:

| Emoji | Code | Use for |
|-------|------|---------|
| :sparkles: | `:sparkles:` | New feature |
| :bug: | `:bug:` | Bug fix |
| :recycle: | `:recycle:` | Refactor (no feature/fix) |
| :memo: | `:memo:` | Documentation only |
| :white_check_mark: | `:white_check_mark:` | Adding or updating tests |
| :lock: | `:lock:` | Security or auth changes |
| :boom: | `:boom:` | Breaking change |
| :arrow_up: | `:arrow_up:` | Dependency upgrade |
| :wrench: | `:wrench:` | Config or tooling changes |
| :lipstick: | `:lipstick:` | UI / style improvement |
| :package: | `:package:` | Build / packaging changes |
| :fire: | `:fire:` | Removing code or files |
| :sparkles: | `:sparkles:` | Initial commit |

Format: `<emoji> Short imperative description (max 72 chars)`

Example:
```
:sparkles: Add KeyBERT keyword extraction CLI demo
:bug: Fix config loading order in pipeline
```

For versioning, commits prefixed with :boom: trigger a major bump, :sparkles:
and :bug: trigger a minor bump, and all others trigger a patch bump.

## Workflow

1. **Find the base branch.** Prefer the repo's main branch. For this repo
   (`kgraph`) use `master`. Confirm with `git remote show origin` if unsure.
2. **Gather the changes.**
   - `git branch --show-current` — current branch name.
   - `git log --oneline <base>..HEAD` — commits in the PR.
   - `git diff --stat <base>...HEAD` — files touched.
   - `git status --short` — uncommitted work; if present, **must commit first**
     before proceeding (see "Creating the PR on GitHub" step 1).
   - Open the key files in the diff (do not skim the stat only) to understand what
     actually changed and reference real names/paths.
3. **Determine the intent** from the branch name, commit subjects, and the diff.
   If the intent is unclear, ask the user what the PR is about.
4. **Write the description** in the format above. Be specific and concrete.
   Review it with the user before creating anything on GitHub.

### Repo-specific notes

- Python package lives under `backend/`. Run commands from there:
  `cd backend && uv sync`, `uv run <script>`.
- CLI entry points: `gliner-demo`, `kbert-demo`, `qwen-demo` (see
  `backend/pyproject.toml`).
- Config lives in `backend/configs/params.yaml`; config models in
  `backend/src/kgraph/graph/config.py`.
- Never invent details that are not in the diff (model names, file paths,
  breaking changes) — verify against the code.

## Creating the PR on GitHub

Only create the PR after the user confirms the description. `gh` (GitHub CLI)
must be installed and authenticated.

1. **Commit first.** If there is uncommitted work (from `git status --short`),
   stage and commit everything with a proper gitmoji-prefixed message:
   `git add --all && git commit -m "<emoji> <description>"`.
   This step is mandatory — never push uncommitted changes.
2. Ensure the branch is pushed: `git push -u origin <current-branch>`.
3. Save the description to a temp file and create the PR:
   `gh pr create --base <base> --head <current-branch> --title "<short title>" --body "$(cat <tempfile>)"`.
4. Pick a concise title (max ~72 chars) that summarizes the change.
5. Report back with the PR URL.

If `gh` is not installed or not authenticated, say so and offer to install
it or create only the description text.
