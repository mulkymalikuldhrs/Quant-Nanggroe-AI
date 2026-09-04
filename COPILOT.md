# COPILOT.md — Quant Nanggroe AI (Quant Nation)

See **AGENTS.md** (canonical). Below is a quick reference.

**Entry:** `python qna.py [daemon|api|status]` (hedge/unified/live legacy modes exist)

**Key:**
- `PYTHONPATH=""` mandatory (Hermes venv leak)
- **MT5 C-API not thread-safe** — `copy_rates_from_pos` must run in thread that called `mt5.initialize()`. Executor threads fail silently.
- **get_rates returns numpy** — do NOT call `list()` on MT5 rates; destroys dtype names. Use `np.asarray()` directly.
- 83 strategies in `quant_nanggroe/engine/strategies/` via `@StrategyRegistry.register` (v8.0.22 CANONICAL SSOT — 9 admitted via CPCV, 207 WF-validated in walk_forward_registry.json)
- Scoring engine wiring disputed between audits — verify core/scoring imports before relying (FusionEngine + 8 scorers + MTFEngine 4-frame overlay + WeightEvolver in `run_once()`)
- KillSwitch C5 in `quant_nanggroe/engine/risk/kill_switch.py` — weekly 0 WIB via `launch.bat weekly-reset`, probe 0/32 CandleScheduler
- 4 git remotes, github2 diverged by 4141 files (full Next.js dashboard)
- Universal path auto-detect (no hardcoded `E:\` at runtime) — external deps in `quant_nanggroe/external/` (kronos, mue_x, hidden_regime) via `Path(__file__).parent / 'external'`; live broker ValetaxIntl-Live2 acct 372044706 BAL $1,445
- 10 exchange clients, 16 agents, 9-stage pipeline + `engine/execution/manager.py` (WIB weekly/PNL guard, one-position-per-symbol, fill-status gate)
- `archive/` = read-only orphan artifacts
- **SSOT:** `CANONICAL.md` v8.0.23 — BAL 1445, weekly 0 WIB, probe 0/32, CPCV 207, launch.bat 1, manager.py WIB

**Ignore:** `paper_state/*.json`, `data/*`, `node_modules/`, `__pycache__/`, `archive/`
**Package:** `uv` (not pip, not poetry)
**Test env broken:** `pip uninstall langsmith` first

---

> **SSOT:** `CANONICAL.md` v8.1.3 — BAL $1,445, weekly 0 WIB, probe 0/32, CPCV 207, launch.bat 1, manager.py WIB

---

> **SSOT:** `CANONICAL.md` v8.1.3 — BAL $1,445, weekly 0 WIB, probe 0/32, CPCV 207, vector 6 modul live, risk per-symbol
