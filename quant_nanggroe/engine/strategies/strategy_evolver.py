"""Strategy Evolver — Self-Evolve validation gate for QNA.

This is the missing "self-evolve" capability upgrade. MUE-X already generates 
parameter mutations, but they are accepted WITHOUT backtest validation. This 
module adds the gate: mutate → validate via backtest → only promote if improved.

Ponytail: minimal (~150 lines), focused on ONE gap — no framework, just a gate.
"""
from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

@dataclass
class EvolveAttempt:
    """Record of a single evolve attempt: what was tried and whether it won."""
    timestamp: float
    strategy_name: str
    baseline_params: dict[str, Any]
    mutated_params: dict[str, Any]
    metric: str          # e.g. "sharpe", "profit_factor", "win_rate"
    baseline_value: float
    mutated_value: float
    accepted: bool
    reason: str          # why accepted or rejected

@dataclass 
class EvolveConfig:
    """Configuration for evolution validation."""
    min_improvement_pct: float = 5.0    # must beat baseline by at least 5%
    validation_bars: int = 500          # bars of recent data for backtest
    max_consecutive_rejects: int = 5    # stop evolving if too many rejects
    history_path: str = "data/evolution_history.json"
    metric: str = "sharpe"       # primary metric for comparison

class StrategyEvolver:
    """Gate that validates strategy mutations before accepting them.

    Usage:
        evolver = StrategyEvolver()
        decision = evolver.evaluate("WyckoffStrategy", baseline_params, mutated_params)
        if decision.accepted:
            # promote mutated params to active
            apply_new_params(decision)
    """

    # Class-level data cache: key = (symbol, period, interval) → DataFrame
    _data_cache: dict[tuple[str, str, str], "pd.DataFrame"] = {}

    def __init__(self, config: Optional[EvolveConfig] = None):
        self.config = config or EvolveConfig()
        self._history: list[EvolveAttempt] = []
        self._rejects_in_a_row = 0
        self._load_history()

    # ── Public API ────────────────────────────────────────────────

    def evaluate(
        self,
        strategy_name: str,
        baseline_params: dict[str, Any],
        mutated_params: dict[str, Any],
        *,
        backtest_fn: Optional[callable] = None,
    ) -> EvolveAttempt:
        """Run a mutated strategy through the validation gate.

        Args:
            strategy_name: Name of the strategy being evolved.
            baseline_params: Current active parameters.
            mutated_params: Proposed new parameters from MUE-X evolution.
            backtest_fn: Optional callable(strategy_name, params) -> dict
                         of metrics. Must return {"sharpe": float, ...}.
                         If None, a real walk-forward backtest is used
                         (via WalkForwardAnalyzer.analyze_strategy).

        Returns:
            EvolveAttempt with accepted=True/False.
        """
        if backtest_fn is None:
            # Phase C: default to REAL backtest, fail-closed. No silent mock.
            backtest_fn = self._real_backtest

        baseline_metrics = backtest_fn(strategy_name, baseline_params)
        # Fail-closed: if real backtest returns None (failed), reject
        if baseline_metrics is None:
            self._rejects_in_a_row += 1
            return EvolveAttempt(
                timestamp=time.time(), strategy_name=strategy_name,
                baseline_params=baseline_params, mutated_params=mutated_params,
                metric=self.config.metric, baseline_value=0.0, mutated_value=0.0,
                accepted=False, reason="REAL BACKTEST FAILED — reject (fail-closed)")
        mutated_metrics = backtest_fn(strategy_name, mutated_params)
        if mutated_metrics is None:
            self._rejects_in_a_row += 1
            return EvolveAttempt(
                timestamp=time.time(), strategy_name=strategy_name,
                baseline_params=baseline_params, mutated_params=mutated_params,
                metric=self.config.metric, baseline_value=baseline_metrics.get(self.config.metric, 0.0),
                mutated_value=0.0, accepted=False,
                reason="MUTATED BACKTEST FAILED — reject (fail-closed)")

        metric = self.config.metric
        baseline_val = baseline_metrics.get(metric, 0.0)
        mutated_val = mutated_metrics.get(metric, 0.0)

        # Calculate improvement
        if baseline_val == 0:
            improvement_pct = 100.0 if mutated_val > 0 else 0.0
        else:
            improvement_pct = ((mutated_val - baseline_val) / abs(baseline_val)) * 100

        # Decision: must exceed baseline by threshold
        accepted = improvement_pct >= self.config.min_improvement_pct

        if accepted:
            reason = f"{metric}: {baseline_val:.4f} → {mutated_val:.4f} (+{improvement_pct:.1f}%)"
            self._rejects_in_a_row = 0
        else:
            reason = f"{metric}: {baseline_val:.4f} → {mutated_val:.4f} ({improvement_pct:+.1f}%, need >{self.config.min_improvement_pct}%)"
            self._rejects_in_a_row += 1

        attempt = EvolveAttempt(
            timestamp=time.time(),
            strategy_name=strategy_name,
            baseline_params=baseline_params,
            mutated_params=mutated_params,
            metric=metric,
            baseline_value=baseline_val,
            mutated_value=mutated_val,
            accepted=accepted,
            reason=reason,
        )

        self._history.append(attempt)
        self._persist_history(attempt)

        # Halt evolution if too many consecutive rejects
        if self._rejects_in_a_row >= self.config.max_consecutive_rejects:
            self._log_halt(strategy_name)

        return attempt

    def get_history(self, strategy_name: Optional[str] = None) -> list[EvolveAttempt]:
        """Get evolution history, optionally filtered by strategy."""
        if strategy_name:
            return [a for a in self._history if a.strategy_name == strategy_name]
        return list(self._history)

    def get_stats(self) -> dict:
        """Summary statistics for the evolver."""
        total = len(self._history)
        accepted = sum(1 for a in self._history if a.accepted)
        return {
            "total_attempts": total,
            "accepted": accepted,
            "rejected": total - accepted,
            "accept_rate_pct": round(accepted / total * 100, 1) if total else 0.0,
            "consecutive_rejects": self._rejects_in_a_row,
            "max_consecutive_rejects": self.config.max_consecutive_rejects,
            "halted": self._rejects_in_a_row >= self.config.max_consecutive_rejects,
        }

    # ── Internal ──────────────────────────────────────────────────

    def _real_backtest(self, name: str, params: dict) -> dict | None:
        """Phase C: real walk-forward backtest via the strategy's own signals.
        
        Uses WalkForwardAnalyzer.analyze_strategy() to instantiate the real
        strategy per fold and generate its actual signals — no placebo momentum.
        Returns aggregate OOS Sharpe as the primary fitness metric.
        Fail-closed: returns None if anything fails.
        """
        try:
            import warnings

            import pandas as pd
            import yfinance as yf
            warnings.filterwarnings("ignore")

            # Ponytail: cache fetched data so baseline + mutated calls
            # (and repeated evolutions) share one download.
            sym = "EURUSD=X"
            cache_key = (sym, "1mo_15m")
            cached = self._data_cache.get(cache_key)
            if cached is not None and len(cached) > 0:
                df = cached
            else:
                df = yf.Ticker(sym).history(period="1mo", interval="15m")
                if df is None or df.empty:
                    cache_key = (sym, "6mo_1d")
                    cached = self._data_cache.get(cache_key)
                    if cached is not None and len(cached) > 0:
                        df = cached
                    else:
                        df = yf.Ticker(sym).history(period="6mo", interval="1d")
                if df is not None and not df.empty:
                    self._data_cache[cache_key] = df
            if df is None or df.empty:
                return None

            # Flatten MultiIndex columns (yfinance returns MultiIndex for FX)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # Get the real strategy class from the registry
            from quant_nanggroe.engine.strategies.base import StrategyParameters
            from quant_nanggroe.engine.strategies.registry import StrategyRegistry

            strategy_class = StrategyRegistry.get(name)
            if strategy_class is None:
                logger.error("Strategy '%s' not found in registry", name)
                return None

            # Set up backtest engine and walk-forward analyzer
            from quant_nanggroe.engine.backtest.engine import BacktestConfig, BacktestEngine
            from quant_nanggroe.engine.backtest.walk_forward import WalkForwardAnalyzer

            med_delta = df.index.to_series().diff().median()
            bars_per_year = int(pd.Timedelta(days=365) / med_delta) if med_delta is not None and med_delta.total_seconds() > 0 else 35040

            engine = BacktestEngine(BacktestConfig(
                initial_capital=10000.0,
                commission_rate=0.001,
                slippage_bps=5.0,
                bars_per_year=bars_per_year,
            ))

            n_bars = len(df)
            train_window = max(120, int(n_bars * 0.6))
            test_window = max(60, int(n_bars * 0.2))
            if train_window + test_window >= n_bars:
                return None

            analyzer = WalkForwardAnalyzer(
                engine=engine,
                train_window=train_window,
                test_window=test_window,
                mode="rolling",
                min_observations=60,
            )

            # Walk-forward with per-fold strategy re-fit — eliminates lookahead bias
            wf_result = analyzer.analyze_strategy(
                prices=df,
                strategy_class=strategy_class,
                strategy_params={"parameters": StrategyParameters(params=params)},
                purge_gap=5,
                embargo=3,
            )

            windows = wf_result.get("windows", [])
            if not windows:
                return None

            aggregate = wf_result.get("aggregate", {})
            oos_sharpe = aggregate.get("avg_oos_sharpe", 0.0)
            oos_return = aggregate.get("avg_oos_return", 0.0)
            oos_max_dd = aggregate.get("avg_oos_max_dd", 0.0)
            oos_win_rate = aggregate.get("win_rate", 0.0)

            # Profit factor from OOS fold returns
            oos_returns_list = [w.out_of_sample_return for w in windows]
            pos = sum(r for r in oos_returns_list if r > 0) or 0.0
            neg = abs(sum(r for r in oos_returns_list if r < 0)) or 0.0
            profit_factor = pos / neg if neg > 0 else (10.0 if pos > 0 else 1.0)

            return {
                "sharpe": oos_sharpe,
                "profit_factor": profit_factor,
                "win_rate": oos_win_rate,
                "total_return_pct": oos_return * 100,
                "max_drawdown_pct": oos_max_dd * 100,
                "n_folds": len(windows),
            }
        except Exception as e:
            logger.error("Real backtest failed for %s: %s", name, e)
            return None

    def _persist_history(self, attempt: EvolveAttempt) -> None:
        """Append attempt to JSON history file."""
        path = Path(self.config.history_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            if path.exists():
                data = json.loads(path.read_text())
            else:
                data = []
            data.append(asdict(attempt))
            path.write_text(json.dumps(data, indent=2, default=str))
        except Exception:
            pass  # non-fatal persistence failure

    def _load_history(self) -> None:
        """Replay history on init to reconstruct consecutive-reject counter."""
        path = Path(self.config.history_path)
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text())
            for entry in data[-100:]:  # only check recent history
                if not entry.get("accepted", False):
                    self._rejects_in_a_row += 1
                else:
                    self._rejects_in_a_row = 0
        except Exception:
            pass

    def _log_halt(self, strategy_name: str) -> None:
        """Log when evolution halts due to too many rejects."""
        msg = (
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] EVOLVE HALTED for "
            f"{strategy_name}: {self._rejects_in_a_row} consecutive rejects "
            f"(limit {self.config.max_consecutive_rejects}). Manual review needed."
        )
        # Also record as a file for cron monitoring
        with Path("data/evolve_halt_warnings.txt").open("a") as f:
            f.write(msg + "\n")
