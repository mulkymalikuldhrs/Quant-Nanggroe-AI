#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$REPO/docs/auto"
mkdir -p "$OUT"

echo "=== Listing All Project Files ==="

echo "--- Python Modules (quant_nanggroe/) ---" > "$OUT/FILE_LIST.md"
find "$REPO/quant_nanggroe" -name "*.py" | sort | sed "s|$REPO/||" >> "$OUT/FILE_LIST.md"
echo "" >> "$OUT/FILE_LIST.md"

echo "--- Scripts (scripts/) ---" >> "$OUT/FILE_LIST.md"
for f in "$REPO/scripts/"*; do
    name=$(basename "$f")
    descr=$(head -2 "$f" 2>/dev/null | grep -E "^#" | tr -d "#" | xargs || echo "no description")
    echo "- $name — $descr" >> "$OUT/FILE_LIST.md"
done
echo "" >> "$OUT/FILE_LIST.md"

echo "--- Documentation (docs/) ---" >> "$OUT/FILE_LIST.md"
find "$REPO/docs" -name "*.md" | sort | sed "s|$REPO/||" >> "$OUT/FILE_LIST.md"
echo "" >> "$OUT/FILE_LIST.md"

echo "--- Root .md files ---" >> "$OUT/FILE_LIST.md"
find "$REPO" -maxdepth 1 -name "*.md" | sort | sed "s|$REPO/||" >> "$OUT/FILE_LIST.md"
echo "" >> "$OUT/FILE_LIST.md"

echo "--- Test Files (tests/) ---" >> "$OUT/FILE_LIST.md"
find "$REPO/tests" -name "*.py" | sort | sed "s|$REPO/||" >> "$OUT/FILE_LIST.md"
echo "" >> "$OUT/FILE_LIST.md"

echo "--- Config Files ---" >> "$OUT/FILE_LIST.md"
for f in "$REPO"/{pyproject.toml,setup.py,setup.cfg,.gitignore,.env*,Dockerfile*,Makefile,.pre-commit-config.yaml,ruff.toml}; do
    [ -f "$f" ] && echo "- $(basename "$f")" >> "$OUT/FILE_LIST.md"
done

echo "--- Summary ---" >> "$OUT/FILE_LIST.md"
echo "" >> "$OUT/FILE_LIST.md"
echo "- Python files: $(find "$REPO/quant_nanggroe" -name '*.py' | wc -l)" >> "$OUT/FILE_LIST.md"
echo "- Scripts: $(ls "$REPO/scripts/"*.py 2>/dev/null | wc -l)" >> "$OUT/FILE_LIST.md"
echo "- Tests: $(find "$REPO/tests" -name '*.py' | wc -l)" >> "$OUT/FILE_LIST.md"
echo "- Docs (.md): $(find "$REPO/docs" -name '*.md' | wc -l)" >> "$OUT/FILE_LIST.md"
echo "- Total lines: $(find "$REPO/quant_nanggroe" -name '*.py' -exec cat {} + | wc -l)" >> "$OUT/FILE_LIST.md"

echo "=== FILE_LIST.md written ==="
wc -l "$OUT/FILE_LIST.md"
