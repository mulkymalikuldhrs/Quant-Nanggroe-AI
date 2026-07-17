#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║            Quant Nanggroe AI — Unified Launcher                    ║
║                                                                    ║
║   Modes:                                                           ║
║     qna cli      → Interactive CLI shell                           ║
║     qna api      → FastAPI server (port 8000)                      ║
║     qna daemon   → Background daemon with agent lifecycle          ║
║     qna web      → Legacy Flask web UI (port 5000)                 ║
║     qna status   → System health & status                          ║
║                                                                    ║
║   Built by Dhaher Labs — Quant Nanggroe Hedge Fund                 ║
╚══════════════════════════════════════════════════════════════════════╝

   This is the SINGLE source of truth for all entry points.
   main.py, cli.py, and daemon_manager.py are thin wrappers that
   delegate to this module.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# ── Ensure project root is on sys.path (BEFORE any project imports) ─
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

# ── Version (single source of truth) ────────────────────────────────
__version__ = "4.3.4"
QNA_VERSION = __version__

# ── PID management for daemon mode ─────────────────────────────────
PID_DIR = Path("data/daemons")
PID_FILE = PID_DIR / "qna_daemon.pid"

# ── Logging ─────────────────────────────────────────────────────────
LOG_LEVEL = os.environ.get("QNA_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("QNA")


# ── Banner ──────────────────────────────────────────────────────────

BANNER = f"""
╔══════════════════════════════════════════════════════════════════════╗
║          Quant Nanggroe AI v{__version__:<29}║
║          Agentic Trading Intelligence OS                            ║
║                                                                    ║
║          Built by Dhaher Labs — Quant Nanggroe Hedge Fund          ║
╚══════════════════════════════════════════════════════════════════════╝
"""


# ══════════════════════════════════════════════════════════════════════
#  AGENT CONFIGURATION — Single source of truth
#  (main.py and daemon_manager.py delegate here via load_agent_config)
# ══════════════════════════════════════════════════════════════════════

DEFAULT_AGENTS: Dict[str, Dict[str, Any]] = {
    # ── Core System Agents (priority 1) ────────────────
    "prompt_master": {
        "module": "quant_nanggroe.agents.prompt_master",
        "class": "PromptMasterAgent",
        "priority": 1,
        "auto_start": True,
        "description": "🧠 Prompt processing & routing",
    },
    "memory_bus": {
        "module": "quant_nanggroe.agents.memory_bus",
        "class": "MemoryBusAgent",
        "priority": 1,
        "auto_start": True,
        "description": "💾 Distributed memory & state management",
    },
    "scheduler": {
        "module": "quant_nanggroe.agents.scheduler",
        "class": "SchedulerAgent",
        "priority": 1,
        "auto_start": True,
        "description": "⏰ Task scheduling & orchestration",
    },
    # ── Trading Agents (priority 2) ────────────────────
    "researcher": {
        "module": "quant_nanggroe.agents.researcher",
        "class": "ResearcherAgent",
        "priority": 2,
        "auto_start": True,
        "description": "🔬 Market research & analysis",
    },
    "trader": {
        "module": "quant_nanggroe.agents.trader",
        "class": "TraderAgent",
        "priority": 2,
        "auto_start": True,
        "description": "📈 Trade execution & decision making",
    },
    "risk_manager": {
        "module": "quant_nanggroe.agents.risk_manager",
        "class": "RiskManagerAgent",
        "priority": 2,
        "auto_start": True,
        "description": "🛡️ Risk assessment & kill switch",
    },
    "strategist": {
        "module": "quant_nanggroe.agents.strategist",
        "class": "StrategistAgent",
        "priority": 2,
        "auto_start": True,
        "description": "📊 Strategy generation & optimization",
    },
    # ── Support Agents (priority 3) ────────────────────
    "cybershell": {
        "module": "quant_nanggroe.agents.cybershell",
        "class": "CyberShellAgent",
        "priority": 3,
        "auto_start": True,
        "description": "🔐 Security & system operations",
    },
    "bug_hunter": {
        "module": "quant_nanggroe.agents.bug_hunter",
        "class": "BugHunterAgent",
        "priority": 3,
        "auto_start": True,
        "description": "🐛 Vulnerability discovery & testing",
    },
    "data_sync": {
        "module": "quant_nanggroe.agents.data_sync",
        "class": "DataSyncAgent",
        "priority": 3,
        "auto_start": True,
        "description": "🔄 Data synchronization & backup",
    },
}


def load_agent_config() -> Dict[str, Dict[str, Any]]:
    """Load agent configuration, merging defaults with user overrides."""
    config_path = PROJECT_ROOT / "config" / "agents.json"
    agents = dict(DEFAULT_AGENTS)

    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                user_config = json.load(f)
            agents.update(user_config)
            logger.info("Loaded agent config from %s", config_path)
        except Exception as e:
            logger.warning("Failed to load agent config: %s", e)

    return agents


# ══════════════════════════════════════════════════════════════════════
#  MODE: CLI
# ══════════════════════════════════════════════════════════════════════

def run_cli(args: argparse.Namespace) -> int:
    """Run interactive CLI shell."""
    print(BANNER)
    print("🎯 Entering CLI mode. Type 'help' for commands, 'exit' to quit.")
    print()

    agents = load_agent_config()

    while True:
        try:
            cmd = input("QNA > ").strip()
            if not cmd:
                continue
            if cmd.lower() in ("exit", "quit"):
                break
            if cmd.lower() == "help":
                _print_cli_help()
                continue
            if cmd.lower() == "status":
                print(f"  Version: {__version__}")
                print(f"  Agents: {len(agents)} configured")
                print(f"  Modes: cli | api | daemon | web")
                continue
            if cmd.lower() == "agents":
                for name, cfg in agents.items():
                    icon = cfg.get("description", "🤖")[:2]
                    print(f"  {icon} {name} (priority {cfg['priority']})")
                continue
            print(f"  Unknown command: {cmd}. Type 'help' for options.")
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except EOFError:
            break

    return 0


def _print_cli_help() -> None:
    """Print CLI usage help."""
    print("""
  Commands:
    help              Show this help
    status            Show system status
    agents            List configured agents
    exit / quit       Exit CLI

  To run in other modes:
    python qna.py api       Start API server
    python qna.py daemon    Start daemon mode
    python qna.py web       Start web UI
""")


# ══════════════════════════════════════════════════════════════════════
#  MODE: API Server
# ══════════════════════════════════════════════════════════════════════

def run_api(args: argparse.Namespace) -> int:
    """Start the FastAPI server."""
    port = args.port or 8000
    host = args.host or "0.0.0.0"

    print(BANNER)
    print(f"🚀 Starting API server on {host}:{port}...")
    print()

    try:
        import uvicorn
        from quant_nanggroe.api.app import create_app

        app = create_app()
        logger.info("API server starting on %s:%s", host, port)

        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level=LOG_LEVEL.lower(),
            reload=args.reload,
        )
    except ImportError as e:
        logger.error("Failed to start API server: %s", e)
        logger.error("Install required packages: pip install uvicorn fastapi")
        return 1
    except Exception as e:
        logger.error("API server error: %s", e)
        return 1

    return 0


