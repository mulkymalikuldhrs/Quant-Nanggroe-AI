"""PerformanceScanner — calculate strategy metrics from journal trade data."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Optional

from quant_nanggroe.engine.evolution.evolution_journal import EvolutionJournal


class PerformanceScanner:
    """Calculate performance metrics for strategies from trade data.

    Uses closed trade PnL series from the journal. All metrics are
    computed from realized trades only (no open positions).
    """

    def __init__(self, journal: Optional[EvolutionJournal] = None) -> None:
        self._journal = journal or EvolutionJournal()

    def scan_strategy(
        self, strategy_name: str, timeframe: str = "", regime: str | None = None
    ) -> dict[str, Any]:
        """Return performance metrics for a strategy.

        If regime is provided, only trades matching that regime_label
        are considered.

        Returns dict with:
            strategy_name, timeframe, trade_count, sharpe, sortino,
            win_rate, profit_factor, max_drawdown, avg_return,
            total_pnl, avg_win, avg_loss, payoff_ratio
        """
        trades = self._journal.get_recent_trades(strategy_name, limit=1000, regime=regime)
        if not trades:
            return {
                "strategy_name": strategy_name,
                "timeframe": timeframe,
                "trade_count": 0,
                "sharpe": 0.0,
                "sortino": 0.0,
                "win_rate": 0.0,
                "profit_factor": 0.0,
                "max_drawdown": 0.0,
                "avg_return": 0.0,
                "total_pnl": 0.0,
            }

        pnls = [t.get("pnl", 0.0) or 0.0 for t in trades]
        # Use pnl_pct for returns if available, else pnl
        returns = [t.get("pnl_pct", t.get("pnl", 0.0)) or 0.0 for t in trades]
        trade_count = len(trades)
        total_pnl = sum(pnls)

        # Win / loss breakdown
        wins = [r for r in returns if r > 0]
        losses = [r for r in returns if r <= 0]
        win_count = len(wins)

        win_rate = win_count / trade_count if trade_count else 0.0

        avg_win = (sum(wins) / len(wins)) if wins else 0.0
        avg_loss = (sum(losses) / len(losses)) if losses else 0.0

        profit_factor = abs(sum(wins) / sum(losses)) if sum(losses) != 0 else (
            float("inf") if sum(wins) > 0 else 0.0
        )

        payoff_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0.0

        # Sharpe-like: annualized if we had timeframe, else raw
        avg_return = sum(returns) / trade_count if trade_count else 0.0
        std = self._std(returns)
        sharpe = (avg_return / std) if std > 0 else 0.0

        # Sortino: downside deviation only
        downside = [r for r in returns if r < 0]
        downside_std = self._std(downside) if downside else 0.0
        sortino = (avg_return / downside_std) if downside_std > 0 else 0.0

        # Max drawdown — cumulative return peak-to-trough
        max_dd = self._max_drawdown(returns)

        return {
            "strategy_name": strategy_name,
            "timeframe": timeframe,
            "trade_count": trade_count,
            "sharpe": round(sharpe, 4),
            "sortino": round(sortino, 4),
            "win_rate": round(win_rate, 4),
            "profit_factor": round(profit_factor, 4),
            "max_drawdown": round(max_dd, 4),
            "avg_return": round(avg_return, 4),
            "total_pnl": round(total_pnl, 4),
            "avg_win": round(avg_win, 4),
            "avg_loss": round(avg_loss, 4),
            "payoff_ratio": round(payoff_ratio, 4),
        }

    def scan_all(
        self, strategy_names: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Scan multiple strategies and return sorted results.

        If strategy_names is None, aggregates from journal's all_trades.
        """
        if strategy_names:
            return sorted(
                (self.scan_strategy(name) for name in strategy_names),
                key=lambda r: r["sharpe"],
                reverse=True,
            )
        # Infer strategy names from journal
        trades = self._journal.all_trades(limit=5000)
        names = sorted({t.get("strategy", "") for t in trades if t.get("strategy")})
        return [self.scan_strategy(n) for n in names]

    # ── Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _std(values: list[float]) -> float:
        n = len(values)
        if n < 2:
            return 0.0
        mean = sum(values) / n
        variance = sum((v - mean) ** 2 for v in values) / (n - 1)
        return math.sqrt(variance) if variance > 0 else 0.0

    @staticmethod
    def _max_drawdown(returns: list[float]) -> float:
        """Compute max drawdown from cumulative return series."""
        if not returns:
            return 0.0
        cum = 0.0
        peak = 0.0
        max_dd = 0.0
        for r in returns:
            cum += r
            if cum > peak:
                peak = cum
            dd = peak - cum
            if dd > max_dd:
                max_dd = dd
        return max_dd

    # ── Regime-stratified scanning ──────────────────────────────────

    @staticmethod
    def _vix_bucket(vix: float | None) -> str:
        if vix is None:
            return "unknown"
        if vix < 15:
            return "low"
        if vix < 25:
            return "normal"
        if vix < 35:
            return "elevated"
        return "high"

    @staticmethod
    def _fear_greed_bucket(fg: int | None) -> str:
        if fg is None:
            return "unknown"
        if fg < 20:
            return "extreme_fear"
        if fg < 40:
            return "fear"
        if fg < 60:
            return "neutral"
        if fg < 80:
            return "greed"
        return "extreme_greed"

    @staticmethod
    def _killzone_from_ts(timestamp: str | None) -> str:
        if not timestamp:
            return "unknown"
        try:
            hour = datetime.fromisoformat(timestamp).hour
        except (ValueError, TypeError):
            return "unknown"
        if hour < 8:
            return "asian"
        if hour < 13:
            return "london"
        if hour < 17:
            return "ny_overlap"
        return "ny_afternoon"

    def _metrics_from_rows(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        """Compute standard metrics from a list of trade rows."""
        if not rows:
            return {"trade_count": 0, "sharpe": 0.0, "win_rate": 0.0, "avg_r": 0.0}

        returns = [r.get("pnl_pct", r.get("pnl", 0.0)) or 0.0 for r in rows]
        pnls = [r.get("pnl", 0.0) or 0.0 for r in rows]
        r_mults = [r.get("r_multiple") for r in rows if r.get("r_multiple") is not None]

        n = len(rows)
        wins = [v for v in returns if v > 0]
        win_rate = len(wins) / n if n else 0.0

        avg_return = sum(returns) / n if n else 0.0
        std = self._std(returns)
        sharpe = (avg_return / std) if std > 0 else 0.0

        avg_r = sum(r_mults) / len(r_mults) if r_mults else 0.0
        total_pnl = sum(pnls)

        return {
            "trade_count": n,
            "sharpe": round(sharpe, 4),
            "win_rate": round(win_rate, 4),
            "avg_return": round(avg_return, 4),
            "total_pnl": round(total_pnl, 4),
            "avg_r": round(avg_r, 4),
        }

    def scan_by_regime(
        self, strategy_name: str, dimension: str = "vix_bucket",
        regime: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return per-regime metrics for a strategy.

        If regime is provided, filter to trades matching that regime_label
        before bucketing by dimension.

        Supported dimensions:
            vix_bucket      — low / normal / elevated / high
            fear_greed_bucket — extreme_fear / fear / neutral / greed / extreme_greed
            regime_label    — raw label from pipeline (e.g. 'bullish', 'bearish', 'ranging')
            killzone        — asian / london / ny_overlap / ny_afternoon
        """
        trades = self._journal.get_recent_trades(strategy_name, limit=2000, regime=regime)
        if not trades:
            return []

        buckets: dict[str, list[dict[str, Any]]] = {}
        for t in trades:
            if dimension == "vix_bucket":
                key = self._vix_bucket(t.get("vix"))
            elif dimension == "fear_greed_bucket":
                key = self._fear_greed_bucket(t.get("fear_greed"))
            elif dimension == "killzone":
                key = self._killzone_from_ts(t.get("timestamp"))
            elif dimension == "regime_label":
                key = t.get("regime_label") or "unknown"
            else:
                key = str(t.get(dimension, "unknown"))
            buckets.setdefault(key, []).append(t)

        result = []
        for label, group in sorted(buckets.items()):
            metrics = self._metrics_from_rows(group)
            metrics["dimension"] = dimension
            metrics["bucket"] = label
            metrics["strategy_name"] = strategy_name
            result.append(metrics)
        return result

    def scan_by_combo(
        self,
        strategy_name: str,
        dims: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Return metrics grouped by dimension combination (multi-dim slice).

        Default dims: ['regime_label', 'killzone']
        """
        if dims is None:
            dims = ["regime_label", "killzone"]

        trades = self._journal.get_recent_trades(strategy_name, limit=2000)
        if not trades:
            return []

        groups: dict[str, list[dict[str, Any]]] = {}
        for t in trades:
            parts: list[str] = []
            for d in dims:
                if d == "vix_bucket":
                    parts.append(self._vix_bucket(t.get("vix")))
                elif d == "fear_greed_bucket":
                    parts.append(self._fear_greed_bucket(t.get("fear_greed")))
                elif d == "killzone":
                    parts.append(self._killzone_from_ts(t.get("timestamp")))
                elif d == "regime_label":
                    parts.append(t.get("regime_label") or "unknown")
                else:
                    parts.append(str(t.get(d, "unknown")))
            key = "|".join(parts)
            groups.setdefault(key, []).append(t)

        result = []
        for combo, group in sorted(groups.items()):
            metrics = self._metrics_from_rows(group)
            metrics["combo_dims"] = dims
            metrics["combo"] = combo
            metrics["strategy_name"] = strategy_name
            result.append(metrics)
        return result

    def scan_all_by_regime(
        self, strategy_names: list[str], dimension: str = "vix_bucket"
    ) -> dict[str, list[dict[str, Any]]]:
        """Run scan_by_regime for multiple strategies. Returns {strategy: [metrics]}."""
        return {name: self.scan_by_regime(name, dimension) for name in strategy_names}
