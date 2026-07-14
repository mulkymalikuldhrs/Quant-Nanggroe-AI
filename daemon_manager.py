#!/usr/bin/env python3
"""
🌐 Quant Nanggroe AI — Legacy Daemon Manager Wrapper
══════════════════════════════════════════════════════

This file is now a THIN WRAPPER that delegates to the unified launcher (qna.py).
The unified launcher is the single source of truth for all entry modes.

Usage:
    python daemon_manager.py start    → same as python qna.py daemon
    python daemon_manager.py status   → same as python qna.py status
    python daemon_manager.py stop     → sends SIGTERM to daemon process

The legacy DaemonManager class with hardcoded agent configs has been removed.
Agent configuration is now centralized in qna.py's load_agent_config().

Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

import os
import sys
import signal
import warnings
from pathlib import Path
from typing import Optional

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

# Delegate to unified launcher
try:
    from qna import __version__, load_agent_config
except ImportError as e:
    print(f"❌ Failed to load unified launcher (qna.py): {e}")
    print("   Ensure qna.py is in the project root directory.")
    sys.exit(1)

# Legacy PID file location
PID_DIR = Path("data/daemons")
PID_FILE = PID_DIR / "qna_daemon.pid"


def main() -> None:
    """Legacy daemon manager entry point — delegates to qna.py."""
    warnings.warn(
        "daemon_manager.py is deprecated. Use 'python qna.py daemon' instead.",
        DeprecationWarning,
        stacklevel=2,
    )

    if len(sys.argv) < 2:
        print("Usage: python daemon_manager.py {start|stop|restart|status}")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "start":
        _start()
    elif command == "stop":
        _stop()
    elif command == "restart":
        _stop()
        _start()
    elif command == "status":
        _status()
    else:
        print(f"Unknown command: {command}")
        print("Usage: python daemon_manager.py {start|stop|restart|status}")
        sys.exit(1)


def _start() -> None:
    """Start daemon via qna.py."""
    print(f"🛡️ Starting Quant Nanggroe AI Daemon v{__version__}")
    print("🇮🇩 Made with ❤️ by Mulky Malikul Dhaher in Indonesia")
    print()

    # Delegate to qna.py's daemon mode
    from qna import run_daemon, build_parser

    parser = build_parser()
    args = parser.parse_args(["daemon"])
    sys.exit(run_daemon(args))


def _stop() -> None:
    """Stop the daemon process."""
    pid = _read_pid()
    if pid is None:
        print("❌ Daemon PID file not found. Is the daemon running?")
        print("   Try: python qna.py status")
        return

    try:
        os.kill(pid, signal.SIGTERM)
        print(f"✅ Daemon (PID {pid}) stopped.")

        # Remove PID file
        if PID_FILE.exists():
            PID_FILE.unlink()
    except ProcessLookupError:
        print(f"⚠️  Daemon (PID {pid}) not found. Removing stale PID file.")
        if PID_FILE.exists():
            PID_FILE.unlink()
    except Exception as e:
        print(f"❌ Failed to stop daemon: {e}")


def _status() -> None:
    """Show daemon status."""
    from qna import run_status, build_parser
    parser = build_parser()
    args = parser.parse_args(["status"])
    sys.exit(run_status(args))


def _read_pid() -> Optional[int]:
    """Read PID from PID file."""
    if not PID_FILE.exists():
        return None
    try:
        with open(PID_FILE, "r") as f:
            return int(f.read().strip())
    except (ValueError, OSError):
        return None


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Shutdown requested.")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)
