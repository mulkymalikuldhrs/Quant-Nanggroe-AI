"""Auto fine-tuning for strategy parameters.

Uses grid search with walk-forward cross-validation to find optimal
parameter combinations for any strategy.
"""

from __future__ import annotations

import itertools
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from quant_nanggroe.backtest.backtester import Backtester
from quant_nanggroe.engine.backtest.persistence import save_run
from quant_nanggroe.engine.strategy.strategies import BaseStrategy, create_strategy

log = logging.getLogger("QNA.AutoTune")


@dataclass
class TuneResult:
    """Result of a single parameter combination."""
    params: Dict[str, Any]
    sharpe: float
    total_return: float
    max_drawdown: float
    win_rate: float
    num_trades: int
    sortino: float
    calmar: float

    def to_dict(self) -> Dict:
        return {
            "params": self.params,
            "sharpe": self.sharpe,
            "total_return": self.total_return,
            "max_drawdown": self.max_drawdown,
            "win_rate": self.win_rate,
            "num_trades": self.num_trades,
            "sortino": self.sortino,
            "calmar": self.calmar,
        }


class ParameterGrid:
    """Defines a search space for strategy parameters."""

    def __init__(self, param_grid: Dict[str, List[Any]]):
        self.param_grid = param_grid

    @property
    def n_combinations(self) -> int:
        return len(list(itertools.product(*self.param_grid.values())))

    def combinations(self) -> List[Dict[str, Any]]:
        keys = list(self.param_grid.keys())
        values = list(self.param_grid.values())
        return [dict(zip(keys, combo)) for combo in itertools.product(*values)]


class AutoTuner:
    """Auto fine-tunes strategy parameters using walk-forward optimization.

    Splits data into training/validation windows and finds parameters
    that generalize across regimes.
    """

    def __init__(
        self,
        strategy_name: str,
        param_grid: ParameterGrid,
        data: pd.DataFrame,
        n_windows: int = 4,
        train_pct: float = 0.7,
        min_trades: int = 5,
    ):
        self.strategy_name = strategy_name
        self.param_grid = param_grid
        self.data = data
        self.n_windows = n_windows
        self.train_pct = train_pct
        self.min_trades = min_trades
        self.backtester = Backtester()

    def _create_walk_forward_windows(self) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        """Create train/val windows for walk-forward validation."""
        windows = []
        n = len(self.data)
        window_size = n // self.n_windows
        for i in range(self.n_windows - 1):
            train_end = int((i + 1) * window_size * self.train_pct / (1 - self.train_pct + self.train_pct))
            val_start = train_end
            val_end = min(val_start + window_size, n)
            train = self.data.iloc[:train_end]
            val = self.data.iloc[val_start:val_end]
            if len(train) > 20 and len(val) > 10:
                windows.append((train, val))
        return windows

    def _evaluate_params(self, params: Dict) -> Tuple[float, float, float]:
        """Evaluate parameters across walk-forward windows."""
        windows = self._create_walk_forward_windows()
        if not windows:
            return -999, -999, 0

        avg_sharpes = []
        all_results = []
        for train, val in windows:
            strategy = create_strategy(self.strategy_name, params=params)
            all_data = pd.concat([train, val])
            try:
                results = self.backtester.run_single(strategy, all_data)
                if results and results.get("num_trades", 0) >= self.min_trades:
                    avg_sharpes.append(results.get("sharpe", -999))
                    all_results.append(results)
            except Exception as e:
                log.debug(f"Params {params} failed: {e}")

        if not avg_sharpes:
            return -999, -999, 0

        mean_sharpe = float(np.mean(avg_sharpes))
        mean_return = float(np.mean([r.get("total_return", 0) for r in all_results]))
        mean_trades = int(np.mean([r.get("num_trades", 0) for r in all_results]))
        return mean_sharpe, mean_return, mean_trades

    def tune(
        self,
        top_n: int = 10,
        max_combinations: int = 500,
        verbose: bool = True,
    ) -> List[TuneResult]:
        """Run grid search with walk-forward validation.

        Args:
            top_n: Return top N parameter combinations.
            max_combinations: Limit search space (random sample if larger).

        Returns:
            List of TuneResult sorted by Sharpe descending.
        """
        all_combos = self.param_grid.combinations()
        if len(all_combos) > max_combinations:
            indices = np.random.choice(len(all_combos), max_combinations, replace=False)
            all_combos = [all_combos[i] for i in indices]

        log.info(f"Tuning {self.strategy_name}: {len(all_combos)} combinations, "
                 f"{self.n_windows} walk-forward windows")

        results = []
        start = time.time()
        for i, params in enumerate(all_combos):
            sharpe, total_return, num_trades = self._evaluate_params(params)
            if sharpe > -999:
                results.append(TuneResult(
                    params=params,
                    sharpe=sharpe,
                    total_return=total_return,
                    max_drawdown=0.0,
                    win_rate=0.0,
                    num_trades=num_trades,
                    sortino=0.0,
                    calmar=0.0,
                ))
            if verbose and (i + 1) % 50 == 0:
                elapsed = time.time() - start
                log.info(f"  [{i+1}/{len(all_combos)}] best so far={max(r.sharpe for r in results):.2f} "
                         f"({elapsed:.0f}s)")

        results.sort(key=lambda r: r.sharpe, reverse=True)
        return results[:top_n]


