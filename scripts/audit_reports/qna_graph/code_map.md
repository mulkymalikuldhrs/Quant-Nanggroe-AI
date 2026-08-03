# QNA Code Map

Base: `D:\repositories\Quant-Nanggroe-AI-worktree\quant_nanggroe`

- Files parsed: 742 (2 parse errors)
- Nodes: 12597  |  Edges: 32864

## Node types
- function: 5594
- method: 4812
- class: 1450
- module: 741

## Edge types
- calls: 12017
- contains: 11865
- imports: 8073
- inherits: 909

## Top-level packages (module count)
- engine: 358
- agents: 92
- api: 48
- core: 34
- data: 33
- exchange: 33
- hedge_fund: 29
- providers: 17
- database: 9
- types: 9
- memory: 8
- pipeline: 7
- security: 7
- strategies: 5
- tests: 5
- utils: 5
- backtest: 4
- skills: 4
- config: 3
- connectors: 3
- mcp: 3
- channels: 2
- db: 2
- llm: 2
- autonomous_cycle: 1

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
