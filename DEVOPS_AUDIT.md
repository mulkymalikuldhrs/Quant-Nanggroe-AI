# DEVOPS / CI AUDIT — Quant-Nanggroe-AI

**Date:** 2026-07-15
**Scope:** `.github/workflows/`, `Dockerfile` (`./deploy/docker/Dockerfile`), `docker-compose.yml`, `vercel.json`, `railway.json`, `k8s-deployment.yaml`
**Action taken:** read-only audit + recommendations. **No deploy performed.**

---

## TL;DR

- **CI runs lint + test, but NOT type-check.** `make typecheck` (mypy) exists in the Makefile and is configured in `pyproject.toml` but is **not wired into any workflow**.
- **Frontend (Next.js dashboard) is never built, linted, or type-checked in CI** despite being a core deliverable.
- **`k8s-deployment.yaml` is broken + leaked secrets.** Uses `:latest` tag, hardcodes placeholder secrets in plaintext, and is copied from an unrelated project ("Agentic AI System").
- **`vercel.json` / `railway.json` target a different project** ("Agentic AI System" by Mulky Malikul Dhaher) — copy-paste contamination.
- **`docker-compose.dev.yml` uses the wrong Python module path** (`quant_nanggroe_ai.*` vs real `quant_nanggroe.*`) — dev compose is broken.
- **No rollback strategy and no staging==prod parity** anywhere.

---

## 1. CI health — what actually runs

| Check | In CI? | Where | Notes |
|-------|--------|-------|-------|
| Python lint (ruff) | ✅ | `.github/workflows/ci.yml` → `make lint` | OK |
| Python test (pytest) | ✅ | `ci.yml` → `make test` | OK |
| Python type-check (mypy) | ❌ | `make typecheck` exists, **not called** | Gap |
| Frontend build (next build) | ❌ | — | Gap |
| Frontend lint (eslint) | ❌ | — | Gap (root `package.json` lint even swallows errors: `\|\| echo 'Lint check complete'`) |
| Frontend type-check (tsc) | ❌ | `dashboard/tsconfig.json` has `strict:true` but no `npm run typecheck` and CI never runs it | Gap |
| Security scan | ✅ | `security-scan.yml` | separate workflow, fine |

**Verdict:** CI passes lint+test but is missing type-check (explicitly requested) and the entire frontend pipeline.

---

## 2. Findings (gaps + bugs)

### F1 — Type-check not in CI  *(requested, missing)*
`Makefile` defines `typecheck:` → `mypy quant_nanggroe/ --ignore-missing-imports`; `pyproject.toml` has `[tool.mypy]` `strict = true`. But `ci.yml` only runs `make lint` + `make test`.
**Fix:** add a step in `ci.yml` after lint:
```yaml
      - name: Type check
        run: make typecheck
```

### F2 — Frontend never built/type-checked in CI  *(missing)*
`dashboard/` is a Next.js 16 app (`next.config.ts`, `tsconfig.json` strict). No workflow builds or type-checks it.
**Fix:** add a job to `ci.yml`:
```yaml
  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20", cache: "npm", cache-dependency-path: dashboard/package-lock.json }
      - run: npm ci
        working-directory: dashboard
      - run: npx tsc --noEmit
        working-directory: dashboard
      - run: npm run build
        working-directory: dashboard
```
(Root `package.json` `lint` script actively hides lint failures — fix it to `eslint src/ --max-warnings=0` with no `|| echo`.)

### F3 — `docker-compose.dev.yml` wrong module path  *(bug)*
Uses `quant_nanggroe_ai.api.app` / `quant_nanggroe_ai.worker`; the real package is `quant_nanggroe` (see `Dockerfile`, `pyproject.toml`). Dev compose will fail to import.
**Fix:** replace `quant_nanggroe_ai` → `quant_nanggroe` in `docker-compose.dev.yml`.

### F4 — Dockerfile build silently degrades  *(bug)*
```dockerfile
RUN poetry config virtualenvs.create false \
 && poetry install --only main ... || \
 pip install --no-cache-dir fastapi uvicorn ...
```
If the primary `poetry install` fails (lock mismatch, network), the `||` fallback installs a **hand-picked, partial, stale** dep list and the build still "succeeds" — shipping a subtly broken image. Also copies all of builder site-packages (heavy, includes build-essential toolchain leftovers).
**Fix:** remove the `|| pip install` fallback; let the build fail loud. Pin `poetry install --only main` against a committed `poetry.lock`.

### F5 — `k8s-deployment.yaml` broken + leaked secrets  *(high)*
- **`:latest` tag** (`image: agentic-ai:latest`) — no rollback, non-reproducible rollouts.
- **Hardcoded secrets** in plaintext `data:` block (base64 of `postgres://user:pass@localhost...`, `redis://localhost:6379`, `your-super-secret-key-here`). Committed to git. Even as placeholders this is an anti-pattern; real values must come from an external secret manager (sealed-secrets / external-secrets / cloud KMS), never the manifest.
- **Unrelated project** ("Agentic AI System", `agentic-ai.example.com`) — copied from another repo. Labels/namespace/ingress host are wrong for Quant-Nanggroe.
- **No `imagePullPolicy`** set with `:latest` → pods may never pull a new build.
- **ReadWriteOnce PVC shared across 3 replicas** — only one pod can mount `agentic-data-pvc` at a time; the other 2 will crashloop.
**Fix:** immutable tag via digest/CI (`image: registry/quant-nanggroe:${{ sha }}`), remove secrets to a SecretStore, add `imagePullPolicy: IfNotPresent`, use RWO per-replica or ReadWriteMany/object storage, and rename namespace/ingress to the real project.