# ══════════════════════════════════════════════════════════════════════
#  MODE: Daemon
# ══════════════════════════════════════════════════════════════════════

class DaemonRunner:
    """Background daemon that manages agent lifecycle."""

    def __init__(self, agents: Dict[str, Dict[str, Any]]):
        self.agents = agents
        self.running: Dict[str, Any] = {}
        self._shutdown = False
        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        """Register signal handlers for graceful shutdown."""
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                signal.signal(sig, self._signal_handler)
            except (OSError, ValueError):
                pass

    def _signal_handler(self, signum: int, frame) -> None:
        """Handle shutdown signals."""
        logger.info("Received signal %s, initiating shutdown...", signum)
        self._shutdown = True

    def start(self) -> None:
        """Start all agents and enter monitor loop."""
        logger.info("Starting %d agents...", len(self.agents))

        # Start agents in priority order
        sorted_agents = sorted(
            self.agents.items(),
            key=lambda x: x[1].get("priority", 5),
        )

        for agent_id, config in sorted_agents:
            if config.get("auto_start", True):
                if self._start_agent(agent_id, config):
                    logger.info("  [OK] %s", agent_id)
                else:
                    logger.warning("  [FAIL] %s", agent_id)

        logger.info("All agents started. Entering monitor loop...")

        # Monitor loop
        while not self._shutdown:
            time.sleep(30)
            self._check_health()

    def _start_agent(self, agent_id: str, config: Dict[str, Any]) -> bool:
        """Start a single agent."""
        try:
            module_path = config["module"]
            class_name = config.get("class", "")
            instance_name = config.get("instance", agent_id)

            module = __import__(module_path, fromlist=[instance_name])
            agent_instance = getattr(module, instance_name, None)

            if agent_instance is None and class_name:
                agent_class = getattr(module, class_name, None)
                if agent_class:
                    agent_instance = agent_class()

            if agent_instance is not None:
                self.running[agent_id] = {
                    "instance": agent_instance,
                    "config": config,
                    "start_time": datetime.now(),
                    "status": "running",
                }
                return True

            logger.warning("Agent %s: module loaded but no instance found", agent_id)
            return False

        except ImportError as e:
            logger.debug("Agent %s not available: %s", agent_id, e)
            return False
        except Exception as e:
            logger.warning("Failed to start agent %s: %s", agent_id, e)
            return False

    def _check_health(self) -> None:
        """Check health of all running agents."""
        for agent_id in list(self.running.keys()):
            try:
                agent = self.running[agent_id]["instance"]
                if hasattr(agent, "status") and agent.status in ("error", "crashed"):
                    logger.warning("Agent %s unhealthy, restarting...", agent_id)
                    self._restart_agent(agent_id)
            except Exception:
                pass

    def _restart_agent(self, agent_id: str) -> None:
        """Restart a failed agent."""
        if agent_id in self.running:
            config = self.running[agent_id]["config"]
            self.stop_agent(agent_id)
            time.sleep(1)
            self._start_agent(agent_id, config)

    def stop_agent(self, agent_id: str) -> None:
        """Stop a specific agent."""
        if agent_id in self.running:
            try:
                agent = self.running[agent_id]["instance"]
                if hasattr(agent, "stop"):
                    agent.stop()
                elif hasattr(agent, "status"):
                    agent.status = "stopped"
            except Exception as e:
                logger.warning("Error stopping agent %s: %s", agent_id, e)
            del self.running[agent_id]

    def stop_all(self) -> None:
        """Stop all running agents."""
        for agent_id in list(self.running.keys()):
            self.stop_agent(agent_id)
        logger.info("All agents stopped.")


