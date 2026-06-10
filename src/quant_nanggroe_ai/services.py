"""
Shared Services — Singleton instances for stateful engine components
=====================================================================
Provides thread-safe lazy singletons for engine components that must
maintain state across requests (PnL tracking, kill switch, regime history).

Usage in route handlers::

    from quant_nanggroe_ai.services import get_kill_switch, get_risk_guard

    ks = get_kill_switch(request.app)
    guard = get_risk_guard(request.app)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from fastapi import FastAPI

logger = structlog.get_logger(__name__)


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
    from quant_nanggroe_ai.engine.kill_switch import KillSwitch

    _ensure_state(app)
    if "kill_switch" not in app.state._services:
        logger.info("services_initializing", component="KillSwitch")
        app.state._services["kill_switch"] = KillSwitch()
    return app.state._services["kill_switch"]


# ══════════════════════════════════════════════════════════════════════
# ConstitutionalRiskGuard
# ══════════════════════════════════════════════════════════════════════

def get_risk_guard(app: FastAPI):
    """
    Return the shared ConstitutionalRiskGuard singleton from app.state.

    The shared instance accumulates PnL and trade-count state so that
    daily/weekly limits are enforced correctly across all requests.
    """
    from quant_nanggroe_ai.engine.risk_guard import ConstitutionalRiskGuard

    _ensure_state(app)
    if "risk_guard" not in app.state._services:
        logger.info("services_initializing", component="ConstitutionalRiskGuard")
        app.state._services["risk_guard"] = ConstitutionalRiskGuard()
    return app.state._services["risk_guard"]


# ══════════════════════════════════════════════════════════════════════
# MarketStateEngine
# ══════════════════════════════════════════════════════════════════════

def get_market_engine(app: FastAPI):
    """
    Return the shared MarketStateEngine singleton from app.state.

    The engine maintains regime history across requests, allowing the
    API to serve the most recently detected regime without recomputation.
    """
    from quant_nanggroe_ai.engine.market_state import MarketStateEngine

    _ensure_state(app)
    if "market_engine" not in app.state._services:
        logger.info("services_initializing", component="MarketStateEngine")
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
    from quant_nanggroe_ai.engine.decision import DecisionSynthesisEngine

    _ensure_state(app)
    if "decision_engine" not in app.state._services:
        logger.info("services_initializing", component="DecisionSynthesisEngine")
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
    from quant_nanggroe_ai.engine.strategy_lifecycle import StrategyLifecycleManager

    _ensure_state(app)
    if "strategy_lifecycle" not in app.state._services:
        logger.info("services_initializing", component="StrategyLifecycleManager")
        app.state._services["strategy_lifecycle"] = StrategyLifecycleManager()
    return app.state._services["strategy_lifecycle"]


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
    get_risk_guard(app)
    get_market_engine(app)
    get_decision_engine(app)
    get_strategy_lifecycle(app)
    logger.info("services_all_initialized")
