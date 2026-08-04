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
    __import__("pathlib").Path(__file__).resolve().parents[1] / "config" / "mt5_accounts.yaml"
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
                with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                    raw = f.read()
                # Fail-closed honesty: os.path.expandvars() leaves ${VAR} untouched
                # when the var is absent from the environment, which then crashes
                # later at int('${QNA_MT5_LOGIN}') with a cryptic ValueError.
                # Detect placeholders whose var is MISSING from os.environ BEFORE
                # parsing and report clearly. Vars present-but-empty are left to
                # the normal flow (empty login -> skipped account -> REAL-ONLY raise).
                unresolved = sorted({
                    v for v in re.findall(r"\$\{([A-Z0-9_]+)\}", raw)
                    if v not in os.environ
                })
                if unresolved:
                    _execution_backend_status = "unavailable"
                    raise RuntimeError(
                        "REAL-ONLY mode: MT5 env vars not set in environment: "
                        f"{unresolved}. Set them in .env / shell (e.g. QNA_MT5_LOGIN, "
                        "QNA_MT5_SERVER, QNA_MT5_PASSWORD) or configure "
                        "config/mt5_accounts.yaml with real values. "
                        "Cannot build live execution."
                    )
                data = yaml.safe_load(os.path.expandvars(raw)) or {}
                accounts = data.get("accounts") or []
                from quant_nanggroe.connectors.mt5_broker import MT5Broker
                from quant_nanggroe.engine.execution.brokers.mt5_adapter import MT5ExecutionBroker
                wired = 0
                for acc in accounts:
                    login = acc.get("login")
                    if not login:
                        continue
                    mt5 = MT5Broker(
                        login=int(login),
                        password=str(acc.get("password", "")),
                        server=str(acc.get("server", "")),
                    )
                    if mt5.connect():
                        # P0 fix: a live (non-paper) account becomes the PRIMARY
                        # broker so orders actually hit the market with SL/TP.
                        # Previously primary was gated on a non-existent
                        # `role:"primary"` key, so it defaulted to paper -> no trades.
                        is_live = not acc.get("paper", False)
                        em.add_broker(MT5ExecutionBroker(mt5), primary=is_live)
                        # P0 fix: give RiskManager the live MT5 handle so the
                        # daily/weekly-loss veto reads REALIZED PnL, not 0.0.
                        # Use the public set_broker_handle() method — NOT
                        # em._risk_manager (private attribute access).
                        em.set_broker_handle(mt5)
                        mt5_connected = True
                        wired += 1
                        logger.info("LIVE MT5 wired: %s (primary=%s)", acc.get("name"), is_live)
                    else:
                        logger.warning("MT5 connect failed for %s — skipped (paper remains)", acc.get("name"))
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
                if b.name == "paper":
                    # PaperBroker: connect synchronously (no network)
                    b._connected = True
                    logger.info("PaperBroker: Connected (simulated)")
                else:
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
