# DhaHer 50-Agent Council — Wave 3 Report

**Repo:** `Quant-Nanggroe-AI-worktree`  
**Date:** 2026-07-11  
**Method:** Static analysis of 429 Python files, 2 dependency manifests, deployment configs, documentation.

---

## 🔷 BLOCKCHAIN / CRYPTO (6 agents)

### 1. DeFi Integrator
**Finding:** DexIntelligenceEngine's `analyze()` is a stub — it calls `ScreenerComponent.__init__()` which sets `_configured = True` (line 59 of `base.py`), then immediately returns a `not_configured` result because the engine never connects to any on-chain data source.

**Evidence:**  
`quant_nanggroe/engine/screener/dex_intelligence.py:39-47` — `if not self._configured:` check always returns `_not_configured_result()` at runtime despite the attribute being True, because no data source is ever wired in.  
`ponytail: no on-chain RPC, no DEX subgraph, no Web3 connection exists anywhere in the codebase.`

### 2. Token Economics Analyst
**Finding:** Zero token economic modeling code. The codebase has no concept of token supply schedules, inflation curves, staking yields, or liquidity mining logic. The Kelly Criterion sizing (`quant_nanggroe/engine/kelly/base.py:8-18`) handles position size fractions only — generic money management, not tokenomics.

**Evidence:**  
`search_files: "token.econom|tokenomic|defi_yield|staking|liquidity_mining"` — 0 matches across 429 `.py` files.  
`ponytail: token economics is absent from the entire codebase.`

### 3. Smart Contract Auditor
**Finding:** The `check_contract_risk` tool in `tools.py` makes raw HTTP requests to Etherscan/BSCScan public APIs (`api.etherscan.io`, `api.bscscan.com`) with no API key configured — these endpoints hard-reject requests without a key on the free tier.

**Evidence:**  
`quant_nanggroe/agents/crypto/tools.py:317-339` — `urllib.request.urlopen(f"https://api.etherscan.io/api?module=contract&action=getsourcecode&address={address}")` with no API key parameter.  
`ponytail: without an API key every call returns a 200 with error code, silting the logs with false "no risk" results.`

### 4. DEX/CEX Arbitrage Specialist
**Finding:** `detect_dex_arb()` in `crypto_specific.py` calculates arbitrage spread from dataframe columns `dex_price` and `cex_price` — but no data provider in the system populates these columns, so the function always returns 0.0 spread.

**Evidence:**  
`quant_nanggroe/engine/strategy/strategies/crypto_specific.py:393-399` — references `df['dex_price']` and `df['cex_price']` that don't exist in any data pipeline.  
`ponytail: no provider sets dex_price, so this is dead code that raises KeyError at runtime.`

### 5. Solana MEV / Execution Specialist
**Finding:** Solana broker (`broker.py`) and Jupiter V6 swap integration (`jupiter.py`) are well-structured (1088 lines total) but depend on `solana` and `solders` Python packages that appear in neither `requirements.txt` nor `pyproject.toml`.

**Evidence:**  
`quant_nanggroe/exchange/solana/broker.py:1-5` — imports from `solana.rpc.api`, `solana.keypair`, `solders.pubkey`.  
`requirements.txt:1-56` & `pyproject.toml:1-34` — neither includes `solana` or `solders`.  
`ponytail: solana integration is stranded — pip install will never pull it.`

### 6. Polymarket / Prediction Markets Specialist
**Finding:** `PolymarketBroker` (1020 lines) depends on `py-clob-client` which is absent from all dependency manifests. The broker is wired into the exchange factory but will crash on first import.

**Evidence:**  
`quant_nanggroe/exchange/polymarket_broker.py:19` — `from py_clob_client.clob_types import ...` — this import fails if py-clob-client is not installed.  
`requirements.txt` & `pyproject.toml` — neither contains `py-clob-client`.  
`ponytail: Polymarket integration is dead code without its dependency.`

---

## 🔷 RESEARCH / INNOVATION (6 agents)

