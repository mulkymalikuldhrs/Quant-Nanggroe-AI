#!/usr/bin/env python3
"""BH Colony — Agent Mesh Management CLI.

Usage:
    bh status
    bh agents list
    bh agents status --id agent_001
    bh mesh status
    bh radar
    bh health

Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

from __future__ import annotations

import argparse
import json
import sys
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure project root on path
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


# ── Output Helpers ────────────────────────────────────────────────────────────

class _C:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    END = "\033[0m"


def _print_header(text: str) -> None:
    print(f"\n{_C.HEADER}{_C.BOLD}🐝 {text}{_C.END}")
    print(f"{_C.CYAN}{'=' * (len(text) + 3)}{_C.END}")


def _print_ok(text: str) -> None:
    print(f"{_C.GREEN}✅ {text}{_C.END}")


def _print_err(text: str) -> None:
    print(f"{_C.RED}❌ {text}{_C.END}")


def _print_warn(text: str) -> None:
    print(f"{_C.YELLOW}⚠️  {text}{_C.END}")


def _print_info(text: str) -> None:
    print(f"{_C.BLUE}ℹ️  {text}{_C.END}")


def _output(data: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(data, indent=2, default=str))
    else:
        for k, v in data.items():
            if isinstance(v, dict):
                print(f"  {k}:")
                for sk, sv in v.items():
                    print(f"    {sk}: {sv}")
            elif isinstance(v, list):
                print(f"  {k}:")
                for item in v:
                    print(f"    - {item}")
            else:
                print(f"  {k}: {v}")


# ── Default Agent Registry ────────────────────────────────────────────────────

_DEFAULT_AGENTS = [
    {
        "id": "agent_001",
        "name": "Market Analyst",
        "role": "research",
        "status": "ready",
        "colony": "alpha",
        "capabilities": ["market_data", "technical_analysis", "sentiment"],
        "last_heartbeat": datetime.now(timezone.utc).isoformat(),
    },
    {
        "id": "agent_002",
        "name": "Risk Officer",
        "role": "risk_management",
        "status": "ready",
        "colony": "alpha",
        "capabilities": ["risk_assessment", "portfolio_analysis", "kill_switch"],
        "last_heartbeat": datetime.now(timezone.utc).isoformat(),
    },
    {
        "id": "agent_003",
        "name": "Strategy Engine",
        "role": "strategy",
        "status": "ready",
        "colony": "beta",
        "capabilities": ["signal_generation", "regime_detection", "kelly_sizing"],
        "last_heartbeat": datetime.now(timezone.utc).isoformat(),
    },
    {
        "id": "agent_004",
        "name": "Execution Agent",
        "role": "execution",
        "status": "ready",
        "colony": "beta",
        "capabilities": ["order_routing", "fill_tracking", "slippage_monitoring"],
        "last_heartbeat": datetime.now(timezone.utc).isoformat(),
    },
    {
        "id": "agent_005",
        "name": "Portfolio Optimizer",
        "role": "portfolio",
        "status": "ready",
        "colony": "alpha",
        "capabilities": ["allocation", "rebalancing", "correlation_monitoring"],
        "last_heartbeat": datetime.now(timezone.utc).isoformat(),
    },
]


def _load_agents() -> list[dict[str, Any]]:
    """Load agent registry from file or return defaults."""
    registry_path = Path(_project_root) / "agent-ctx" / "agent_registry.json"
    if registry_path.exists():
        try:
            with open(registry_path) as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                return data.get("agents", _DEFAULT_AGENTS)
        except Exception:
            pass
    return _DEFAULT_AGENTS


# ── BH Status ─────────────────────────────────────────────────────────────────

def cmd_status(args: argparse.Namespace) -> None:
    """Check overall BH system status."""
    _print_header("BH Colony System Status")

    agents = _load_agents()
    active = sum(1 for a in agents if a.get("status") == "ready")
    total = len(agents)

    result = {
        "system": "BH Colony Mesh",
        "version": "1.0.0",
        "status": "operational",
        "agents_active": active,
        "agents_total": total,
        "uptime_seconds": int(time.time() % 86400),
        "colony_count": len({a.get("colony", "default") for a in agents}),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    _print_ok(f"System: {result['system']} v{result['version']}")
    _print_ok(f"Status: {result['status']}")
    _print_info(f"Agents: {active}/{total} active")
    _print_info(f"Colonies: {result['colony_count']}")

    _output(result, args.json)


# ── Agents List ───────────────────────────────────────────────────────────────

def cmd_agents_list(args: argparse.Namespace) -> None:
    """List all registered agents."""
    _print_header("BH Agent Registry")

    agents = _load_agents()

    if not agents:
        _print_warn("No agents registered")
        return

    result = {"agents": [], "total": len(agents)}

    for agent in agents:
        entry = {
            "id": agent.get("id", "unknown"),
            "name": agent.get("name", "Unknown"),
            "role": agent.get("role", "unknown"),
            "status": agent.get("status", "unknown"),
            "colony": agent.get("colony", "default"),
        }
        result["agents"].append(entry)

        status_icon = "🟢" if agent.get("status") == "ready" else "🔴"
        print(f"  {status_icon} {entry['id']}: {entry['name']}")
        print(f"     Role: {entry['role']} | Colony: {entry['colony']} | Status: {entry['status']}")
        caps = agent.get("capabilities", [])
        if caps:
            print(f"     Capabilities: {', '.join(caps)}")
        print()

    _print_ok(f"Total agents: {len(agents)}")
    _output(result, args.json)


# ── Agent Status ──────────────────────────────────────────────────────────────

def cmd_agents_status(args: argparse.Namespace) -> None:
    """Check status of a specific agent."""
    _print_header(f"Agent Status: {args.id}")

    agents = _load_agents()
    agent = next((a for a in agents if a.get("id") == args.id), None)

    if not agent:
        _print_err(f"Agent '{args.id}' not found")
        sys.exit(1)

    result = {
        "id": agent.get("id"),
        "name": agent.get("name"),
        "role": agent.get("role"),
        "status": agent.get("status"),
        "colony": agent.get("colony"),
        "capabilities": agent.get("capabilities", []),
        "last_heartbeat": agent.get("last_heartbeat", "unknown"),
        "uptime_seconds": int(time.time() % 86400),
    }

    status_icon = "🟢" if result["status"] == "ready" else "🔴"
    print(f"  {status_icon} Agent: {result['name']} ({result['id']})")
    print(f"     Role: {result['role']}")
    print(f"     Colony: {result['colony']}")
    print(f"     Status: {result['status']}")
    print(f"     Last Heartbeat: {result['last_heartbeat']}")
    if result["capabilities"]:
        print(f"     Capabilities: {', '.join(result['capabilities'])}")

    _output(result, args.json)


# ── Mesh Status ───────────────────────────────────────────────────────────────

def cmd_mesh_status(args: argparse.Namespace) -> None:
    """Check mesh network status."""
    _print_header("BH Mesh Network Status")

    agents = _load_agents()
    colonies = {}
    for a in agents:
        colony = a.get("colony", "default")
        if colony not in colonies:
            colonies[colony] = {"agents": [], "active": 0, "total": 0}
        colonies[colony]["agents"].append(a.get("id"))
        colonies[colony]["total"] += 1
        if a.get("status") == "ready":
            colonies[colony]["active"] += 1

    result = {
        "mesh_status": "operational",
        "total_agents": len(agents),
        "colonies": {},
        "connections": [],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    for colony_name, info in colonies.items():
        result["colonies"][colony_name] = {
            "agents": info["agents"],
            "active": info["active"],
            "total": info["total"],
            "health": "healthy" if info["active"] == info["total"] else "degraded",
        }
        status_icon = "🟢" if info["active"] == info["total"] else "🟡"
        print(f"  {status_icon} Colony '{colony_name}': {info['active']}/{info['total']} active")

    # Simulate inter-colony connections
    colony_names = list(colonies.keys())
    for i in range(len(colony_names)):
        for j in range(i + 1, len(colony_names)):
            result["connections"].append({
                "from": colony_names[i],
                "to": colony_names[j],
                "status": "connected",
                "latency_ms": 12,
            })

    print()
    _print_ok(f"Mesh: {result['mesh_status']} | Colonies: {len(colonies)} | Connections: {len(result['connections'])}")

    _output(result, args.json)


# ── Radar ─────────────────────────────────────────────────────────────────────

def cmd_radar(args: argparse.Namespace) -> None:
    """Check radar peers (external agents and services)."""
    _print_header("BH Radar — Peer Discovery")

    # Simulated peer list; production would query network
    peers = [
        {"id": "peer_quant_001", "name": "Quant Engine", "type": "internal", "status": "connected", "latency_ms": 8},
        {"id": "peer_llm_001", "name": "LLM Gateway", "type": "external", "status": "connected", "latency_ms": 42},
        {"id": "peer_data_001", "name": "Data Provider", "type": "external", "status": "connected", "latency_ms": 15},
        {"id": "peer_broker_001", "name": "Broker Adapter", "type": "external", "status": "pending", "latency_ms": 0},
    ]

    result = {
        "radar_status": "active",
        "peers": peers,
        "total_peers": len(peers),
        "connected": sum(1 for p in peers if p["status"] == "connected"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    for peer in peers:
        icon = "🟢" if peer["status"] == "connected" else "🟡"
        print(f"  {icon} {peer['name']} ({peer['id']})")
        print(f"     Type: {peer['type']} | Status: {peer['status']} | Latency: {peer['latency_ms']}ms")
        print()

    _print_ok(f"Radar: {result['connected']}/{result['total_peers']} peers connected")

    _output(result, args.json)


# ── Health ────────────────────────────────────────────────────────────────────

def cmd_health(args: argparse.Namespace) -> None:
    """Comprehensive system health check."""
    _print_header("BH System Health")

    checks: dict[str, Any] = {}
    all_ok = True

    # 1. Python environment
    checks["python"] = {"status": "ok", "version": sys.version.split()[0]}

    # 2. Core modules
    modules = {
        "engine": "quant_nanggroe.engine",
        "api": "quant_nanggroe.api",
        "security": "quant_nanggroe.security",
        "kelly": "quant_nanggroe.engine.kelly",
        "regime": "quant_nanggroe.engine.regime",
        "stress_testing": "quant_nanggroe.engine.stress_testing",
        "backtest": "quant_nanggroe.engine.backtest",
        "risk": "quant_nanggroe.engine.risk",
    }
    for name, mod_path in modules.items():
        try:
            __import__(mod_path)
            checks[name] = {"status": "ok"}
        except ImportError:
            checks[name] = {"status": "degraded", "error": "not installed"}
            all_ok = False

    # 3. Agent registry
    agents = _load_agents()
    active = sum(1 for a in agents if a.get("status") == "ready")
    checks["agents"] = {
        "status": "ok" if active > 0 else "warning",
        "active": active,
        "total": len(agents),
    }

    # 4. Data directory
    data_dir = Path(_project_root) / "data"
    checks["data_dir"] = {
        "status": "ok" if data_dir.exists() else "warning",
        "path": str(data_dir),
    }

    # 5. Config
    env_file = Path(_project_root) / ".env"
    checks["config"] = {
        "status": "ok" if env_file.exists() else "warning",
        "env_file": str(env_file),
    }

    # Output
    for name, info in checks.items():
        status = info["status"]
        icon = "✅" if status == "ok" else "⚠️ " if status in ("warning", "degraded") else "❌"
        line = f"  {icon} {name}: {status}"
        if "error" in info:
            line += f" ({info['error']})"
        print(line)

    overall = "healthy" if all_ok else "degraded"
    print()
    _print_ok(f"Overall: {overall}")

    if args.json:
        print(json.dumps({"status": overall, "checks": checks}, indent=2, default=str))


# ── Argument Parser ───────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bh",
        description="BH Colony — Agent Mesh Management CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  bh status\n"
            "  bh agents list\n"
            "  bh agents status --id agent_001\n"
            "  bh mesh status\n"
            "  bh radar\n"
            "  bh health\n"
        ),
    )
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    sub = parser.add_subparsers(dest="command", help="Available commands")

    # ── status ──
    p_status = sub.add_parser("status", help="Check BH system status")
    p_status.set_defaults(func=cmd_status)

    # ── agents ──
    p_agents = sub.add_parser("agents", help="Agent management")
    agents_sub = p_agents.add_subparsers(dest="agents_command")

    p_agents_list = agents_sub.add_parser("list", help="List all agents")
    p_agents_list.set_defaults(func=cmd_agents_list)

    p_agents_status = agents_sub.add_parser("status", help="Check agent status")
    p_agents_status.add_argument("--id", required=True, help="Agent ID")
    p_agents_status.set_defaults(func=cmd_agents_status)

    # ── mesh ──
    p_mesh = sub.add_parser("mesh", help="Mesh network management")
    mesh_sub = p_mesh.add_subparsers(dest="mesh_command")
    p_mesh_status = mesh_sub.add_parser("status", help="Check mesh status")
    p_mesh_status.set_defaults(func=cmd_mesh_status)

    # ── radar ──
    p_radar = sub.add_parser("radar", help="Check radar peers")
    p_radar.set_defaults(func=cmd_radar)

    # ── health ──
    p_health = sub.add_parser("health", help="System health check")
    p_health.set_defaults(func=cmd_health)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Route sub-sub-commands (agents list, agents status, mesh status)
    if hasattr(args, "agents_command") and args.agents_command:
        if args.agents_command == "list":
            cmd_agents_list(args)
        elif args.agents_command == "status":
            cmd_agents_status(args)
        else:
            parser.print_help()
            sys.exit(1)
    elif hasattr(args, "mesh_command") and args.mesh_command:
        if args.mesh_command == "status":
            cmd_mesh_status(args)
        else:
            parser.print_help()
            sys.exit(1)
    else:
        args.func(args)


if __name__ == "__main__":
    main()
