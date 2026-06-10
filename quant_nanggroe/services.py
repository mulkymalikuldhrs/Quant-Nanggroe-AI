"""Shared Services — Singleton instances for stateful engine components
=====================================================================
Provides thread-safe lazy singletons for engine components that must
maintain state across requests (PnL tracking, kill switch, regime history).

Usage in route handlers::

    from quant_nanggroe.services import get_kill_switch, get_risk_manager

    ks = get_kill_switch(request.app)
    rm = get_risk_manager(request.app)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# Helper
# ══════════════════════════════════════════════════════════════════════

def _ensure_state(app: FastAPI) -> None:
    """Ensure app.state has the _services dict initialized."""
    if not hasattr(app.state, "_services"):
        app.state._services = {}


# ══════════════════════════════════════════════════════════════════════
# KillSwitch
# ══════════════════════════════════════════════════════════════════════

def get_kill_switch(app: FastAPI):
    """
    Return the shared KillSwitch singleton from app.state.

    Creates and stores the instance on first access so that activation
    state persists across requests.
    """
    from quant_nanggroe.engine.risk.kill_switch import KillSwitch

    _ensure_state(app)
    if "kill_switch" not in app.state._services:
        logger.info("services_initializing", extra={"component": "KillSwitch"})
        app.state._services["kill_switch"] = KillSwitch()
    return app.state._services["kill_switch"]


# ══════════════════════════════════════════════════════════════════════
# RiskManager
# ══════════════════════════════════════════════════════════════════════

def get_risk_manager(app: FastAPI):
    """
    Return the shared RiskManager singleton from app.state.

    The shared instance accumulates PnL and trade-count state so that
    daily/weekly limits are enforced correctly across all requests.
    """
    from quant_nanggroe.engine.risk.manager import RiskManager

    _ensure_state(app)
    if "risk_manager" not in app.state._services:
        logger.info("services_initializing", extra={"component": "RiskManager"})
        app.state._services["risk_manager"] = RiskManager()
    return app.state._services["risk_manager"]


# ══════════════════════════════════════════════════════════════════════
# MarketStateEngine
# ══════════════════════════════════════════════════════════════════════

def get_market_engine(app: FastAPI):
    """
    Return the shared MarketStateEngine singleton from app.state.

    The engine maintains regime history across requests, allowing the
    API to serve the most recently detected regime without recomputation.
    """
    from quant_nanggroe.engine.market_state import MarketStateEngine

    _ensure_state(app)
    if "market_engine" not in app.state._services:
        logger.info("services_initializing", extra={"component": "MarketStateEngine"})
        app.state._services["market_engine"] = MarketStateEngine()
    return app.state._services["market_engine"]


# ══════════════════════════════════════════════════════════════════════
# DecisionSynthesisEngine
# ══════════════════════════════════════════════════════════════════════

def get_decision_engine(app: FastAPI):
    """
    Return the shared DecisionSynthesisEngine singleton from app.state.

    The engine caches the last decision for quick status queries.
    """
    from quant_nanggroe.engine.decision import DecisionSynthesisEngine

    _ensure_state(app)
    if "decision_engine" not in app.state._services:
        logger.info("services_initializing", extra={"component": "DecisionSynthesisEngine"})
        app.state._services["decision_engine"] = DecisionSynthesisEngine()
    return app.state._services["decision_engine"]


# ══════════════════════════════════════════════════════════════════════
# StrategyLifecycleManager
# ══════════════════════════════════════════════════════════════════════

def get_strategy_lifecycle(app: FastAPI):
    """
    Return the shared StrategyLifecycleManager singleton from app.state.

    Maintains the Darwinian strategy lifecycle across all requests.
    """
    from quant_nanggroe.engine.strategy_lifecycle import StrategyLifecycleManager

    _ensure_state(app)
    if "strategy_lifecycle" not in app.state._services:
        logger.info("services_initializing", extra={"component": "StrategyLifecycleManager"})
        app.state._services["strategy_lifecycle"] = StrategyLifecycleManager()
    return app.state._services["strategy_lifecycle"]


# ══════════════════════════════════════════════════════════════════════
# AutoSwitchEngine
# ══════════════════════════════════════════════════════════════════════

def get_autoswitch_engine(app: FastAPI):
    """
    Return the shared AutoSwitchEngine singleton from app.state.

    Tracks provider health for failover routing.
    """
    from quant_nanggroe.engine.autoswitch import AutoSwitchEngine

    _ensure_state(app)
    if "autoswitch_engine" not in app.state._services:
        logger.info("services_initializing", extra={"component": "AutoSwitchEngine"})
        app.state._services["autoswitch_engine"] = AutoSwitchEngine()
    return app.state._services["autoswitch_engine"]


# ══════════════════════════════════════════════════════════════════════
# AuditLogger
# ══════════════════════════════════════════════════════════════════════

def get_audit_logger(app: FastAPI):
    """
    Return the shared AuditLogger singleton from app.state.

    Maintains the audit trail across all requests.
    """
    from quant_nanggroe.engine.audit import AuditLogger

    _ensure_state(app)
    if "audit_logger" not in app.state._services:
        logger.info("services_initializing", extra={"component": "AuditLogger"})
        app.state._services["audit_logger"] = AuditLogger()
    return app.state._services["audit_logger"]


# ══════════════════════════════════════════════════════════════════════
# Convenience: initialise all singletons at once (called from lifespan)
# ══════════════════════════════════════════════════════════════════════

def init_all_services(app: FastAPI) -> None:
    """
    Eagerly initialise all shared singletons and attach them to app.state.

    Called during application startup so that any import errors surface
    immediately rather than on the first request.
    """
    get_kill_switch(app)
    get_risk_manager(app)
    get_market_engine(app)
    get_decision_engine(app)
    get_strategy_lifecycle(app)
    get_autoswitch_engine(app)
    get_audit_logger(app)
    logger.info("services_all_initialized")
