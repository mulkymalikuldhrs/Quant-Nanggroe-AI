"""Hedge-fund trading loop — wires strategy -> risk -> execution -> portfolio.

Single entry point ``run_cycle`` that turns market data into a (paper or live)
trade through the already-wired ExchangeManager + ExecutionTool. This is the
"start button" that was missing: every component existed, they just were not
connected into one callable path.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from quant_nanggroe.agents.tools.execution import ExecutionTool
from quant_nanggroe.exchange.manager import ExchangeManager
from quant_nanggroe.engine.strategies.registry import StrategyRegistry
from quant_nanggroe.engine.strategies.base import StrategyParameters

logger = logging.getLogger(__name__)


@dataclass
class CycleResult:
    symbol: str
    signal: str
    confidence: float
    order: Optional[Dict[str, Any]] = None
    portfolio: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


async def run_cycle(
    em: ExchangeManager,
    symbol: str = "AAPL",
    strategy_name: str = "trend_follow",
    quantity: float = 10.0,
) -> CycleResult:
    """Run one hedge-fund cycle for ``symbol``.

    1. Fetch OHLCV via ExchangeManager (yfinance/ccxt/MT5).
    2. Strategy generates a signal from closes.
    3. If not hold, route through ExecutionTool (kill-switch + risk guards inside).
    4. Return portfolio snapshot.
    """
    result = CycleResult(symbol=symbol, signal="hold", confidence=0.0)

    # 1. data
    try:
        candles = await em.get_ohlcv(symbol)
        if not candles:
            result.error = "no market data"
            return result
        closes = [float(c.close) for c in candles]
    except Exception as exc:  # noqa: BLE001
        result.error = f"data fetch failed: {exc}"
        return result

    # 2. strategy — use StrategyRegistry for any registered strategy
    strategy = StrategyRegistry.create(strategy_name)
    if strategy is None:
        result.error = f"unknown or inactive strategy: {strategy_name}"
        return result

    import pandas as pd
    df = pd.DataFrame({"close": closes})
    signal = strategy.generate_signal(df)
    result.signal = signal.direction.value.lower()
    result.confidence = float(signal.confidence)

    if result.signal == "hold":
        # still report portfolio so UI stays live
        pass
    else:
        side = "BUY" if result.signal == "buy" else "SELL"
        try:
            ex = ExecutionTool()
            order = await ex.execute_order(
                symbol=symbol, side=side, quantity=quantity, order_type="MARKET"
            )
            result.order = order
        except Exception as exc:  # noqa: BLE001
            result.error = f"execution failed: {exc}"
            return result

    # 4. portfolio snapshot
    try:
        pf = await em.get_portfolio()
        result.portfolio = {
            "total_value": pf.total_value,
            "cash": pf.cash,
            "unrealized_pnl": pf.total_unrealized_pnl,
            "position_count": len(pf.positions),
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("portfolio snapshot failed: %s", exc)

    return result
