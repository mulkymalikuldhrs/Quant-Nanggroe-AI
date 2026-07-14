# SECURITY AUDIT — SWARM

**Repo:** `D:\repositories\Quant-Nanggroe-AI-worktree` (branch `master`, profile `hackerbot`)
**Mode:** fail-closed, report-only. **Nothing was deleted, modified, committed, or pushed.**
**Date:** 2026-07-15
**Scope:** hardcoded secrets, auth-bypass paths, kill-switch integrity, dependency CVEs.

Tooling: `grep`/ripgrep over `*.py`, `*.yaml`, `*.yml`, `*.json`, `*.env*` (excluding `.venv/`); `git ls-files` for tracking; `uvx pip-audit` (OSV) over 118 installed deps.

---

## Severity summary

| # | Finding | Severity | File:line |
|---|---------|----------|-----------|
| 1 | Hardcoded live MT5 broker credentials in committed config | **CRITICAL** | `config/mt5_accounts.yaml:7-8`, `config/credentials.json:8-9` |
| 2 | Kill-switch monitor loop is inert (never reads real state) | **HIGH** | `quant_nanggroe/worker.py:305` |
| 3 | Kill-switch reset via API is inert (confirmation mismatch) | **HIGH** | `api/routes/agents.py:219` vs `engine/risk/kill_switch.py:26` |
| 4 | Auth fully bypassed in default "dev mode" (no QNAI_API_KEY) | **HIGH** | `api/middleware.py:51`, `api/app.py:284` |
| 5 | Arbitrary code exec via regex-blocklist strategy sandbox | **MEDIUM** | `engine/shadow/codegen.py:240` |
| 6 | Unauthenticated broker registration + immediate connect | **MEDIUM** | `api/routes/brokers.py:182-196` |
| 7 | JWT secret ephemeral/random when QNAI_JWT_SECRET unset | **LOW** | `api/middleware.py:41-45` |
| 8 | Dependency CVE scan (118 deps) | **INFO** | `pip-audit` → none found |

---

## 1. CRITICAL — Hardcoded MT5 credentials committed to git

`config/mt5_accounts.yaml` (git-tracked, **not** gitignored):

```
7:    login: "414016058"
8:    password: "@15September"
```

Same live account is duplicated in `config/credentials.json` (git-tracked):

```
8:     "login": "414016058",
9:     "password": "@15September",
```

- These are **live trading broker credentials** (Exness MT5). Anyone with repo access can authenticate to the broker account.
- `git ls-files config/` confirms both files are committed (`046ed5e`, `df4c21f`, `d72aa73` history). Neither is matched by `.gitignore` (only `.env`/`.env.local`/`.env.*.local` are ignored — lines 21, 67-69).
- CWE-798 (hardcoded credentials) / CWE-259 (use of hard-coded password).

**Action:** rotate/disable this MT5 account immediately; purge from git history (BFG/filter-repo); move to env/secret store; add `config/mt5_accounts.yaml` and `config/credentials.json` to `.gitignore`.

---

## 2. HIGH — Kill-switch monitor loop is inert

`quant_nanggroe/worker.py:297-319` `_kill_switch_monitor_loop`:

```python
305:                self._kill_switch_active = False  # Default: not active
306:
307:                if self._kill_switch_active and not was_active:
308:                    logger.warning("kill_switch_activated", ...)
```

The loop **hardcodes `_kill_switch_active = False` every iteration** and never reads the real `KillSwitch` instance or calls `check_auto_activate()` / `can_trade()`. So:
- The worker's safety monitor never reflects an actual activation.
- It never auto-halts trading on loss/drawdown/volatility (auto-trigger is only consulted in `engine/execution/hermes_execution.py:139` and tests, not in the runtime worker loop).
- The header comments ("Periodically check the kill switch state") are false — the mechanism is non-functional at the worker layer.

**Action:** have the monitor read `get_kill_switch().is_active` and call `check_auto_trigger(...)` with live P&L each interval; gate trading on it.

---

## 3. HIGH — Kill-switch reset via API is inert (confirmation mismatch)

- Core `reset()` requires the constant `RESET_CONFIRMATION = "CONFIRM_RESET_AFTER_REVIEW"`:
  `engine/risk/kill_switch.py:26,160`
- But the API endpoint checks `request.confirmation != "CONFIRM"`:
  `api/routes/agents.py:219`

`"CONFIRM"` ≠ `"CONFIRM_RESET_AFTER_REVIEW"` → the documented `POST /api/kill-switch/reset` endpoint **can never succeed**. Once the kill switch trips, it cannot be cleared through the API. Fail-closed (safe direction) but operationally broken / un-resettable.