def _write_pid() -> None:
    """Write current PID to PID file."""
    PID_DIR.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()))


def _read_pid() -> Optional[int]:
    """Read PID from PID file."""
    if not PID_FILE.exists():
        return None
    try:
        return int(PID_FILE.read_text().strip())
    except (ValueError, OSError):
        return None


def stop_daemon() -> int:
    """Stop the running daemon process."""
    pid = _read_pid()
    if pid is None:
        print("❌ No daemon PID file found. Is the daemon running?")
        print("   Try: python qna.py status")
        return 1
    try:
        os.kill(pid, signal.SIGTERM)
        print(f"✅ Daemon (PID {pid}) stopped.")
        if PID_FILE.exists():
            PID_FILE.unlink()
    except ProcessLookupError:
        print(f"⚠️  Daemon (PID {pid}) not found. Removing stale PID file.")
        if PID_FILE.exists():
            PID_FILE.unlink()
    except Exception as e:
        print(f"❌ Failed to stop daemon: {e}")
        return 1
    return 0


def run_daemon(args: argparse.Namespace) -> int:
    """Run daemon mode with agent lifecycle management."""
    print(BANNER)
    _write_pid()
    agents = load_agent_config()

    daemon = DaemonRunner(agents)
    try:
        daemon.start()
    except KeyboardInterrupt:
        logger.info("Shutdown requested...")
    finally:
        daemon.stop_all()
        if PID_FILE.exists():
            PID_FILE.unlink()

    return 0


# ══════════════════════════════════════════════════════════════════════
#  MODE: Web UI (Legacy)
# ══════════════════════════════════════════════════════════════════════

def run_web(args: argparse.Namespace) -> int:
    """Start the legacy Flask web UI."""
    port = args.port or 5000

    print(BANNER)
    print(f"🌐 Starting web UI on port {port}...")
    print()

    try:
        from web_interface.app import app as flask_app
        flask_app.run(host="0.0.0.0", port=port, debug=False)
    except ImportError as e:
        logger.error("Web UI not available: %s", e)
        print("  Install Flask: pip install flask")
        return 1
    except Exception as e:
        logger.error("Web UI error: %s", e)
        return 1

    return 0


