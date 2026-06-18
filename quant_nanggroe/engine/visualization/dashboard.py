"""
QNA Dashboard — Main visualization dashboard.
Aggregates charts, metrics, and data into a unified view.

Features:
- Refresh button for manual data reload
- Date range selector for time period filtering
- Portfolio summary panel with key holdings
- Risk metrics panel with VaR, CVaR, drawdown analysis
- Real-time updates via WebSocket (optional, requires websocket-server)
"""
from __future__ import annotations

from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import logging
import json
import threading

from .chart_factory import ChartFactory, HAS_PLOTLY

logger = logging.getLogger(__name__)


@dataclass
class DashboardMetrics:
    total_return: float = 0.0
    annualized_return: float = 0.0
    annualized_volatility: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    calmar_ratio: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    kelly_fraction: float = 0.0
    current_regime: str = "unknown"
    var_95: float = 0.0
    cvar_95: float = 0.0


@dataclass
class PositionSummary:
    """Summary of a single portfolio position."""
    symbol: str
    quantity: float = 0.0
    entry_price: float = 0.0
    current_price: float = 0.0
    market_value: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    weight: float = 0.0


@dataclass
class PortfolioSummary:
    """Aggregate portfolio summary."""
    total_equity: float = 0.0
    cash: float = 0.0
    invested: float = 0.0
    positions: List[PositionSummary] = field(default_factory=list)
    num_positions: int = 0
    largest_position_pct: float = 0.0
    concentration_index: float = 0.0


@dataclass
class DateRange:
    """Date range for dashboard filtering."""
    start: Optional[str] = None
    end: Optional[str] = None
    label: str = "all"

    @staticmethod
    def last_n_days(n: int) -> DateRange:
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=n)).strftime("%Y-%m-%d")
        return DateRange(start=start, end=end, label=f"last_{n}d")

    @staticmethod
    def this_month() -> DateRange:
        now = datetime.now()
        start = now.replace(day=1).strftime("%Y-%m-%d")
        end = now.strftime("%Y-%m-%d")
        return DateRange(start=start, end=end, label="this_month")

    @staticmethod
    def this_year() -> DateRange:
        now = datetime.now()
        start = f"{now.year}-01-01"
        end = now.strftime("%Y-%m-%d")
        return DateRange(start=start, end=end, label="this_year")

    @staticmethod
    def all() -> DateRange:
        return DateRange(start=None, end=None, label="all")


