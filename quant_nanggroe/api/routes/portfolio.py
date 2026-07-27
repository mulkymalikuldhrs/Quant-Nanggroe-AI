"""Portfolio API routes."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import numpy as np
from fastapi import APIRouter, Request

from quant_nanggroe.api.schemas import (
    PortfolioRiskResponse,
    PortfolioSummaryResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_exchange_manager(http_request: Request):
    """Retrieve the singleton ExchangeManager from services."""
    from quant_nanggroe.services import get_exchange_manager
    return get_exchange_manager(http_request.app)


# ---------------------------------------------------------------------------
# Historical stress-test scenarios (percentage returns for a single day)
# ---------------------------------------------------------------------------
STRESS_SCENARIOS: dict[str, dict[str, float]] = {
    "2008_financial_crisis": {
        "description": "Lehman Brothers collapse (Sep 15, 2008)",
        "equity_shock": -0.047,   # S&P 500 single-day drop
        "vol_shock": 0.80,        # VIX spike
        "credit_spread_widen": 0.03,
        "liquidity_dry_up": 0.70,
    },
    "2020_covid_crash": {
        "description": "COVID-19 market crash (Mar 2020)",
        "equity_shock": -0.12,    # S&P 500 multi-day crash
        "vol_shock": 0.85,
        "credit_spread_widen": 0.04,
        "liquidity_dry_up": 0.60,
    },
    "flash_crash_2010": {
        "description": "Flash Crash (May 6, 2010)",
        "equity_shock": -0.09,    # Intraday drop
        "vol_shock": 0.65,
        "credit_spread_widen": 0.01,
        "liquidity_dry_up": 0.90,
    },
    "taper_tantrum_2013": {
        "description": "Taper Tantrum (May-Jun 2013)",
        "equity_shock": -0.06,
        "vol_shock": 0.45,
        "credit_spread_widen": 0.05,
        "liquidity_dry_up": 0.40,
    },
    "rate_shock_100bps": {
        "description": "Sudden 100bps rate hike",
        "equity_shock": -0.05,
        "vol_shock": 0.35,
        "credit_spread_widen": 0.02,
        "liquidity_dry_up": 0.25,
    },
    "crypto_winter_2022": {
        "description": "Crypto Winter / LUNA collapse (May 2022)",
        "equity_shock": -0.03,
        "vol_shock": 0.55,
        "credit_spread_widen": 0.015,
        "liquidity_dry_up": 0.50,
    },
}


@router.get("/summary", response_model=PortfolioSummaryResponse)
async def get_portfolio_summary(http_request: Request) -> PortfolioSummaryResponse:
    """Get portfolio summary.

    Returns current portfolio value, positions, and PnL by querying
    the ExchangeManager's aggregated portfolio.

    Args:
        http_request: HTTP request for accessing app state.

    Returns:
        PortfolioSummaryResponse with portfolio data.
    """
    try:
        from quant_nanggroe.api.schemas import PositionResponse
        from quant_nanggroe.services import get_risk_manager

        rm = get_risk_manager(http_request.app)
        status = rm.status()

        # Attempt to get real positions from ExchangeManager
        positions = []
        cash_balance = 0.0
        total_value = status.get("current_equity", 0.0)
        unrealized_pnl = 0.0

        try:
            em = _get_exchange_manager(http_request)
            portfolio = await em.get_aggregated_portfolio()
            total_value = portfolio.total_value
            cash_balance = portfolio.cash
            unrealized_pnl = portfolio.total_unrealized_pnl

            for symbol, pos in portfolio.positions.items():
                positions.append(
                    PositionResponse(
                        ticker=symbol,
                        amount=pos.quantity,
                        avg_price=pos.entry_price,
                        current_price=pos.current_price,
                        pnl=pos.market_value - pos.cost_basis if pos.cost_basis > 0 else 0.0,
                    )
                )
        except Exception:
            logger.exception("exchange_manager_portfolio_failed: ExchangeManager may not have connected exchanges")

        return PortfolioSummaryResponse(
            total_value=total_value,
            unrealized_pnl=unrealized_pnl,
            realized_pnl=status.get("daily_pnl", 0.0),
            positions=positions,
            position_count=len(positions),
            cash_balance=cash_balance,
        )
    except Exception:
        logger.exception("portfolio_summary_failed: returning empty response")
        return PortfolioSummaryResponse()


@router.get("/performance")
async def get_portfolio_performance(http_request: Request) -> dict[str, Any]:
    """Portfolio performance metrics computed from closed trade history via PnLEvaluator."""
    try:
        from quant_nanggroe.engine.analytics.pnl_evaluator import PnLEvaluator

        evaluator = PnLEvaluator()
        # Aggregate across all strategies
        all_pnls: list[float] = []
        total_wins = 0
        total_trades = 0
        for strategy_name, trades in evaluator._trade_history.items():
            for t in trades:
                if t.is_closed():
                    pnl = t.realized_pnl()
                    all_pnls.append(pnl)
                    total_trades += 1
                    if pnl > 0:
                        total_wins += 1

        if not all_pnls:
            return {
                "total_return": 0.0,
                "cagr": 0.0,
                "sharpe_ratio": 0.0,
                "sortino_ratio": 0.0,
                "max_drawdown": 0.0,
                "win_rate": 0.0,
                "total_trades": 0,
                "status": "no_trades",
                "timestamp": datetime.now().isoformat(),
            }

        pnl_arr = np.array(all_pnls)
        total_return = float(np.sum(pnl_arr))
        win_rate = total_wins / total_trades if total_trades > 0 else 0.0

        # Sharpe ratio (annualized, assuming daily trades)
        if len(pnl_arr) > 1 and np.std(pnl_arr) > 0:
            sharpe = float(np.mean(pnl_arr) / np.std(pnl_arr) * np.sqrt(252))
        else:
            sharpe = 0.0

        # Sortino ratio (downside deviation only)
        downside = pnl_arr[pnl_arr < 0]
        if len(downside) > 0 and np.std(downside) > 0:
            sortino = float(np.mean(pnl_arr) / np.std(downside) * np.sqrt(252))
        else:
            sortino = 0.0

        # Max drawdown from cumulative PnL
        cum_pnl = np.cumsum(pnl_arr)
        running_max = np.maximum.accumulate(cum_pnl)
        drawdowns = running_max - cum_pnl
        max_dd = float(np.max(drawdowns)) if len(drawdowns) > 0 else 0.0

        return {
            "total_return": round(total_return, 6),
            "cagr": round(total_return, 6),  # simplified; real CAGR needs time span
            "sharpe_ratio": round(sharpe, 4),
            "sortino_ratio": round(sortino, 4),
            "max_drawdown": round(max_dd, 6),
            "win_rate": round(win_rate, 4),
            "total_trades": total_trades,
            "status": "live",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception:
        logger.exception("portfolio_performance_failed")
        return {
            "total_return": 0.0,
            "cagr": 0.0,
            "sharpe_ratio": 0.0,
            "sortino_ratio": 0.0,
            "max_drawdown": 0.0,
            "win_rate": 0.0,
            "total_trades": 0,
            "status": "error",
            "timestamp": datetime.now().isoformat(),
        }


@router.get("/risk", response_model=PortfolioRiskResponse)
async def get_portfolio_risk(http_request: Request) -> PortfolioRiskResponse:
    """Get portfolio risk metrics.

    Returns VaR, CVaR, drawdown, and other risk metrics computed
    from the RiskManager's state.

    Args:
        http_request: HTTP request for accessing app state.

    Returns:
        PortfolioRiskResponse with risk metrics.
    """
    try:
        from quant_nanggroe.services import get_risk_manager

        rm = get_risk_manager(http_request.app)
        status = rm.status()

        dd_info = status.get("drawdown", {})

        risk_status = "OK"
        if status.get("overall_status") == "TRADING_HALT":
            risk_status = "HALT"

        # Compute VaR/CVaR if we have daily return history
        var_95 = 0.0
        cvar_95 = 0.0
        try:
            daily_returns = status.get("daily_returns", [])
            if daily_returns and len(daily_returns) >= 10:
                from quant_nanggroe.engine.risk.var import VaRCalculator

                var_calc = VaRCalculator(default_confidence=0.95)
                portfolio_value = status.get("current_equity", 10000.0)
                returns_arr = np.array(daily_returns, dtype=np.float64)
                var_result = var_calc.calculate(
                    returns=returns_arr,
                    confidence_level=0.95,
                    method="auto",
                    portfolio_value=portfolio_value,
                )
                var_95 = round(var_result.var_value, 4)
                cvar_95 = round(var_result.cvar_value, 4)
        except Exception:
            logger.exception("var_calculation_failed: could not compute VaR/CVaR")

        daily_pnl_pct = 0.0
        raw_daily = status.get("daily_loss_pct", "0")
        if isinstance(raw_daily, str) and "%" in raw_daily:
            daily_pnl_pct = float(raw_daily.rstrip("%")) / 100
        elif isinstance(raw_daily, (int, float)):
            daily_pnl_pct = float(raw_daily)

        return PortfolioRiskResponse(
            var_95=var_95,
            cvar_95=cvar_95,
            max_drawdown=float(dd_info.get("max_drawdown", 0.0)),
            current_drawdown=float(dd_info.get("current_drawdown", 0.0)),
            daily_pnl_pct=daily_pnl_pct,
            risk_status=risk_status,
        )
    except Exception:
        return PortfolioRiskResponse()


@router.get("/stress-test")
async def run_stress_test(http_request: Request) -> dict[str, Any]:
    """Run portfolio stress test.

    Applies historical-like scenarios to estimate portfolio performance
    under adverse conditions. Uses the current portfolio equity and
    applies scenario-specific shocks (equity drawdown, volatility spike,
    credit spread widening, liquidity dry-up) to compute estimated losses.

    If a VaR model is available from the RiskManager, the stress test
    also uses Monte Carlo simulation to project scenario-adjusted losses.

    Args:
        http_request: HTTP request for accessing app state.

    Returns:
        Dict with stress test results per scenario.
    """
    try:
        from quant_nanggroe.services import get_risk_manager

        rm = get_risk_manager(http_request.app)
        status = rm.status()
        portfolio_value = status.get("current_equity", 100000.0)
    except Exception:
        logger.exception("stress_test_risk_manager_failed: using hardcoded portfolio_value fallback")
        portfolio_value = 100000.0

    # Get current portfolio positions to compute position-aware shocks
    positions: dict[str, float] = {}
    try:
        em = _get_exchange_manager(http_request)
        portfolio = await em.get_aggregated_portfolio()
        for symbol, pos in portfolio.positions.items():
            positions[symbol] = pos.market_value
    except Exception:
        # If no exchange connected, assume a single-equity portfolio
        positions = {"EQUITY": portfolio_value}

    total_position_value = sum(positions.values()) or portfolio_value

    scenario_results: dict[str, Any] = {}

    for scenario_name, scenario in STRESS_SCENARIOS.items():
        equity_shock = scenario["equity_shock"]
        vol_shock = scenario["vol_shock"]
        credit_shock = scenario.get("credit_spread_widen", 0.0)
        liquidity_shock = scenario.get("liquidity_dry_up", 0.0)

        # Apply shock to each position proportionally
        estimated_loss = 0.0
        position_impacts: dict[str, Any] = {}

        for symbol, value in positions.items():
            # Base loss from equity shock
            position_loss = value * equity_shock

            # Additional loss from volatility (convexity effect)
            position_loss -= value * (vol_shock * 0.005)

            # Credit spread impact (for fixed-income-like positions)
            position_loss -= value * (credit_shock * 0.5)

            # Liquidity discount on the remaining value
            remaining_value = value + position_loss
            liquidity_cost = abs(remaining_value) * liquidity_shock * 0.02
            position_loss -= liquidity_cost

            estimated_loss += position_loss
            position_impacts[symbol] = {
                "pre_shock_value": round(value, 2),
                "estimated_loss": round(position_loss, 2),
                "post_shock_value": round(value + position_loss, 2),
                "loss_pct": round(position_loss / value, 4) if value > 0 else 0.0,
            }

        post_shock_value = total_position_value + estimated_loss
        loss_pct = estimated_loss / total_position_value if total_position_value > 0 else 0.0

        # Monte Carlo refinement: generate 1000 scenario-adjusted returns
        # to estimate tail risk under this scenario
        mc_losses = []
        try:
            mean_shock = equity_shock
            std_shock = abs(equity_shock) * vol_shock * 0.5
            simulated = np.random.normal(mean_shock, max(std_shock, 0.001), size=1000)
            for sim_return in simulated:
                mc_losses.append(total_position_value * sim_return)
            p95_loss = float(np.percentile(mc_losses, 5))
            p99_loss = float(np.percentile(mc_losses, 1))
        except Exception:
            p95_loss = estimated_loss
            p99_loss = estimated_loss * 1.5

        scenario_results[scenario_name] = {
            "description": scenario["description"],
            "portfolio_value_pre": round(total_position_value, 2),
            "estimated_loss": round(estimated_loss, 2),
            "loss_pct": round(loss_pct, 4),
            "portfolio_value_post": round(post_shock_value, 2),
            "p95_loss": round(p95_loss, 2),
            "p99_loss": round(p99_loss, 2),
            "position_impacts": position_impacts,
        }

    # Overall summary
    worst_scenario = max(
        scenario_results.items(),
        key=lambda x: abs(x[1]["loss_pct"]),
        default=(None, {}),
    )

    return {
        "scenarios": scenario_results,
        "summary": {
            "portfolio_value": round(total_position_value, 2),
            "worst_scenario": worst_scenario[0] if worst_scenario[0] else "N/A",
            "worst_case_loss_pct": worst_scenario[1].get("loss_pct", 0.0) if worst_scenario[1] else 0.0,
            "total_scenarios": len(scenario_results),
        },
        "timestamp": datetime.now().isoformat(),
    }