# ══════════════════════════════════════════════════════════════════════
#  MODE: Status / Health Check
# ══════════════════════════════════════════════════════════════════════

def run_status(args: argparse.Namespace) -> int:
    """Show system status and health."""
    print(BANNER)
    print("📊 System Status\n")

    print(f"  Version:      {__version__}")
    print(f"  Python:       {sys.version.split()[0]}")
    print(f"  Platform:     {sys.platform}")
    print(f"  Project Root: {PROJECT_ROOT}")
    print()

    # Check if API server is running
    try:
        import urllib.request
        resp = urllib.request.urlopen("http://localhost:8000/health", timeout=3)
        if resp.status == 200:
            print("  API Server:   ✅ Running (port 8000)")
        else:
            print("  API Server:   ⚠️  Responding but unhealthy")
    except Exception:
        print("  API Server:   ❌ Not running (port 8000)")
        print("                 Start with: python qna.py api")

    # Check if web UI is running
    try:
        import urllib.request
        resp = urllib.request.urlopen("http://localhost:5000/", timeout=3)
        print("  Web UI:       ✅ Running (port 5000)")
    except Exception:
        print("  Web UI:       ❌ Not running (port 5000)")
        print("                 Start with: python qna.py web")

    # Import project to check version consistency
    _import_quant_nanggroe()

    print()
    print("  Modes available:")
    print("    python qna.py cli         Interactive CLI")
    print("    python qna.py api         API server (FastAPI)")
    print("    python qna.py daemon      Background daemon")
    print("    python qna.py web         Legacy web UI")
    print("    python qna.py status      This status check")
    print("    python qna.py stop        Stop running daemon")

    return 0


def _import_quant_nanggroe() -> bool:
    """Lazy import of quant_nanggroe package. Returns True if successful."""
    try:
        import quant_nanggroe  # noqa: F401
        logger.debug("quant_nanggroe package loaded successfully")
        return True
    except ImportError as e:
        logger.debug("quant_nanggroe package not available: %s", e)
        return False
    except Exception as e:
        logger.warning("quant_nanggroe package import warning: %s", e)
        return False


# ══════════════════════════════════════════════════════════════════════
#  CLI ARGUMENT PARSER
# ══════════════════════════════════════════════════════════════════════

def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(
        prog="qna",
        description="Quant Nanggroe AI — Unified Launcher",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python qna.py cli              Interactive CLI shell
  python qna.py api              Start API server on port 8000
  python qna.py api --port 8080  Custom port
  python qna.py daemon           Background daemon mode
  python qna.py web              Legacy web UI on port 5000
  python qna.py status           System health check
        """,
    )

    parser.add_argument(
        "mode",
        nargs="?",
        choices=["cli", "api", "daemon", "web", "status", "stop"],
        default="cli",
        help="Launch mode (default: cli)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port number (api: 8000, web: 5000)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Host address (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable hot-reload (api mode only)",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version and exit",
    )

    return parser


# ══════════════════════════════════════════════════════════════════════
#  MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════════════════

def main() -> int:
    """Main entry point — routes to the selected mode."""
    parser = build_parser()
    args, _ = parser.parse_known_args()

    if args.version:
        print(f"Quant Nanggroe AI v{__version__}")
        return 0

    # ── C5: converge every mode (cli/daemon/api/web) on ONE kill-switch
    # state file. Without this the daemon + api + any bridge each keep their
    # own in-memory switch and never agree (split-brain). Idempotent; tests
    # that set QNA_KILL_SWITCH_STATE_FILE keep their isolation. Fail-closed
    # is enforced inside KillSwitch() if the file later becomes unreadable.
    try:
        from quant_nanggroe.engine.risk.kill_switch import configure_kill_switch_file
        configure_kill_switch_file()
    except Exception:  # pragma: no cover - never block boot on this
        pass

    # Route to the selected mode
    mode_map = {
        "cli": run_cli,
        "api": run_api,
        "daemon": run_daemon,
        "web": run_web,
        "status": run_status,
        "stop": lambda a: stop_daemon(),
    }

    runner = mode_map.get(args.mode, run_cli)
    return runner(args)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n👋 Shutdown requested.")
        sys.exit(0)
    except Exception as e:
        logger.critical("Fatal error: %s", e)
        sys.exit(1)
