# DOC_GAPS.md — Quant-Nanggroe-AI Documentation Audit

**Audit date:** 2026-07-09
**Scope:** `docs/` (20 files), `README.md` (241 lines), `CHANGELOG.md`, source module docstrings, `pyproject.toml` vs `requirements.txt`

---

## 1. CRITICAL: pyproject.toml vs requirements.txt Misalignment

These two dependency files describe **completely different stacks** and are not aligned.

| Dimension | pyproject.toml | requirements.txt |
|-----------|---------------|-----------------|
| Web framework | FastAPI + Uvicorn | Flask + Gunicorn + Gevent |
| Agent framework | LangChain + LangGraph | Direct OpenAI/Anthropic API |
| Serialization | Pydantic v2 | Pydantic v2 |
| Database | SQLAlchemy + Alembic + Redis | SQLAlchemy + Alembic + Redis (shared) |

**Packages in pyproject.toml NOT in requirements.txt:**
langgraph, langchain, langchain-openai, langchain-anthropic, langchain-google-genai, langchain-core, pydantic-settings, scipy, ccxt, fastapi, uvicorn, httpx, click, scikit-learn

**Packages in requirements.txt NOT in pyproject.toml:**
flask, flask-socketio, python-socketio, werkzeug, jinja2, markupsafe, itsdangerous, gunicorn, gevent, gevent-websocket, aiofiles, websockets, requests, feedparser, openai, anthropic, tiktoken, psycopg2-binary, numexpr, beautifulsoup4, python-dotenv, cryptography, psutil, croniter, pyyaml, python-dateutil, python-multipart, jsonschema, toml, cachetools, diskcache, watchdog, pathspec, pillow, google-auth, google-auth-oauthlib, textdistance, opentelemetry-api, opentelemetry-sdk

**Verdict:** Two stacks diverge completely. requirements.txt appears to be a legacy Flask-based system, while pyproject.toml is the current LangGraph/FastAPI stack. **One should be removed** and the remaining one updated to reflect the actual runtime.

**→ FIX:** Delete the file that represents the deprecated stack. Add `openai`, `anthropic`, `python-dotenv`, `cryptography`, `psutil`, `watchdog` to pyproject.toml if still needed.

---

## 2. docs/ Folder — Completeness Audit

| # | File | Lines | Owned by QNAI? | Quality |
|---|------|-------|----------------|---------|
| 1 | AGENT_ARCHITECTURE.md | 662 | ❌ (AI-MultiColony-Ecosystem) | Good but wrong repo |
| 2 | ARCHITECTURE.md | 771 | ✅ | Excellent — comprehensive |
| 3 | BLUEPRINT.md | 79 | ✅ | Thin, in Indonesian |
| 4 | BUILD_PLAN.md | 56 | ✅ | Thin, in Indonesian |
| 5 | CHANGELOG.md | 276 | ✅ | Good — duplicates root CHANGELOG |
| 6 | DECISION_LOG.md | 398 | ✅ | Good — ADR-style records |
| 7 | EVOLUTION_MANIFEST.md | 54 | ✅ | Thin |
| 8 | MEMORY_ARCHITECTURE.md | 622 | ❌ (AI-MultiColony-Ecosystem) | Good but wrong repo |
| 9 | MERGE_PLAN.md | 464 | ✅ | Good |
| 10 | MIGRATION_PLAN.md | 179 | ✅ | Partial — work in progress |
| 11 | RESEARCH.md | 649 | ✅ | Good — benchmarking & references |
| 12 | RISK_REGISTER.md | 277 | ✅ | Good — detailed |
| 13 | ROADMAP.md | 370 | ✅ | Good — detailed phases |
| 14 | SERVICES_GUIDE.md | 97 | ✅ | Thin, references TS not Python |
| 15 | SKILL_REGISTRY.md | 404 | ❌ (AI-MultiColony-Ecosystem) | Good but wrong repo |
| 16 | STORAGE.md | 37 | ✅ | Very thin — stub level |
| 17 | SYSTEM_AUDIT_LOG.md | 68 | ✅ | Thin — one-time audit snapshot |
| 18 | SYSTEM_DESIGN.md | 850 | ✅ | Excellent — most thorough doc |
| 19 | TOOL_REGISTRY.md | 445 | ❌ (AI-MultiColony-Ecosystem) | Good but wrong repo |
| 20 | USER_GUIDE.md | 62 | ✅ | Very thin — high level only |

