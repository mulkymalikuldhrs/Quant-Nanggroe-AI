#!/bin/bash
# Automated shell syntax test — run by CI
set -euo pipefail
echo "=== Shell syntax check ==="
errors=0
for f in ../*.sh; do
  [ -f "$f" ] || continue
  if bash -n "$f" 2>/dev/null; then
    echo "  ✅ $(basename "$f")"
  else
    echo "  ❌ $(basename "$f") — syntax error"
    errors=$((errors + 1))
  fi
done
[ "$errors" -eq 0 ] && echo "=== All shell scripts pass ===" || echo "=== $errors errors ==="
exit $errors
