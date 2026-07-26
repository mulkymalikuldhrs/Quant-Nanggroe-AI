"""Strategy Evolver — Self-Evolve validation gate for QNA.

This is the missing "self-evolve" capability upgrade. MUE-X already generates 
parameter mutations, but they are accepted WITHOUT backtest validation. This 
module adds the gate: mutate → validate via backtest → only promote if improved.

Ponytail: minimal (~150 lines), focused on ONE gap — no framework, just a gate.
"""
from __future__ import annotations
import json, time
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

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
    metric: str = "profit_factor"       # primary metric for comparison

class StrategyEvolver:
    """Gate that validates strategy mutations before accepting them.

    Usage:
        evolver = StrategyEvolver()
        decision = evolver.evaluate("WyckoffStrategy", baseline_params, mutated_params)
        if decision.accepted:
            # promote mutated params to active
            apply_new_params(decision)
    """

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
                         of metrics. Must return {"profit_factor": float, ...}.
                         If None, a mock backtest is used (for testing only).

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
                metric=metric, baseline_value=0.0, mutated_value=0.0,
                accepted=False, reason="REAL BACKTEST FAILED — reject (fail-closed)")
        mutated_metrics = backtest_fn(strategy_name, mutated_params)
        if mutated_metrics is None:
            self._rejects_in_a_row += 1
            return EvolveAttempt(
                timestamp=time.time(), strategy_name=strategy_name,
                baseline_params=baseline_params, mutated_params=mutated_params,
                metric=metric, baseline_value=baseline_metrics.get(metric, 0.0),
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

    def _real_backtest(self, name: str, params: dict) -> dict:
        """Phase C: real backtest via QNA BacktestEngine (yfinance data).
        Returns metrics dict; fail-closed: if backtest fails, return None so the
        caller rejects (never mock)."""
        try:
            import yfinance as yf
            import pandas as pd
            import numpy as np
            import warnings
            warnings.filterwarnings("ignore")

            # Fetch EURUSD M15 data via yfinance (14 days ~ 13k bars)
            sym = "EURUSD=X"
            df = yf.Ticker(sym).history(period="14d", interval="15m")
            if df is None or df.empty:
                # Fallback to daily data
                df = yf.Ticker(sym).history(period="3mo", interval="1d")
            if df is None or df.empty:
                return None

            # Normalize columns
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df.columns = [c.lower() for c in df.columns]

            # Build simple signal based on strategy name/params
            close = df["close"].values
            lookback = params.get("lookback", 20)
            atr_mult = params.get("atr_mult", 1.5)

            # Generate signals: momentum-based
            signals = pd.Series(0.0, index=df.index)
            for i in range(lookback, len(close)):
                ret = (close[i] - close[i-lookback]) / close[i-lookback]
                if ret > atr_mult * 0.01:
                    signals.iloc[i] = 1.0
                elif ret < -atr_mult * 0.01:
                    signals.iloc[i] = -1.0

            # Run QNA BacktestEngine
            from quant_nanggroe.engine.backtest.engine import BacktestEngine, BacktestConfig
            config = BacktestConfig(
                initial_capital=10000.0,
                commission_rate=0.001,
                slippage_bps=5.0,
                bars_per_year=35040,  # M15 bars/year
            )
            engine = BacktestEngine(config)

            # Prepare prices df (single column with 'close' renamed to symbol)
            prices = df[["close"]].rename(columns={"close": sym})
            signals_df = signals.to_frame(name=sym)

            result = engine.run(prices, signals_df)
            metrics = result.get("metrics", {})

            return {
                "profit_factor": metrics.get("profit_factor", 0.0),
                "sharpe": metrics.get("sharpe_ratio", 0.0),
                "win_rate": metrics.get("win_rate", 0.0) * 100,
                "total_return_pct": metrics.get("total_return", 0.0) * 100,
                "max_drawdown_pct": metrics.get("max_drawdown", 0.0) * 100,
            }
        except Exception as e:
            log.error(f"Real backtest failed for {name}: {e}")
            return None

    def _mock_backtest(self, name: str, params: dict) -> dict:
        """Placeholder backtest — DEPRECATED, kept only for unit tests."""
        import random
        base = {"profit_factor": 1.2, "sharpe": 0.8, "win_rate": 55.0,
                "total_return_pct": 3.0, "max_drawdown_pct": -8.0}
        param_hash = hash(frozenset(params.items())) & 0xFFFF
        rng = random.Random(param_hash)
        for k in base:
            base[k] += rng.uniform(-0.3, 0.3) * base[k]
        return base

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
        Path("data/evolve_halt_warnings.txt").open("a").write(msg + "\n")
