#!/bin/bash
# repo-structure-test.sh — Verify this repo meets Dhaher Labs standards
# Usage: bash test.sh

errors=0
pass() { echo "  [PASS] $1"; }
fail() { echo "  [FAIL] $1"; errors=$((errors+1)); }

[ -f README.md ] && pass "README exists" || fail "README missing"
[ -f AGENTS.md ] && pass "AGENTS.md exists" || fail "AGENTS.md missing"
[ -f LICENSE ] && pass "LICENSE exists" || fail "LICENSE missing"

# Check .git (handles both worktree and standalone)
if [ -f .git ] && head -1 .git 2>/dev/null | grep -q "gitdir:"; then
  pass ".git worktree link valid"
elif [ -d .git ]; then
  pass ".git directory exists"
else
  fail "No .git found"
fi

echo ""
if [ "$errors" -eq 0 ]; then
  echo "All structure tests passed!"
else
  echo "$errors structure test(s) failed"
fi
exit $errors
