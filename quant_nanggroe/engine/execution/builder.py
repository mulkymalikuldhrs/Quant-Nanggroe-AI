"""Single source of truth for building a wired ExecutionManager.

ponytail: every entrypoint (agents/execution/tools.py, api/routes/trading.py,
engine/autonomous/pipeline.py, agents/trader/tools.py) was building its own
ExecutionManager with a hardcoded PaperBroker. That's why wiring was "broken into
pieces" — no two paths agreed on the broker. Now they all call build_execution_manager().

Fail-closed: allow_live defaults False -> paper only. Live MT5 requires
QNA_LIVE_TRADING=1 AND a running MT5 terminal. Never silent-trading.
"""
from __future__ import annotations

import logging
import os
import threading
from typing import Optional

logger = logging.getLogger(__name__)

_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "config", "mt5_accounts.yaml",
)


_em_singleton = None
_em_lock = threading.Lock()


def build_execution_manager(allow_live: Optional[bool] = None) -> "object":
    global _em_singleton
    if _em_singleton is not None:
        return _em_singleton
    with _em_lock:
        if _em_singleton is not None:
            return _em_singleton
        from quant_nanggroe.engine.execution.brokers.paper import PaperBroker
        from quant_nanggroe.engine.execution.manager import ExecutionManager
        from quant_nanggroe.engine.risk.kill_switch import KillSwitch, configure_kill_switch_file
        from quant_nanggroe.engine.risk.manager import RiskManager

        em = ExecutionManager()
        # P0 fix: create risk manager + kill switch BEFORE live wiring so the
        # broker handle can attach to a real RiskManager instance (not None).
        configure_kill_switch_file()
        em.set_kill_switch(KillSwitch())
        em.set_risk_manager(RiskManager())
        # paper always present as safe fallback (no market impact)
        paper = PaperBroker()
        em.add_broker(paper, primary=False)

        if allow_live is None:
            allow_live = os.environ.get("QNA_LIVE_TRADING", "0") == "1"

        if allow_live:
            try:
                import yaml
                with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(os.path.expandvars(f.read())) or {}
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
                        em._risk_manager.set_broker_handle(mt5)
                        wired += 1
                        logger.info("LIVE MT5 wired: %s (primary=%s)", acc.get("name"), is_live)
                    else:
                        logger.warning("MT5 connect failed for %s — skipped (paper remains)", acc.get("name"))
                if wired == 0:
                    logger.warning("allow_live=True but no MT5 connected — paper only, no market trades")
            except Exception as exc:
                logger.error("build_execution_manager live wiring failed: %s", exc)

        # Connect all brokers — PaperBroker connects synchronously, others async
        import asyncio
        for b in em._brokers.values():
            try:
                # PaperBroker: connect synchronously (no network)
                if type(b).__name__ == "PaperBroker":
                    b._connected = True
                    logger.info("PaperBroker: Connected (simulated)")
                else:
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.ensure_future(b.connect())
                        else:
                            loop.run_until_complete(b.connect())
                    except RuntimeError:
                        pass  # will connect lazily on first order
            except Exception as exc:
                logger.warning("broker %s connect failed: %s", getattr(b, "name", "?"), exc)

        _em_singleton = em
        return _em_singleton
