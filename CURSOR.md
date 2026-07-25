# Cursor IDE Instructions — Quant Nanggroe AI v5.2.0

## Entry Point
Single entry: `python qna.py [cli|api|daemon|web|status|stop]`

## Rules
- Always read README → AGENTS → ARCHITECTURE → TODO before making changes.
- `qna.py` is the ONLY root entry point. Never create another.
- Use `uv` for package management (not pip, not poetry).
- Keep docs synchronized with code changes.

## Indexing Preferences
- Index: `quant_nanggroe/`, `dashboard/src/`, `docs/`, `qna.py`
- Exclude: `data/`, `paper_state/`, `node_modules/`, `__pycache__/`, `archive/`