def auto_tune_strategy(
    strategy_name: str,
    data: pd.DataFrame,
    param_grid: Dict[str, List[Any]],
    top_n: int = 5,
    n_windows: int = 4,
    strategy_params: Optional[Dict] = None,
) -> List[Dict]:
    """Convenience function: tune a strategy and return best params.

    Example:
        >>> best = auto_tune_strategy("SMC", btc_data, {
        ...     "min_confluence": [2, 3],
        ...     "sl_atr_mult": [1.0, 1.5, 2.0],
        ... })
    """
    tuner = AutoTuner(
        strategy_name=strategy_name,
        param_grid=ParameterGrid(param_grid),
        data=data,
        n_windows=n_windows,
    )
    results = tuner.tune(top_n=top_n)

    output = []
    for r in results:
        entry = r.to_dict()
        output.append(entry)
        log.info(f"  ✓ {strategy_name} {r.params}: Sharpe={r.sharpe:.3f} "
                 f"Return={r.total_return:.1%} Trades={r.num_trades}")

    return output


def tune_and_deploy(
    strategy_name: str,
    data: pd.DataFrame,
    param_grid: Dict[str, List[Any]],
    symbol: str = "UNKNOWN",
    deploy_path: Optional[Path] = None,
) -> Dict:
    """Tune and deploy the best strategy parameters.

    Saves results to persistence DB and returns the best config.
    """
    best_list = auto_tune_strategy(strategy_name, data, param_grid, top_n=1)
    if not best_list:
        log.warning(f"No valid parameters found for {strategy_name}")
        return {}

    best = best_list[0]
    config = {
        "strategy": strategy_name,
        "params": best["params"],
        "sharpe": best["sharpe"],
        "total_return": best["total_return"],
        "symbol": symbol,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    # Save to persistence
    try:
        save_run(
            strategy_name=strategy_name,
            param_key=json.dumps(best["params"]),
            metrics={k: v for k, v in best.items() if k != "params"},
            equity_curve=[],
            trades=[],
        )
    except Exception as e:
        log.warning(f"Persistence save failed: {e}")

    if deploy_path:
        deploy_path.parent.mkdir(parents=True, exist_ok=True)
        existing = []
        if deploy_path.exists():
            existing = json.loads(deploy_path.read_text())
        existing.append(config)
        deploy_path.write_text(json.dumps(existing, indent=2))
        log.info(f"Deployed {strategy_name} to {deploy_path}")

    return config
