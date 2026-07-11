"""
QNA Portable Config — auto-detect OS, paths, environment.

Provides a single source of truth for all paths, SSH config, and OS detection.
Works on Linux, Mac, Windows, and Termux/Android.
All paths are relative to PROJECT_ROOT for full portability.
"""
from __future__ import annotations

import os
import platform
import sys
from pathlib import Path
from typing import Dict, List, Optional

__all__ = [
    "PROJECT_ROOT", "DATA_DIR", "LOG_DIR", "CONFIG_DIR",
    "OS_NAME", "IS_LINUX", "IS_MAC", "IS_WINDOWS", "IS_TERMUX", "IS_ANDROID",
    "PYTHON", "PIP",
    "SSH_USER", "SSH_HOST", "SSH_PORT", "SSH_ARGS",
    "WARP_CONF_PATH", "WARP_REG_PATH",
    "get_env", "load_env_file",
    "platform_info", "ensure_dirs",
]

# ── Project root ──────────────────────────────────────────────────────────
# Auto-detect: the directory containing the quant_nanggroe package
_QNA_PKG = Path(__file__).resolve().parent
PROJECT_ROOT = _QNA_PKG.parent

# ── OS detection ──────────────────────────────────────────────────────────
OS_NAME = sys.platform           # 'linux', 'darwin', 'win32'
IS_LINUX = OS_NAME == "linux"
IS_MAC = OS_NAME == "darwin"
IS_WINDOWS = OS_NAME == "win32"

_IS_TERMUX = (
    "com.termux" in os.environ.get("PREFIX", "").lower()
    or "termux" in os.environ.get("HOME", "").lower()
)
_IS_ANDROID = _IS_TERMUX or bool(os.environ.get("ANDROID_ROOT"))
IS_TERMUX = _IS_TERMUX
IS_ANDROID = _IS_ANDROID

# ── Python executable ─────────────────────────────────────────────────────
PYTHON = sys.executable or "python3"
PIP = os.path.join(os.path.dirname(PYTHON), "pip") if os.path.dirname(PYTHON) else "pip3"

# ── Data directories (relative to project root) ──────────────────────────
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"
CONFIG_DIR = PROJECT_ROOT / "config"

# ── WARP paths (OS-aware) ────────────────────────────────────────────────
if IS_WINDOWS:
    _WARP_BASE = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))) / "qna"
elif IS_MAC:
    _WARP_BASE = Path.home() / "Library" / "Application Support" / "qna"
else:
    _WARP_BASE = Path.home() / ".config" / "qna"

WARP_REG_PATH = _WARP_BASE / "warp_reg.json"
WARP_CONF_PATH = (
    Path("/etc/wireguard/warp.conf") if IS_LINUX and not IS_TERMUX
    else _WARP_BASE / "warp.conf"
)

# ── SSH relay config (from env, with fallback) ────────────────────────────
def _load_env_file() -> None:
    env_paths = [
        PROJECT_ROOT / ".env",
        PROJECT_ROOT / ".env.local",
        CONFIG_DIR / ".env",
    ]
    for p in env_paths:
        if p.is_file():
            try:
                for line in p.read_text().splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, _, v = line.partition("=")
                    k, v = k.strip(), v.strip().strip("\"'")
                    if k not in os.environ:
                        os.environ[k] = v
            except Exception:
                pass
            break

_load_env_file()

def _env_or(key: str, default: str) -> str:
    return os.environ.get(key, default)

SSH_USER = _env_or("QNA_SSH_USER", "u0_a467")
SSH_HOST = _env_or("QNA_SSH_HOST", "10.210.13.229")
SSH_PORT = int(_env_or("QNA_SSH_PORT", "8022"))
SSH_ARGS = [
    "ssh",
    "-o", "StrictHostKeyChecking=no",
    "-o", "ConnectTimeout=10",
    "-p", str(SSH_PORT),
    f"{SSH_USER}@{SSH_HOST}",
]

def get_env(key: str, default: str = "") -> str:
    return _env_or(key, default)

def load_env_file() -> None:
    _load_env_file()

def platform_info() -> Dict[str, bool]:
    return {
        "os": OS_NAME,
        "linux": IS_LINUX,
        "mac": IS_MAC,
        "windows": IS_WINDOWS,
        "termux": IS_TERMUX,
        "android": IS_ANDROID,
        "python": PYTHON,
    }

def ensure_dirs() -> None:
    for d in [DATA_DIR, LOG_DIR, _WARP_BASE]:
        d.mkdir(parents=True, exist_ok=True)
