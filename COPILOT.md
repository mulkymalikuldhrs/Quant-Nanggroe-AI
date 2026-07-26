# GitHub Copilot Instructions — Quant Nanggroe AI v6.0.0

## Entry Point
Single entry: `python qna.py [cli|api|daemon|web|status|stop]`

## Suggested Ignore Patterns
- `paper_state/*.json` — auto-generated trading state.
- `data/*` — runtime data.
- `node_modules/` — JavaScript dependencies.
- `__pycache__/` — Python cache.
- `archive/` — Legacy files (do not edit).

## Commit Message Convention
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `refactor:` Code refactoring
- `test:` Test changes
- `chore:` Maintenance
- `audit:` Codebase audit

## Key Locations
- Strategies: `quant_nanggroe/engine/strategies/` (79+ registered, canonical) + legacy shim (139 frozen, backward-compat)
- Risk: `quant_nanggroe/engine/risk/`
- Docs: `docs/` (58 documents)
