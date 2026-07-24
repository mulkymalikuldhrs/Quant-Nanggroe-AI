#!/usr/bin/env python3
"""Strategy migration tool — audit and migrate strategies from old path to canonical.

Old path: quant_nanggroe/engine/strategy/strategies/ (139 files, pre-migration)
New path: quant_nanggroe/engine/strategies/ (28 files, using new base + registry)

Usage:
    python scripts/migrate_strategies.py          # dry-run audit
    python scripts/migrate_strategies.py --report  # generate JSON report
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
OLD_DIR = REPO_ROOT / "quant_nanggroe" / "engine" / "strategy" / "strategies"
NEW_DIR = REPO_ROOT / "quant_nanggroe" / "engine" / "strategies"


def audit() -> dict:
    old_files = {p.stem: p for p in OLD_DIR.glob("*.py") if p.stem != "__init__"}
    new_files = {p.stem: p for p in NEW_DIR.glob("*.py") if p.stem != "__init__"}

    migrated = {name for name in old_files if name in new_files}
    pending = {name for name in old_files if name not in new_files}
    new_only = {name for name in new_files if name not in old_files}

    return {
        "old_count": len(old_files),
        "new_count": len(new_files),
        "migrated_count": len(migrated),
        "pending_count": len(pending),
        "new_only_count": len(new_only),
        "migrated": sorted(migrated),
        "pending": sorted(pending),
        "new_only": sorted(new_only),
    }


def print_report(report: dict) -> None:
    print("Strategy Migration Report")
    print("=" * 40)
    print(f"  Old path: {OLD_DIR}")
    print(f"  New path: {NEW_DIR}")
    print(f"  Old strategies: {report['old_count']}")
    print(f"  New strategies: {report['new_count']}")
    print(f"  Already migrated: {report['migrated_count']}")
    print(f"  Pending migration: {report['pending_count']}")
    print(f"  New only (no old equivalent): {report['new_only_count']}")
    print()
    if report["pending"]:
        print(f"Pending ({len(report['pending'])}):")
        for name in report["pending"]:
            print(f"  - {name}")


def main():
    parser = argparse.ArgumentParser(description="Audit strategy migration status")
    parser.add_argument("--report", action="store_true", help="Output JSON report")
    args = parser.parse_args()

    report = audit()

    if args.report:
        json.dump(report, sys.stdout, indent=2)
        print()
    else:
        print_report(report)

    return 0 if report["pending_count"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
