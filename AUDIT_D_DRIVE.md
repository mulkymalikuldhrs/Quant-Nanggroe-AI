# AUDIT: D: DRIVE — Quant Trading / Hedge-Fund / Strategy / Risk / MT5 Content for QNA

**Generated:** 2026-07-23
**Scan roots:** `D:/repositories`, `D:/docs`, `D:/Obsidian/DhaherLabs`
**Target repo (output + destination):** `D:/repositories/Quant-Nanggroe-AI-worktree` (QNA)
**Scope:** trading / quant / hedge-fund / strategy / risk / MT5 / broker logic only. Personal, visa, jobs, and bug-bounty content excluded.
**Method:** `git-bash` `find`/`diff`/`grep` on Windows. No files were modified.

> **Key conclusion:** Most executable trading *code* already lives inside QNA (packaged 2026-07-23, newer than the D:-drive snapshots dated 2026-07-19). The D:-drive copies are **superseded snapshots** of `E:/trading`. The high-value migration targets are: (1) the analysis/integration Markdown docs, (2) QNA's own Obsidian notes, and (3) the master plans / decision ledgers. A **security blocker** exists in two D:-drive files (hardcoded MT5 demo password) — do NOT migrate those bytes.

---

## TABLE SUMMARY

| # | Path | What it contains | QNA already has? | Recommendation |
|---|------|------------------|------------------|----------------|
| 1 | `D:/docs/trading/` (entire tree) | HF engine snapshot 2026-07-19: `hedge_fund*.py`, `market_context.py`, `mtf_framework.py`, `multi_pair_scanner.py`, `risk_module.py`, `strategy_registry.py`, `strategy_fixes.py`, `sahamid.py`, `wyckoff_optimizer.py`, `backtest_pipeline.py`, `config/`, `research/`, `results/` | YES — packaged in `quant_nanggroe/hedge_fund/` (2026-07-23, newer) | **SKIP** (code superseded) · **MERGE** unique result reports (row 11) |
| 2 | `D:/docs/trading/hedge_fund.py` | Orchestrator w/ hardcoded MT5 password fallback | YES (`quant_nanggroe/hedge_fund/hedge_fund.py`, pw removed) | **SKIP** + **SECURITY FLAG** |
| 3 | `D:/Obsidian/DhaherLabs/_full_trading/trading/` | Identical to `D:/docs/trading` (source snapshot of `E:/trading`) | YES (packaged, newer) | **SKIP** (superseded) |
| 4 | `D:/Obsidian/DhaherLabs/_full_trading/trading/hedge_fund.py:13` | `CREDS` w/ literal password `@15September` fallback + `metatrader-mcp.env` | QNA uses `os.environ.get("MT5_PASSWORD")` only | **SKIP** + **SECURITY FLAG** (never re-introduce) |
| 5 | `D:/Obsidian/DhaherLabs/_full_trading/data/` (trades.csv, votes.csv) | Live demo trade/vote logs (Valetax 372044706) | QNA writes its own `data/` logs | **SKIP** raw logs (or MERGE as historical archive) |
| 6 | `D:/Obsidian/DhaherLabs/_trading/HedgeFund.md` | Obsidian portfolio note: balance, pairs, broker, strategy Sharpe table | No dedicated note in repo | **MERGE** → `docs/` or `research/` |
| 7 | `D:/Obsidian/DhaherLabs/_trading_data/` | Duplicate of `D:/docs/trading` ARCHITECTURE/EVALUATION/HANDOFF/JOURNAL/TRADING_PLAN | Same as row 1 | **SKIP** (duplicate) |
| 8 | `D:/Obsidian/DhaherLabs/Quant-Nanggroe-AI/` | QNA's own Obsidian notes (Architecture-Deep-Dive, Gap-Analysis, MTF, Risk, Backtesting, Integration, Production-Status) | **NOT IN REPO** (verified) | **MIGRATE** → `docs/` |
| 9 | `D:/docs/QUANTDINGER-ANALYSIS.md`, `TRADEBOBBY-INTEGRATION.md`, `KRONOS-ANALYSIS.md`, `OPENALICE-ANALYSIS.md`, `AI-MM-INTEGRATION.md` | Repo integration analyses (external trading OSes) | Code exists (`kronos_wrapper.py`, `tradebobby_smc_scanner.py`) but **NOT these MDs** | **MIGRATE** → `research/` |
| 10 | `D:/docs/QUANTSCIENCE-RESEARCH.md`, `QNA-ML-REFERENCES.md` | Research paper / ML references for trading | Partial (`research/` exists, not these files) | **MIGRATE** → `research/` |
| 11 | `D:/docs/trading/results/dhaher_system_results.md`, `smc-upgrade-results.md` | Strategy implementation/fix reports | Not in repo | **MERGE** → `research/` |
| 12 | `D:/docs/COUNCIL-HF-EXTRACT.md`, `COUNCIL-QNA-EXTRACT.md` | Council deep-extraction of HF + QNA | Not in repo (only summary in `archive/reports/`) | **MIGRATE** → `docs/` |
| 13 | `D:/docs/QNA-FINAL-MASTER-PLAN.md`, `QNA-KENYANG-GANAS-PLAN.md`, `MASTER-PLAN-SENIN.md`, `PHASE3-PLAN.md`, `PRE-MONDAY-PLAN.md` | QNA/HF master plans | Not in repo | **MERGE** → `docs/` |
| 14 | `D:/docs/DECISION_LEDGER.md` | QNA v4.6.0 upgrade ledger (MT5 live verified, backtest verified) | Not in repo | **MERGE** → `docs/` |
| 15 | `D:/repositories/blackhornet/src/bridge/qna_bridge.py` | BlackHornet AGI ↔ QNA bridge | No BH bridge in QNA | **MERGE** (bridge concept) · SKIP AGI core |
| 16 | `D:/repositories/blackhornet/src/hermes_quant.py` | 21-agent trading OS definition (risk veto rules) | QNA has its own risk agents | **SKIP** (separate AGI project) |
| 17 | `D:/repositories/archived/Dhaher-Corporation-worktree/16_RISK_MANAGEMENT.md` (+ `11_INVESTMENT_SYSTEM.md`, `18_ROADMAP.md`) | Corporate blueprint risk docs | Superseded by `docs/19_RISK_REGISTER.md` | **SKIP** (generic/corporate) |
| 18 | `D:/docs/E-DRIVE-AUDIT-MAP.md`, `D-DRIVE-INVENTORY.md`, `D-DRIVE-KNOWLEDGE.md` | Drive inventories (mostly non-trading) | Reference only | **SKIP** (meta/reference) |
| 19 | Other D:/repositories folders (Autonomous-Organism, seulanga-*, JeumpaLLM, kalen-worktree, etc.) | Incidental grep hits only; no trading engine | n/a | **SKIP** |

