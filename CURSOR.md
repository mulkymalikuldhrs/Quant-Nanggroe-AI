# Cursor IDE Instructions — Quant Nanggroe AI v6.2.0

## Entry Point
Single entry: `python qna.py [unified|api|daemon|hedge|status|stop]`

## Rules
- Always read README → AGENTS → ARCHITECTURE → TODO → CHANGELOG before making changes.
- `qna.py` is the ONLY root entry point. Never create another.
- Use `uv` for package management (not pip, not poetry).
- Keep docs synchronized with code changes.
- Check `quant_nanggroe/engine/causal/` for causal engine modules. 🆕
- Check `quant_nanggroe/engine/risk/dcc_garch.py` for DCC-GARCH. 🆕

## Indexing Preferences — Updated v6.2.0
- Index: `quant_nanggroe/`, `dashboard/src/`, `docs/`, `qna.py`, `quant_nanggroe/engine/causal/`, `quant_nanggroe/engine/risk/`, `quant_nanggroe/engine/strategies/`
- Exclude: `data/`, `paper_state/`, `node_modules/`, `__pycache__/`, `archive/`
