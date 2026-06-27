#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$REPO/docs/auto/graphs"
mkdir -p "$OUT"

echo "=== Graphify: Dependency Graph ==="
python3 "$REPO/scripts/qna-architect.py" --mermaid 2>/dev/null > "$OUT/dependency.mmd" || echo "WARNING: qna-architect failed"

echo "=== Graphify: Package Tree ==="
(
  echo "graph TD"
  find "$REPO/quant_nanggroe" -name "__init__.py" -maxdepth 3 | while read -r f; do
    pkg="$(echo "$f" | sed "s|$REPO/quant_nanggroe/||; s|/__init__.py||; s|/|.|g")"
    echo "    ${pkg//./_}[${pkg//\"/\\\"}]"
  done
) > "$OUT/package_tree.mmd"

echo "=== Graphify: Import Map ==="
python3 -c "
import ast, os
from pathlib import Path
root = Path('$REPO/quant_nanggroe')
print('graph LR')
for f in sorted(root.rglob('*.py')):
    rel = f.relative_to(root)
    mod = str(rel.with_suffix('')).replace(os.sep, '.')
    try:
        tree = ast.parse(f.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith('quant_nanggroe'):
                        print(f'    {mod.replace(chr(46), chr(95))} --> {alias.name.replace(chr(46), chr(95))}')
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.startswith('quant_nanggroe'):
                    print(f'    {mod.replace(chr(46), chr(95))} --> {node.module.replace(chr(46), chr(95))}')
    except SyntaxError:
        pass
" > "$OUT/import_map.mmd"

echo "=== Graphify: Architecture Diagram ==="
python3 -c "
print('''graph TD
    SYNTH[GARCH Synthetic Data] --> STRAT[8 Strategies]
    STRAT --> BT[Backtest Engine]
    BT --> RISK[Risk Layer]
    RISK --> DAEMON[Paper Daemon]
    DAEMON --> AUDIT[Alpha Audit]
    DAEMON --> DASH[Dashboard]
    DAEMON --> PNL[PnL CSV]
    DAEMON --> STATE[AutoDisable State]
    RISK --> KS[KillSwitch]
    RISK --> KELLY[Kelly Sizing]
    RISK --> REGIME[Regime Detection]
    BT --> WALK[Walk-Forward]
    BT --> CPCV[Combinatorial CPCV]
    BT --> PSR[PSR/DSR]
    BT --> MC[Monte Carlo]
    STRAT --> MOM[Momentum]
    STRAT --> MR[Mean-Reversion]
    STRAT --> BO[Breakout]
    STRAT --> PAIRS[Pairs Trading]
    STRAT --> ML[ML Strategy]
    STRAT --> STAT[Statistical Arb]
    STRAT --> HFT[HFT Strategy]
    STRAT --> MACRO[Macro Strategy]
    DATA[Data Layer] --> FAILOVER[FailoverProvider]
    DATA --> CACHE[SQLite Cache]
    DATA --> PROVIDERS[12 Providers]
    EXEC[Execution Layer] --> BROKER[Broker Wrappers]
    EXEC --> FILL[Fill Tracker]
    EXEC --> GUARD[Position Guards]
    SEC[Security Layer] --> PII[PII Redaction]
    SEC --> AUDITLOG[AuditLogger]
    MEM[Memory Layer] --> JEUM[JeumpaLLM]
    MEM --> SEUL[SeulangaRAG]
''')" > "$OUT/architecture.mmd"

echo "=== Graphify: Strategy Flow ==="
python3 -c "
print('''flowchart LR
    subgraph Input
        A[GARCH Synthetic Data]
        B[CSV Cache]
    end
    subgraph Engine
        C[8 Strategies]
        D[Backtest Engine]
        E[Risk Layer]
        F[Kelly Sizing]
    end
    subgraph Output
        G[Paper Daemon]
        H[Dashboard]
        I[Alpha Reports]
        J[State Files]
    end
    A --> C
    B --> D
    C --> D
    D --> E
    E --> F
    F --> G
    G --> H
    G --> I
    G --> J
''')" > "$OUT/strategy_flow.mmd"

echo "=== Graphify Complete ==="
ls -lh "$OUT/"
