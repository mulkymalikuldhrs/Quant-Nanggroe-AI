"""Backtest Report Generation.

Generates structured backtest reports with performance metrics,
equity curves, and trade analysis. Supports JSON, HTML, and text output.

Report contents:
- Performance summary (total return, CAGR, Sharpe, etc.)
- Equity curve visualization data
- Drawdown chart data
- Monthly returns heatmap data
- Trade distribution analysis
- Parameter sensitivity (if available)
- Benchmark comparison (if available)
- Risk metrics breakdown
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
    - HTML report with embedded charts (using inline SVG/JS)
    - Text summary for console output
    - Trade-by-trade analysis
    - Performance attribution
    - Monthly returns heatmap
    - Drawdown analysis
    - Parameter sensitivity (if provided)
    - Benchmark comparison (if provided)
    """

    @staticmethod
    def generate(
        metrics: Dict[str, Any],
        equity_curve: pd.Series,
        trades: List[TradeRecord],
        config: Optional[Dict[str, Any]] = None,
        format: str = "json",
        benchmark_comparison: Optional[Dict[str, Any]] = None,
        sensitivity_analysis: Optional[Dict[str, Any]] = None,
        strategy_name: str = "",
    ) -> str:
        """Generate a backtest report.

        Args:
            metrics: Performance metrics dict.
            equity_curve: Equity curve series.
            trades: List of trade records.
            config: Backtest configuration dict.
            format: Output format ('json', 'html', 'text').
            benchmark_comparison: Optional benchmark comparison dict.
            sensitivity_analysis: Optional sensitivity analysis results.
            strategy_name: Optional strategy name for the report.

        Returns:
            Formatted report string.
        """
        if format == "json":
            return BacktestReport._generate_json(
                metrics, equity_curve, trades, config,
                benchmark_comparison, sensitivity_analysis, strategy_name,
            )
        elif format == "html":
            return BacktestReport._generate_html(
                metrics, equity_curve, trades, config,
                benchmark_comparison, sensitivity_analysis, strategy_name,
            )
        elif format == "text":
            return BacktestReport._generate_text(
                metrics, equity_curve, trades, config,
                benchmark_comparison, strategy_name,
            )
        else:
            raise ValueError(f"Unknown report format: {format}")

    @staticmethod
    def generate_json(
        metrics: Dict[str, Any],
        equity_curve: pd.Series,
        trades: List[TradeRecord],
        config: Optional[Dict[str, Any]] = None,
        benchmark_comparison: Optional[Dict[str, Any]] = None,
        sensitivity_analysis: Optional[Dict[str, Any]] = None,
        strategy_name: str = "",
    ) -> str:
        """Generate JSON report.

        Args:
            metrics: Performance metrics dict.
            equity_curve: Equity curve series.
            trades: List of trade records.
            config: Backtest configuration dict.
            benchmark_comparison: Optional benchmark comparison.
            sensitivity_analysis: Optional sensitivity analysis.
            strategy_name: Strategy name.

        Returns:
            JSON report string.
        """
        return BacktestReport._generate_json(
            metrics, equity_curve, trades, config,
            benchmark_comparison, sensitivity_analysis, strategy_name,
        )

    @staticmethod
    def generate_html(
        metrics: Dict[str, Any],
        equity_curve: pd.Series,
        trades: List[TradeRecord],
        config: Optional[Dict[str, Any]] = None,
        benchmark_comparison: Optional[Dict[str, Any]] = None,
        sensitivity_analysis: Optional[Dict[str, Any]] = None,
        strategy_name: str = "",
    ) -> str:
        """Generate HTML report.

        Args:
            metrics: Performance metrics dict.
            equity_curve: Equity curve series.
            trades: List of trade records.
            config: Backtest configuration dict.
            benchmark_comparison: Optional benchmark comparison.
            sensitivity_analysis: Optional sensitivity analysis.
            strategy_name: Strategy name.

        Returns:
            HTML report string.
        """
        return BacktestReport._generate_html(
            metrics, equity_curve, trades, config,
            benchmark_comparison, sensitivity_analysis, strategy_name,
        )

    @staticmethod
    def _generate_json(
        metrics: Dict[str, Any],
        equity_curve: pd.Series,
        trades: List[TradeRecord],
        config: Optional[Dict[str, Any]],
        benchmark_comparison: Optional[Dict[str, Any]],
        sensitivity_analysis: Optional[Dict[str, Any]],
        strategy_name: str,
    ) -> str:
        """Generate JSON report."""
        # Equity curve data
        equity_data = []
        if len(equity_curve) > 0:
            # Downsample if too many points
            step = max(1, len(equity_curve) // 500)
            for i in range(0, len(equity_curve), step):
                equity_data.append({
                    "timestamp": str(equity_curve.index[i]),
                    "equity": round(float(equity_curve.iloc[i]), 2),
                })

        # Drawdown data
        drawdown_data = BacktestReport._compute_drawdown_data(equity_curve)

        # Monthly returns heatmap
        monthly_returns = BacktestReport._compute_monthly_returns(equity_curve)

        # Trade distribution
        trade_distribution = BacktestReport._compute_trade_distribution(trades)

        report = {
            "generated_at": datetime.now().isoformat(),
            "strategy_name": strategy_name,
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
                for t in trades[:200]  # Limit to first 200 trades
            ],
            "equity_curve": equity_data,
            "drawdown": drawdown_data,
            "monthly_returns": monthly_returns,
            "trade_distribution": trade_distribution,
        }

        # Add benchmark comparison if available
        if benchmark_comparison:
            report["benchmark_comparison"] = benchmark_comparison

        # Add sensitivity analysis if available
        if sensitivity_analysis:
            # Include only summary, not raw results
            report["sensitivity_analysis"] = {
                "param_name": sensitivity_analysis.get("param_name", ""),
                "optimal": sensitivity_analysis.get("optimal", {}),
            }

        return json.dumps(report, indent=2, default=str)

    @staticmethod
    def _generate_html(
        metrics: Dict[str, Any],
        equity_curve: pd.Series,
        trades: List[TradeRecord],
        config: Optional[Dict[str, Any]],
        benchmark_comparison: Optional[Dict[str, Any]],
        sensitivity_analysis: Optional[Dict[str, Any]],
        strategy_name: str,
    ) -> str:
        """Generate HTML report with embedded chart data."""
        # Compute chart data
        equity_data = BacktestReport._compute_equity_chart_data(equity_curve)
        drawdown_data = BacktestReport._compute_drawdown_data(equity_curve)
        monthly_returns = BacktestReport._compute_monthly_returns(equity_curve)
        trade_distribution = BacktestReport._compute_trade_distribution(trades)

        # Metrics sections
        perf_section = BacktestReport._html_metrics_section(metrics, "Performance Summary")
        risk_section = BacktestReport._html_risk_section(metrics)
        trade_section = BacktestReport._html_trade_section(metrics)

        benchmark_html = ""
        if benchmark_comparison:
            benchmark_html = BacktestReport._html_benchmark_section(benchmark_comparison)

        sensitivity_html = ""
        if sensitivity_analysis:
            sensitivity_html = BacktestReport._html_sensitivity_section(sensitivity_analysis)

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Backtest Report{f' — {strategy_name}' if strategy_name else ''}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
               background: #f5f5f5; color: #333; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ font-size: 24px; color: #1a1a1a; margin-bottom: 8px; }}
        h2 {{ font-size: 18px; color: #444; margin: 20px 0 12px; border-bottom: 2px solid #e0e0e0;
              padding-bottom: 6px; }}
        .subtitle {{ color: #888; font-size: 14px; margin-bottom: 20px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                 gap: 16px; margin-bottom: 20px; }}
        .card {{ background: #fff; border-radius: 8px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        .metric {{ margin-bottom: 8px; }}
        .metric-label {{ font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 0.5px; }}
        .metric-value {{ font-size: 20px; font-weight: 600; color: #1a1a1a; }}
        .positive {{ color: #16a34a; }}
        .negative {{ color: #dc2626; }}
        .chart-container {{ background: #fff; border-radius: 8px; padding: 16px;
                           box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 16px; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
        th {{ text-align: left; padding: 8px 12px; background: #f9f9f9; border-bottom: 2px solid #e0e0e0;
             font-weight: 600; color: #555; }}
        td {{ padding: 8px 12px; border-bottom: 1px solid #f0f0f0; }}
        tr:hover {{ background: #fafafa; }}
        .heatmap {{ display: grid; gap: 2px; font-size: 12px; text-align: center; }}
        .heatmap-cell {{ padding: 4px 8px; border-radius: 3px; min-width: 50px; }}
        .footer {{ text-align: center; color: #aaa; font-size: 12px; margin-top: 30px; padding: 10px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Backtest Report{f' — {strategy_name}' if strategy_name else ''}</h1>
        <p class="subtitle">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

        {perf_section}
        {risk_section}

        <h2>📈 Equity Curve</h2>
        <div class="chart-container">
            <div id="equity-chart" style="height:300px;"></div>
            <script>
            // Simple inline equity curve rendering
            (function() {{
                var data = {json.dumps(equity_data)};
                var container = document.getElementById('equity-chart');
                if (!data || data.length === 0) {{
                    container.innerHTML = '<p style="color:#888;text-align:center;">No equity data available</p>';
                    return;
                }}
                var minV = Math.min.apply(null, data.map(function(d){{ return d.e; }}));
                var maxV = Math.max.apply(null, data.map(function(d){{ return d.e; }}));
                var range = maxV - minV || 1;
                var w = container.clientWidth || 800;
                var h = 280;
                var svg = '<svg width="100%" height="' + h + '" viewBox="0 0 ' + w + ' ' + h + '">';
                svg += '<rect width="' + w + '" height="' + h + '" fill="#fafafa" rx="4"/>';
                // Grid lines
                for (var g = 0; g <= 4; g++) {{
                    var gy = 10 + (h - 20) * g / 4;
                    svg += '<line x1="40" y1="' + gy + '" x2="' + (w-10) + '" y2="' + gy +
                           '" stroke="#e8e8e8" stroke-width="1"/>';
                    var val = maxV - range * g / 4;
                    svg += '<text x="5" y="' + (gy+4) + '" font-size="10" fill="#999">' +
                           val.toFixed(0) + '</text>';
                }}
                // Equity line
                var points = '';
                for (var i = 0; i < data.length; i++) {{
                    var x = 40 + (w - 50) * i / (data.length - 1 || 1);
                    var y = 10 + (h - 20) * (1 - (data[i].e - minV) / range);
                    points += (i === 0 ? 'M' : 'L') + x.toFixed(1) + ',' + y.toFixed(1);
                }}
                svg += '<path d="' + points + '" fill="none" stroke="#2563eb" stroke-width="2"/>';
                svg += '</svg>';
                container.innerHTML = svg;
            }})();
            </script>
        </div>

        <h2>📉 Drawdown</h2>
        <div class="chart-container">
            <div id="drawdown-chart" style="height:200px;"></div>
            <script>
            (function() {{
                var data = {json.dumps(drawdown_data)};
                var container = document.getElementById('drawdown-chart');
                if (!data || data.length === 0) {{
                    container.innerHTML = '<p style="color:#888;text-align:center;">No drawdown data available</p>';
                    return;
                }}
                var minV = Math.min.apply(null, data.map(function(d){{ return d.d; }}));
                var maxV = 0;
                var range = maxV - minV || 1;
                var w = container.clientWidth || 800;
                var h = 180;
                var svg = '<svg width="100%" height="' + h + '" viewBox="0 0 ' + w + ' ' + h + '">';
                svg += '<rect width="' + w + '" height="' + h + '" fill="#fafafa" rx="4"/>';
                var points = '';
                for (var i = 0; i < data.length; i++) {{
                    var x = 40 + (w - 50) * i / (data.length - 1 || 1);
                    var y = 10 + (h - 20) * (1 - (data[i].d - minV) / range);
                    points += (i === 0 ? 'M' : 'L') + x.toFixed(1) + ',' + y.toFixed(1);
                }}
                svg += '<path d="' + points + '" fill="none" stroke="#dc2626" stroke-width="1.5"/>';
                svg += '</svg>';
                container.innerHTML = svg;
            }})();
            </script>
        </div>

        <h2>📅 Monthly Returns</h2>
        <div class="card">
            {BacktestReport._html_monthly_returns_heatmap(monthly_returns)}
        </div>

        {trade_section}

        <h2>📊 Trade Distribution</h2>
        <div class="grid">
            <div class="card">
                {BacktestReport._html_trade_distribution(trade_distribution)}
            </div>
        </div>

        {benchmark_html}
        {sensitivity_html}

        <div class="footer">
            Quant Nanggroe AI — Backtest Report — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </div>
    </div>
</body>
</html>"""
        return html

    @staticmethod
    def _generate_text(
        metrics: Dict[str, Any],
        equity_curve: pd.Series,
        trades: List[TradeRecord],
        config: Optional[Dict[str, Any]],
        benchmark_comparison: Optional[Dict[str, Any]],
        strategy_name: str,
    ) -> str:
        """Generate text summary report."""
        name_str = f" — {strategy_name}" if strategy_name else ""
        lines = [
            "=" * 60,
            f"  QUANT-NANGGROE-AI BACKTEST REPORT{name_str}",
            "=" * 60,
            "",
            "PERFORMANCE SUMMARY",
            "-" * 40,
            f"  Total Return:      {metrics.get('total_return', 0):.2%}",
            f"  CAGR:              {metrics.get('cagr', metrics.get('annual_return', 0)):.2%}",
            f"  Max Drawdown:      {metrics.get('max_drawdown', 0):.2%}",
            f"  Max DD Duration:   {metrics.get('max_drawdown_duration', 0)} bars",
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
            f"  Recovery Factor:   {metrics.get('recovery_factor', 0):.4f}",
            f"  Tail Ratio:        {metrics.get('tail_ratio', 0):.4f}",
            f"  Ulcer Index:       {metrics.get('ulcer_index', 0):.4f}",
            "",
            "TRADE STATISTICS",
            "-" * 40,
            f"  Total Trades:      {metrics.get('total_trades', 0)}",
            f"  Win Rate:          {metrics.get('win_rate', 0):.2%}",
            f"  Profit Factor:     {metrics.get('profit_factor', 0):.4f}",
            f"  Avg Trade P&L:     {metrics.get('avg_trade_pnl', 0):.4f}",
            f"  Avg Win:           {metrics.get('avg_win', 0):.4f}",
            f"  Avg Loss:          {metrics.get('avg_loss', 0):.4f}",
            f"  Profit/Loss Ratio: {metrics.get('profit_loss_ratio', 0):.4f}",
            f"  Avg Holding Bars:  {metrics.get('avg_holding_bars', 0):.1f}",
            f"  Max Consec Losses: {metrics.get('max_consecutive_losses', 0)}",
            "",
        ]

        if benchmark_comparison or "benchmark_return" in metrics:
            bench_ret = metrics.get("benchmark_return", 0)
            excess = metrics.get("excess_return", 0)
            info = metrics.get("information_ratio", 0)
            alpha = metrics.get("alpha", 0)
            beta = metrics.get("beta", 0)
            lines.extend([
                "BENCHMARK COMPARISON",
                "-" * 40,
                f"  Benchmark Return:  {bench_ret:.2%}",
                f"  Excess Return:     {excess:.2%}",
                f"  Alpha:             {alpha:.4f}",
                f"  Beta:              {beta:.4f}",
                f"  Information Ratio: {info:.4f}",
                f"  Tracking Error:    {metrics.get('tracking_error', 0):.4f}",
                "",
            ])

        lines.append("=" * 60)
        return "\n".join(lines)

    # ── Chart data computation ────────────────────────────────────────

    @staticmethod
    def _compute_equity_chart_data(equity_curve: pd.Series) -> List[Dict[str, Any]]:
        """Compute equity curve data for chart rendering.

        Downsamples to a maximum of 500 points for performance.
        """
        if len(equity_curve) == 0:
            return []

        step = max(1, len(equity_curve) // 500)
        data = []
        for i in range(0, len(equity_curve), step):
            data.append({
                "t": str(equity_curve.index[i])[:10],  # Date only
                "e": round(float(equity_curve.iloc[i]), 2),
            })
        return data

    @staticmethod
    def _compute_drawdown_data(equity_curve: pd.Series) -> List[Dict[str, Any]]:
        """Compute drawdown chart data.

        Returns:
            List of dicts with 't' (timestamp) and 'd' (drawdown as decimal).
        """
        if len(equity_curve) < 2:
            return []

        peak = equity_curve.cummax()
        drawdown = (equity_curve - peak) / peak.replace(0, 1)

        step = max(1, len(drawdown) // 500)
        data = []
        for i in range(0, len(drawdown), step):
            data.append({
                "t": str(drawdown.index[i])[:10],
                "d": round(float(drawdown.iloc[i]), 6),
            })
        return data

    @staticmethod
    def _compute_monthly_returns(equity_curve: pd.Series) -> Dict[str, Any]:
        """Compute monthly returns for heatmap visualization.

        Returns:
            Dict with 'years', 'months', 'data' keys.
            'data' is a dict mapping "YYYY-MM" to return value.
        """
        if len(equity_curve) < 2:
            return {"years": [], "months": [], "data": {}}

        # Resample to monthly
        try:
            monthly_eq = equity_curve.resample('ME').last()
            monthly_returns = monthly_eq.pct_change().fillna(0.0)

            data = {}
            years = set()
            months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

            for idx, val in monthly_returns.items():
                if pd.isna(val):
                    continue
                key = f"{idx.year}-{idx.month:02d}"
                data[key] = round(float(val) * 100, 2)  # As percentage
                years.add(idx.year)

            return {
                "years": sorted(list(years)),
                "months": months,
                "data": data,
            }
        except Exception as e:
            logger.warning(f"Failed to compute monthly returns: {e}")
            return {"years": [], "months": [], "data": {}}

    @staticmethod
    def _compute_trade_distribution(trades: List[TradeRecord]) -> Dict[str, Any]:
        """Compute trade distribution statistics.

        Returns:
            Dict with distribution data for visualization.
        """
        if not trades:
            return {"bins": [], "counts": [], "win_rate_by_bin": []}

        pnls = [t.pnl_pct for t in trades]
        if not pnls:
            return {"bins": [], "counts": [], "win_rate_by_bin": []}

        # Create histogram bins
        pnl_array = np.array(pnls)
        try:
            counts, bin_edges = np.histogram(pnl_array, bins=20)
            bins = [round((bin_edges[i] + bin_edges[i + 1]) / 2, 2) for i in range(len(counts))]
        except Exception:
            return {"bins": [], "counts": [], "win_rate_by_bin": []}

        # Win rate by P&L bin
        win_rate_by_bin = []
        for i in range(len(counts)):
            if counts[i] > 0:
                mask = (pnl_array >= bin_edges[i]) & (pnl_array < bin_edges[i + 1])
                bin_pnls = pnl_array[mask]
                wr = float(np.mean(bin_pnls > 0)) if len(bin_pnls) > 0 else 0.0
                win_rate_by_bin.append(round(wr, 4))
            else:
                win_rate_by_bin.append(0.0)

        return {
            "bins": bins,
            "counts": counts.tolist(),
            "win_rate_by_bin": win_rate_by_bin,
        }

    # ── HTML helper methods ───────────────────────────────────────────

    @staticmethod
    def _html_metrics_section(metrics: Dict[str, Any], title: str) -> str:
        """Generate HTML for performance summary section."""
        total_return = metrics.get("total_return", 0)
        cagr = metrics.get("cagr", metrics.get("annual_return", 0))
        max_dd = metrics.get("max_drawdown", 0)
        sharpe = metrics.get("sharpe_ratio", 0)
        sortino = metrics.get("sortino_ratio", 0)
        calmar = metrics.get("calmar_ratio", 0)

        tr_class = "positive" if total_return > 0 else "negative"
        cagr_class = "positive" if cagr > 0 else "negative"

        return f"""
        <h2>{title}</h2>
        <div class="grid">
            <div class="card">
                <div class="metric">
                    <div class="metric-label">Total Return</div>
                    <div class="metric-value {tr_class}">{total_return:.2%}</div>
                </div>
            </div>
            <div class="card">
                <div class="metric">
                    <div class="metric-label">CAGR</div>
                    <div class="metric-value {cagr_class}">{cagr:.2%}</div>
                </div>
            </div>
            <div class="card">
                <div class="metric">
                    <div class="metric-label">Max Drawdown</div>
                    <div class="metric-value negative">{max_dd:.2%}</div>
                </div>
            </div>
            <div class="card">
                <div class="metric">
                    <div class="metric-label">Sharpe Ratio</div>
                    <div class="metric-value">{sharpe:.4f}</div>
                </div>
            </div>
            <div class="card">
                <div class="metric">
                    <div class="metric-label">Sortino Ratio</div>
                    <div class="metric-value">{sortino:.4f}</div>
                </div>
            </div>
            <div class="card">
                <div class="metric">
                    <div class="metric-label">Calmar Ratio</div>
                    <div class="metric-value">{calmar:.4f}</div>
                </div>
            </div>
        </div>"""

    @staticmethod
    def _html_risk_section(metrics: Dict[str, Any]) -> str:
        """Generate HTML for risk metrics section."""
        return f"""
        <h2>⚠️ Risk Metrics</h2>
        <div class="grid">
            <div class="card">
                <div class="metric">
                    <div class="metric-label">Volatility</div>
                    <div class="metric-value">{metrics.get('volatility', 0):.4%}</div>
                </div>
            </div>
            <div class="card">
                <div class="metric">
                    <div class="metric-label">VaR (95%)</div>
                    <div class="metric-value">{metrics.get('var_95', 0):.4%}</div>
                </div>
            </div>
            <div class="card">
                <div class="metric">
                    <div class="metric-label">CVaR (95%)</div>
                    <div class="metric-value">{metrics.get('cvar_95', 0):.4%}</div>
                </div>
            </div>
            <div class="card">
                <div class="metric">
                    <div class="metric-label">Recovery Factor</div>
                    <div class="metric-value">{metrics.get('recovery_factor', 0):.4f}</div>
                </div>
            </div>
            <div class="card">
                <div class="metric">
                    <div class="metric-label">Tail Ratio</div>
                    <div class="metric-value">{metrics.get('tail_ratio', 0):.4f}</div>
                </div>
            </div>
            <div class="card">
                <div class="metric">
                    <div class="metric-label">Ulcer Index</div>
                    <div class="metric-value">{metrics.get('ulcer_index', 0):.4f}</div>
                </div>
            </div>
        </div>"""

    @staticmethod
    def _html_trade_section(metrics: Dict[str, Any]) -> str:
        """Generate HTML for trade statistics section."""
        return f"""
        <h2>🔄 Trade Statistics</h2>
        <div class="grid">
            <div class="card">
                <div class="metric">
                    <div class="metric-label">Total Trades</div>
                    <div class="metric-value">{metrics.get('total_trades', 0)}</div>
                </div>
            </div>
            <div class="card">
                <div class="metric">
                    <div class="metric-label">Win Rate</div>
                    <div class="metric-value">{metrics.get('win_rate', 0):.2%}</div>
                </div>
            </div>
            <div class="card">
                <div class="metric">
                    <div class="metric-label">Profit Factor</div>
                    <div class="metric-value">{metrics.get('profit_factor', 0):.4f}</div>
                </div>
            </div>
            <div class="card">
                <div class="metric">
                    <div class="metric-label">Avg Trade P&L</div>
                    <div class="metric-value">{metrics.get('avg_trade_pnl', 0):.4f}</div>
                </div>
            </div>
            <div class="card">
                <div class="metric">
                    <div class="metric-label">Avg Win</div>
                    <div class="metric-value positive">{metrics.get('avg_win', 0):.4f}</div>
                </div>
            </div>
            <div class="card">
                <div class="metric">
                    <div class="metric-label">Avg Loss</div>
                    <div class="metric-value negative">{metrics.get('avg_loss', 0):.4f}</div>
                </div>
            </div>
        </div>"""

    @staticmethod
    def _html_benchmark_section(benchmark: Dict[str, Any]) -> str:
        """Generate HTML for benchmark comparison section."""
        return f"""
        <h2>📊 Benchmark Comparison</h2>
        <div class="grid">
            <div class="card">
                <div class="metric">
                    <div class="metric-label">Benchmark Return</div>
                    <div class="metric-value">{benchmark.get('benchmark_return', 0):.2%}</div>
                </div>
            </div>
            <div class="card">
                <div class="metric">
                    <div class="metric-label">Excess Return</div>
                    <div class="metric-value {'positive' if benchmark.get('excess_return', 0) > 0 else 'negative'}">{benchmark.get('excess_return', 0):.2%}</div>
                </div>
            </div>
            <div class="card">
                <div class="metric">
                    <div class="metric-label">Alpha</div>
                    <div class="metric-value">{benchmark.get('alpha', 0):.4f}</div>
                </div>
            </div>
            <div class="card">
                <div class="metric">
                    <div class="metric-label">Beta</div>
                    <div class="metric-value">{benchmark.get('beta', 0):.4f}</div>
                </div>
            </div>
        </div>"""

    @staticmethod
    def _html_sensitivity_section(sensitivity: Dict[str, Any]) -> str:
        """Generate HTML for parameter sensitivity section."""
        optimal = sensitivity.get("optimal", {})
        param_name = sensitivity.get("param_name", "")
        return f"""
        <h2>🔬 Parameter Sensitivity</h2>
        <div class="card">
            <p><strong>Parameter:</strong> {param_name}</p>
            <p><strong>Optimal Value:</strong> {optimal.get('optimal_value', 'N/A')}</p>
            <p><strong>Optimal {optimal.get('metric_name', 'Sharpe')}:</strong> {optimal.get('optimal_metric', 0):.4f}</p>
        </div>"""

    @staticmethod
    def _html_monthly_returns_heatmap(monthly_data: Dict[str, Any]) -> str:
        """Generate HTML for monthly returns heatmap."""
        if not monthly_data.get("data"):
            return '<p style="color:#888">No monthly return data available</p>'

        years = monthly_data.get("years", [])
        months = monthly_data.get("months", [])
        data = monthly_data.get("data", {})

        if not years or not months:
            return '<p style="color:#888">No monthly return data available</p>'

        html = '<table><tr><th></th>'
        for m in months:
            html += f'<th>{m}</th>'
        html += '</tr>'

        for year in years:
            html += f'<tr><td><strong>{year}</strong></td>'
            for m_idx in range(12):
                month = m_idx + 1
                key = f"{year}-{month:02d}"
                val = data.get(key, None)
                if val is not None:
                    if val > 0:
                        intensity = min(255, int(abs(val) * 10))
                        color = f'rgb({220-intensity}, 255, {220-intensity})'
                    elif val < 0:
                        intensity = min(255, int(abs(val) * 10))
                        color = f'rgb(255, {220-intensity}, {220-intensity})'
                    else:
                        color = '#f5f5f5'
                    html += f'<td style="background:{color};padding:4px 8px;text-align:center;font-size:11px;">{val:.1f}%</td>'
                else:
                    html += '<td style="padding:4px 8px;text-align:center;color:#ccc;">—</td>'
            html += '</tr>'

        html += '</table>'
        return html

    @staticmethod
    def _html_trade_distribution(dist: Dict[str, Any]) -> str:
        """Generate HTML for trade distribution."""
        bins = dist.get("bins", [])
        counts = dist.get("counts", [])

        if not bins or not counts:
            return '<p style="color:#888">No trade distribution data available</p>'

        html = '<table><tr><th>P&L Bin (%)</th><th>Count</th></tr>'
        for i, (b, c) in enumerate(zip(bins, counts)):
            html += f'<tr><td>{b:.2f}</td><td>{c}</td></tr>'
        html += '</table>'
        return html
