# CURSOR.md — Quant Nanggroe AI (Quant Nation)

See **AGENTS.md** for canonical instructions.

**Entry:** `python qna.py [daemon|api|status]` (hedge/unified/live legacy modes exist)

**Rules:**
- `PYTHONPATH=""` mandatory (Hermes venv leak)
- `qna.py` is the ONLY root entry point. Never create another.
- Use `uv` for package management (not pip, not poetry).
- `archive/` = read-only orphan artifacts from v6.2.
- Keep docs synchronized with code changes.
- Scoring engine wiring disputed between audits — verify core/scoring imports before relying (FusionEngine + 8 scorers + MTFEngine + WeightEvolver in run_once()). Test counts: see CHANGELOG.

**Index:**
- Include: `quant_nanggroe/`, `dashboard/src/`, `docs/`, `qna.py`
- Exclude: `data/`, `paper_state/`, `node_modules/`, `__pycache__/`, `archive/`
