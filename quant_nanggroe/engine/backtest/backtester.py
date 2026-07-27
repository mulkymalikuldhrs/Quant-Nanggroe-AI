"""Backtester — High-level wrapper around BacktestEngine.

Provides a simplified ``run_single(strategy, data)`` interface for
auto-tuning and other callers that need a one-shot strategy → metrics flow.

Ponytail: thin adapter, no new logic — delegates to BacktestEngine.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import pandas as pd

from quant_nanggroe.engine.backtest.engine import BacktestConfig, BacktestEngine

logger = logging.getLogger(__name__)


class Backtester:
    """High-level backtest runner for auto-tune and ad-hoc validation.

    Usage::

        backtester = Backtester()
        results = backtester.run_single(my_strategy, price_data)
        print(results["sharpe"], results["total_return"])
    """

    def __init__(self, config: Optional[BacktestConfig] = None) -> None:
        self._config = config or BacktestConfig()

    def run_single(
        self,
        strategy: Any,
        data: pd.DataFrame,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Run a single strategy backtest.

        Generates signals bar-by-bar via the strategy's ``generate_signal``
        method, then feeds them into ``BacktestEngine.run()``.

        Args:
            strategy: BaseStrategy instance.
            data: Price DataFrame with DatetimeIndex and OHLCV columns.
            **kwargs: Additional arguments passed to engine.run().

        Returns:
            Dict with keys ``sharpe``, ``total_return``, ``num_trades``,
            ``max_drawdown``, ``sortino``, ``calmar``, plus full engine result.
        """

        signals = []
        warmup = getattr(strategy, "warmup_period", lambda: 20)()
        warmup = max(warmup, 10)

        # Normalise column names to lowercase
        df = data.rename(columns={c: c.lower() for c in data.columns})

        for i in range(len(df)):
            data_slice = df.iloc[max(0, i - warmup):i + 1]
            if len(data_slice) < warmup:
                signals.append(0.0)
                continue
            try:
                signal = strategy.generate_signal(data_slice)
                if signal is None:
                    signals.append(0.0)
                else:
                    weight = signal.strength if signal.strength not in (None, 0.0) else (
                        1.0 if signal.direction in ("BUY", "LONG") else -1.0
                    )
                    signals.append(weight)
            except Exception:
                signals.append(0.0)

        signals_df = pd.DataFrame(
            {df.columns[0]: signals}, index=df.index
        )

        engine = BacktestEngine(self._config)
        result = engine.run(df, signals_df, **kwargs)

        metrics = result.get("metrics", {})
        return {
            "sharpe": metrics.get("sharpe_ratio", 0.0),
            "total_return": metrics.get("total_return", 0.0),
            "max_drawdown": metrics.get("max_drawdown", 0.0),
            "sortino": metrics.get("sortino_ratio", 0.0),
            "calmar": metrics.get("calmar_ratio", 0.0),
            "num_trades": len(result.get("trades", [])),
        }


__all__ = ["Backtester"]
