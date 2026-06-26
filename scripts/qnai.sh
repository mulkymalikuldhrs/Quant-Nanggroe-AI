#!/usr/bin/env bash
# qnai.sh — Shell wrapper for unified qnai CLI.
# Usage: bash scripts/qnai.sh <subcommand> [args...]
set -e
DIR="$(cd "$(dirname "$0")/.." && pwd)"
for py in python3 python python3.12; do
    if command -v "$py" >/dev/null 2>&1; then
        exec "$py" "$DIR/scripts/qnai" "$@"
    fi
done
echo "Error: no Python interpreter found" >&2
exit 1
