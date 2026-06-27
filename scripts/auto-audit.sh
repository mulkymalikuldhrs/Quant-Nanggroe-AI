#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$REPO/docs/auto/audit"
mkdir -p "$OUT"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "=== Auto-Audit: Comprehensive Codebase Audit ==="

echo "--- 1. Import Integrity Check ---"
python3 -c "
import sys
sys.path.insert(0, '$REPO')
checks = [
    ('quant_nanggroe', '__init__'),
    ('quant_nanggroe.engine', 'MarketStateEngine'),
    ('quant_nanggroe.agents', '*'),
    ('quant_nanggroe.data', '*'),
    ('quant_nanggroe.exchange', '*'),
    ('quant_nanggroe.llm', 'HAS_JEUMPA'),
    ('quant_nanggroe.memory', 'HAS_SEULANGA'),
    ('quant_nanggroe.engine.compliance', 'ComplianceJournal'),
    ('quant_nanggroe.data.providers.crypto_provider', 'CryptoProvider'),
    ('quant_nanggroe.engine.risk.kelly', 'KellyCriterion'),
    ('quant_nanggroe.engine.risk.kill_switch', 'KillSwitch'),
    ('quant_nanggroe.engine.backtest.psr', 'PSRResult'),
    ('quant_nanggroe.engine.event_engine', 'EventEngine'),
    ('quant_nanggroe.data.failover_provider', 'FailoverDataProvider'),
]
passed = 0
failed = 0
results = []
for module, attr in checks:
    try:
        mod = __import__(module, fromlist=[attr])
        if attr == '*' or hasattr(mod, attr):
            results.append(f'✅ {module}.{attr}')
            passed += 1
        else:
            results.append(f'❌ {module}.{attr} — missing')
            failed += 1
    except Exception as e:
        results.append(f'❌ {module}.{attr} — {e}')
        failed += 1

print(f'Import check: {passed}/{passed+failed} pass')
for r in results:
    print(f'  {r}')
" 2>&1 | tee "$OUT/import_check_$TIMESTAMP.txt"

echo ""
echo "--- 2. Ruff Lint Check ---"
ruff check "$REPO/quant_nanggroe/" --statistics 2>&1 | tee "$OUT/ruff_report_$TIMESTAMP.txt" || true

echo ""
echo "--- 3. Python Syntax Check ---"
find "$REPO/quant_nanggroe" -name "*.py" -exec python3 -c "
import ast, sys
fails = []
for f in sys.argv[1:]:
    try:
        ast.parse(open(f).read())
    except SyntaxError as e:
        fails.append(f'{f}: {e}')
if fails:
    for f in fails:
        print(f'❌ {f}')
else:
    print('✅ All files parse clean')
" {} + 2>&1 | tee "$OUT/syntax_check_$TIMESTAMP.txt"

echo ""
echo "--- 4. File Encoding Check ---"
find "$REPO/quant_nanggroe" -name "*.py" -exec python3 -c "
import sys
for f in sys.argv[1:]:
    try:
        open(f, encoding='utf-8').read()
    except UnicodeDecodeError as e:
        print(f'❌ {f}: {e}')
" {} + 2>&1 | tee "$OUT/encoding_check_$TIMESTAMP.txt"

echo ""
echo "--- 5. Orphan File Check ---"
python3 "$REPO/scripts/qna-architect.py" --check 2>&1 | head -20 | tee "$OUT/orphan_check_$TIMESTAMP.txt" || true

echo ""
echo "--- 6. Test Discovery ---"
python3 -m unittest discover -s "$REPO/tests" -p 'test_*.py' 2>&1 | tail -5 | tee "$OUT/test_discovery_$TIMESTAMP.txt"

echo ""
echo "=== Auto-Audit Complete ==="
echo "Reports saved to: $OUT/"
