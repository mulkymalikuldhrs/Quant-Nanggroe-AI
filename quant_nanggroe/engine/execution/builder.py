"""Single source of truth for building a wired ExecutionManager.

ponytail: every entrypoint (agents/execution/tools.py, api/routes/trading.py,
engine/autonomous/pipeline.py, agents/trader/tools.py) was building its own
ExecutionManager with a hardcoded PaperBroker. That's why wiring was "broken into
pieces" — no two paths agreed on the broker. Now they all call build_execution_manager().

Fail-closed: allow_live defaults False -> paper only. Live MT5 requires
QNA_LIVE_TRADING=1 AND a running MT5 terminal. Never silent-trading.

v6.5.0: When MT5 is live and connected, PaperBroker is NOT added — all trading
operations go exclusively through MT5. Paper is only used when MT5 is unavailable.
"""
from __future__ import annotations

import logging
import os
import threading
from typing import Optional

logger = logging.getLogger(__name__)

_CONFIG_PATH = str(
    __import__("pathlib").Path(__file__).resolve().parents[3] / "config" / "mt5_accounts.yaml"
)


_em_singleton = None
_em_lock = threading.Lock()
_connection_tasks: list = []  # Track async broker connection tasks for monitoring

# D-audit (2026-08-04): record the LAST build outcome so /health can honestly
# report execution-backend availability instead of lying "healthy" when MT5 is
# unconfigured (the RuntimeError is caught at boot -> system boots green but
# cannot trade). Read via get_execution_backend_status().
_execution_backend_status: str = "unknown"  # unknown|mt5|unavailable


def get_execution_backend_status() -> str:
    """Honest execution-backend status for health endpoints."""
    return _execution_backend_status


