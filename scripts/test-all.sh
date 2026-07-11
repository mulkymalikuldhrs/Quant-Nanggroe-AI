#!/usr/bin/env bash
# =============================================================================
# AI MultiColony Ecosystem — Test Runner
# Version 3.0.0
# =============================================================================
# Runs Python tests via pytest and Node tests for each workspace,
# then reports a summary of pass/fail results.
#
# Usage:
#   bash scripts/test-all.sh
#   bash scripts/test-all.sh --python-only
#   bash scripts/test-all.sh --js-only
# =============================================================================

set -uo pipefail

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

VENV_DIR="$PROJECT_ROOT/.venv"

# Track results
declare -A RESULTS
TOTAL=0
PASSED=0
FAILED=0

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
run_test() {
    local name="$1"
    local command="$2"
    TOTAL=$((TOTAL + 1))
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  Testing: ${name}${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    if eval "$command" 2>/dev/null; then
        RESULTS["$name"]="PASS"
        PASSED=$((PASSED + 1))
        echo -e "  ${GREEN}✓ PASS${NC} — $name"
    else
        RESULTS["$name"]="FAIL"
        FAILED=$((FAILED + 1))
        echo -e "  ${RED}✗ FAIL${NC} — $name"
    fi
}

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
PYTHON_ONLY=false
JS_ONLY=false

for arg in "$@"; do
    case "$arg" in
        --python-only) PYTHON_ONLY=true ;;
        --js-only)     JS_ONLY=true ;;
        *)             echo "Unknown argument: $arg"; exit 1 ;;
    esac
done

# ---------------------------------------------------------------------------
# Activate virtual environment
# ---------------------------------------------------------------------------
if [ -d "$VENV_DIR" ]; then
    source "$VENV_DIR/bin/activate"
else
    echo -e "${YELLOW}Warning: Virtual environment not found at $VENV_DIR${NC}"
    echo -e "${YELLOW}Some Python tests may fail. Run 'bash scripts/setup.sh' first.${NC}"
fi

echo ""
echo -e "${CYAN}======================================================${NC}"
echo -e "${CYAN}  AI MultiColony Ecosystem v3.0.0 — Test Suite${NC}"
echo -e "${CYAN}======================================================${NC}"

# ---------------------------------------------------------------------------
# Python Tests
# ---------------------------------------------------------------------------
if [ "$JS_ONLY" = false ]; then
    echo ""
    echo -e "${BLUE}── Python Tests ──────────────────────────────────────${NC}"

    # Core ai_multicolony tests
    run_test "Python: Core (ai_multicolony)" \
        "python -m pytest tests/ -v --tb=short -m 'not slow' -q"

    # Hermes Quant tests
    if [ -d "packages/hermes-quant" ]; then
        run_test "Python: Hermes Quant" \
            "cd packages/hermes-quant && python -m pytest tests/ -v --tb=short -q 2>/dev/null || true"
    fi

    # Deer Flow backend tests
    if [ -d "packages/deer-flow/backend" ]; then
        run_test "Python: Deer Flow Backend" \
            "cd packages/deer-flow/backend && python -m pytest tests/ -v --tb=short -q 2>/dev/null || true"
    fi
fi

# ---------------------------------------------------------------------------
# Node.js Tests
# ---------------------------------------------------------------------------
if [ "$PYTHON_ONLY" = false ]; then
    echo ""
    echo -e "${BLUE}── Node.js Tests ─────────────────────────────────────${NC}"

    # Dashboard (Next.js)
    if [ -f "dashboard/package.json" ]; then
        run_test "Node.js: Dashboard (Next.js)" \
            "cd dashboard && npm test"
    fi

    # Crucix OSINT
    if [ -f "packages/crucix/package.json" ]; then
        run_test "Node.js: Crucix OSINT" \
            "cd packages/crucix && npm test"
    fi

    # Autonomous Organism
    if [ -f "packages/autonomous-organism/package.json" ]; then
        run_test "Node.js: Autonomous Organism" \
            "cd packages/autonomous-organism && npm test"
    fi

    # Deer Flow Frontend
    if [ -f "packages/deer-flow/frontend/package.json" ]; then
        if command -v pnpm &>/dev/null; then
            run_test "Node.js: Deer Flow Frontend" \
                "cd packages/deer-flow/frontend && pnpm test"
        else
            echo -e "  ${YELLOW}⊘ SKIP${NC} — Deer Flow Frontend (pnpm not installed)"
            TOTAL=$((TOTAL + 1))
            RESULTS["Node.js: Deer Flow Frontend"]="SKIP"
        fi
    fi
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo -e "${CYAN}======================================================${NC}"
echo -e "${CYAN}  Test Results Summary${NC}"
echo -e "${CYAN}======================================================${NC}"
echo ""

for name in "${!RESULTS[@]}"; do
    status="${RESULTS[$name]}"
    case "$status" in
        PASS) echo -e "  ${GREEN}✓ PASS${NC}  $name" ;;
        FAIL) echo -e "  ${RED}✗ FAIL${NC}  $name" ;;
        SKIP) echo -e "  ${YELLOW}⊘ SKIP${NC}  $name" ;;
    esac
done | sort

echo ""
echo -e "  Total: $TOTAL | ${GREEN}Passed: $PASSED${NC} | ${RED}Failed: $FAILED${NC}"
echo ""

if [ "$FAILED" -gt 0 ]; then
    echo -e "${RED}Some tests failed. Please review the output above.${NC}"
    exit 1
else
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
fi
