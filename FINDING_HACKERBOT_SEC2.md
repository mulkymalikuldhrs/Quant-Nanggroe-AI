# FINDING — HACKERBOT SEC RE-AUDIT #2

**Agent:** @dhaherhackerbot (Security)
**Repo:** `D:\repositories\Quant-Nanggroe-AI-worktree`
**Scope:** `quant_nanggroe/` (archive/, .kilo/, .verify_venv/ excluded)
**Version audited:** 6.1.0

---

## Summary

| # | Area | Severity | Status |
|---|------|----------|--------|
| 1 | Secrets in git tracking | **MEDIUM** | Partially confirmed — 1 tracked file |
| 2 | CORS config | **PASS** | Restricted, no wildcard |
| 3 | JWT boot sentinel | **PASS** | Real + enforced (2 layers) |
| 4 | Auth bypass | **CRITICAL** | Unauthenticated open proxy |
| 5 | SQL injection | **PASS** | No first-party string-built SQL |
| 6 | Dependency CVEs | **MEDIUM** | Unpinned floors below fixed versions |

---

## 1. Secrets / git tracking — MEDIUM

`.gitignore` coverage is correct:
- `.gitignore:49` `.env`
- `.gitignore:52` `.secrets-local/`
- `.gitignore:54` `config/mt5_accounts.yaml`
- `.gitignore:60` `.qna-secrets/`, `:64` `metatrader-mcp.env`, `:65` `*.mcp.env`

Verified:
- `.secrets-local/` — does not exist on disk, not tracked. **Prior report of a leak here re-confirmed as FALSE POSITIVE.**
- `.env` — exists on disk, **not tracked**, ignore rule active (`git check-ignore` → `.gitignore:49`). Clean.
- `git ls-files | grep -i secret` → no secret-bearing files.

**Finding — `config/mt5_accounts.yaml` is TRACKED despite being gitignored.**
`.gitignore` has no effect on already-tracked files, so the ignore rule at `.gitignore:54` is silently inert for this path.

- Tracked blob content (`config/mt5_accounts.yaml:1-10`) contains **env-var placeholders only** (`${QNA_MT5_LOGIN}`, `${QNA_MT5_SERVER}`, `${QNA_MT5_PASSWORD}`). **No credentials are currently exposed.**
- Working copy is identical to HEAD (clean `git status`), 3/3 placeholders intact.

**Risk:** the file is live-tracked. Any operator who edits it in place with real broker credentials — which the header comment explicitly (and incorrectly) tells them is safe: *"This file is gitignored"* — will have those credentials staged by `git add -A` with no ignore protection. This is a latent live-broker credential leak.

**Note:** three example variants are also tracked and are appropriate: `.env.example`, `.env.template`, `config/mt5_accounts.example.yaml`, `config/mt5_accounts.yaml.example`.

---

## 2. CORS — PASS

`quant_nanggroe/api/app.py:254-260`
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=settings.cors_methods,
    allow_headers=settings.cors_headers,
)
```

Defaults at `quant_nanggroe/config/settings.py:176-187`:
- `cors_origins` → `["http://localhost:3000", "http://localhost:8000", "http://localhost:8080"]`
- `cors_methods` → explicit verb list (no `*`)
- `cors_headers` → `["Authorization", "Content-Type", "X-API-Key", "X-Request-ID"]` (no `*`)

**No wildcard anywhere.** `allow_credentials=True` is correctly paired with an explicit origin allowlist. Config is env-overridable — deployment must set real production origins; a wildcard override would be accepted by the code, so this is config-discipline dependent but the shipped default is correct.

---

## 3. JWT boot sentinel — PASS (enforced, two layers)

**Layer 1 — `quant_nanggroe/api/app.py:196-207`**
```python
_jwt = _os.environ.get("QNAI_JWT_SECRET", "") or settings.jwt_secret
_WEAK = {"__UNSET_QNAI_JWT_SECRET__", "change-me-in-production", ""}
if _jwt in _WEAK:
    raise RuntimeError("REFUSING TO BOOT: QNAI_JWT_SECRET is unset or a known-default. ...")
