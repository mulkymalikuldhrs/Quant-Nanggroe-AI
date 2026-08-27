"""MT5 account auto-discovery (user mandate 2026-08-04: "account must auto
detect ... detect all available accounts").

MT5's C-API binds one process to one terminal+account, and there is no native
"list all accounts" call. But a *running* terminal that is already logged in
exposes its live account via ``mt5.account_info()``. So real auto-detection =
enumerate every installed MT5 terminal, initialise each with its own path, and
read the account it is currently authenticated as.

This module:
- scans known MT5 terminal install locations (+ a configurable list),
- for each, initialises MT5, reads the active account,
- returns a list of ``DiscoveredAccount`` (login/server/equity/balance/path),
- is fail-closed: a terminal with no account, or missing lib, yields nothing
  rather than a fake/default account.

It never invents credentials. It only surfaces what the terminal itself
reports. Multi-account (one terminal, many logins) is not possible in MT5's
design; for that, run multiple terminals and this scanner picks each up.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)

# Known MT5 terminal install roots to scan (extend via env QNA_MT5_TERMINALS).
_DEFAULT_TERMINAL_DIRS = [
    r"C:\Program Files\MetaTrader 5",
    r"C:\Program Files (x86)\MetaTrader 5",
    r"C:\Program Files\Valutrades MT5",
    r"C:\Program Files\Exness MT5",
    r"C:\Program Files\IC Markets MT5",
    r"C:\Program Files\Pepperstone MT5",
    r"C:\Program Files\MetaQuotes\Terminal",
    # Broker-branded terminals (terminal64.exe still inside) — match
    # quant_nanggroe.utils.mt5_launcher._COMMON_DIRS so discovery finds the
    # SAME terminals the launcher knows about.
    r"C:\Program Files\MetaTrader 5 Valetax",
    r"C:\Program Files\MetaTrader 5 Exness",
    r"C:\Program Files\MetaTrader 5 IC Markets",
    r"C:\Program Files\MetaTrader 5 Pepperstone",
    r"C:\Program Files\MetaTrader 5 XM",
    r"D:\MetaTrader 5",
    r"E:\MetaTrader 5",
    r"D:\Program Files\MetaTrader 5",
    r"E:\Program Files\MetaTrader 5",
]


@dataclass
class DiscoveredAccount:
    login: int
    server: str
    name: str = ""
    equity: float = 0.0
    balance: float = 0.0
    currency: str = ""
    terminal_path: str = ""          # which terminal64.exe this account lives in
    source: str = "mt5_terminal"     # how we found it (terminal-scan | config)

    def to_dict(self) -> dict:
        return {
            "login": self.login,
            "server": self.server,
            "name": self.name,
            "equity": round(self.equity, 2),
            "balance": round(self.balance, 2),
            "currency": self.currency,
            "terminal_path": self.terminal_path,
            "source": self.source,
        }


def _candidate_terminal_dirs(extra: Optional[List[str]] = None) -> List[str]:
    """Build the list of terminal install directories to scan."""
    dirs = list(_DEFAULT_TERMINAL_DIRS)
    env = os.environ.get("QNA_MT5_TERMINALS")
    if env:
        dirs.extend([d.strip() for d in env.split(";") if d.strip()])
    if extra:
        dirs.extend(extra)
    # de-dup, keep order
    seen = set()
    out = []
    for d in dirs:
        if d not in seen:
            seen.add(d)
            out.append(d)
    return out


def _read_account_from_terminal(term_path: str) -> Optional[DiscoveredAccount]:
    """Initialise MT5 against one terminal path and read its active account.

    Returns a DiscoveredAccount or None (no account / terminal not running /
    lib missing). Always shuts MT5 down afterwards so we don't leak a binding.
    """
    try:
        import MetaTrader5 as mt5
    except ImportError:
        logger.debug("MetaTrader5 lib missing — cannot discover accounts")
        return None
    exe = os.path.join(term_path, "terminal64.exe")
    if not os.path.isfile(exe):
        return None
    try:
        if not mt5.initialize(path=exe, timeout=8000):
            # terminal not running / cannot start
            mt5.shutdown()
            return None
        info = mt5.account_info()
        if info is None:
            mt5.shutdown()
            return None
        acc = DiscoveredAccount(
            login=int(getattr(info, "login", 0) or 0),
            server=str(getattr(info, "server", "") or ""),
            name=str(getattr(info, "name", "") or ""),
            equity=float(getattr(info, "equity", 0.0) or 0.0),
            balance=float(getattr(info, "balance", 0.0) or 0.0),
            currency=str(getattr(info, "currency", "") or ""),
            terminal_path=term_path,
            source="mt5_terminal",
        )
        mt5.shutdown()
        if acc.login:
            return acc
        return None
    except Exception as exc:  # noqa: BLE001
        logger.debug("account discovery failed for %s: %s", term_path, exc)
        try:
            mt5.shutdown()
        except Exception:
            pass
        return None


def discover_accounts(extra_dirs: Optional[List[str]] = None) -> List[DiscoveredAccount]:
    """Scan installed MT5 terminals and return every currently-logged-in account.

    Fail-closed: returns an empty list if MT5 is unavailable or no terminal is
    authenticated. Never fabricates an account.
    """
    out: List[DiscoveredAccount] = []
    seen_logins: set[int] = set()
    for d in _candidate_terminal_dirs(extra_dirs):
        if not os.path.isdir(d):
            continue
        acc = _read_account_from_terminal(d)
        if acc and acc.login not in seen_logins:
            seen_logins.add(acc.login)
            out.append(acc)
            logger.info(
                "DISCOVERED MT5 account login=%s server=%s terminal=%s equity=%.2f",
                acc.login, acc.server, d, acc.equity,
            )
    if not out:
        logger.info("account_discovery: no logged-in MT5 terminal found")
    return out


def discover_active_account() -> Optional[DiscoveredAccount]:
    """Convenience: return the first discovered account, or None."""
    accounts = discover_accounts()
    return accounts[0] if accounts else None
