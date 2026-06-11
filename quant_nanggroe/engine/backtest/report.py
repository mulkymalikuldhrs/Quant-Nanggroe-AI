"""Backtest Report Generation.

Generates structured backtest reports with performance metrics,
equity curves, and trade analysis. Supports JSON and text output.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.backtest.portfolio import TradeRecord

logger = logging.getLogger(__name__)


class BacktestReport:
    """Generates backtest reports.

    Supports:
    - JSON report for programmatic consumption
    - Text summary for console output
    - Trade-by-trade analysis
    - Performance attribution
    """

    @staticmethod
    def generate(
        metrics: Dict[str, Any],
        equity_curve: pd.Series,
        trades: List[TradeRecord],
        config: Optional[Dict[str, Any]] = None,
        format: str = "json",
    ) -> str:
        """Generate a backtest report.

        Args:
            metrics: Performance metrics dict.
            equity_curve: Equity curve series.
            trades: List of trade records.
            config: Backtest configuration dict.
            format: Output format ('json' or 'text').

        Returns:
            Formatted report string.
        """
        if format == "json":
            return BacktestReport._generate_json(metrics, equity_curve, trades, config)
        elif format == "text":
            return BacktestReport._generate_text(metrics, equity_curve, trades, config)
        else:
            raise ValueError(f"Unknown report format: {format}")

    @staticmethod
    def _generate_json(
        metrics: Dict[str, Any],
        equity_curve: pd.Series,
        trades: List[TradeRecord],
        config: Optional[Dict[str, Any]],
    ) -> str:
        """Generate JSON report."""
        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "summary": {k: v for k, v in metrics.items() if not isinstance(v, dict)},
            "config": config or {},
            "trade_count": len(trades),
            "trades": [
                {
                    "symbol": t.symbol,
                    "direction": "LONG" if t.direction == 1 else "SHORT",
                    "entry_price": round(t.entry_price, 4),
                    "exit_price": round(t.exit_price, 4),
                    "pnl": round(t.pnl, 4),
                    "pnl_pct": round(t.pnl_pct, 2),
                    "exit_reason": t.exit_reason,
                    "holding_bars": t.holding_bars,
                }
                for t in trades[:100]  # Limit to first 100 trades
            ],
        }
        return json.dumps(report, indent=2, default=str)

    @staticmethod
    def _generate_text(
        metrics: Dict[str, Any],
        equity_curve: pd.Series,
        trades: List[TradeRecord],
        config: Optional[Dict[str, Any]],
    ) -> str:
        """Generate text summary report."""
        lines = [
            "=" * 60,
            "  QUANT-NANGGROE-AI BACKTEST REPORT",
            "=" * 60,
            "",
            "PERFORMANCE SUMMARY",
            "-" * 40,
            f"  Total Return:      {metrics.get('total_return', 0):.2%}",
            f"  Annual Return:     {metrics.get('annual_return', 0):.2%}",
            f"  Max Drawdown:      {metrics.get('max_drawdown', 0):.2%}",
            f"  Sharpe Ratio:      {metrics.get('sharpe_ratio', 0):.4f}",
            f"  Sortino Ratio:     {metrics.get('sortino_ratio', 0):.4f}",
            f"  Calmar Ratio:      {metrics.get('calmar_ratio', 0):.4f}",
            "",
            "RISK METRICS",
            "-" * 40,
            f"  Volatility:        {metrics.get('volatility', 0):.4%}",
            f"  VaR (95%):         {metrics.get('var_95', 0):.4%}",
            f"  CVaR (95%):        {metrics.get('cvar_95', 0):.4%}",
            f"  Downside Dev:      {metrics.get('downside_deviation', 0):.4%}",
            "",
            "TRADE STATISTICS",
            "-" * 40,
            f"  Total Trades:      {metrics.get('total_trades', 0)}",
            f"  Win Rate:          {metrics.get('win_rate', 0):.2%}",
            f"  Profit Factor:     {metrics.get('profit_factor', 0):.4f}",
            f"  Avg Holding Bars:  {metrics.get('avg_holding_bars', 0):.1f}",
            f"  Max Consec Losses: {metrics.get('max_consecutive_losses', 0)}",
            "",
        ]

        if "benchmark_return" in metrics:
            lines.extend([
                "BENCHMARK COMPARISON",
                "-" * 40,
                f"  Benchmark Return:  {metrics.get('benchmark_return', 0):.2%}",
                f"  Excess Return:     {metrics.get('excess_return', 0):.2%}",
                f"  Information Ratio: {metrics.get('information_ratio', 0):.4f}",
                "",
            ])

        lines.append("=" * 60)
        return "\n".join(lines)
