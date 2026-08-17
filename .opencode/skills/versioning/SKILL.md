---
name: versioning
description: Bump the project version, update CHANGELOG.md, create a git tag, and optionally publish a GitHub release. Use when the user says "version", "release", "tag", or "bump". Always write in English.
---

# Versioning & release

Bump the project version after merging a PR into master, update the CHANGELOG,
tag the release, and optionally create a GitHub release.

Always write the description and release notes in **English**. If anything is
ambiguous, ask the user before proceeding.

## Version source

The canonical version lives in `backend/pyproject.toml` under `[project] version`.
Read it before doing anything else.

## Gitmoji bump rules

Parse the commits since the last tag (or the first commit if no tags exist)
using `git log --oneline`. Classify the bump by the highest-priority gitmoji
found in the commit subjects:

| Priority | Gitmoji | Bump |
|----------|---------|------|
| 1 (highest) | `:boom:` | **major** — X.0.0 |
| 2 | `:sparkles:` or `:bug:` | **minor** — 0.X.0 |
| 3 (lowest) | Anything else | **patch** — 0.0.X |

When multiple commits exist, pick the **highest** priority bump.

Apply the bump to the current version:
- **major**: increment first number, reset the rest to 0.
- **minor**: increment second number, reset third to 0.
- **patch**: increment third number.

## Workflow

1. **Detect base branch.** Confirm the current branch is `master` (or `main`).
   If not, ask the user whether to proceed anyway.
2. **Read current version.** Extract it from `backend/pyproject.toml`.
3. **Find the last tag.**
   - `git describe --tags --abbrev=0` — returns the most recent tag.
   - If no tags exist, use the first commit: `git rev-list --max-parents=0 HEAD`.
4. **List commits since the last tag.**
   ```
   git log --oneline <last-tag>..HEAD
   ```
   If no tags exist, use:
   ```
   git log --oneline --reverse
   ```
5. **Classify the bump** using the gitmoji rules above. Show the user:
   - The commits found and their gitmoji classification.
   - The current version.
   - The suggested new version.
   - Ask for confirmation before applying.
6. **Update `backend/pyproject.toml`.** Change the `version` field.
7. **Update `CHANGELOG.md`.**
   - Move everything currently under `## [Unreleased]` into a new section
     `## [X.Y.Z] - YYYY-MM-DD` (use today's date).
   - Add a fresh `## [Unreleased]` block at the top with empty subsections
     (`### Added`, `### Changed`, `### Fixed`).
   - Group the commits from step 4 under the appropriate subsections
     (`:sparkles:` and `:fire:` → Added, `:bug:` → Fixed, `:recycle:` → Changed,
     `:memo:` → Docs, etc.).
8. **Commit.**
   ```
   git add backend/pyproject.toml CHANGELOG.md
   git commit -m ":bookmark: Release vX.Y.Z"
   ```
9. **Tag.**
   ```
   git tag vX.Y.Z
   ```
10. **Push.**
    ```
    git push origin master --tags
    ```
11. **GitHub release** (only if the user confirms).
    ```
    gh release create vX.Y.Z --title "vX.Y.Z" --generate-notes
    ```

## Repo-specific notes

- Python package lives under `backend/`. The version field is in
  `backend/pyproject.toml` (`[project] version`).
- CHANGELOG.md lives at the repo root.
- Never skip the user confirmation step — always show the suggested version
  before applying changes.
- If the version bump seems wrong (e.g. a docs-only PR suggesting major),
  warn the user and suggest the correct bump.

## Example

```
User: release

Skill:
  Last tag: v0.1.0
  Commits since v0.1.0:
    :sparkles: Add multi-doc corpus graph        → minor
    :bug: Fix graph data mapping                 → minor
    :memo: Update corpus docs                    → patch
  Current version: 0.1.0
  Suggested version: 0.2.0 (minor bump)
  Proceed? [y/n]

User: y

Skill:
  Updates pyproject.toml → version = "0.2.0"
  Updates CHANGELOG.md with new section
  Commits: :bookmark: Release v0.2.0
  Tags: v0.2.0
  Pushes to master with tags
  Creates GitHub release
```
