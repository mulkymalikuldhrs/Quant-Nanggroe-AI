# QNA Knowledge Graph — Report

**Date:** 2026-08-01
**Base indexed:** `D:\repositories\Quant-Nanggroe-AI-worktree\quant_nanggroe`
**Method:** Read-only stdlib `ast` analyzer (graphify pip package not installed; used skill's stdlib-fallback approach — QNA code untouched).

## Outcome
- **742 Python files** scanned (2 parse errors — likely py2/syntax-incompatible files, skipped safely).
- **Nodes detected: 12,597**
- **Edges detected: 32,864**

### Node breakdown (entities)
| Type | Count |
|------|-------|
| module | 741 |
| class | 1,450 |
| method | 4,812 |
| function | 5,594 |

### Edge breakdown (relationships)
| Type | Count |
|------|-------|
| imports | 8,073 |
| calls | 12,017 |
| contains (module→class/func, class→method) | 11,865 |
| inherits | 909 |

## Artifacts
- `qna_graph\graph.json` — full node/edge store (JSON graph).
- `qna_graph\code_map.md` — human-readable code map (node/edge stats + top-level package inventory).
- `qna_graph\build_graph.py` — the read-only analyzer script (re-runnable).

## Notes
- `calls` edges are heuristic (matched by function/method name against defined symbols) — approximate, not fully call-resolved.
- No QNA source files were modified. Analysis only.
- graphify PyPI tool was absent in the Hermes venv; the skill's documented stdlib-AST fallback was used, which is more reliable and avoids the known silent-empty-graph pitfall.


<!-- CODE-TRUTH STATUS FOOTER — appended 2026-08-03 23:43:45 by autobot (QNA audit 2026-08-03) -->
<!-- Method: append-only. Source of truth = code, not prior .md claims. -->
## 🔍 CODE-TRUTH STATUS (2026-08-03 audit)
- **FusionEngine**: EXISTS — `quant_nanggroe/core/scoring/fusion_engine.py:27` (prior claim "false" RETRACTED).
- **API server**: EXISTS + startable — `quant_nanggroe/cli.py:603` uvicorn :8000; `launch.bat api`; 223 routes wired.
- **Dashboard**: UNWIRED only because server not started; UI code present (`dashboard/`, 261 tsx+ts).
- **Phantom-equity ($1M default)**: MITIGATED — P1b fail-CLOSED `_resolve_equity()` floor $1000 in `risk_gate_bridge.py` (ctor:145, evaluate:194, evaluate_from_state:449). Live path uses `evaluate_from_state` -> real MT5 equity.
- **Polars**: NOT imported anywhere (`import polars`=0) -> `engine/data/providers/yahoo_polars.py` genuinely MISSING (archive gap real).
- **Secrets**: 0 hardcoded (grep `sk-`/`AKIA`=0). `eval`/`pickle`: 0 live vulns (only security-linter strings).
- **ENV BLOCKER**: all venv numpy ABI broken (cp311 `.pyd` under cp312) -> runtime import unverified until `uv sync`. Patch syntax+logic verified standalone.
- **Archive upgrade**: 8/11 new modules ALREADY in code; 4 missing (quality.py, yahoo_polars.py, feature_engine.py, alerting/).
- **Audit trail**: `C:/Users/Hi/Desktop/QNA_AUDIT_DEBAT.txt` | inventory `QNA_FILE_INVENTORY.txt` | `QNA_EXTENSION_LEDGER.txt`.
<!-- END CODE-TRUTH FOOTER -->
