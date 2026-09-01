# CURSOR.md — Quant Nanggroe AI (Quant Nation)

See **AGENTS.md** for canonical instructions.

**Entry:** `python qna.py [daemon|api|status]` (hedge/unified/live legacy modes exist)

**Rules:**
- `PYTHONPATH=""` mandatory (Hermes venv leak)
- **MT5 C-API not thread-safe** — `copy_rates_from_pos` must run in thread that called `mt5.initialize()`. Executor threads fail silently.
- **get_rates returns numpy** — do NOT call `list()` on MT5 rates; destroys dtype names. Use `np.asarray()` directly.
- `qna.py` is the ONLY root entry point. Never create another.
- Use `uv` for package management (not pip, not poetry).
- `archive/` = read-only orphan artifacts from v6.2.
- Keep docs synchronized with code changes.
- Scoring engine wiring disputed between audits — verify core/scoring imports before relying (FusionEngine + 8 scorers + MTFEngine + WeightEvolver in run_once()). Test counts: see CHANGELOG. SSOT: `CANONICAL.md` v8.0.19 BAL $1,445 weekly 0 WIB probe 0/32 CPCV 207 launch.bat 1 manager.py WIB.

**Index:**
- Include: `quant_nanggroe/`, `dashboard/src/`, `docs/`, `qna.py`
- Exclude: `data/`, `paper_state/`, `node_modules/`, `__pycache__/`, `archive/`

---

> **SSOT:** `CANONICAL.md` v8.0.19 — BAL $1,445, weekly 0 WIB, probe 0/32, CPCV 207, launch.bat 1, manager.py WIB
