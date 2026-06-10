"""
Portfolio Validator for Quant Nanggroe AI Trading Framework v2.

Implements portfolio-level validation checks that go beyond the 9-checkpoint
risk gate. Specifically validates:

1. **Concentration limits** — No single position exceeds MAX_POSITION_SIZE_PCT
2. **Correlation checks** — No more than MAX_CORRELATED_POSITIONS in one group
3. **Kelly Criterion** — Position sizes don't exceed half-Kelly limits

This node runs after position sizing and before portfolio optimization,
acting as an additional gate on portfolio-level risk.
"""

from __future__ import annotations

import logging
import math
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from quant_nanggroe.agents.state import (
    AgentState,
    MAX_CORRELATED_POSITIONS,
    MAX_POSITION_SIZE_PCT,
    MAX_RISK_PER_TRADE,
    PortfolioValidation,
)


logger = logging.getLogger(__name__)


# =============================================================================
# Correlation groups (shared with risk/tools.py, duplicated here for
# node independence to avoid circular imports)
# =============================================================================

CORRELATION_GROUPS: List[set] = [
    {"EURUSD", "GBPUSD", "AUDUSD", "NZDUSD"},
    {"USDJPY", "USDCHF", "USDCAD"},
    {"XAUUSD", "XAGUSD"},
    {"BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"},
    {"SPY", "IVV", "VOO"},
    {"QQQ", "ONEQ", "TQQQ"},
    # Sector correlations
    {"AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA"},  # Big tech
    {"JPM", "BAC", "WFC", "C", "GS"},  # Banks
    {"XOM", "CVX", "COP", "SLB"},  # Energy
]

# Maximum total risk budget (sum of all position risks)
MAX_TOTAL_RISK_BUDGET: float = 0.05  # 5% total portfolio risk

# Maximum sector/asset-class concentration
MAX_SECTOR_CONCENTRATION_PCT: float = 0.30  # 30% max in one correlation group


def _are_correlated(symbol_a: str, symbol_b: str) -> bool:
    """Check if two symbols are in the same correlation group."""
    a_upper = symbol_a.upper()
    b_upper = symbol_b.upper()
    for group in CORRELATION_GROUPS:
        if a_upper in group and b_upper in group:
            return True
    return False


def _get_correlation_group(symbol: str) -> Optional[set]:
    """Get the correlation group for a symbol, if any."""
    symbol_upper = symbol.upper()
    for group in CORRELATION_GROUPS:
        if symbol_upper in group:
            return group
    return None


# =============================================================================
# Concentration check
# =============================================================================

def check_concentration(
    signals: List[Dict[str, Any]],
    portfolio_state: Dict[str, Any],
    portfolio_value: float,
) -> Dict[str, Any]:
    """
    Validate that no single position exceeds concentration limits.

    Checks both individual position size and proposed new positions.

    Args:
        signals: Proposed trading signals with position sizing
        portfolio_state: Current portfolio state with existing positions
        portfolio_value: Total portfolio value

    Returns:
        Concentration check result dict
    """
    max_single_pct = MAX_POSITION_SIZE_PCT * 100  # Convert to percentage
    violations: List[str] = []
    per_symbol: Dict[str, Any] = {}

    # Check existing positions
    existing_positions = portfolio_state.get("positions", {})
    if isinstance(existing_positions, dict):
        for symbol, pos_data in existing_positions.items():
            if isinstance(pos_data, dict):
                pos_value = pos_data.get("market_value", pos_data.get("unrealized_pnl", 0))
                if portfolio_value > 0 and pos_value > 0:
                    pct = (pos_value / portfolio_value) * 100
                    per_symbol[symbol] = {
                        "current_pct": round(pct, 2),
                        "limit_pct": max_single_pct,
                        "within_limit": pct <= max_single_pct,
                    }
                    if pct > max_single_pct:
                        violations.append(
                            f"Existing position {symbol} at {pct:.1f}% "
                            f"exceeds limit of {max_single_pct:.0f}%"
                        )

    # Check proposed new positions from signals
    for signal in signals:
        if not isinstance(signal, dict):
            continue
        symbol = signal.get("symbol", "")
        pos_pct = signal.get("position_size_pct", 0)
        if pos_pct > max_single_pct:
            violations.append(
                f"Proposed position {symbol} at {pos_pct:.1f}% "
                f"exceeds limit of {max_single_pct:.0f}%"
            )
            per_symbol[symbol] = {
                "proposed_pct": round(pos_pct, 2),
                "limit_pct": max_single_pct,
                "within_limit": False,
            }
        elif symbol:
            per_symbol[symbol] = {
                "proposed_pct": round(pos_pct, 2),
                "limit_pct": max_single_pct,
                "within_limit": True,
            }

    # Calculate max single exposure
    all_pcts = [
        info.get("current_pct", info.get("proposed_pct", 0))
        for info in per_symbol.values()
    ]
    max_exposure = max(all_pcts) if all_pcts else 0.0

    return {
        "passed": len(violations) == 0,
        "max_single_position_pct": max_single_pct,
        "max_exposure_pct": round(max_exposure, 2),
        "violations": violations,
        "per_symbol": per_symbol,
    }