**Action:** align the confirmation string on both sides (or remove the dead branch).

---

## 4. HIGH — Full auth bypass in default "dev mode"

`api/middleware.py:51` / `api/app.py:284`:

```python
51:        self._dev_mode = not bool(os.environ.get("QNAI_API_KEY", ""))
52:        if self._dev_mode:
53:            logger.warning("Auth in DEV mode — no QNAI_API_KEY set, all requests allowed")
...
59:        if self._dev_mode:
60:            return await call_next(request)   # skips ALL auth on every /api/* route
```

If `QNAI_API_KEY` is unset (the default — `.env.template` ships it empty), **every** `/api/*` endpoint is unauthenticated, including:
- `POST /api/kill-switch/activate` and `/reset` (trading control plane)
- `POST /api/brokers/register` (see #6)

Thus a default/forgotten deployment exposes full control with no auth. CWE-284 (improper access control). Combined with #3, a remote attacker who trips the kill switch can also block its reset.

**Action:** never fall back to dev-mode for protected routes; require an explicit, non-default opt-in (e.g. `QNAI_ALLOW_INSECURE_DEV=true`) and refuse to start the API server in prod config without `QNAI_API_KEY`.

---

## 5. MEDIUM — Arbitrary code execution via weak strategy sandbox

`engine/shadow/codegen.py:224-240`:

```python
233:        is_valid, errors = self.validate_code(code)
...
240:            exec(code, namespace)
```

`validate_code` (lines 200-222) only runs a **regex blocklist** (`FORBIDDEN_PATTERNS` = `import os`, `import subprocess`, `__import__`, `eval(`, `exec(`, `open(`, ...). This is trivially bypassable for in-process RCE, e.g. `importlib.import_module('os')`, `getattr(__builtins__,'__import__')('os').system(...)`, base64/`compile()`, f-strings. LLM- or user-supplied strategy code is executed with full process privileges.

**Action:** do not `exec` untrusted code in-process; use a real sandbox (subprocess + seccomp/nsjail), or restrict to an AST allowlist of permitted calls, or a restricted `globals` namespace with `__builtins__` stripped.

---

## 6. MEDIUM — Unauthenticated broker registration + immediate connect

`api/routes/brokers.py:165-198` `POST /api/brokers/register`:

```python
182:        broker = ExchangeFactory().create("mt5",
183:            api_key=payload.get("login"),
184:            api_secret=payload.get("password"),
185:            passphrase=payload.get("server"))
...
194:        await broker.connect()
```

Accept arbitrary `login`/`password`/`server` and immediately connects to a broker. Behind the #4 dev-mode bypass this is unauthenticated; even with auth, any valid API key (which can be a low-priv `viewer`) reaches it. Credentials handled in-memory only (no persistence beyond runtime) — acceptable, but the open registration surface is the issue.

**Action:** restrict to `admin`/`trader` role; require auth even in dev; rate-limit.

---

## 7. LOW — Ephemeral JWT secret

`api/middleware.py:41-45`: when `QNAI_JWT_SECRET` is unset, a per-process `uuid4().hex` secret is generated. Tokens are invalid after restart and any in-process code can read the secret. The warning is logged but enforcement is absent.

**Action:** fail startup (or refuse JWT issuance) when `QNAI_JWT_SECRET` is empty outside explicit dev opt-in.

---

## 8. INFO — Dependency CVE scan

`uvx pip-audit -r <118 deps>` (OSV) → **No known vulnerabilities found.**
(`quant-nanggroe-ai` local package skipped — not on PyPI.)

Note: 253 packages in `.venv/Lib/site-packages`; `pip` is not installed in the venv, so the scan used `uv pip freeze` + `pip-audit`. No CVEs against the pinned versions.

---

## Positive notes (no finding)

- `.env.example` / `.env.template` contain only blank/placeholder values — no leaked keys.
- `config/system_config.yaml` references API keys via `${ENV_VAR}` substitution (lines 171, 182, 191) — not hardcoded.
- `pii_redaction.py` and `security.py` show intentional secret-handling awareness.
- Auth module itself (HMAC-SHA256, expiry, revocation, RBAC hierarchy) is sound — the weaknesses are in wiring/defaults, not the primitive.

---

## Recommended order of remediation

1. **CRITICAL** — rotate & purge MT5 creds (#1), then add config files to `.gitignore`.
2. **HIGH** — fix dev-mode auth fallback (#4) and kill-switch inertness (#2, #3) before any live deployment.
3. **MEDIUM** — sandbox strategy `exec` (#5) and lock down broker registration (#6).
4. **LOW** — enforce JWT secret presence (#7).