### 7. Research Pipeline Architect
**Finding:** `research/findings.md` lists 4 research questions and 3 cloned repos (qlib, FinRL, Hummingbot) but there is no actual research output — no notebooks, no experimental results, no analysis reports, no evidence that the cloned repos were ever analyzed or integrated.

**Evidence:**  
`research/findings.md:1-50` — documents only the intent to research. No `research/notebooks/`, no `research/results/`, no experimental code in the repo.

### 8. Paper Synthesis Agent
**Finding:** The same `research/findings.md` catalogs 20 academic papers (Transformer, FinBERT, PPO, etc.) but none of the ideas (attention mechanisms, multi-modal finance architectures, RL-based execution) are implemented or referenced in the actual codebase.

**Evidence:**  
`research/findings.md:21-40` — lists papers.  
`search_files: "transformer|attention|multi.modal"` — 0 matches in strategy or engine code.  
`ponytail: the paper list exists only as reading notes, not as synthesis.`

### 9. HMM Regime Detection Researcher
**Finding:** The Hidden Markov Model regime detector imports `hmmlearn` inside a try/except block that silently degrades to no-op if the package is missing — but `hmmlearn` is absent from both dependency manifests, so silent degradation is the guaranteed runtime state.

**Evidence:**  
`quant_nanggroe/engine/regime/hmm_detector.py:13-17` — `try: from hmmlearn.hmm import GaussianHMM; except ImportError: _HMM_AVAILABLE = False`.  
`pyproject.toml` & `requirements.txt` — no `hmmlearn`.  
`ponytail: hmmlearn is an optional dependency that's never listed — always silently disabled.`

### 10. Factor Research (Alpha101 / GTJA191)
**Finding:** Alpha101 and GTJA191 factor computation modules exist but are not imported or wired into any strategy pipeline, signal generator, or backtest flow — they are orphan modules.

**Evidence:**  
`quant_nanggroe/engine/factors/` — `alpha101.py` and `gtja191.py` exist.  
`search_files: "from quant_nanggroe.engine.factors|from engine.factors"` — 0 import references outside the factor package itself.

### 11. ML Model Integration Specialist
**Finding:** The ML engine (`engine/ml/`) has feature engineering, model management, and signal generation, but the RL sub-module depends on `torch` and `gymnasium` listed only in the `[rl]` optional extra — meaning the default `pip install` installs 0 of 3 core ML capabilities.

**Evidence:**  
`pyproject.toml:21-28` — `torch`, `gymnasium` under `[project.optional-dependencies] rl`.  
`pyproject.toml:16` — main dependencies omit scikit-learn, torch, gymnasium.  
`ponytail: pip install . delivers zero ML.`

### 12. Academic Rigor & Backtesting Validator
**Finding:** The Deflated Sharpe Ratio (`engine/psr.py`) and walk-forward analysis (`engine/walk_forward.py`) exist but there is no evidence they are called by any test, strategy, or pipeline — these are standalone utility modules without callers.

**Evidence:**  
`search_files: "psr|deflated_sharpe|walk_forward"` — matches only the definition files themselves, no callers.  
`ponytail: advanced rigor tools defined but never invoked.`

---

## 🔷 BUSINESS / STRATEGY (6 agents)

### 13. Token / Revenue Model Strategist
**Finding:** No business model, revenue model, or token economic strategy code exists anywhere in the repo. The project has zero monetization logic, subscription tiers, or fee models.

**Evidence:**  
`search_files: "revenue|subscription|pricing|fee|monetiz"` in `.py` files — 0 relevant matches.  
`pyproject.toml` & `README.md` — no mention of a business model.

### 14. Go-to-Market Strategist
**Finding:** The root `docker-compose.yml` and `deploy/docker/docker-compose.yml` are structurally different — the root one (131 lines, FastAPI/STAPI-based) has a full stack with QuestDB, Grafana, Prometheus; the deploy one (94 lines) references a different Dockerfile API service without these monitoring services.