# =============================================================================
# Correlation check
# =============================================================================

def check_correlation(
    signals: List[Dict[str, Any]],
    portfolio_state: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Validate portfolio correlation risk.

    Checks that no correlation group has more than MAX_CORRELATED_POSITIONS
    and that sector concentration stays within limits.

    Args:
        signals: Proposed trading signals
        portfolio_state: Current portfolio state

    Returns:
        Correlation check result dict
    """
    # Collect all symbols (existing + proposed)
    existing_symbols: List[str] = []
    positions = portfolio_state.get("positions", {})
    if isinstance(positions, dict):
        existing_symbols = list(positions.keys())

    proposed_symbols: List[str] = []
    for signal in signals:
        if isinstance(signal, dict) and signal.get("action") in ("BUY", "SELL"):
            proposed_symbols.append(signal.get("symbol", ""))

    all_symbols = list(set(existing_symbols + proposed_symbols))

    # Analyze each correlation group
    group_analysis: Dict[str, Any] = {}
    total_violations: List[str] = []
    max_group_count = 0

    for group in CORRELATION_GROUPS:
        group_key = "/".join(sorted(group)[:3]) + ("..." if len(group) > 3 else "")
        symbols_in_group = [s for s in all_symbols if s.upper() in group]

        count = len(symbols_in_group)
        max_group_count = max(max_group_count, count)

        group_analysis[group_key] = {
            "symbols": symbols_in_group,
            "count": count,
            "limit": MAX_CORRELATED_POSITIONS,
            "within_limit": count < MAX_CORRELATED_POSITIONS,
        }

        if count >= MAX_CORRELATED_POSITIONS:
            total_violations.append(
                f"Correlation group {group_key} has {count} positions "
                f"(limit: {MAX_CORRELATED_POSITIONS})"
            )

    # Sector concentration check
    sector_concentration_violations: List[str] = []
    for group in CORRELATION_GROUPS:
        group_symbols = [s for s in all_symbols if s.upper() in group]
        if len(group_symbols) >= 2:
            # Approximate: if multiple positions in same group,
            # they could represent >30% concentration
            sector_concentration_violations.append(
                f"Group {group_key} has {len(group_symbols)} correlated positions "
                f"— verify total exposure < {MAX_SECTOR_CONCENTRATION_PCT * 100:.0f}%"
            )

    return {
        "passed": len(total_violations) == 0,
        "max_correlated_positions": MAX_CORRELATED_POSITIONS,
        "max_group_count": max_group_count,
        "violations": total_violations,
        "sector_warnings": sector_concentration_violations,
        "group_analysis": group_analysis,
    }


# =============================================================================
# Kelly Criterion check
# =============================================================================

def check_kelly(
    signals: List[Dict[str, Any]],
    portfolio_state: Dict[str, Any],
    portfolio_value: float,
) -> Dict[str, Any]:
    """
    Validate position sizes against Kelly Criterion limits.

    Uses half-Kelly as the safe upper bound. If win rate / avg win/loss
    data is not available, uses a conservative default.

    Args:
        signals: Proposed trading signals with position sizing
        portfolio_state: Current portfolio state
        portfolio_value: Total portfolio value

    Returns:
        Kelly check result dict
    """
    # Default historical stats if not available in metadata
    default_win_rate = 0.50
    default_avg_win = 0.02
    default_avg_loss = 0.01

    metadata = portfolio_state.get("metadata", {})
    win_rate = metadata.get("win_rate", default_win_rate)
    avg_win = metadata.get("avg_win", default_avg_win)
    avg_loss = metadata.get("avg_loss", default_avg_loss)

    # Compute Kelly fraction: f = (p * b - q) / b
    if avg_loss <= 0:
        kelly_fraction = 0.0
    else:
        b = avg_win / avg_loss
        q = 1 - win_rate
        kelly_fraction = (win_rate * b - q) / b

    # Half-Kelly for safety
    half_kelly = max(0, kelly_fraction / 2)

    # Cap at constitutional max
    capped_kelly = min(half_kelly, MAX_POSITION_SIZE_PCT)

    violations: List[str] = []
    per_symbol: Dict[str, Any] = {}

    for signal in signals:
        if not isinstance(signal, dict):
            continue
        symbol = signal.get("symbol", "")
        pos_pct = signal.get("position_size_pct", 0) / 100  # Convert to fraction

        if pos_pct > capped_kelly:
            violations.append(
                f"Position {symbol} at {pos_pct*100:.1f}% exceeds "
                f"half-Kelly limit of {capped_kelly*100:.1f}%"
            )
            per_symbol[symbol] = {
                "proposed_pct": round(pos_pct * 100, 2),
                "kelly_limit_pct": round(capped_kelly * 100, 2),
                "within_kelly": False,
            }
        elif symbol:
            per_symbol[symbol] = {
                "proposed_pct": round(pos_pct * 100, 2),
                "kelly_limit_pct": round(capped_kelly * 100, 2),
                "within_kelly": True,
            }

    return {
        "passed": len(violations) == 0,
        "raw_kelly_fraction": round(kelly_fraction, 4),
        "half_kelly_fraction": round(half_kelly, 4),
        "capped_kelly_pct": round(capped_kelly * 100, 2),
        "win_rate_used": win_rate,
        "avg_win_loss_ratio": round(avg_win / avg_loss, 2) if avg_loss > 0 else 0,
        "violations": violations,
        "per_symbol": per_symbol,
    }


# =============================================================================
# LangGraph node
# =============================================================================

class PortfolioValidator:
    """
    Portfolio validation node for the v2 LangGraph trading graph.

    Runs concentration, correlation, and Kelly Criterion checks on
    proposed positions. Produces a PortfolioValidation result that
    downstream nodes can use to gate execution.
    """

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """
        Execute portfolio validation.

        Args:
            state: Current agent state

        Returns:
            State updates with portfolio_validation result
        """
        logger.info("=== Portfolio Validation Phase ===")

        signals = state.get("signals", [])
        portfolio_state = state.get("portfolio_state", {})
        portfolio_value = (
            portfolio_state.get("total_value", 100000.0)
            if isinstance(portfolio_state, dict)
            else 100000.0
        )

        # Run all three checks
        concentration = check_concentration(signals, portfolio_state, portfolio_value)
        correlation = check_correlation(signals, portfolio_state)
        kelly = check_kelly(signals, portfolio_state, portfolio_value)

        # Aggregate results
        all_passed = (
            concentration.get("passed", True)
            and correlation.get("passed", True)
            and kelly.get("passed", True)
        )

        # Collect all errors (blocking) and warnings
        errors: List[str] = []
        errors.extend(concentration.get("violations", []))
        errors.extend(correlation.get("violations", []))
        errors.extend(kelly.get("violations", []))

        warnings: List[str] = []
        warnings.extend(correlation.get("sector_warnings", []))

        # Compute total risk budget used
        total_risk = 0.0
        for signal in signals:
            if isinstance(signal, dict):
                pos_pct = signal.get("position_size_pct", 0) / 100
                # Approximate: position_size * risk_fraction
                total_risk += pos_pct * MAX_RISK_PER_TRADE / MAX_POSITION_SIZE_PCT

        # Build validation result
        validation = PortfolioValidation(
            is_valid=all_passed,
            concentration_check=concentration,
            correlation_check=correlation,
            kelly_check=kelly,
            total_risk_budget_used=round(total_risk, 4),
            max_single_exposure_pct=concentration.get("max_exposure_pct", 0.0),
            warnings=warnings,
            errors=errors,
        )

        if all_passed:
            logger.info("Portfolio validation PASSED — all checks clear")
        else:
            logger.warning(
                f"Portfolio validation FAILED — {len(errors)} error(s), "
                f"{len(warnings)} warning(s)"
            )

        return {
            "portfolio_validation": validation.model_dump(),
            "sender": "portfolio_validator",
        }


def validate_portfolio(state: AgentState) -> Dict[str, Any]:
    """
    Functional interface for the portfolio validation node.

    Args:
        state: Current agent state

    Returns:
        State updates with portfolio validation results
    """
    validator = PortfolioValidator()
    return validator(state)
