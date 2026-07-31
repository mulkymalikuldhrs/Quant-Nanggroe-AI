"""
MT5 Auto-Path Detection & Launcher
===================================

Detects MetaTrader 5 terminal installation anywhere on the system,
sets up the environment so the `MetaTrader5` Python package can load
its native `mt5plugin.dll` / `mt5api.dll`, and optionally launches the
terminal if not running.

Usage:
    from quant_nanggroe.utils.mt5_launcher import detect_mt5, ensure_mt5_env, launch_mt5_if_needed

    # 1. Make sure MT5 native lib is loadable
    ensure_mt5_env()

    # 2. Import MT5 (now it will find the plugin)
    import MetaTrader5 as mt5

    # 3. (Optional) launch terminal if not running
    term = launch_mt5_if_needed()
"""

from __future__ import annotations

import os
import sys
import subprocess
import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

# Common MT5 terminal install roots (broker-agnostic — terminal64.exe lives here)
_COMMON_DIRS = [
    r"C:\Program Files\MetaTrader 5",
    r"C:\Program Files (x86)\MetaTrader 5",
    r"C:\Users\{user}\AppData\Roaming\MetaQuotes\Terminal",
    r"C:\Users\{user}\AppData\Local\MetaQuotes\Terminal",
    r"C:\Program Files\MetaTrader 5 Terminal",
    r"D:\MetaTrader 5",
    r"E:\MetaTrader 5",
    r"D:\Program Files\MetaTrader 5",
    r"E:\Program Files\MetaTrader 5",
    # Broker-branded terminals (terminal64.exe still inside)
    r"C:\Program Files\MetaTrader 5 IC Markets",
    r"C:\Program Files\MetaTrader 5 Valetax",
    r"C:\Program Files\MetaTrader 5 Pepperstone",
    r"C:\Program Files\MetaTrader 5 XM",
    r"C:\Program Files\MetaTrader 5 Exness",
]


def _expand_dirs() -> List[Path]:
    """Expand template paths with the real username."""
    user = os.getenv("USERNAME", "")
    out: List[Path] = []
    for d in _COMMON_DIRS:
        d2 = d.format(user=user) if "{user}" in d else d
        out.append(Path(d2))
    # Also scan all top-level C:/D:/E: Program Files for any *MetaTrader* folder
    for drive in ("C:", "D:", "E:", "F:"):
        for base in (f"{drive}/Program Files", f"{drive}/Program Files (x86)"):
            try:
                for entry in os.scandir(base):
                    if entry.is_dir() and "metatrader" in entry.name.lower():
                        out.append(Path(entry.path))
            except (OSError, PermissionError):
                continue
    return out


def find_terminal_exe() -> Optional[Path]:
    """Return the first found terminal64.exe (or terminal.exe) path."""
    for d in _expand_dirs():
        if not d.exists():
            continue
        # Direct hit
        for name in ("terminal64.exe", "terminal.exe"):
            cand = d / name
            if cand.exists():
                return cand
        # Recursive (MetaQuotes stores terminals in hashed subfolders)
        try:
            for root, _dirs, files in os.walk(d):
                for f in files:
                    if f.lower() in ("terminal64.exe", "terminal.exe"):
                        return Path(root) / f
        except (OSError, PermissionError):
            continue
    return None


def find_mt5_plugin_dir() -> Optional[Path]:
    """Find the directory containing mt5plugin.dll / mt5api.dll."""
    term = find_terminal_exe()
    if term is None:
        return None
    term_dir = term.parent
    # The native libs usually sit next to terminal64.exe
    for lib in ("mt5plugin.dll", "mt5api.dll", "mt5manager.dll"):
        if (term_dir / lib).exists():
            return term_dir
    # Some brokers ship them in a subfolder
    for sub in ("MQL5", "libs", "plugins"):
        subp = term_dir / sub
        if subp.exists() and any(subp.glob("mt5*.dll")):
            return subp
    return term_dir  # fallback: same dir as terminal


def ensure_mt5_env() -> bool:
    """Add MT5 native lib dir to PATH + os.add_dll_directory so the
    Python `MetaTrader5` package can load its plugin.

    Returns True if a terminal was found, False otherwise.
    """
    plugin_dir = find_mt5_plugin_dir()
    if plugin_dir is None:
        logger.warning("MT5 terminal not found on this system — paper mode only")
        return False

    plugin_str = str(plugin_dir)
    # 1. PATH (classic DLL resolution)
    env_path = os.environ.get("PATH", "")
    if plugin_str not in env_path:
        os.environ["PATH"] = plugin_str + os.pathsep + env_path

    # 2. Windows DLL search order (Python 3.8+)
    if sys.platform == "win32":
        try:
            os.add_dll_directory(plugin_str)
        except (OSError, AttributeError, FileNotFoundError):
            pass

    logger.info("MT5 env ready — plugin dir: %s", plugin_str)
    return True


def is_mt5_running() -> bool:
    """Check if terminal64.exe is already running."""
    try:
        out = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq terminal64.exe", "/NH"],
            capture_output=True, text=True, timeout=10,
        )
        return "terminal64.exe" in out.stdout
    except Exception:
        return False


def launch_mt5_if_needed() -> Optional[Path]:
    """Launch MT5 terminal if not running. Returns terminal path or None."""
    term = find_terminal_exe()
    if term is None:
        logger.warning("Cannot launch MT5 — terminal not found")
        return None
    if is_mt5_running():
        logger.info("MT5 terminal already running")
        return term
    try:
        subprocess.Popen([str(term)], shell=False)
        logger.info("MT5 terminal launched: %s", term)
    except Exception as e:
        logger.error("Failed to launch MT5: %s", e)
    return term


def detect_mt5() -> dict:
    """Convenience: return a status dict for logging / health checks."""
    term = find_terminal_exe()
    plugin = find_mt5_plugin_dir()
    return {
        "found": term is not None,
        "terminal_path": str(term) if term else None,
        "plugin_dir": str(plugin) if plugin else None,
        "running": is_mt5_running() if term else False,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(detect_mt5(), indent=2))
    ensure_mt5_env()
