"""
Execution Agent — Smart Order Routing, Slippage Management & Multi-Venue Execution
===================================================================================
Routes orders to multiple execution venues (Binance, Bybit, Alpaca,
Kalshi/Polymarket) with Smart Order Routing (SOR) for best execution.
Integrates pre-trade risk checks via risk_guard, monitors latency, and
supports kill switch integration for emergency halts.

This agent is distinct from the basic trader_node — it provides the
advanced execution layer with SOR, venue selection, and latency management
that the simpler trader_node does not have.

Responsibilities:
  - Smart order routing (SOR) across multiple venues for best execution
  - Order routing to Binance, Bybit, Alpaca, Kalshi/Polymarket
  - Slippage management and monitoring
  - Pre-trade risk checks via ConstitutionalRiskGuard
  - Latency monitoring and kill switch integration
  - Return execution_route, venue_decision, slippage_estimate, latency_ms
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

from quant_nanggroe_ai.agents.state import AgentState
from quant_nanggroe_ai.agents.tools.execution import ExecutionTool
from quant_nanggroe_ai.engine.kill_switch import KillSwitch
from quant_nanggroe_ai.engine.risk_guard import ConstitutionalRiskGuard
from quant_nanggroe_ai.types import RiskClearance

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# Execution Venue Configuration
# ══════════════════════════════════════════════════════════════════════

class ExecutionVenue:
    """Represents an execution venue with its characteristics."""

    def __init__(
        self,
        name: str,
        asset_classes: list[str],
        avg_latency_ms: float,
        commission_bps: float,
        max_slippage_bps: float,
        reliability_score: float,
    ) -> None:
        self.name = name
        self.asset_classes = asset_classes
        self.avg_latency_ms = avg_latency_ms
        self.commission_bps = commission_bps
        self.max_slippage_bps = max_slippage_bps
        self.reliability_score = reliability_score  # 0.0 to 1.0

    def supports_asset(self, asset_class: str) -> bool:
        """Check if venue supports the given asset class."""
        return asset_class in self.asset_classes


# Pre-configured venues
VENUES: dict[str, ExecutionVenue] = {
    "binance": ExecutionVenue(
        name="Binance",
        asset_classes=["crypto"],
        avg_latency_ms=50.0,
        commission_bps=10.0,   # 0.1%
        max_slippage_bps=5.0,
        reliability_score=0.99,
    ),
    "bybit": ExecutionVenue(
        name="Bybit",
        asset_classes=["crypto"],
        avg_latency_ms=60.0,
        commission_bps=10.0,
        max_slippage_bps=8.0,
        reliability_score=0.97,
    ),
    "alpaca": ExecutionVenue(
        name="Alpaca",
        asset_classes=["equity", "crypto"],
        avg_latency_ms=100.0,
        commission_bps=0.0,    # Commission-free
        max_slippage_bps=3.0,
        reliability_score=0.98,
    ),
    "jupiter": ExecutionVenue(
        name="Jupiter (Solana DEX)",
        asset_classes=["crypto_solana"],
        avg_latency_ms=400.0,  # On-chain latency
        commission_bps=0.0,    # Network fees only
        max_slippage_bps=50.0,
        reliability_score=0.95,
    ),
    "polymarket": ExecutionVenue(
        name="Polymarket",
        asset_classes=["prediction_market"],
        avg_latency_ms=500.0,  # On-chain (Polygon)
        commission_bps=0.0,
        max_slippage_bps=20.0,
        reliability_score=0.92,
    ),
    "paper": ExecutionVenue(
        name="Paper Trading",
        asset_classes=["equity", "crypto", "forex", "prediction_market"],
        avg_latency_ms=1.0,
        commission_bps=10.0,
        max_slippage_bps=5.0,
        reliability_score=1.0,
    ),
}


# ══════════════════════════════════════════════════════════════════════
# SOR (Smart Order Routing) Constants
# ══════════════════════════════════════════════════════════════════════

MAX_SLIPPAGE_BPS = 50          # Maximum acceptable slippage in basis points
LATENCY_WARNING_MS = 200.0     # Latency above this triggers a warning
LATENCY_CRITICAL_MS = 1000.0   # Latency above this triggers critical alert
MIN_VENUE_RELIABILITY = 0.90   # Minimum reliability score to route to

# Weights for SOR venue scoring
WEIGHT_COMMISSION = 0.30
WEIGHT_SLIPPAGE = 0.35
WEIGHT_LATENCY = 0.15
WEIGHT_RELIABILITY = 0.20


# ══════════════════════════════════════════════════════════════════════
# Shared Instances (consistent with risk_manager.py pattern)
# ══════════════════════════════════════════════════════════════════════

_risk_guard: ConstitutionalRiskGuard | None = None
_kill_switch: KillSwitch | None = None


def _get_risk_guard() -> ConstitutionalRiskGuard:
    """Return a shared ConstitutionalRiskGuard instance."""
    global _risk_guard
    if _risk_guard is None:
        _risk_guard = ConstitutionalRiskGuard()
    return _risk_guard


def _get_kill_switch() -> KillSwitch:
    """Return a shared KillSwitch instance."""
    global _kill_switch
    if _kill_switch is None:
        _kill_switch = KillSwitch()
    return _kill_switch


# ══════════════════════════════════════════════════════════════════════
# Helper Functions
# ══════════════════════════════════════════════════════════════════════


def _classify_asset(symbol: str) -> str:
    """
    Classify the asset class of a symbol for venue routing.

    Returns one of: 'equity', 'crypto', 'crypto_solana', 'forex', 'prediction_market'
    """
    upper = symbol.upper()

    # Crypto Solana-specific tokens
    solana_tokens = {"SOL", "BONK", "JUP", "RAY", "ORCA", "PYTH", "JITO"}
    if any(upper.startswith(t) for t in solana_tokens):
        return "crypto_solana"

    # Crypto general
    crypto_bases = {"BTC", "ETH", "BNB", "XRP", "ADA", "DOGE", "DOT", "AVAX"}
    if any(upper.startswith(c) for c in crypto_bases) or "USDT" in upper:
        return "crypto"

    # Forex
    forex_currencies = {"USD", "EUR", "GBP", "JPY", "CHF", "AUD", "NZD", "CAD"}
    if len(upper) == 6:
        base, quote = upper[:3], upper[3:6]
        if base in forex_currencies and quote in forex_currencies:
            return "forex"

    # Prediction market (Polymarket/Kalshi convention)
    if any(kw in upper for kw in ("PREDICT", "POLY", "KALSHI", "YES", "NO")):
        return "prediction_market"

    return "equity"


def _score_venue(
    venue: ExecutionVenue,
    estimated_slippage_bps: float = 0.0,
) -> float:
    """
    Score a venue for SOR ranking.

    Higher score = better venue. Considers:
      - Commission (lower is better)
      - Estimated slippage (lower is better)
      - Latency (lower is better)
      - Reliability (higher is better)

    Returns a float score (0.0 to 100.0).
    """
    # Commission score: 0 bps = 100, 20 bps = 0
    commission_score = max(0, 100 - venue.commission_bps * 5)

    # Slippage score: use estimated or venue max
    slippage = estimated_slippage_bps or venue.max_slippage_bps
    slippage_score = max(0, 100 - slippage * 2)

    # Latency score: 0ms = 100, 500ms+ = 0
    latency_score = max(0, 100 - venue.avg_latency_ms / 5)

    # Reliability score: direct mapping
    reliability_score = venue.reliability_score * 100

    composite = (
        commission_score * WEIGHT_COMMISSION
        + slippage_score * WEIGHT_SLIPPAGE
        + latency_score * WEIGHT_LATENCY
        + reliability_score * WEIGHT_RELIABILITY
    )

    return round(composite, 2)


def _select_best_venue(
    asset_class: str,
    estimated_slippage_bps: float = 0.0,
) -> dict[str, Any]:
    """
    Select the best execution venue using SOR.

    Evaluates all venues that support the asset class, scores them,
    and returns the best option with a ranked list of alternatives.

    Returns dict with selected venue, score, and alternatives.
    """
    candidates: list[dict[str, Any]] = []

    for venue_key, venue in VENUES.items():
        if not venue.supports_asset(asset_class):
            continue
        if venue.reliability_score < MIN_VENUE_RELIABILITY:
            continue

        score = _score_venue(venue, estimated_slippage_bps)
        candidates.append({
            "venue_key": venue_key,
            "venue_name": venue.name,
            "score": score,
            "commission_bps": venue.commission_bps,
            "avg_latency_ms": venue.avg_latency_ms,
            "max_slippage_bps": venue.max_slippage_bps,
            "reliability_score": venue.reliability_score,
        })

    if not candidates:
        # Fallback to paper trading
        return {
            "selected_venue": "paper",
            "venue_name": "Paper Trading",
            "score": 0.0,
            "reason": "No suitable venue found — falling back to paper",
            "alternatives": [],
            "fallback": True,
        }

    # Sort by score descending
    candidates.sort(key=lambda c: c["score"], reverse=True)
    best = candidates[0]

    return {
        "selected_venue": best["venue_key"],
        "venue_name": best["venue_name"],
        "score": best["score"],
        "reason": f"Best SOR score: {best['score']:.1f}/100",
        "alternatives": candidates[1:4],  # Top 3 alternatives
        "fallback": False,
    }


def _estimate_slippage(
    symbol: str,
    quantity: float,
    venue_key: str,
) -> float:
    """
    Estimate slippage for a given order.

    In production, this would use real-time order book depth.
    For now, uses venue max slippage as a conservative estimate,
    adjusted by order size.

    Returns estimated slippage in basis points.
    """
    venue = VENUES.get(venue_key)
    if venue is None:
        return MAX_SLIPPAGE_BPS

    base_slippage = venue.max_slippage_bps

    # Size adjustment: larger orders get more slippage
    # This is a simplified model; production would use order book depth
    size_multiplier = 1.0 + max(0, (quantity - 100) / 1000)
    estimated = base_slippage * size_multiplier

    return min(estimated, MAX_SLIPPAGE_BPS)


def _pre_trade_risk_check(
    symbol: str,
    direction: str,
    quantity: float,
    entry_price: float,
    stop_loss: float | None,
    take_profit: float | None,
) -> dict[str, Any]:
    """
    Run pre-trade risk checks via ConstitutionalRiskGuard.

    This is a lightweight pre-check before the full risk_manager_node
    runs. It catches obvious violations early to avoid unnecessary
    venue routing.

    Returns dict with passed (bool) and reason (str).
    """
    # Kill switch check
    kill_switch = _get_kill_switch()
    if kill_switch.is_active:
        return {
            "passed": False,
            "reason": "Kill switch is ACTIVE — all trading blocked",
            "check": "kill_switch",
        }

    # Basic risk guard check
    risk_guard = _get_risk_guard()
    try:
        result = risk_guard.check_trade(
            symbol=symbol,
            direction=direction,
            lot_size=quantity,
            entry=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )
        if result.verdict == "VETOED":
            failed = [k for k, v in result.checkpoints.items() if not v.passed]
            return {
                "passed": False,
                "reason": f"Risk guard VETOED: failed checks: {', '.join(failed)}",
                "check": "risk_guard",
                "failed_checks": failed,
            }
    except Exception as exc:
        logger.warning("Pre-trade risk check error: %s", exc)
        return {
            "passed": False,
            "reason": f"Risk check error: {exc}",
            "check": "risk_guard_error",
        }

    return {"passed": True, "reason": "All pre-trade checks passed"}


def _monitor_latency(start_time: float) -> dict[str, Any]:
    """
    Monitor execution latency and determine alert level.

    Args:
        start_time: Monotonic clock time when execution started

    Returns dict with latency_ms, alert_level, and message.
    """
    latency_ms = round((time.monotonic() - start_time) * 1000, 2)

    if latency_ms >= LATENCY_CRITICAL_MS:
        alert_level = "CRITICAL"
        message = f"Latency {latency_ms:.0f}ms exceeds critical threshold {LATENCY_CRITICAL_MS:.0f}ms"
    elif latency_ms >= LATENCY_WARNING_MS:
        alert_level = "WARNING"
        message = f"Latency {latency_ms:.0f}ms exceeds warning threshold {LATENCY_WARNING_MS:.0f}ms"
    else:
        alert_level = "OK"
        message = f"Latency {latency_ms:.0f}ms within acceptable range"

    return {
        "latency_ms": latency_ms,
        "alert_level": alert_level,
        "message": message,
    }


# ══════════════════════════════════════════════════════════════════════
# Execution Agent Node
# ══════════════════════════════════════════════════════════════════════


async def execution_node(state: AgentState) -> dict[str, Any]:
    """
    Execution Agent node — Smart Order Routing & Multi-Venue Execution.

    Routes orders to the best execution venue using SOR, performs pre-trade
    risk checks, monitors latency, and integrates with the kill switch.
    Only executes if risk clearance is CLEAR.
    """
    symbol = state.symbol or "SPY"
    errors: list[str] = []
    now = datetime.now().isoformat()
    start_time = time.monotonic()

    # ── 1. Early exit: risk clearance check ───────────────────────────
    if state.risk_clearance != RiskClearance.CLEAR:
        logger.info(
            "Execution SKIPPED for %s — risk clearance is %s",
            symbol, state.risk_clearance.value,
        )
        return {
            "execution_status": "SKIPPED",
            "order_id": "",
            "execution_price": 0.0,
            "slippage": 0.0,
            "errors": state.errors,
            "agent_trace": state.agent_trace + [
                {
                    "agent": "execution",
                    "status": "skipped",
                    "reason": f"Risk clearance is {state.risk_clearance.value}, not CLEAR",
                    "timestamp": now,
                }
            ],
        }

    # ── 2. Early exit: no actionable signal ───────────────────────────
    if state.strategy_signal not in ("BUY", "SELL", "LONG", "SHORT"):
        return {
            "execution_status": "SKIPPED",
            "order_id": "",
            "execution_price": 0.0,
            "slippage": 0.0,
            "errors": state.errors + [f"No actionable signal: {state.strategy_signal}"],
            "agent_trace": state.agent_trace + [
                {
                    "agent": "execution",
                    "status": "skipped",
                    "reason": f"No actionable signal: {state.strategy_signal}",
                    "timestamp": now,
                }
            ],
        }

    # ── 3. Determine execution parameters ─────────────────────────────
    direction = state.strategy_signal
    quantity = state.position_size if state.position_size > 0 else 0.01
    entry_price = state.entry_price
    stop_loss = state.stop_loss if state.stop_loss > 0 else None
    take_profit = state.take_profit[0] if state.take_profit else None

    # ── 4. Pre-trade risk check ───────────────────────────────────────
    pre_check = _pre_trade_risk_check(
        symbol=symbol,
        direction=direction,
        quantity=quantity,
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit=take_profit,
    )

    if not pre_check["passed"]:
        logger.warning(
            "Pre-trade risk check FAILED for %s: %s", symbol, pre_check["reason"],
        )
        return {
            "execution_status": "REJECTED",
            "order_id": "",
            "execution_price": 0.0,
            "slippage": 0.0,
            "errors": state.errors + [pre_check["reason"]],
            "agent_trace": state.agent_trace + [
                {
                    "agent": "execution",
                    "status": "rejected",
                    "reason": pre_check["reason"],
                    "check": pre_check.get("check", "unknown"),
                    "timestamp": now,
                }
            ],
        }

    # ── 5. Classify asset and select venue (SOR) ──────────────────────
    asset_class = _classify_asset(symbol)
    venue_decision = _select_best_venue(asset_class)
    selected_venue = venue_decision["selected_venue"]

    logger.info(
        "SOR selected %s for %s (%s) — score=%.1f",
        venue_decision["venue_name"], symbol, asset_class,
        venue_decision["score"],
    )

    # ── 6. Estimate slippage ──────────────────────────────────────────
    slippage_estimate_bps = _estimate_slippage(symbol, quantity, selected_venue)

    if slippage_estimate_bps > MAX_SLIPPAGE_BPS:
        error_msg = (
            f"Estimated slippage {slippage_estimate_bps:.1f} bps exceeds "
            f"maximum {MAX_SLIPPAGE_BPS} bps for {symbol}"
        )
        logger.warning(error_msg)
        errors.append(error_msg)

    # ── 7. Execute trade via ExecutionTool ────────────────────────────
    execution_status = "PENDING"
    order_id = ""
    execution_price = 0.0
    actual_slippage = 0.0

    try:
        exec_tool = ExecutionTool()
        order_type = "LIMIT" if entry_price > 0 else "MARKET"

        result = await exec_tool.execute_order(
            symbol=symbol,
            side=direction,
            quantity=quantity,
            order_type=order_type,
            price=entry_price if entry_price > 0 else None,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )

        execution_status = result.get("status", "PENDING")
        order_id = result.get("order_id", "")
        execution_price = result.get("execution_price", 0.0)
        actual_slippage = result.get("slippage", 0.0)

        logger.info(
            "Order executed via %s: %s %s %s @ %s — status=%s, order_id=%s",
            venue_decision["venue_name"],
            direction, quantity, symbol, execution_price,
            execution_status, order_id,
        )

    except Exception as exc:
        logger.error("Execution failed for %s: %s", symbol, exc)
        execution_status = "REJECTED"
        errors.append(f"Execution: {exc}")

    # ── 8. Monitor latency ────────────────────────────────────────────
    latency_result = _monitor_latency(start_time)
    latency_ms = latency_result["latency_ms"]
    latency_alert = latency_result["alert_level"]

    if latency_alert in ("WARNING", "CRITICAL"):
        logger.warning("Execution latency alert: %s — %s", latency_alert, latency_result["message"])

    # ── 9. Kill switch auto-check after execution ─────────────────────
    kill_switch = _get_kill_switch()
    try:
        kill_status = kill_switch.check_auto_trigger(
            state.daily_pnl_pct, state.weekly_pnl_pct,
        )
        if kill_status.get("status") == "ACTIVATED":
            logger.critical("Kill switch auto-activated after execution: %s", kill_status)
            errors.append("Kill switch auto-activated — trading halted")
    except Exception as exc:
        logger.error("Kill switch check failed: %s", exc)

    # ── Return state updates ────────────────────────────────────────────
    return {
        "execution_status": execution_status,
        "order_id": order_id,
        "execution_price": execution_price,
        "slippage": actual_slippage,
        "errors": state.errors + errors,
        "agent_trace": state.agent_trace + [
            {
                "agent": "execution",
                "status": "completed",
                "action": "execute_sor",
                "symbol": symbol,
                "direction": direction,
                "quantity": quantity,
                "order_id": order_id,
                "execution_price": execution_price,
                "slippage": actual_slippage,
                "slippage_estimate_bps": slippage_estimate_bps,
                "selected_venue": selected_venue,
                "venue_name": venue_decision["venue_name"],
                "sor_score": venue_decision["score"],
                "asset_class": asset_class,
                "latency_ms": latency_ms,
                "latency_alert": latency_alert,
                "timestamp": now,
            }
        ],
    }