---

## DETAIL

### 1. `D:/docs/trading/` (and mirror `D:/Obsidian/DhaherLabs/_full_trading/trading/`)
**Contains:** Full snapshot of the `E:/trading` hedge-fund runtime, dated 2026-07-19. Core modules:
- `hedge_fund.py` (305 ln) — 15-agent voting aggregator + MT5 live execution
- `hedge_fund_mtf.py`, `hedge_fund_multipair.py` — MTF / multi-pair executors
- `market_context.py`, `mtf_framework.py`, `multi_pair_scanner.py` — context, MTF, pair scan
- `risk_module.py` — Kelly + Monte Carlo + dynamic sizing
- `strategy_registry.py`, `strategy_fixes.py`, `sahamid.py`, `wyckoff_optimizer.py`
- `backtest_pipeline.py`, `master_backtest.py`, `full_optimizer.py`
- `config/` (`freqtrade.json`, `risk.json`), `research/` (13 market/quant reports), `results/` (backtest JSON + impl MD)

**QNA equivalent:** Already packaged and **newer (2026-07-23)** under:
- `quant_nanggroe/hedge_fund/hedge_fund.py`, `mtf.py`, `multipair.py`
- `quant_nanggroe/hedge_fund/tools/{market_context,mtf_framework,multi_pair_scanner,risk_module,risk_guard}.py`
- Root-level `hedge_fund_mtf.py`, `hedge_fund_multipair.py`, `sahamid.py`, `strategy_fixes.py`, `strategy_registry.py` (differ in line count; QNA versions de-`E:/trading`-ified)
- `quant_nanggroe/strategies/` already holds `dhaher_system.py`, `kronos_wrapper.py`, `tradebobby_smc_scanner.py`, `trend_follow.py`, `tsmom.py`, `xgboost_alpha.py`, `pairs_trade.py` (Wyckoff/MSNR/SMC strategies present in engine)
- `research/` in QNA already contains 20 files including the same 13 report names + extras (`hedge_fund_research.md`, `NEW_STRATEGY_PROPOSALS.md`, `findings.md`)