### docs/ Gaps Summary

**Cross-repo contamination:** 4 of 20 files (AGENT_ARCHITECTURE, MEMORY_ARCHITECTURE, SKILL_REGISTRY, TOOL_REGISTRY) are from the **AI-MultiColony-Ecosystem** repo (Cluster 2), not Quant-Nanggroe-AI (Cluster 3). They describe a different system's architecture.

**Missing critical docs:**
- **No API reference** — the 6 API route groups (Market, Trading, Agents, Backtest, Portfolio, WebSocket) have no endpoint docs anywhere
- **No broker setup guide** — how to configure Alpaca, Binance, CCXT, IBKR, MT5, Polymarket, Solana
- **No backtesting tutorial** — how to write and run a strategy end-to-end
- **No quickstart guide** — step-by-step from clone to running
- **No testing guide** — how to run tests, test conventions
- **No database schema docs** — PostgreSQL/Redis schemas undocumented
- **No live trading ops guide** — how to start/manage live trading, what to watch
- **No strategy writer's guide** — how to implement a custom strategy
- **No factor engine docs** — Alpha101, GTJA191, Qlib158, Barra factor catalogs unindexed
- **No exchange integration docs** — each of the 15+ exchange connectors lacks a setup doc

**Thin docs needing expansion:**
- `USER_GUIDE.md` (62 lines) — lacks detailed usage scenarios
- `STORAGE.md` (37 lines) — stub
- `EVOLUTION_MANIFEST.md` (54 lines) — thin
- `BLUEPRINT.md` (79 lines) — in Indonesian only
- `BUILD_PLAN.md` (56 lines) — in Indonesian only
- `SERVICES_GUIDE.md` (97 lines) — references TypeScript services that may not exist in Python

---

## 3. README.md — Coverage Gaps

| Required Section | Present? | Quality |
|-----------------|----------|---------|
| Installation | ✅ Partial | Frontend uses `cd frontend` (no `frontend/` dir exists); backend uses `cd backend` (no `backend/` dir exists) |
| Broker setup | ❌ **Missing** | No mention of Alpaca/Binance/IBKR/MT5 setup |
| API keys config | ❌ **Missing** | No link to `.env.example` or instructions |
| Quick start / Running | ✅ Partial | Missing actual `git clone` at root level |
| Architecture description | ✅ Good | ASCII diagram, missing LangGraph DAG detail |
| Multi-agent system description | ❌ **Missing** | No mention of agent council, debate, personas |
| Risk management description | ❌ **Missing** | No mention of kill switch, drawdown limits, correlation monitors |
| Backtesting guide | ❌ **Missing** | Code snippet shows `from quant_nanggroe import BacktestEngine` but no setup info |
| Live trading guide | ❌ **Missing** | Not mentioned at all |
| Configuration reference | ❌ **Missing** | No env vars documented |
| Testing | ❌ **Missing** | No pytest/CI info |
| Project structure map | ❌ **Missing** | No tree or file layout |

**Note:** The installation section references `frontend/` and `backend/` directories that don't exist in the repo — it's a React/Vite frontend at root level and Python modules at `quant_nanggroe/`. The Docker instructions use `docker-compose up -d` without specifying which compose file.

---

## 4. CHANGELOG.md — Assessment

- **Root CHANGELOG.md** (98 lines): Covers v15.3.1 → v12.0.0. Detailed but mixed EN/ID.
- **docs/CHANGELOG.md** (276 lines): Longer, more detailed, but duplicates root.
- **Gaps:** No sections for upcoming changes, no migration notes between major versions.

