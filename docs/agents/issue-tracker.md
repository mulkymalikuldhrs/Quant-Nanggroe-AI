# Issue tracker: GitHub (primary) + GitLab + Codeberg + Local markdown

This repo is mirrored to 7 remotes. The skills resolve the issue tracker in a fixed order: **GitHub first, then GitLab, then Codeberg, then Local markdown**. Whichever surface is reachable wins; the rest are documented fallbacks.

| # | Tracker | CLI | When to use |
|---|---------|-----|-------------|
| 1 | **GitHub** (primary) | `gh` | Default. Issues live in `Dhaher-Labs/Quant-Nanggroe-AI` or `mulkymalikuldhrs/Quant-Nanggroe-AI` or `mulkymalikuldhaher/Quant-Nanggroe-AI`. |
| 2 | **GitLab** (fallback) | `glab` | When GitHub is down or rate-limited. Issues live in `gitlab.com/mulkymalikuldhr/Quant-Nanggroe-AI`. |
| 3 | **Codeberg** (fallback) | REST API | `codeberg.org/Dhaher-Labs/Quant-Nanggroe-AI`. No official CLI — use `curl` with the v1 API + token. |
| 4 | **Local markdown** (offline) | filesystem | `.scratch/<feature>/<id>.md`. Solo work, no remote. |

The "primary" remote is **codeberg** (the `origin` remote), but issues are tracked on **GitHub** because the skills are designed for `gh`. The 3 GitHub mirrors are functionally equivalent — pick one with `gh repo set-default` and the rest stay in sync via push.

---

## Conventions — GitHub (default)

Use the `gh` CLI for all operations.

- **Create an issue**: `gh issue create --title "..." --body "..."`. Use a heredoc for multi-line bodies.
- **Read an issue**: `gh issue view <number> --comments`, filtering comments by `jq` and also fetching labels.
- **List issues**: `gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'` with appropriate `--label` and `--state` filters.
- **Comment on an issue**: `gh issue comment <number> --body "..."`
- **Apply / remove labels**: `gh issue edit <number> --add-label "..."` / `--remove-label "..."`
- **Close**: `gh issue close <number> --comment "..."`

Infer the repo from `git remote -v` — `gh` does this automatically when run inside a clone. To force a specific GitHub repo, set `gh repo set-default Dhaher-Labs/Quant-Nanggroe-AI`.

### PRs as a triage surface: **no**

External PRs are not routed through the triage queue by default. A maintainer who wants this can flip the flag in this file.

---

## Conventions — GitLab (fallback)

