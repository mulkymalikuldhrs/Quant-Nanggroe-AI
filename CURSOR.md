# CURSOR.md — Quant Nanggroe AI

See **AGENTS.md** for canonical instructions.

**Entry:** `python qna.py [unified|api|daemon|hedge|status|stop]`

**Rules:**
- `PYTHONPATH=""` mandatory (Hermes venv leak)
- `qna.py` is the ONLY root entry point. Never create another.
- Use `uv` for package management (not pip, not poetry).
- `archive/` = read-only orphan artifacts from v6.2.
- Keep docs synchronized with code changes.

**Index:**
- Include: `quant_nanggroe/`, `dashboard/src/`, `docs/`, `qna.py`
- Exclude: `data/`, `paper_state/`, `node_modules/`, `__pycache__/`, `archive/`