**Diff evidence:** `risk_module.py` line counts 195 (`_full_trading`) vs 196 (QNA tools) — content reorganized. `strategy_registry.py` 369 → 487 (QNA expanded). QNA `risk_module.py` head removed the `SRC = Path(r'E:/trading')` hardpath; QNA `hedge_fund.py` uses `os.environ.get("MT5_PASSWORD")` (line 58) instead of literal.

**Recommendation:** **SKIP** the code — it is a superseded snapshot. **MERGE** only the two unique result reports (row 11). Do not re-copy wholesale.

### 2 & 4. SECURITY FLAG — hardcoded MT5 credentials
- `D:/Obsidian/DhaherLabs/_full_trading/trading/hedge_fund.py:13`
  `CREDS = {"login": 372044706, "password": os.environ.get("MT5_PASSWORD", "@15September"), "server": "ValetaxIntl_Live-2"}`
- `D:/Obsidian/DhaherLabs/_full_trading/trading/metatrader-mcp.env` → `MT5_PASSWORD=<literal>`
- `D:/docs/trading/hedge_fund.py` — note: the `D:/docs` copy was verified and does **NOT** contain the literal (already partly scrubbed), but the `_full_trading` copy does.
- `multi_pair_scanner.py` header also embeds live account `372044706` + `ValetaxIntl-Live2` (metadata only, not secret).

**QNA state:** `quant_nanggroe/hedge_fund/hedge_fund.py:58` reads `os.environ.get("MT5_PASSWORD")` only; `quant_nanggroe/connectors/mt5_broker.py` takes password via constructor/env. **No literal secret in QNA.**

**Recommendation:** **SKIP / never migrate** the literal password. Add a secrets-rotation note; the demo account password should be treated as compromised. QNA's env-only approach is correct.

### 5. `D:/Obsidian/DhaherLabs/_full_trading/data/` (trades.csv, votes.csv)
Live demo execution logs for Valetax 372044706. QNA regenerates equivalent logs in its own `data/`. **SKIP** raw (or optionally archive to `data/` as historical backtest reference). No code value.

### 6. `D:/Obsidian/DhaherLabs/_trading/HedgeFund.md`
Portfolio note: $1,000 demo, 28 pairs, Valetax 1:2000, strategy Sharpe table (Wyckoff 3.02, MeanReversion 1.98, MSNR 1.889, SMC 2.156). **MERGE** into QNA `docs/` as a reference note (QNA has no equivalent hand-written portfolio note).

### 8. `D:/Obsidian/DhaherLabs/Quant-Nanggroe-AI/` (NOT in repo — verified by grep)
QNA's own architecture/planning notes:
- `Architecture-Deep-Dive.md`, `Audit-Upgrade-Log-2026-07-21.md`, `Gap-Analysis-Action-Plan.md`, `Master-Index.md`, `Production-Status-2026-07-21.md`
- Subfolders: `Backtesting/`, `Integration/`, `MTF/`, `Risk/Risk-Management-Framework.md`, `Signals/`, `Strategies/`

**Recommendation:** **MIGRATE** — these are QNA's canonical design notes and are currently only in Obsidian, not in the repo (a continuity risk). Move into `docs/`.