### F6 — Deploy manifests target a different project  *(contamination)*
`vercel.json` (`name: agentic-ai-system`, `X-Powered-By: Agentic AI System`), `railway.json` (`Agentic AI System`), and `k8s-deployment.yaml` all carry "Agentic AI System" / "Mulky Malikul Dhaher" branding and a repo URL `github.com/eemdeexyz/Agentic-AI-System`. These are copy-paste leftovers. `railway.json` `startCommand` is `python start_system.py --production` — the file is `scripts/start_system.py` (path resolvable from repo root, OK) but the manifest's `buildCommand` does `pip install -r requirements.txt` while the pinned Dockerfile uses Poetry; the dep set diverges between Railway and Docker.
**Fix:** rewrite branding to Quant-Nanggroe; unify dependency source (single `requirements.txt` or single `pyproject`+lock) so Railway == Docker.

### F7 — `docker-compose.yml` references root `Dockerfile`  *(config drift)*
`docker-compose.yml` declares `dockerfile: Dockerfile` at repo root, but the actual Dockerfile is `./deploy/docker/Dockerfile`. `docker compose up --build` from root will fail to find it.
**Fix:** point `build.dockerfile` to `deploy/docker/Dockerfile` (and `build.context: .`), or move/copy the Dockerfile to root.

---

## 3. Rollback strategy (recommended)

Today nothing supports rollback — K8s uses `:latest`, Vercel auto-aliases, Railway restarts on failure only.

**Minimum viable rollback:**
1. **Immutable tags.** Build once, tag with git SHA + semver, push to a registry. Deploy only pinned digests. (`image: .../quant-nanggroe@sha256:...`)
2. **K8s:** `kubectl rollout undo deployment/agentic-ai-app -n <ns>` is instant *if* the previous ReplicaSet still exists. Keep `revisionHistoryLimit: 5` (default) and never use `:latest`.
3. **DB migrations are the real risk** (Alembic). A code rollback with a forward-only migration breaks the app.
   - Prefer **expand/contract** migrations (additive, backward-compatible).
   - Or gate releases: never auto-run `alembic upgrade head` on deploy; run it as a separate, reversible step. `Makefile` already has `db-downgrade`.
4. **Health-gated rollout:** add `strategy.rollingUpdate` + `maxUnavailable: 0` and rely on existing liveness/readiness probes so a bad build self-stops instead of serving 500s.
5. **Vercel:** keep `autoAlias: false` (already set) and promote via `vercel promote <deployment-url>` only after smoke tests; instant revert by re-promoting the prior URL.
6. **Railway:** pin a specific deployment in the dashboard / use `railway up --detach` + manual promote; keep `restartPolicyType: ON_FAILURE` but add a post-deploy smoke check (`curl /api/system/status`).

---

## 4. Staging == Prod parity (recommended)

The repo has three deployment targets with three different shapes (Docker Compose, Vercel serverless Flask, Railway Nixpacks, K8s). They do **not** match.

**Make staging a clone of prod, not a weaker copy:**
- Railway already defines `staging` vs `production` env blocks — good start, but staging sets `FLASK_DEBUG: true` and omits `DATABASE_URL`/`REDIS_URL`/`SECRET_KEY`. Staging should use the **same variable set** as prod, just pointing at a staging DB/Redis. Same image, same config keys.
- Single source of truth for env: one `.env.example` (exists: `.env.example`) documenting every var; both staging and prod read the same keys.
- **Same image in both environments.** Build once, deploy the same SHA to staging first, then promote to prod. Don't let Railway/Vercel rebuild from source independently (F6 dependency drift).
- K8s: add a `staging` namespace + Deployment reusing the **same** Deployment manifest via Kustomize overlay (only `replicas`, `DATABASE_URL`, `ingress host` differ). Avoid a hand-written second manifest that rots.

---

## 5. Priority order

| # | Item | Effort | Impact |
|---|------|--------|--------|
| 1 | F5 — K8s secrets out of git + immutable tag | low | high (security + rollback) |
| 2 | F1 — add type-check to CI | trivial | high (requested) |
| 3 | F2 — frontend build+type-check in CI | low | high (ship confidence) |
| 4 | F3/F7 — fix compose module path + Dockerfile ref | trivial | med (local dev broken) |
| 5 | F4 — remove Dockerfile `\|\| pip` fallback | trivial | med (silent bad builds) |
| 6 | F6 — de-contaminate Vercel/Railway branding + unify deps | low | med |
| 7 | §3/§4 — rollback + staging parity | med | high (ops maturity) |

---

## 6. What was NOT changed
No files modified, no deploy, no secrets altered. This document is the only artifact. Recommendations above are safe to apply incrementally; items marked *trivial/low* can land in one PR.