---

## 5. Source Module Docstrings

### quant_nanggroe/ (main package)
| Metric | Count | Coverage |
|--------|-------|----------|
| Modules with docstrings | 311/311 | **100%** ✅ |
| Classes with docstrings | 749/750 | **99.9%** ✅ |
| Top-level functions | 689/819 | **84%** ⚠️ |
| Methods | 1858/2456 | **76%** ⚠️ |

**Missing docstrings (130 functions + 598 methods):**
- All 6 geopolitics agents (american_order, chinese_order, european_order, islamic_finance, multipolar) — methods lack any docstring
- All 6 persona agents (cathie_wood, michael_burry, peter_lynch, ray_dalio, stanley_druckenmiller, warren_buffett) — methods lack docstrings
- debate/graph.py — 3/4 methods missing
- debate/reflection.py — 3/13 methods missing
- crypto/agent.py, forex/agent.py, macro/agent.py — method docstrings missing
- Various tools files (backtest, competition, emotional, flow, geopolitical, screener) — partial coverage
- engine/ submodules — many methods undocumented

### packages/hermes-quant/src
| Metric | Count | Coverage |
|--------|-------|----------|
| Modules with docstrings | 24/26 | **92%** ✅ |
| Classes with docstrings | 30/32 | **94%** ✅ |
| Top-level functions | 3/5 | **60%** ⚠️ |
| Methods | 127/178 | **71%** ⚠️ |

### packages/deer-flow/backend
| Metric | Count | Coverage |
|--------|-------|----------|
| Modules with docstrings | 389/515 | **76%** ⚠️ |
| Classes with docstrings | 379/791 | **48%** ❌ |
| Top-level functions | 1628/3250 | **50%** ❌ |
| Methods | 1178/3456 | **34%** ❌ |

**Verdict:** quant_nanggroe/ has good module/class coverage but methods lag at 76%. deer-flow is severely under-documented.

---

## 6. Root-Level Doc Files

| File | Lines | Assessment |
|------|-------|------------|
| ARCHITECTURE.md | 536 | ✅ Excellent — 5-layer stack deep-dive |
| DEPLOYMENT_STATUS.md | 114 | ✅ Good — platform readiness matrix |
| deployment-guide.md | 477 | ✅ Good — multi-platform deploy instructions |
| CONTRIBUTING.md | 133 | ⚠️ Generic template, no project-specific setup |
| SECURITY.md | 15 | ⚠️ Very thin — only vulnerability reporting |
| CODE_OF_CONDUCT.md | — | Generic file |
| CONVENTIONS.md | — | Not reviewed |
| FLOW_START.md | — | Not reviewed |

---

## 7. Summary of Action Items

### 🔴 High Priority (blocking for new users)
1. **Reconcile pyproject.toml vs requirements.txt** — pick one stack, delete the other
2. **Fix README installation paths** — `cd frontend` and `cd backend` don't exist
3. **Add broker/API key setup guide** to README
4. **Add quickstart section** to README (clone → configure → run in 5 steps)

### 🟡 Medium Priority (missing production docs)
5. **Add API reference** for all 6 route groups
6. **Add multi-agent system overview** to README
7. **Add risk management overview** to README
8. **Add live trading ops guide**
9. **Prune 4 cross-repo docs** that belong to AI-MultiColony-Ecosystem, not QNAI
10. **Expand USER_GUIDE.md** beyond 62 lines
11. **Add backtesting tutorial**
12. **Add database schema docs**

### 🟢 Low Priority (incremental polish)
13. **Fill remaining method docstrings** (~600 in quant_nanggroe, ~2300 in deer-flow)
14. **Add testing guide**
15. **Add strategy writer's guide**
16. **Translate BLUEPRINT.md and BUILD_PLAN.md** to English
17. **Consolidate root and docs/ CHANGELOG.md** into one