def build_execution_manager(allow_live: Optional[bool] = None) -> "object":
    global _em_singleton, _execution_backend_status
    if _em_singleton is not None:
        return _em_singleton
    with _em_lock:
        if _em_singleton is not None:
            return _em_singleton
        from quant_nanggroe.engine.execution.manager import ExecutionManager
        from quant_nanggroe.engine.risk.kill_switch import KillSwitch, configure_kill_switch_file
        from quant_nanggroe.engine.risk.manager import RiskManager

        em = ExecutionManager()
        # P0 fix: create risk manager + kill switch BEFORE live wiring so the
        # broker handle can attach to a real RiskManager instance (not None).
        configure_kill_switch_file()
        em.set_kill_switch(KillSwitch())
        em.set_risk_manager(RiskManager())

        if allow_live is None:
            allow_live = os.environ.get("QNA_LIVE_TRADING", "0") == "1"

        mt5_connected = False
        if allow_live:
            try:
                import re
                import yaml
                from quant_nanggroe.connectors.mt5_broker import MT5Broker
                from quant_nanggroe.engine.execution.brokers.mt5_adapter import MT5ExecutionBroker
                from quant_nanggroe.engine.execution.account_discovery import discover_accounts

                # ── ACCOUNT AUTO-DETECT FIRST (user mandate 2026-08-04) ──────
                # The terminal may be logged into a DIFFERENT account than the
                # config (root cause of "0 trades = wrong account"). Discover
                # every currently-authenticated MT5 account up front, so we can
                # trade the REAL account even when config/yaml env vars are
                # absent. This is the primary source of truth for "which account
                # is live".
                discovered = discover_accounts()
                if discovered:
                    logger.info("ACCOUNT AUTO-DETECT: %d terminal(s) logged in: %s",
                                len(discovered),
                                [(a.login, a.server) for a in discovered])
                    try:
                        from quant_nanggroe.engine.execution.account_ledger import record_account
                        for _d in discovered:
                            record_account(login=_d.login, server=_d.server, name=_d.name)
                    except Exception as _ledger_err:
                        logger.debug("account_ledger record failed: %s", _ledger_err)
                else:
                    logger.warning("ACCOUNT AUTO-DETECT: no logged-in MT5 terminal found")

                # Config accounts (yaml) are secondary — they only contribute
                # if their env vars resolve. A missing/unresolved yaml does NOT
                # block live trading when a real terminal account was detected.
                accounts: list = []
                with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                    raw = f.read()
                unresolved = sorted({
                    v for v in re.findall(r"\$\{([A-Z0-9_]+)\}", raw)
                    if v not in os.environ
                })
                if unresolved:
                    logger.warning(
                        "MT5 yaml env vars not set (%s) — using auto-detected "
                        "terminal account(s) only.", unresolved,
                    )
                else:
                    data = yaml.safe_load(os.path.expandvars(raw)) or {}
                    accounts = data.get("accounts") or []

                # When a live terminal is detected, ONLY its account is wired
                # (config yaml skipped). Otherwise fall back to config yaml.
                wired = 0
                _wired_logins = set()

                def _wire_account(login: int, password: str, server: str,
                                  name: str, paper: bool, terminal_path: str = "") -> None:
                    nonlocal wired, mt5_connected
                    if not login or login in _wired_logins:
                        return
                    mt5 = MT5Broker(
                        login=int(login),
                        password=str(password or ""),
                        server=str(server or ""),
                    )
                    if mt5.connect():
                        is_live = not paper
                        em.add_broker(MT5ExecutionBroker(mt5), primary=is_live)
                        em.set_broker_handle(mt5)
                        mt5_connected = True
                        _wired_logins.add(login)
                        wired += 1
                        logger.info("LIVE MT5 wired: %s (primary=%s) login=%s server=%s",
                                    name, is_live, login, server)
                    else:
                        logger.warning("MT5 connect failed for %s (login=%s) — skipped", name, login)

                # USER MANDATE 2026-08-20: trade whatever account is already
                # logged into the MT5 terminal — the discovered (live) account is
                # the SINGLE SOURCE OF TRUTH. Config yaml accounts are SKIPPED
                # when a real terminal is detected, so QNA never attempts a
                # credential login with a stale/wrong server (root cause of
                # "wrong account" trades — e.g. ValetaxIntl_Live-2 vs the real
                # ValetaxIntl-Live2, or bogus Exness #999).
                if discovered:
                    logger.info(
                        "ACCOUNT AUTO-DETECT active — trading the live terminal account(s) ONLY; "
                        "config yaml accounts SKIPPED: %s",
                        [(d.login, d.server) for d in discovered],
                    )
                    for d in discovered:
                        _wire_account(
                            login=d.login,
                            password="",  # terminal already holds credentials
                            server=d.server,
                            name=f"discovered-{d.login}",
                            paper=False,
                            terminal_path=d.terminal_path,
                        )
                else:
                    # No live terminal detected — legacy fallback to config yaml.
                    logger.warning(
                        "No live MT5 terminal detected — falling back to config yaml accounts"
                    )
                    for acc in accounts:
                        login = acc.get("login")
                        if not login:
                            continue
                        _wire_account(
                            login=int(login),
                            password=str(acc.get("password", "")),
                            server=str(acc.get("server", "")),
                            name=str(acc.get("name", f"acc-{login}")),
                            paper=bool(acc.get("paper", False)),
                        )

                if wired == 0:
                    logger.warning("allow_live=True but no MT5 connected — paper only, no market trades")
            except Exception as exc:
                logger.error("build_execution_manager live wiring failed: %s (falling back to paper)", exc)

        # REAL-ONLY: NO paper fallback. If MT5 is not connected, raise — do NOT
        # add a simulated broker. Fail-closed: no market = no trades.
        if not mt5_connected:
            _execution_backend_status = "unavailable"
            raise RuntimeError(
                "REAL-ONLY mode: no MT5 account connected. "
                "PaperBroker removed — cannot trade on simulation."
            )
        else:
            _execution_backend_status = "mt5"
            logger.info("MT5 live — PaperBroker DISABLED (all trades via MT5)")

        # Connect all brokers — async with tracking
        import asyncio

        for b in em.get_brokers().values():
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    task = asyncio.ensure_future(b.connect())
                    _connection_tasks.append(task)
                    task.add_done_callback(lambda t: logger.info(
                        "Broker %s async connect completed: success=%s",
                        getattr(b, "name", "?"),
                        not t.cancelled() and not t.exception(),
                    ))
                else:
                    loop.run_until_complete(b.connect())
            except Exception as exc:
                logger.warning("broker %s connect failed: %s", getattr(b, "name", "?"), exc)

        if _connection_tasks:
            logger.info("Broker async connection tasks: %d pending", len(_connection_tasks))

        _em_singleton = em
        return _em_singleton
