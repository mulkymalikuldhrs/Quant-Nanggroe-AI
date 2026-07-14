#!/usr/bin/env python3
"""qna-toggle.py — Strategy on/off toggle for Quant Nanggroe AI paper daemon.

Usage:
    python3 scripts/qna-toggle.py list                     # List all strategies + status
    python3 scripts/qna-toggle.py enable <strategy>        # Enable a strategy
    python3 scripts/qna-toggle.py disable <strategy>       # Disable a strategy
    python3 scripts/qna-toggle.py status                   # Show full status
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from quant_nanggroe.engine.audit import AuditLogger
from quant_nanggroe.engine.strategy.strategies import list_strategies

DEFAULT_STATE_DIR = "/root/paper_runs/qna-paper-run-001"


# ── Config I/O ──────────────────────────────────────────────────────────

def read_config(state_dir: str) -> dict:
    path = Path(state_dir) / "strategy_config.json"
    if not path.exists():
        return {"enabled": [], "disabled": [], "last_modified": None}
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"enabled": [], "disabled": [], "last_modified": None}


def write_config(state_dir: str, config: dict) -> None:
    path = Path(state_dir) / "strategy_config.json"
    config["last_modified"] = datetime.now(timezone.utc).isoformat()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(config, f, indent=2)


def _log_audit(state_dir: str, message: str) -> None:
    try:
        audit = AuditLogger(log_dir=str(Path(state_dir)))
        audit.log("SYSTEM", "INFO", message)
        audit.save_to_file()
    except Exception:
        pass


# ── Core API (testable via importlib) ────────────────────────────────────

def _normalize(name: str) -> str:
    """CamelCase/PascalCase → snake_case for strategy name matching."""
    import re
    s = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1_\2', name)
    s = re.sub(r'([a-z\d])([A-Z])', r'\1_\2', s)
    return s.lower()

def _find_strategy(name: str, all_strats: list) -> str | None:
    """Find strategy by exact match or normalized match."""
    if name in all_strats:
        return name
    norm = _normalize(name)
    for s in all_strats:
        if _normalize(s) == norm:
            return s
    return None

def enable_strategy(state_dir: str, strategy: str) -> dict:
    all_strats = list_strategies()
    found = _find_strategy(strategy, all_strats)
    if found is None:
        raise ValueError(
            f"Unknown strategy '{strategy}'. Available: {', '.join(all_strats)}"
        )
    strategy = found
    config = read_config(state_dir)
    enabled = set(config.get("enabled", []))
    disabled = set(config.get("disabled", []))
    if strategy in enabled:
        return config
    disabled.discard(strategy)
    enabled.add(strategy)
    config["enabled"] = sorted(enabled)
    config["disabled"] = sorted(disabled)
    write_config(state_dir, config)
    _log_audit(state_dir, f"Strategy '{strategy}' enabled")
    return config


def disable_strategy(state_dir: str, strategy: str) -> dict:
    all_strats = list_strategies()
    found = _find_strategy(strategy, all_strats)
    if found is None:
        raise ValueError(
            f"Unknown strategy '{strategy}'. Available: {', '.join(all_strats)}"
        )
    strategy = found
    config = read_config(state_dir)
    enabled = set(config.get("enabled", []))
    disabled = set(config.get("disabled", []))
    if strategy in disabled:
        return config

    enabled.discard(strategy)

    remaining = set(list_strategies()) - disabled - {strategy}
    if not remaining:
        raise ValueError("Cannot disable last strategy — at least 1 must remain enabled")

    disabled.add(strategy)
    config["enabled"] = sorted(enabled)
    config["disabled"] = sorted(disabled)
    write_config(state_dir, config)
    _log_audit(state_dir, f"Strategy '{strategy}' disabled")
    return config


def get_strategy_statuses(state_dir: str) -> list[dict]:
    all_strats = list_strategies()
    config = read_config(state_dir)
    enabled_set = set(config.get("enabled", []))
    disabled_set = set(config.get("disabled", []))
    results = []
    for name in all_strats:
        if name in disabled_set:
            status = "disabled"
        else:
            status = "enabled"
        results.append({"name": name, "status": status})
    return results


# ── CLI Commands ─────────────────────────────────────────────────────────

def cmd_list(state_dir: str) -> None:
    statuses = get_strategy_statuses(state_dir)
    print(f"{'Strategy':<25} {'Status':<10}")
    print("-" * 35)
    for s in statuses:
        print(f"{s['name']:<25} {s['status']:<10}")


def cmd_enable(state_dir: str, strategy: str) -> None:
    try:
        enable_strategy(state_dir, strategy)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    print(f"Strategy '{strategy}' enabled")


def cmd_disable(state_dir: str, strategy: str) -> None:
    try:
        disable_strategy(state_dir, strategy)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    print(f"Strategy '{strategy}' disabled")


def cmd_status(state_dir: str) -> None:
    config = read_config(state_dir)
    statuses = get_strategy_statuses(state_dir)
    enabled_count = sum(1 for s in statuses if s["status"] == "enabled")
    disabled_count = sum(1 for s in statuses if s["status"] == "disabled")
    print(f"Config file: {Path(state_dir) / 'strategy_config.json'}")
    print(f"Last modified: {config.get('last_modified', 'never')}")
    print()
    print(f"{'Strategy':<25} {'Status':<10}")
    print("-" * 35)
    for s in statuses:
        print(f"{s['name']:<25} {s['status']:<10}")
    print()
    print(f"Enabled: {enabled_count}")
    print(f"Disabled: {disabled_count}")


# ── Argument Parsing ────────────────────────────────────────────────────

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="qna-toggle",
        description="Strategy on/off toggle for Quant Nanggroe AI paper daemon",
    )
    parser.add_argument(
        "--state-dir", default=DEFAULT_STATE_DIR,
        help=f"Paper run state directory (default: {DEFAULT_STATE_DIR})",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="List all strategies and their status")
    p_enable = sub.add_parser("enable", help="Enable a strategy")
    p_enable.add_argument("strategy", help="Strategy name to enable")
    p_disable = sub.add_parser("disable", help="Disable a strategy")
    p_disable.add_argument("strategy", help="Strategy name to disable")
    sub.add_parser("status", help="Show full status with counts and config path")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if args.command == "list":
        cmd_list(args.state_dir)
    elif args.command == "enable":
        cmd_enable(args.state_dir, args.strategy)
    elif args.command == "disable":
        cmd_disable(args.state_dir, args.strategy)
    elif args.command == "status":
        cmd_status(args.state_dir)


if __name__ == "__main__":
    main()
