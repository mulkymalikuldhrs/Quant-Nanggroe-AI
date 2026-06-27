#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$REPO/docs/auto"
mkdir -p "$OUT"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "=== Auto-Report: Generating Consolidated Report ==="

{
echo "# QNA Consolidated Report — $(date '+%Y-%m-%d %H:%M')"
echo ""
echo "## 1. Project Stats"
echo ""
echo "| Metric | Value |"
echo "|--------|-------|"

# Python file count
PY_COUNT=$(find "$REPO/quant_nanggroe" -name "*.py" | wc -l)
echo "| Python modules | $PY_COUNT |"

# Total lines
TOTAL_LINES=$(find "$REPO/quant_nanggroe" -name "*.py" -exec cat {} + | wc -l)
echo "| Total Python lines | $TOTAL_LINES |"

# Script count
SCRIPT_COUNT=$(find "$REPO/scripts" -maxdepth 1 -name "*.py" -o -name "*.sh" | wc -l)
echo "| Automation scripts | $SCRIPT_COUNT |"

# Test count
TEST_COUNT=$(find "$REPO/tests" -name "*.py" | wc -l)
echo "| Test files | $TEST_COUNT |"

# Test count
TEST_OUT=$(python3 -m unittest discover -s "$REPO/tests" -p 'test_*.py' 2>&1 | tail -1)
TEST_NUM=$(echo "$TEST_OUT" | sed 's/.*Ran \([0-9]*\) test.*/\1/')
[ -n "$TEST_NUM" ] && echo "| Unit tests | $TEST_NUM |" || echo "| Unit tests | unknown |"

# Docs
DOC_COUNT=$(find "$REPO/docs" -name "*.md" | wc -l)
echo "| Doc files | $DOC_COUNT |"

# QNA version
VERSION=$(python3 -c "import sys, importlib; sys.path.insert(0, \"$REPO\"); mod = importlib.import_module(\"quant_nanggroe\"); print(mod.QNA_VERSION)" 2>/dev/null || echo "unknown")
echo "| QNA version | $VERSION |"

echo ""

echo "## 2. Module Overview"
echo ""
python3 -c "
import os
from pathlib import Path
qna = Path('$REPO/quant_nanggroe')
for d in sorted(qna.iterdir()):
    if d.is_dir() and not d.name.startswith('__'):
        pyfiles = list(d.rglob('*.py'))
        lines = sum(len(f.read_text().splitlines()) for f in pyfiles)
        print(f'- **{d.name}/**: {len(pyfiles)} files, ~{lines} LOC')
"

echo ""
echo "## 3. Test Status"
echo ""
if python3 -m unittest discover -s "$REPO/tests" -p 'test_*.py' 2>&1 | tail -3 > /tmp/qna_test_out.txt 2>&1; then
    grep -E "^(OK|FAILED|Ran)" /tmp/qna_test_out.txt || echo "(unittest output not parsed)"
else
    echo "Tests completed with results above"
fi

echo ""
echo "## 4. Audit Status"
echo ""
# Check ruff
ruff check "$REPO/quant_nanggroe/" --statistics 2>&1 | grep -E "^(Found|[0-9])" || echo "No ruff issues found"

echo ""
echo "## 5. Recent Changes (git log -5)"
echo ""
git -C "$REPO" log --oneline -5 2>/dev/null || echo "(no git history)"

} > "$OUT/report_$TIMESTAMP.md"

echo "=== Report saved: $OUT/report_$TIMESTAMP.md ==="
wc -l "$OUT/report_$TIMESTAMP.md"