class RealtimeUpdater:
    """Optional WebSocket-based real-time updater.

    Provides a simple pub/sub mechanism for pushing dashboard updates
    to connected clients. Falls back to polling if WebSocket is unavailable.
    """

    def __init__(self, enabled: bool = False, port: int = 8765) -> None:
        self.enabled = enabled
        self.port = port
        self._subscribers: List[Callable[[Dict[str, Any]], None]] = []
        self._latest_data: Optional[Dict[str, Any]] = None
        self._lock = threading.Lock()
        self._ws_server: Optional[Any] = None

        if enabled:
            self._try_start_server()

    def _try_start_server(self) -> None:
        """Attempt to start WebSocket server; fail silently."""
        try:
            import asyncio

            async def _handler(websocket: Any, path: str) -> None:
                with self._lock:
                    if self._latest_data is not None:
                        await websocket.send(json.dumps(self._latest_data))

            try:
                from websockets.serve import serve as ws_serve
                loop = asyncio.new_event_loop()
                self._ws_server = ws_serve(_handler, "localhost", self.port)
                thread = threading.Thread(
                    target=loop.run_until_complete,
                    args=(self._ws_server,),
                    daemon=True,
                )
                thread.start()
                logger.info(f"WebSocket server started on ws://localhost:{self.port}")
            except ImportError:
                logger.debug("websockets not available, real-time updates disabled")
                self.enabled = False

        except Exception as exc:
            logger.debug(f"Could not start WebSocket server: {exc}")
            self.enabled = False

    def publish(self, data: Dict[str, Any]) -> None:
        """Publish a dashboard update to all subscribers."""
        with self._lock:
            self._latest_data = data

        for subscriber in self._subscribers:
            try:
                subscriber(data)
            except Exception as exc:
                logger.warning(f"Subscriber callback failed: {exc}")

    def subscribe(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Register a callback for dashboard updates."""
        self._subscribers.append(callback)

    def get_latest(self) -> Optional[Dict[str, Any]]:
        """Return the latest published data."""
        with self._lock:
            return self._latest_data


class QNADashboard:
    """Main dashboard aggregating all visualizations and metrics.

    Features:
        - Refresh button: Call refresh() to reload all data
        - Date range selector: Use set_date_range() to filter time periods
        - Portfolio summary: Use build_portfolio_summary() for holdings view
        - Risk metrics panel: Use build_risk_panel() for detailed risk analysis
        - Real-time updates: Enable via config={'realtime': True}
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.chart = ChartFactory(
            theme=self.config.get("theme", "dark"),
            width=self.config.get("width", 1200),
            height=self.config.get("height", 600),
        )
        self.metrics = DashboardMetrics()
        self._charts: Dict[str, Any] = {}
        self._date_range: DateRange = DateRange.all()
        self._last_refresh: Optional[datetime] = None
        self._refresh_callbacks: List[Callable[[], None]] = []
        self._raw_returns: Optional[pd.Series] = None
        self._raw_prices: Optional[pd.DataFrame] = None

        self._updater = RealtimeUpdater(
            enabled=self.config.get("realtime", False),
            port=self.config.get("ws_port", 8765),
        )

    # -- Refresh -------------------------------------------------------

    def register_refresh_callback(self, callback: Callable[[], None]) -> None:
        """Register a callback to be invoked on refresh."""
        self._refresh_callbacks.append(callback)

    def refresh(self) -> Dict[str, Any]:
        """Refresh all dashboard data.

        Triggers registered callbacks and re-computes metrics.
        Returns a status dict with refresh timestamp and affected panels.
        """
        self._last_refresh = datetime.now()

        for cb in self._refresh_callbacks:
            try:
                cb()
            except Exception as exc:
                logger.error(f"Refresh callback failed: {exc}")

        recomputed: Dict[str, bool] = {}
        if self._raw_returns is not None and len(self._raw_returns) > 0:
            filtered = self._apply_date_filter_returns(self._raw_returns)
            self.compute_metrics(filtered)
            recomputed["metrics"] = True

        if self._raw_prices is not None and not self._raw_prices.empty:
            filtered_returns = (
                self._apply_date_filter_returns(self._raw_returns)
                if self._raw_returns is not None
                else pd.Series(dtype=float)
            )
            filtered_prices = self._apply_date_filter_prices(self._raw_prices)
            self._charts = {
                "equity_curve": self.chart.equity_curve(filtered_returns),
                "drawdown": self.chart.drawdown_chart(filtered_returns),
                "distribution": self.chart.distribution_chart(filtered_returns),
                "price_chart": (
                    self.chart.ohlcv_chart(filtered_prices)
                    if not filtered_prices.empty
                    else None
                ),
            }
            recomputed["charts"] = True

        status = {
            "timestamp": self._last_refresh.isoformat(),
            "date_range": self._date_range.label,
            "recomputed": recomputed,
        }

        if self._updater.enabled:
            self._updater.publish({
                "type": "refresh",
                "status": status,
                "metrics": self.to_dict(),
            })

        logger.info(f"Dashboard refreshed at {status['timestamp']}")
        return status

    @property
    def last_refresh(self) -> Optional[datetime]:
        return self._last_refresh

    # -- Date Range ----------------------------------------------------

    def set_date_range(self, date_range: DateRange) -> None:
        """Set the dashboard date range filter."""
        self._date_range = date_range
        logger.info(
            f"Date range set to: {date_range.label} "
            f"({date_range.start} -> {date_range.end})"
        )

    def set_date_range_preset(self, preset: str) -> None:
        """Set date range from a preset string.

        Presets: '1d', '7d', '30d', '90d', 'ytd', '1y', 'all'
        """
        presets = {
            "1d": lambda: DateRange.last_n_days(1),
            "7d": lambda: DateRange.last_n_days(7),
            "30d": lambda: DateRange.last_n_days(30),
            "90d": lambda: DateRange.last_n_days(90),
            "ytd": DateRange.this_year,
            "1y": lambda: DateRange.last_n_days(365),
            "all": DateRange.all,
        }
        factory = presets.get(preset.lower())
        if factory:
            self._date_range = factory()
        else:
            logger.warning(f"Unknown date range preset: {preset}")

    @property
    def date_range(self) -> DateRange:
        return self._date_range

    def _apply_date_filter_returns(self, returns: pd.Series) -> pd.Series:
        """Filter returns series by date range."""
        if returns is None or returns.empty:
            return returns if returns is not None else pd.Series(dtype=float)

        if self._date_range.start:
            mask = returns.index >= pd.Timestamp(self._date_range.start)
            returns = returns[mask]
        if self._date_range.end:
            mask = returns.index <= pd.Timestamp(self._date_range.end)
            returns = returns[mask]
        return returns

    def _apply_date_filter_prices(self, prices: pd.DataFrame) -> pd.DataFrame:
        """Filter price DataFrame by date range."""
        if prices is None or prices.empty:
            return prices if prices is not None else pd.DataFrame()

        if self._date_range.start:
            prices = prices[prices.index >= pd.Timestamp(self._date_range.start)]
        if self._date_range.end:
            prices = prices[prices.index <= pd.Timestamp(self._date_range.end)]
        return prices

    # -- Metrics -------------------------------------------------------

    def compute_metrics(
        self, returns: pd.Series, risk_free_rate: float = 0.05
    ) -> DashboardMetrics:
        """Compute all portfolio metrics from returns."""
        self.metrics.total_return = (
            float((1 + returns).prod() - 1) if len(returns) > 0 else 0.0
        )

        n_years = len(returns) / 252 if len(returns) > 0 else 1.0
        self.metrics.annualized_return = (
            float((1 + self.metrics.total_return) ** (1 / n_years) - 1)
            if n_years > 0
            else 0.0
        )
        self.metrics.annualized_volatility = (
            float(returns.std() * np.sqrt(252)) if len(returns) > 0 else 0.0
        )

        excess = self.metrics.annualized_return - risk_free_rate
        self.metrics.sharpe_ratio = (
            float(excess / self.metrics.annualized_volatility)
            if self.metrics.annualized_volatility > 0
            else 0.0
        )

        neg_returns = returns[returns < 0]
        downside_std = (
            float(neg_returns.std() * np.sqrt(252))
            if len(neg_returns) > 0
            else 1.0
        )
        self.metrics.sortino_ratio = (
            float(excess / downside_std) if downside_std > 0 else 0.0
        )

        equity = (1 + returns).cumprod()
        running_max = equity.expanding().max()
        drawdowns = (equity - running_max) / running_max
        self.metrics.max_drawdown = float(drawdowns.min())
        self.metrics.calmar_ratio = (
            float(self.metrics.annualized_return / abs(self.metrics.max_drawdown))
            if self.metrics.max_drawdown < 0
            else 0.0
        )

        wins = returns[returns > 0]
        losses = returns[returns < 0]
        self.metrics.win_rate = float(len(wins) / max(len(returns), 1))
        self.metrics.profit_factor = (
            float(abs(wins.sum() / max(losses.sum(), 1e-10)))
            if len(losses) > 0
            else float("inf")
        )
        self.metrics.total_trades = len(returns)

        sorted_ret = np.sort(returns.values)
        n = len(sorted_ret)
        self.metrics.var_95 = float(np.percentile(sorted_ret, 5)) if n > 0 else 0.0
        self.metrics.cvar_95 = (
            float(np.mean(sorted_ret[: max(1, int(0.05 * n))])) if n > 0 else 0.0
        )

        return self.metrics

    def update_regime(self, regime: str) -> None:
        self.metrics.current_regime = regime

    def update_kelly(self, kelly_frac: float) -> None:
        self.metrics.kelly_fraction = kelly_frac

    # -- Overview ------------------------------------------------------

    def build_overview(
        self, returns: pd.Series, prices: pd.DataFrame
    ) -> Dict[str, Any]:
        """Build overview page with key charts."""
        self._raw_returns = returns
        self._raw_prices = prices

        filtered_returns = self._apply_date_filter_returns(returns)
        filtered_prices = self._apply_date_filter_prices(prices)

        self.compute_metrics(filtered_returns)

        self._charts = {
            "equity_curve": self.chart.equity_curve(filtered_returns),
            "drawdown": self.chart.drawdown_chart(filtered_returns),
            "distribution": self.chart.distribution_chart(filtered_returns),
            "price_chart": (
                self.chart.ohlcv_chart(filtered_prices)
                if not filtered_prices.empty
                else None
            ),
        }

        return {
            "metrics": {
                "total_return": f"{self.metrics.total_return*100:.2f}%",
                "sharpe": f"{self.metrics.sharpe_ratio:.2f}",
                "max_drawdown": f"{self.metrics.max_drawdown*100:.2f}%",
                "win_rate": f"{self.metrics.win_rate*100:.1f}%",
                "var_95": f"{self.metrics.var_95*100:.2f}%",
                "trades": self.metrics.total_trades,
                "regime": self.metrics.current_regime,
            },
            "charts": list(self._charts.keys()),
            "date_range": self._date_range.label,
            "last_refresh": (
                self._last_refresh.isoformat() if self._last_refresh else None
            ),
        }

    # -- Portfolio Summary Panel ----------------------------------------

    def build_portfolio_summary(
        self,
        positions: Optional[List[Dict[str, Any]]] = None,
        cash: float = 0.0,
    ) -> Dict[str, Any]:
        """Build portfolio summary panel.

        Args:
            positions: List of position dicts with keys: symbol, quantity,
                       entry_price, current_price.
            cash: Current cash balance.

        Returns:
            Portfolio summary dict with holdings table and aggregate stats.
        """
        summary = PortfolioSummary()
        pos_summaries: List[PositionSummary] = []

        if positions:
            for pos in positions:
                symbol = pos.get("symbol", "UNKNOWN")
                qty = float(pos.get("quantity", 0))
                entry = float(pos.get("entry_price", 0))
                current = float(pos.get("current_price", entry))

                market_value = qty * current
                unrealized_pnl = qty * (current - entry)
                unrealized_pnl_pct = (
                    (current - entry) / entry if entry > 0 else 0.0
                )

                pos_summaries.append(PositionSummary(
                    symbol=symbol,
                    quantity=qty,
                    entry_price=entry,
                    current_price=current,
                    market_value=market_value,
                    unrealized_pnl=unrealized_pnl,
                    unrealized_pnl_pct=unrealized_pnl_pct,
                    weight=0.0,
                ))

            total_invested = sum(p.market_value for p in pos_summaries)
            total_equity = total_invested + cash

            if total_equity > 0:
                for p in pos_summaries:
                    p.weight = p.market_value / total_equity

            summary.total_equity = total_equity
            summary.cash = cash
            summary.invested = total_invested
            summary.positions = pos_summaries
            summary.num_positions = len(pos_summaries)

            if pos_summaries:
                summary.largest_position_pct = max(p.weight for p in pos_summaries)
                weights = np.array([p.weight for p in pos_summaries])
                summary.concentration_index = float(np.sum(weights ** 2))

        holdings = []
        for p in summary.positions:
            pnl_class = "positive" if p.unrealized_pnl >= 0 else "negative"
            holdings.append({
                "symbol": p.symbol,
                "qty": p.quantity,
                "entry": f"${p.entry_price:.2f}",
                "current": f"${p.current_price:.2f}",
                "pnl": f"${p.unrealized_pnl:.2f}",
                "pnl_pct": f"{p.unrealized_pnl_pct*100:.2f}%",
                "pnl_class": pnl_class,
                "weight": f"{p.weight*100:.1f}%",
            })

        return {
            "total_equity": f"${summary.total_equity:,.2f}",
            "cash": f"${summary.cash:,.2f}",
            "invested": f"${summary.invested:,.2f}",
            "num_positions": summary.num_positions,
            "largest_position": f"{summary.largest_position_pct*100:.1f}%",
            "concentration_hhi": f"{summary.concentration_index:.4f}",
            "holdings": holdings,
        }

    # -- Risk Metrics Panel --------------------------------------------

    def build_risk_panel(
        self,
        stress_results: Optional[Dict[str, Any]] = None,
        additional_var: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Build detailed risk metrics panel.

        Args:
            stress_results: Optional stress test scenario results.
            additional_var: Optional additional VaR calculations
                           (e.g. {"var_99": -0.05, "var_90": -0.02}).

        Returns:
            Risk metrics panel dict.
        """
        risk_data: Dict[str, Any] = {
            "var_95": f"{self.metrics.var_95*100:.2f}%",
            "cvar_95": f"{self.metrics.cvar_95*100:.2f}%",
            "max_drawdown": f"{self.metrics.max_drawdown*100:.2f}%",
            "annualized_volatility": f"{self.metrics.annualized_volatility*100:.2f}%",
            "sortino_ratio": f"{self.metrics.sortino_ratio:.2f}",
            "calmar_ratio": f"{self.metrics.calmar_ratio:.2f}",
            "profit_factor": (
                f"{self.metrics.profit_factor:.2f}"
                if self.metrics.profit_factor != float("inf")
                else "inf"
            ),
        }

        if additional_var:
            for label, value in additional_var.items():
                risk_data[label] = f"{value*100:.2f}%"

        if stress_results:
            scenarios = []
            for name, result in stress_results.items():
                if isinstance(result, dict):
                    scenarios.append({
                        "scenario": name,
                        "impact": result.get("impact", "N/A"),
                        "recovery": result.get("recovery", "N/A"),
                    })
                else:
                    scenarios.append({"scenario": name, "impact": str(result)})
            risk_data["stress_scenarios"] = scenarios

        risk_data["risk_score"] = self._compute_risk_score()

        return risk_data

    def _compute_risk_score(self) -> str:
        """Compute an overall risk score (low/medium/high/critical)."""
        dd = abs(self.metrics.max_drawdown)
        vol = self.metrics.annualized_volatility

        score = 0
        if dd > 0.20:
            score += 3
        elif dd > 0.10:
            score += 2
        elif dd > 0.05:
            score += 1

        if vol > 0.40:
            score += 3
        elif vol > 0.25:
            score += 2
        elif vol > 0.15:
            score += 1

        if score >= 5:
            return "critical"
        elif score >= 3:
            return "high"
        elif score >= 1:
            return "medium"
        return "low"

    # -- Kelly View ----------------------------------------------------

    def build_kelly_view(self, kelly_signals: List[Any]) -> Dict[str, Any]:
        """Build Kelly analysis view."""
        if not kelly_signals:
            return {"metrics": {}, "charts": []}

        fractions = [s.capped_fraction for s in kelly_signals]
        convictions = [s.conviction for s in kelly_signals]

        self._charts["kelly_fraction"] = self.chart.line_chart(
            {"Kelly Fraction": pd.Series(fractions)},
            title="Kelly Fraction Over Time",
        )

        return {
            "metrics": {
                "current_kelly": (
                    f"{fractions[-1]*100:.1f}%" if fractions else "N/A"
                ),
                "avg_conviction": (
                    f"{np.mean(convictions)*100:.1f}%" if convictions else "N/A"
                ),
                "max_kelly": (
                    f"{max(fractions)*100:.1f}%" if fractions else "N/A"
                ),
            },
            "charts": list(self._charts.keys()),
        }

    # -- Export --------------------------------------------------------

    def export_html(self, filename: str = "qna_dashboard.html") -> str:
        """Export dashboard as HTML."""
        if not HAS_PLOTLY:
            return json.dumps({"error": "Plotly not available"}, indent=2)

        html_parts = [
            '<html><head><title>QNA Dashboard</title>',
            '<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>',
            '<style>',
            'body { font-family: monospace; background: #1a1a2e; color: #e0e0e0; padding: 20px; }',
            '.metric { display: inline-block; background: #2a2a4e; padding: 15px; margin: 5px; border-radius: 5px; min-width: 120px; }',
            '.metric .value { font-size: 24px; font-weight: bold; color: #00d2ff; }',
            '.metric .label { font-size: 12px; color: #888; }',
            '.panel { background: #2a2a4e; padding: 20px; margin: 10px 0; border-radius: 8px; }',
            '.panel h3 { color: #00d2ff; margin-top: 0; }',
            '.refresh-btn { background: #00d2ff; color: #1a1a2e; border: none; padding: 10px 20px; border-radius: 5px; cursor: pointer; font-weight: bold; margin: 10px 0; }',
            '.refresh-btn:hover { background: #00b8d4; }',
            'table { border-collapse: collapse; width: 100%; }',
            'th, td { border: 1px solid #4a4a6e; padding: 8px; text-align: right; }',
            'th { background: #3a3a5e; color: #00d2ff; }',
            '.positive { color: #00e676; }',
            '.negative { color: #ff6b6b; }',
            '</style></head><body>',
            '<h1>QNA Dashboard</h1>',
            '<button class="refresh-btn" onclick="location.reload()">Refresh</button>',
            f'<span style="color:#888; margin-left:10px;">Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</span>',
        ]

        metrics = self.build_overview(pd.Series(), pd.DataFrame())["metrics"]
        html_parts.append('<h2>Portfolio Metrics</h2>')
        for k, v in metrics.items():
            html_parts.append(
                f'<div class="metric"><div class="value">{v}</div>'
                f'<div class="label">{k}</div></div>'
            )

        for name, chart in self._charts.items():
            if chart is not None and hasattr(chart, "to_html"):
                html_parts.append(
                    chart.to_html(full_html=False, include_plotlyjs=False)
                )

        html_parts.append("</body></html>")
        html_content = "\n".join(html_parts)

        with open(filename, "w") as f:
            f.write(html_content)

        logger.info(f"Dashboard exported to {filename}")
        return filename

    def to_dict(self) -> Dict[str, Any]:
        """Export dashboard state as dict (for API responses)."""
        return {
            "metrics": {
                "total_return": self.metrics.total_return,
                "sharpe_ratio": self.metrics.sharpe_ratio,
                "max_drawdown": self.metrics.max_drawdown,
                "win_rate": self.metrics.win_rate,
                "var_95": self.metrics.var_95,
                "regime": self.metrics.current_regime,
                "kelly": self.metrics.kelly_fraction,
            },
            "charts": list(self._charts.keys()),
            "date_range": self._date_range.label,
            "last_refresh": (
                self._last_refresh.isoformat() if self._last_refresh else None
            ),
            "timestamp": datetime.now().isoformat(),
        }