### 9–12. Analysis / council / master-plan Markdown (D:/docs)
None of these exist in the QNA repo (verified via grep):
- Repo integration analyses: `QUANTDINGER-ANALYSIS.md`, `TRADEBOBBY-INTEGRATION.md`, `KRONOS-ANALYSIS.md`, `OPENALICE-ANALYSIS.md`, `AI-MM-INTEGRATION.md` — decision records behind the already-integrated `kronos_wrapper.py` / `tradebobby_smc_scanner.py`. **MIGRATE** to `research/`.
- Research refs: `QUANTSCIENCE-RESEARCH.md`, `QNA-ML-REFERENCES.md`. **MIGRATE** to `research/`.
- Council extractions: `COUNCIL-HF-EXTRACT.md` (716 ln), `COUNCIL-QNA-EXTRACT.md` (424 ln). **MIGRATE** to `docs/`.
- Master plans / ledgers: `QNA-FINAL-MASTER-PLAN.md`, `QNA-KENYANG-GANAS-PLAN.md`, `MASTER-PLAN-SENIN.md`, `PHASE3-PLAN.md`, `PRE-MONDAY-PLAN.md`, `DECISION_LEDGER.md`. **MERGE** to `docs/`.

### 15–16. `D:/repositories/blackhornet/` (sibling project in D:/repositories)
- `src/bridge/qna_bridge.py` — BlackHornet AGI → QNA bridge (query signals, send decisions, read perf). QNA has no BH bridge. **MERGE** the bridge concept if cross-repo AGI orchestration is desired.
- `src/hermes_quant.py` — 21-agent autonomous trading OS (separate AGI system, hardcoded risk rules). **SKIP** — distinct project, QNA already has its own risk/agent stack.

### 17. `D:/repositories/archived/Dhaher-Corporation-worktree/` risk docs
`16_RISK_MANAGEMENT.md`, `11_INVESTMENT_SYSTEM.md`, `18_ROADMAP.md` — generic corporate investment/risk blueprint, not engine-specific. Superseded by QNA `docs/19_RISK_REGISTER.md` + `quant_nanggroe/engine/risk/`. **SKIP**.

### 19. Other repositories
`Autonomous-Organism`, `seulanga-rag(-archive)`, `seulanga-archive`, `JeumpaLLM`, `kalen-worktree`, `ai-multicolony-worktree`, etc. produced only incidental grep hits (e.g., `CONSTITUTION.md`, `architecture.md`); no trading engine/strategy/MT5 content. **SKIP**.

---

## ACTION CHECKLIST (for parent agent)

1. **SECURITY (do first):** Treat MT5 demo password `@15September` as compromised. Confirm QNA uses env-only auth (verified: `quant_nanggroe/hedge_fund/hedge_fund.py:58`, `connectors/mt5_broker.py`). Never copy `hedge_fund.py:13` literal or `metatrader-mcp.env` into QNA.
2. **MIGRATE docs (no code risk):** Copy rows 8–13 into QNA `docs/` + `research/` (Obsidian QNA notes, analysis MDs, council extractions, master plans, decision ledger).
3. **MERGE notes:** `HedgeFund.md` (row 6), result reports (row 11) into `research/`.
4. **SKIP:** All HF engine code from `D:/docs/trading` and `_full_trading/trading` (superseded by QNA's 2026-07-23 packaged engine). Do not duplicate.
5. **OPTIONAL:** Evaluate `blackhornet/src/bridge/qna_bridge.py` for cross-repo orchestration (row 15).

## MIGRATION VALUE TALLY
- **MIGRATE (net-new to QNA):** 8 (Obsidian QNA notes) + 5 (analysis MDs) + 2 (research refs) + 2 (council) + 6 (plans/ledger) ≈ **23 documents**
- **MERGE (partial):** 3 (HedgeFund note, 2 result reports)
- **SKIP (superseded/non-trading/security):** code snapshots, raw logs, corporate docs, other repos
- **SECURITY FLAG:** 2 files with live credential

*End of audit. No files on D: were modified.*