Use the [`glab`](https://gitlab.com/gitlab-org/cli) CLI.

- **Create**: `glab issue create --title "..." --description "..."`
- **Read**: `glab issue view <number> --comments`. `-F json` for machine-readable.
- **List**: `glab issue list -F json` with `--label` filters.
- **Comment**: `glab issue note <number> --message "..."` (GitLab calls comments "notes").
- **Label**: `glab issue update <number> --label "..."` / `--unlabel "..."`
- **Close**: `glab issue close <number>` (post the closing note first; `glab issue close` does not accept a closing comment).
- **MRs** (GitLab's PRs): `glab mr create`, `glab mr view`, `glab mr note` — same shape as `gh pr ...` with `mr` and `note`/`--message` in place of `pr` and `comment`/`--body`.

GitLab numbers issues and MRs separately, so `#42` is unambiguous once you know which surface.

### MRs as a triage surface: **no**

Same as GitHub — not routed through triage by default.

---

## Conventions — Codeberg (fallback)

No official CLI. Use the Codeberg REST API directly with a personal access token.

- **Token**: set `CODEBERG_TOKEN` in the environment. Generate at `https://codeberg.org/user/settings/applications`.
- **Base URL**: `https://codeberg.org/api/v1`
- **Create issue**: `curl -X POST "$BASE/repos/Dhaher-Labs/Quant-Nanggroe-AI/issues" -H "Authorization: token $CODEBERG_TOKEN" -H "Content-Type: application/json" -d '{"title":"...","body":"..."}'`
- **Read issue**: `curl "$BASE/repos/Dhaher-Labs/Quant-Nanggroe-AI/issues/<number>" -H "Authorization: token $CODEBERG_TOKEN"`
- **List issues**: `curl "$BASE/repos/Dhaher-Labs/Quant-Nanggroe-AI/issues?state=open" -H "Authorization: token $CODEBERG_TOKEN"`
- **Comment**: `curl -X POST "$BASE/repos/Dhaher-Labs/Quant-Nanggroe-AI/issues/<number>/comments" -H "Authorization: token $CODEBERG_TOKEN" -d '{"body":"..."}'`
- **Label / Close**: `curl -X PATCH .../issues/<number>` with `{ "labels": [...], "state": "closed" }`.

Codeberg's API is Gitea-compatible; the same patterns work for any Gitea instance.

### PRs as a triage surface: **no**

Codeberg calls PRs "pull requests" too. Not in triage by default.

---

## Conventions — Local markdown (offline)

Issues live as files under `.scratch/<feature>/<id>-<slug>.md` in this repo. Use this when offline, for solo work, or for ephemeral tickets that don't need to live on a remote.

- **Directory layout**:
  ```
  .scratch/
  ├── risk-config-live/
  │   ├── 001-per-symbol-eurusd-0.3.md
  │   └── 002-per-symbol-xau-0.7.md
  └── vector-arbitrage/
      ├── 001-currency-graph.md
      └── 002-tri-arb-dry-run.md
  ```
- **File format** (front-matter + body, Gitea/GitHub-flavoured):
  ```markdown
  ---
  id: 1
  title: "Per-symbol risk config for EURUSD"
  state: open
  labels: [ready-for-agent]
  created: 2026-09-03
  ---

  ## Body

  Free-form markdown. Mirrors a GitHub issue body.

  ## Comments

  <!-- 2026-09-03T10:00Z @agent: opened -->
  <!-- 2026-09-03T10:05Z @agent: assigned to dev for hot-reload test -->
  ```
- **Add to .gitignore?**: **no.** Issues-as-markdown only work if they're committed. Use `.scratch/` as a feature folder.
- **Cross-link**: every local file should reference the source issue (if it was migrated from GitHub): `migrated-from: github.com/Dhaher-Labs/Quant-Nanggroe-AI#42`.

---

## When a skill says "publish to the issue tracker"

Try GitHub first (`gh issue create ...`). If `gh` is unauthenticated or rate-limited, fall back to GitLab (`glab issue create ...`), then Codeberg (`curl .../api/v1/...`), then write a local file under `.scratch/`.

## When a skill says "fetch the relevant ticket"

Try `gh issue view <number> --comments` first. If the issue doesn't exist on GitHub, try `glab issue view <number> --comments`, then Codeberg's API, then read `.scratch/<feature>/<id>-<slug>.md`.

## Wayfinding operations

Used by `/wayfinder`. The **map** is a single issue with **child** issues as tickets.

- **Map**: a single issue labelled `wayfinder:map`, holding the Notes / Decisions-so-far / Fog body.
- **Child ticket**: an issue linked to the map. On GitHub, use sub-issues (where enabled) or `Part of #<map>` at the top. On GitLab, `Part of #<map>` plus `/blocked_by` quick action. On Codeberg/Gitea, `Part of #<map>` plus a `Blocked by:` line in the body. On local markdown, sibling files in the same `.scratch/<feature>/` directory.
- **Blocking**: prefer native issue dependencies (GitHub `gh api .../dependencies/blocked_by`, GitLab `/blocked_by`). Fall back to a `Blocked by: #<n>, #<n>` line at the top of the child body.
- **Frontier query**: list the map's open children, drop any with an open blocker or an assignee; first in map order wins.
- **Claim**: `gh issue edit <n> --add-assignee @me` (or glab/codeberg equivalent).
- **Resolve**: comment with the answer, close, then append a context pointer (gist + link) to the map's Decisions-so-far.

---

## Why a custom multi-tracker doc?

This repo is mirrored across 7 remotes (codeberg primary, 3× GitHub, GitLab, GitLab backup). The skills' default of "pick one tracker" breaks here — the same issue must exist on the primary and at least one GitHub mirror so the 5-remote push stays consistent. The fallback chain keeps the skills working whether the user's local clone is set to `origin` (codeberg), a GitHub remote, or the GitLab mirror.

If you want a single-tracker setup, delete this file and re-run the `setup-matt-pocock-skills` skill with a single choice.
