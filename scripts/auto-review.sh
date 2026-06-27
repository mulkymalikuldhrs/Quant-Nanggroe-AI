#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$REPO/docs/auto/review"
mkdir -p "$OUT"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "=== Auto-Review: Code Review Automation ==="

{
echo "# QNA Code Review — $(date '+%Y-%m-%d %H:%M')"
echo ""

echo "## 1. Ruff Lint Report"
echo ""
echo '```'
ruff check "$REPO/quant_nanggroe/" 2>&1 || echo "(ruff not found or no issues)"
echo '```'
echo ""

echo "## 2. Python Syntax Verification"
echo ""
ERRORS=0
while IFS= read -r -d '' f; do
    if ! python3 -c "import ast; ast.parse(open('$f').read())" 2>/dev/null; then
        echo "- ❌ $f: SyntaxError"
        ERRORS=$((ERRORS + 1))
    fi
done < <(find "$REPO/quant_nanggroe" -name "*.py" -print0)
if [ "$ERRORS" -eq 0 ]; then
    echo "- ✅ All files parse clean"
fi
echo ""

echo "## 3. Import Consistency"
echo ""
python3 -c "
import ast, os
from pathlib import Path
qna = Path('$REPO/quant_nanggroe')
issues = []
for f in qna.rglob('*.py'):
    rel = f.relative_to(qna)
    content = f.read_text()
    tree = ast.parse(content)
    modpath = str(rel.with_suffix('')).replace(os.sep, '.')
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            # Check relative imports exceed allowed depth
            if node.level and node.level > 2:
                issues.append(f'{modpath}: deep relative import (level={node.level})')
            # Check direct imports that should be relative
            if not node.level and node.module.startswith('quant_nanggroe'):
                parts = modpath.split('.')
                if node.module != 'quant_nanggroe' and len(parts) > 1:
                    # Could be relative but isn't
                    pass  # not enforcing relative imports
for i in issues:
    print(f'- ⚠️ {i}')
if not issues:
    print('- ✅ No import issues found')
"
echo ""

echo "## 4. Large Files (>500 lines)"
echo ""
find "$REPO/quant_nanggroe" -name "*.py" -exec wc -l {} + | sort -rn | awk '$1 > 500 {print "- ⚠️ " $2 ": " $1 " lines"}' | head -10
echo ""

echo "## 5. TODO/FIXME Audit"
echo ""
grep -rn "TODO\|FIXME\|XXX\|HACK\|WORKAROUND" "$REPO/quant_nanggroe/" --include="*.py" 2>/dev/null | head -20 | while IFS=: read -r f line rest; do
    short=$(echo "$f" | sed "s|$REPO/||")
    echo "- $short:$line — \`$rest\`"
done
echo ""

echo "## 6. Duplicate Code Detection (simple hash check)"
echo ""
python3 -c "
import hashlib, os
from collections import defaultdict
from pathlib import Path

qna = Path('$REPO/quant_nanggroe')
hashes = defaultdict(list)
for f in qna.rglob('*.py'):
    content = f.read_text().strip()
    h = hashlib.md5(content.encode()).hexdigest()
    hashes[h].append(str(f.relative_to(qna)))

for h, files in hashes.items():
    if len(files) > 1 and len(files[0]) > 50:  # skip tiny files
        print(f'- ⚠️ Duplicate ({len(files)} copies):')
        for f in files:
            print(f'    - {f}')
"
} > "$OUT/review_$TIMESTAMP.md"

echo "=== Review saved: $OUT/review_$TIMESTAMP.md ==="
wc -l "$OUT/review_$TIMESTAMP.md"
