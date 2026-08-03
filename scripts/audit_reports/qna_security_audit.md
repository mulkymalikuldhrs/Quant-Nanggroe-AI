# QNA Security Audit

**Date:** 2026-08-01
**Repo:** D:\repositories\Quant-Nanggroe-AI-worktree (branch: master, 1305 tracked files)
**Mode:** Read-only. No code modified.
**Skills used:** qna-security-audit, codebase-secret-scan, db-orm-security-audit

## Summary

**4 findings — highest severity MEDIUM. NO CRITICAL.** No live secrets found committed or tracked in the repo. The `credentials.md.txt` quarantine is verified working: the repo copy is a pointer only; real secrets live in `C:\Users\Hi\.qna-secrets\credentials.md.txt` (local, not in git). All SQL is parameterized; JWT auth is soundly implemented.

## Quarantine Verification (primary check) — PASS ✅

- `quant_nanggroe/credentials.md.txt` exists on disk but is a **single-line pointer**:
  `CREDENTIALS QUARANTINED — see C:\Users\Hi\.qna-secrets\credentials.md.txt (local only, NOT in git)`
- `git ls-files --error-unmatch` → **NOT tracked** (error: did not match).
- `git log -- <file>` → **no commit history**.
- No real secret values present in the repo copy.
- Actual secrets confirmed present ONLY in quarantine dir `C:\Users\Hi\.qna-secrets\credentials.md.txt` (FRED key, GitHub PAT `ghp_`, GitLab `glpat-`, Codeberg token). These are correctly OUT of the repo.
- **Verdict: quarantine successful — no CRITICAL secret-in-repo flag.**

## Findings

### 🟡 MEDIUM

`config/credentials.json:16` | JSON password field | MEDIUM (info)
- `"password": "${MT5_PASSWORD}"` — uses env-var indirection (safe pattern), NOT a literal. File is **gitignored** (`git check-ignore` exit 0). No leak. Noted for completeness.

### 🔵 LOW

1. `.env:QNAI_JWT_SECRET` | weak/placeholder dev secret | LOW
   - Value `qna-dev-jwt-secret-change-in-production-b27f8c1a` is a dev placeholder. File **IS gitignored** (verified `git check-ignore ./.env` → ignored), so not a leak. Must be replaced with a strong random secret before production launch. (Matches skill's known finding: QNAI_JWT_SECRET must be set for prod.)

2. `quant_nanggroe/database/migrations.py:232` (and duplicate `database/migrations.py:231`) | f-string in `text(f"DROP TABLE IF EXISTS {table}")` | LOW (code smell only)
   - `{table}` iterates a **hardcoded literal list** of table names — NOT user input. Not exploitable SQLi. Flagged as code smell + note: two divergent migration copies exist (`database/` legacy + `quant_nanggroe/database/`).

3. `scripts/ENHANCED_ECOSYSTEM_INTEGRATION.py:712` | `cursor.execute(f"... WHERE {where_clause} ...")` | LOW (safe pattern, verified)
   - `where_clause` is `" AND ".join(where_conditions)` where every condition is a **hardcoded SQL fragment** (`"content_type = ?"`, `"(title LIKE ? OR ...)"`). All user data (query, content_type, user_id) is bound via `?` placeholders in `params`. **Not SQLi** — reported only to document that this f-string was inspected and cleared.

## Vectors Cleared (no exploitable issue)

- **Leaked secrets (sk-/ghp_/glpat-/AKIA/PEM):** none in app source (`quant_nanggroe`, `scripts`, `config`, `database`, `web_interface`). Only hits were in `.venv`/`.tmp-*-venv`/`.kilo` third-party packages (excluded) and the quarantine pointer.
- **Hardcoded passwords:** none. Only matches were pip internals (`:****` mask), the security scanner's own detection strings (`quant_nanggroe/agents/security.py:160-162`), and env-var references.
- **Hardcoded JWT/secret_key:** only in docstring examples (`auth.py:274` = `"my-secret-key"` in a `.. code-block::`) and test files (`test-secret-key`). No production secret hardcoded.
- **SQL injection (ORM/raw):** all `cursor.execute`/`text()` sites use `?`/bound params. No f-string concatenation of user data into SQL.
- **eval/exec/os.system/shell=True/pickle.load:** in app dirs, only appear as **detection patterns** inside the repo's own security scanners (`agents/coder.py`, `agents/security.py`, `scripts/security_audit.py`) and `.eval()` = PyTorch model eval-mode (`engine/model_registry.py:786`). No dangerous execution sinks.
- **JWT implementation (`quant_nanggroe/security/auth.py`):** sound — HS256 header hardcoded (no alg-confusion), signature verified with `hmac.compare_digest`, expiry enforced (`time.time() > expires_at`), revocation checked. No `alg:none` bypass.
- **.env hygiene:** `./.env` is gitignored; `config/credentials.json` and `data/credentials.db` both gitignored.

## Recommendations (non-blocking)

1. Before production: set a strong random `QNAI_JWT_SECRET` (LOW #1).
2. Consolidate the two divergent `migrations.py` copies to reduce drift (LOW #2).
3. Keep `.qna-secrets` quarantine as-is — working correctly.


<!-- CODE-TRUTH STATUS FOOTER — appended 2026-08-03 23:43:45 by autobot (QNA audit 2026-08-03) -->
<!-- Method: append-only. Source of truth = code, not prior .md claims. -->
## 🔍 CODE-TRUTH STATUS (2026-08-03 audit)
- **FusionEngine**: EXISTS — `quant_nanggroe/core/scoring/fusion_engine.py:27` (prior claim "false" RETRACTED).
- **API server**: EXISTS + startable — `quant_nanggroe/cli.py:603` uvicorn :8000; `launch.bat api`; 223 routes wired.
- **Dashboard**: UNWIRED only because server not started; UI code present (`dashboard/`, 261 tsx+ts).
- **Phantom-equity ($1M default)**: MITIGATED — P1b fail-CLOSED `_resolve_equity()` floor $1000 in `risk_gate_bridge.py` (ctor:145, evaluate:194, evaluate_from_state:449). Live path uses `evaluate_from_state` -> real MT5 equity.
- **Polars**: NOT imported anywhere (`import polars`=0) -> `engine/data/providers/yahoo_polars.py` genuinely MISSING (archive gap real).
- **Secrets**: 0 hardcoded (grep `sk-`/`AKIA`=0). `eval`/`pickle`: 0 live vulns (only security-linter strings).
- **ENV BLOCKER**: all venv numpy ABI broken (cp311 `.pyd` under cp312) -> runtime import unverified until `uv sync`. Patch syntax+logic verified standalone.
- **Archive upgrade**: 8/11 new modules ALREADY in code; 4 missing (quality.py, yahoo_polars.py, feature_engine.py, alerting/).
- **Audit trail**: `C:/Users/Hi/Desktop/QNA_AUDIT_DEBAT.txt` | inventory `QNA_FILE_INVENTORY.txt` | `QNA_EXTENSION_LEDGER.txt`.
<!-- END CODE-TRUTH FOOTER -->