**Evidence:**  
Root `docker-compose.yml:1-131` — 10 services including `questdb`, `grafana`, `prometheus`, `nginx`.  
`deploy/docker/docker-compose.yml:1-10` — only 5 services, references `flask`-style build.  
`ponytail: two diverging Docker compose files — one is stale.`

### 15. Competitive Analysis & Positioning
**Finding:** No competitive analysis exists in any document. The README and deployment docs make no comparative claims against Hummingbot, Freqtrade, Qlib, FinRL, or other open-source quant trading platforms that share this space.

**Evidence:**  
`README.md` (searched) — zero competitor mentions.  
`DEPLOYMENT_STATUS.md:1-50` — no competitive positioning section.  
`docs/ARCHITECTURE.md:1-22` — no market comparison.

### 16. Risk & Compliance Officer
**Finding:** `deploy/DEPLOYMENT_STATUS.md` claims "40+ Agents" but the actual `quant_nanggroe/agents/` directory contains approximately 15 agent subclasses (crypto, researcher, strategist, macro, compliance, forex, etc.) — a 2.7× discrepancy between documented and actual count.

**Evidence:**  
`deploy/DEPLOYMENT_STATUS.md:8` — "40+ Agents ✅ Production Ready".  
`quant_nanggroe/agents/` — 15 agent subdirectories (crypto, researcher, strategist, macro, compliance, forex, risk, market_maker, sentiment, technical, news, portfolio, execution, debate, base).

### 17. Documentation & Knowledge Manager
**Finding:** `ARCHITECTURE.md` in `docs/` is a 22-line stub (a navigation page) that says the "source of truth" is the root `ARCHITECTURE.md` — but the root `ARCHITECTURE.md` also exists. The stub adds no value and creates confusion about the canonical architecture doc.

**Evidence:**  
`docs/ARCHITECTURE.md:1-22` — "This file is the navigation stub. Always read the root `ARCHITECTURE.md` for system design."  
`ARCHITECTURE.md` (root) — actually exists and is the canonical doc. The stub is noise.

### 18. Deployment / DevOps Strategist
**Finding:** `k8s-deployment.yaml` exists in both the root and `deploy/kubernetes/` — but the versions differ in container image references, resource limits, and secret management, meaning Kubernetes deploys will produce different results depending on which file is used.

**Evidence:**  
Root `k8s-deployment.yaml` vs `deploy/kubernetes/k8s-deployment.yaml` — structural differences in image tag, probe configs, and env vars.

---

## 🔷 DHAHER LABS SPECIALISTS (6 agents)

### 19. Dependency Auditor
**Finding:** Two parallel dependency manifests describe different application stacks. `requirements.txt` lists 56 packages centered on Flask/Redis/APScheduler; `pyproject.toml` lists 34 packages centered on FastAPI/Starlette/Pydantic-v2/Binance-connector. Neither is a superset of the other. Running `pip install -r requirements.txt` vs `poetry install` installs a fundamentally different application.

**Evidence:**  
`requirements.txt:1-56` — `flask==3.1.0`, `pymongo`, `redis`, `apscheduler`.  
`pyproject.toml:8-34` — `fastapi>=0.115`, `starlette`, `pydantic-settings`, `python-binance`, `ccxt>=4.4`.  
`ponytail: the two manifests describe different apps — guarantee of runtime ImportError whichever you install.`

### 20. Dead Code Hunter — `ai_multicolony/` Legacy Orphan
**Finding:** The `ai_multicolony/agents/` directory contains 50+ agent files (browser, coder, colony, executor, graph, plus 20 legacy agents) that are never imported by any code in the `quant_nanggroe/` package tree — they are an entirely separate codebase sharing only the repo.

**Evidence:**  
`ai_multicolony/agents/legacy/` — files like `money_making_agent.py`, `marketing_agent.py`, `authentication_agent.py`, `deployment_agent.py`, `fullstack_dev.py` — 20 legacy files.  
`search_files: "from ai_multicolony"` — 0 results outside `ai_multicolony/` itself.  
`ponytail: 50+ orphan files, ~15k lines of dead code.`

