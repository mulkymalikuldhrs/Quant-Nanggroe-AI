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
