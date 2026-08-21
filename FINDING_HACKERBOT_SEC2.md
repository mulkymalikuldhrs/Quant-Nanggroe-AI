# QNA Security Audit — hackerbot Phase 4/5

Audited: `quant_nanggroe/` (excluded archive/, .kilo/, .verify_venv/)
Date: 2026-08-22

## Severity Summary

| Severity | Count |
|----------|-------|
| CRITICAL | 1 |
| HIGH | 1 |
| MEDIUM | 2 |
| LOW | 0 |
| **Total** | **4** |

---

## Findings

### CRITICAL — `/api/otto` authenticated open proxy (auth carve-out)

**Location:** `quant_nanggroe/api/app.py:303` (exclude_paths), `quant_nanggroe/api/middleware.py:69` (auth skip), `quant_nanggroe/api/routes/otto_proxy.py:6-25`

`api/app.py:303`: `exclude_paths=["/api/otto"]` — auth is skipped for this path.
`api/middleware.py:69`: `if path.startswith("/api/otto"): return response` — raw bypass.
`api/routes/otto_proxy.py:6-25`: catch-all `@router.api_route("/{full_path:path}")` over all 7 verbs, forwards attacker-controlled path + query string + headers to `http://localhost:8765`, reflects response headers back.

Unauthenticated open proxy exposing a loopback MCP service. SSRF + encoded-traversal surface via `full_path`.

**Impact:** RCE on loopback MCP service, credential exfiltration, internal port scanning.

**Fix:** Remove `/api/otto` from exclude_paths; require auth on all non-static routes. Add path allowlisting + block loopback/LAN targets.

---

### HIGH — RiskManager / kill switch unreachable on live execution path

**Location:** `quant_nanggroe/engine/execution/manager.py:79-196` (execute_order + _run_guards)

`RiskManager.check_trade()` exists at `quant_nanggroe/engine/risk/manager.py:316` (9-checkpoint gate + kill_switch.is_active) — but the live execution path (`ExecutionManager.execute_order`) NEVER calls it.

`manager.py:166-196` (`_run_guards`) only checks: cooldown, max_position, whitelist. Does NOT call `check_trade` or `kill_switch.is_active`.

**Two sub-gaps:**
1. **ExecutionManager bypass:** `manager.py:79` `execute_order` — no `risk.can_trade()` call. P0 fix adds it at `:367` (RISK-PATH) but live path is `:79`.
2. **ExecutionTool docstring-only guard:** `agents/tools/execution.py:230` docstring claims `KillSwitchActiveError` is raised; body never checks kill switch (line 40 imports it, line 659 catches it, but it's never thrown).

**Impact:** Veto cannot be bypassed — but only on the agent/API path (`risk_gate_bridge.py:290`). Direct execution path (`ExecutionManager`) has zero risk enforcement.

**Fix:** Add `self.risk.check_trade()` at top of `ExecutionManager.execute_order()` (line 79). Wire `risk_gate_bridge.RiskGateBridge` into `ExecutionManager` construction.

---

### MEDIUM — `.env` tracked in git with live secrets

**Location:** repo root `.env` (git ls-files confirms tracked)

Prior audit (2026-08-05) retracted: `.env` was claimed "untracked" — that retraction was itself WRONG.

`git ls-files`: `.env` IS listed as tracked.
`.env` contains populated live values: `QNA_MT5_PASSWORD`, `QNA_MT5_LOGIN`, `QNA_MT5_SERVER`, `QNAI_JWT_SECRET`, `QNAI_ENCRYPTION_KEY`, `QNAI_API_KEY`.

`.gitignore` has NO rule matching `.env` (`git check-ignore -v .env` → fires nothing).

**Impact:** Broker credentials + JWT secret + API key in version history across all commits.

**Fix:** `git rm --cached .env` immediately; add `.env` to `.gitignore:49`; rotate ALL secrets.

Note: `config/mt5_accounts.yaml` is tracked but uses env-var placeholders only (`${QNA_MT5_PASSWORD}`) — no real leak. `dashboard/.env.local` re-exposes `QNAI_API_KEY` as `NEXT_PUBLIC_API_KEY` (ships to browser) — but git tracking status needs verification.

---

### MEDIUM — `credentials.py` sets `QNAI_API_KEY` at runtime

**Location:** `quant_nanggroe/api/routes/credentials.py:45-46`

`if not os.environ.get("QNAI_API_KEY"): os.environ["QNAI_API_KEY"] = key`

This route mutates `os.environ` on the running process — a TOCTOU window where an authenticated user can inject an API key override. Combined with the `middleware.py:58` check (`if not os.environ.get("QNAI_API_KEY")` → warn), a user who authenticates once via `credentials.py` can flip the sentinel state.

**Impact:** Post-authentication environment mutation; potential auth-bypass if the set value is accepted by downstream middleware in-process.

**Fix:** Use a dedicated secret store; never write `os.environ` from an HTTP route.

---

## Clean (Verified PASS)

- **MT5Broker credential handling** — `quant_nanggroe/connectors/mt5_broker.py:25`: `login: int = 0, password: str = "", server: str = ""` — constructor params, no hardcoded defaults. Credentials passed from env, never logged. ✓
- **No hardcoded secrets repo-wide** — grep for `password|secret|api_key|token.*=.*` literal patterns in `quant_nanggroe/*.py` returns 0. All env lookups use `os.environ.get("NAME", "")`. ✓
- **MT5 fail-closed** — `mt5_broker.py:90, 95, 66-69`: `RuntimeError` on init failure, no silent paper fallback. `get_balance/get_positions/get_equity` raise `RuntimeError("not connected")`. ✓
- **CORS** — `api/app.py:254-260`: explicit allowlist, no wildcard, paired with `allow_credentials=True`. ✓
- **JWT sentinel** — `api/app.py:198-207`: raises `RuntimeError` before `FastAPI()` construction on `__UNSET_QNAI_JWT_SECRET__`, `change-me-in-production`, `""`. `middleware.py:45-52`: refuses to build `AuthMiddleware` with ephemeral key. ✓
- **JWT HS256 + constant-time compare** — `security/auth.py:274`: HS256 pinned in header, `hmac.compare_digest`, expiry + revocation enforced. No alg-none bypass. ✓
- **Kill switch reachable on agent/API path** — `risk_gate_bridge.py:290`: `check_auto_activate` + `is_active` + `check_trade` all called. `autonomous_cycle.py:1002` + `:1023`: syncs `is_active` via cross-process file. ✓
- **Kill switch fail-closed** — `kill_switch.py:55-57`: corrupt state file ⇒ ACTIVE (halt). `kill_switch.py:304-314`: stale daily limit auto-expires. Env `QNA_KILL_SWITCH_STATE_FILE` gates persistence (`kill_switch.py:41`). ✓
- **Cross-proc persistence** — `kill_switch.py:41` env-gated; `kill_switch.py:279,327` early-return if unset. Production bridge calls `configure_kill_switch_file()`. ✓

---

## Retracted Prior Findings (not re-raised)

- `.secrets-local/` credential leak — FALSE POSITIVE (dir doesn't exist, not tracked, `.gitignore:52` covers it). ✓ re-confirmed
- `config/mt5_accounts.yaml` held live creds — FALSE (env-var placeholders only). ✓ re-confirmed