```
Runs inside `create_app()` **before** the `FastAPI(...)` instance is constructed (`app.py:221`) — fail-closed, unreachable-to-skip on the normal boot path. Also blocks the extra weak value `change-me-in-production` and empty string, not just the sentinel.

**Layer 2 — `quant_nanggroe/api/middleware.py:45-52`**
`AuthMiddleware` refuses construction if built without an injected auth object and `QNAI_JWT_SECRET` is unset, rather than silently generating an ephemeral key.

Sentinel default declared at `quant_nanggroe/config/settings.py:192-193`. **Check is real and enforced.**

---

## 4. Auth bypass — CRITICAL

### 4a. Unauthenticated open proxy at `/api/otto/*` — **CRITICAL**

`quant_nanggroe/api/app.py:303`
```python
exclude_paths={"/api/otto"}
```
`quant_nanggroe/api/middleware.py:69`
```python
if not path.startswith("/api/") or path.startswith("/api/otto"):
    return await call_next(request)
```

The entire `/api/otto/*` subtree is excluded from JWT **and** API-key auth. The router mounted there is a catch-all pass-through:

`quant_nanggroe/api/routes/otto_proxy.py:6-25`
```python
@router.api_route("/{full_path:path}", methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS","HEAD"])
async def proxy(request: Request, full_path: str):
    target_url = f"http://localhost:8765/{full_path}" + ...
    headers = dict(request.headers); headers.pop("host", None)
    body = await request.body()
    response = await client.request(method, target_url, headers=headers, content=body, timeout=30.0)
    return Response(content=response.content, status_code=response.status_code, headers=dict(response.headers))
```

Compounding issues in that 25-line file:
- **No authentication, no authorization, no rate limit** on any method incl. write verbs.
- **Attacker-controlled path** (`otto_proxy.py:14`) interpolated straight into the target URL — reaches every route on the Otto MCP service, which is presumably bound to loopback precisely *because* it is unauthenticated. This endpoint publicly re-exposes that trusted-local service.
- **Query string forwarded verbatim** (`:14`), **all client headers forwarded** minus `host` (`:17-19`) — lets a caller inject arbitrary auth/control headers into the internal service.
- **All upstream response headers reflected back** (`:25`), including hop-by-hop and any internal `Set-Cookie`.
- **SSRF surface**: encoded traversal in `full_path` (`..%2F`, `%2e%2e/`) can attempt to escape the `localhost:8765/` prefix.

**Impact:** full unauthenticated read/write access to the internal Otto MCP service from any client that can reach the API. Highest-severity item in this audit.

**Direction:** put `/api/otto` behind the same auth as the rest of `/api/*`; if it must stay public, allowlist paths/methods and strip forwarded headers.

### 4b. Non-`/api/` paths unauthenticated — LOW (by design)

`quant_nanggroe/api/middleware.py:69` — anything not starting with `/api/` skips auth (static dashboard UI). Acceptable for static assets; only a risk if a future data route is mounted outside `/api/`.

### 4c. Public exclude list — INFO

`quant_nanggroe/api/middleware.py:55-56`: `/health`, `/metrics`, `/docs`, `/openapi.json`, `/favicon.ico` (+ `/docs`, `/redoc`, `/openapi.json` prefixes at `:65`). Standard. Note `/metrics` unauthenticated exposes Prometheus counters incl. per-endpoint paths (`app.py:236-251`) — minor internal-topology disclosure.

### 4d. No dev-mode backdoors — PASS

Grep across `quant_nanggroe/api/` for `dev_mode|devmode|skip_auth|auth_disabled|bypass|DISABLE_AUTH|allow_anonymous|no_auth` returned **no toggle-based bypass**. `middleware.py:57` comment *"Auth is always enforced. No bypass mechanisms."* is accurate for env toggles — the real bypass is the structural `/api/otto` carve-out in 4a, not a flag. `middleware.py:58-59` correctly logs a warning and still enforces auth when `QNAI_API_KEY` is unset (fail-closed).

---

## 5. SQL injection — PASS

Grep over `quant_nanggroe/engine/` for `execute(f"`, `executemany(f`, `.format(`, `%`-interp and `+` concatenation in execute calls: **zero matches**.

Repo-wide `execute(\s*f["']` matched only vendored third-party code inside `.verify_venv/` (`pandas/io/sql.py:2455`, `pandas/tests/io/test_sql.py:566,573,587,593,4082`) — not first-party, not shipped, out of scope.

**No string-formatted SQL in application code.**

---

## 6. Dependency CVEs — MEDIUM

`pyproject.toml` uses **unpinned `>=` floors with no upper bounds and no committed lockfile**. A clean install resolves to current versions (likely patched), but the declared floors permit known-vulnerable builds, and any environment resolved at an older date is unverifiable. Listing floors that sit below a known fix:

| Package | Declared | pyproject.toml | Known issue at/below floor |
|---|---|---|---|
| `aiohttp` | `>=3.9` | :38 | CVE-2024-23334 static-route path traversal; CVE-2024-30251 DoS. Fixed 3.9.2 / 3.9.4 |
| `cryptography` | `>=41.0` | :52 | CVE-2023-50782 Bleichenbacher; CVE-2024-26130 NULL-deref. Fixed 42.0.0 / 42.0.4 |
| `torch` | `>=2.0` (opt: ml, rl) | :61, :84 | CVE-2024-31580 / CVE-2024-31583 heap overflow. Fixed 2.2.0 |
| `langchain` | `>=0.3` | :16 | Historical SSRF/code-exec class in langchain-community chains; floor is post-0.3 so mostly clear, but unbounded |
| `fastapi` | `>=0.100` | :34 | ReDoS in older python-multipart pulled transitively (CVE-2024-24762); ensure `python-multipart>=0.0.7` |
| `redis` | `>=5.0` | :32 | Ensure ≥5.0.1 (async connection reuse, CVE-2023-28859 class) |
| `sqlalchemy` `>=2.0` :30, `uvicorn` `>=0.24` :35, `requests`(transitive), `pydantic` `>=2.0` :22 | — | No specific CVE at floor; unbounded ranges only |

**Systemic finding (the actual risk here):** no upper bounds + no lockfile means builds are non-reproducible and unauditable. Version listing above is floor-based per task scope; no fix applied.

---

## Priority

1. **MEDIUM (DOWNGRADED from CRITICAL — code-truth 2026-08-03 devbot):** `/api/otto/*` — this finding describes an EARLIER code state. Current `api/middleware.py:69-72` requires `Authorization` header (401 if missing) for ALL `/api/*` including `/api/otto` — there is NO `exclude_paths={"/api/otto"}` carve-out nor `path.startswith("/api/otto")` bypass in the current dispatch. So it is NOT unauthenticated. Residual = authenticated SSRF to localhost:8765 + no path-traversal guard + forwards all headers. `otto_proxy.py` still exists (1237b), DELETE agreed (zero live referrers). See `QNA_AUDIT_DEBAT.txt`.
2. **MEDIUM** — `config/mt5_accounts.yaml` tracked in git despite `.gitignore:54`; header comment falsely claims it is ignored
3. **MEDIUM** — unpinned dependency floors below known fixed versions; no lockfile
4. **LOW** — `/metrics` unauthenticated endpoint-path disclosure

**Clean:** CORS (no wildcard), JWT boot sentinel (enforced, two layers), SQL injection (none), env-toggle auth bypass (none), `.secrets-local/` and `.env` (properly ignored, untracked).


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