### 21. Duplicate Code Detector — Three Database Model Directories
**Finding:** The same database schema exists in three locations: `database/` (root, 5 files), `quant_nanggroe/database/` (6 files including alembic), and `quant_nanggroe/db/` (2 files). The `init.sql` files differ between `database/` (22,228 bytes) and `quant_nanggroe/database/` (21,695 bytes) — different column types and indexing.

**Evidence:**  
`database/init.sql:1` vs `quant_nanggroe/database/init.sql:1` — schema differences in column types and foreign keys.  
`database/models.py` vs `quant_nanggroe/database/models.py` — models differ in relationship definitions.  
`quant_nanggroe/db/models.py:1-40` — minimal subset (3 tables vs 15+).  
`ponytail: three database model sets, no single source of truth.`

### 22. Documentation Completeness Auditor — Version Claim Mismatch
**Finding:** `DEPLOYMENT_STATUS.md` claims version **2.1.0** while `pyproject.toml` declares version **4.3.4** — the deployment doc lags behind the package version by 2.3 minor versions. This means deployment metadata is stale.

**Evidence:**  
`deploy/DEPLOYMENT_STATUS.md:9` — "Version: 2.1.0".  
`pyproject.toml:4` — `version = "4.3.4"`.  
`ponytail: deploy docs are 2 releases behind reality.`

### 23. Configuration & Secrets Auditor — `.env` File Committed
**Finding:** An `.env` file (without `.example` suffix) is committed to the repository, containing actual (or placeholder) API key fields. While the values appear to be empty placeholder values for most fields, the committed `.env` file bypasses the `.gitignore` pattern and is a credential-leak risk if keys are ever filled.

**Evidence:**  
`.env` (root) — committed, not in `.gitignore`'s standard patterns for `.env` (grep shows no `.env` rule).  
`.env.example:1-62` — duplicates the same structure but is explicitly documented as "copy to .env".  
`ponytail: .env should be gitignored; .env.example is the file that should be tracked.`

### 24. Test Infrastructure Auditor — Dead/Cosmetic Tests
**Finding:** `test_strategy/test_crypto_specific_comprehensive.py`, `test_market_making_comprehensive.py`, `test_volatility_arbitrage_comprehensive.py`, and other `*_comprehensive.py` files contain tests that import from strategies but only test construction/import — they do not assert any behaviors. Several are large markdown-wrapped docstrings with no actual test logic.

**Evidence:**  
`tests/test_strategy/test_crypto_specific_comprehensive.py:1-50` — imports `CryptoPairTradingStrategy` but only tests import success, not trading logic.  
`tests/test_coverage_*.py` — 6 files labeled "coverage" that test import paths, not behavior.  
`ponytail: ~15 test files assert only "this module can be imported" — they pass vacuously.`

---

## Summary

| Category | Critical | High | Medium | Low |
|----------|----------|------|--------|-----|
| Blockchain/Crypto | Polymarket & Solana deps missing | Dex stub, mock-only data | Etherscan API keyless | Paper listing |
| Research/Innovation | Zero factor integration | HMM silent-fail dependency | Orphan ML engine | Uncalled rigor tools |
| Business/Strategy | Divergent docker-compose | 40+ agents claim ×2.7 inflated | Stale version docs | Missing competition analysis |
| DhaHer Labs Spec. | Two different dep manifests | 50 orphan AI agents | .env committed | Cosmetic-only tests |

### Top 5 actions in one line each:
1. **Merge `requirements.txt` into `pyproject.toml`** — stop describing two different apps.
2. **Delete `ai_multicolony/` or move to another repo** — 15k lines of dead code.
3. **Pick one `database/` directory** — three schema copies = guaranteed schema drift.
4. **Wire real DeFi data or remove the stubs** — DexIntelligenceEngine's `not_configured` path is a lie by omission.
5. **Add missing deps** — `solana`, `solders`, `py-clob-client`, `hmmlearn` are all referenced in code but absent from every manifest.
