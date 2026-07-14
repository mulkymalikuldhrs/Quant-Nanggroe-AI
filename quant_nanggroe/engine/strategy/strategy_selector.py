"""Adaptive strategy selector.

Selects the best strategy(ies) for current market conditions based on:
- Market regime (bull/bear/sideways/volatile)
- Recent strategy performance (rolling Sharpe)
- Strategy-regime compatibility matrix
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.loader import create_strategy
from quant_nanggroe.engine.strategies.registry import (
    get_strategy_metadata,
    list_strategies,
)

log = logging.getLogger("QNA.StrategySelector")


class StrategySelector:
    """Selects optimal strategy(ies) for current market conditions.

    Maintains a performance history per strategy and selects based on
    regime compatibility + recent track record.

    Parameters:
        performance_window (int): Number of signals to track per strategy (default 20)
        min_signals (int): Min signals before strategy is eligible (default 3)
        top_n (int): Number of strategies to select (default 3)
        enable_auto_tune (bool): Auto-tune params on deploy (default False)
    """

    # Regime compatibility matrix: strategy_category -> regime -> suitability (0-1)
    REGIME_MATRIX = {
        "mean_reversion": {
            "ranging": 0.9, "volatile": 0.3, "bullish": 0.4, "bearish": 0.4,
            "crisis": 0.1,
        },
        "momentum": {
            "bullish": 0.9, "bearish": 0.7, "ranging": 0.2, "volatile": 0.5,
            "crisis": 0.1,
        },
        "pairs_trading": {
            "ranging": 0.7, "volatile": 0.6, "bullish": 0.5, "bearish": 0.5,
            "crisis": 0.3,
        },
        "volatility": {
            "volatile": 0.9, "crisis": 0.8, "ranging": 0.2, "bullish": 0.3,
            "bearish": 0.5,
        },
        "statistical_arbitrage": {
            "ranging": 0.8, "volatile": 0.6, "bullish": 0.5, "bearish": 0.5,
            "crisis": 0.2,
        },
        "market_making": {
            "ranging": 0.8, "bullish": 0.4, "bearish": 0.4, "volatile": 0.7,
            "crisis": 0.3,
        },
        "regime_detection": {
            "bullish": 0.7, "bearish": 0.7, "ranging": 0.6, "volatile": 0.6,
            "crisis": 0.5,
        },
        "crypto": {
            "bullish": 0.8, "bearish": 0.6, "volatile": 0.8, "ranging": 0.3,
            "crisis": 0.2,
        },
        "pattern": {
            "ranging": 0.7, "bullish": 0.6, "bearish": 0.6, "volatile": 0.5,
            "crisis": 0.2,
        },
        "supply_demand": {
            "ranging": 0.8, "bullish": 0.6, "bearish": 0.6, "volatile": 0.5,
            "crisis": 0.3,
        },
        "wyckoff": {
            "ranging": 0.6, "bullish": 0.8, "bearish": 0.7, "volatile": 0.4,
            "crisis": 0.3,
        },
        "cot": {
            "bullish": 0.6, "bearish": 0.6, "ranging": 0.5, "volatile": 0.3,
            "crisis": 0.1,
        },
        "fundamental": {
            "bullish": 0.7, "bearish": 0.7, "ranging": 0.6, "volatile": 0.8,
            "crisis": 0.5,
        },
    }

    def __init__(
        self,
        performance_window: int = 20,
        min_signals: int = 3,
        top_n: int = 3,
        enable_auto_tune: bool = False,
    ):
        self.performance_window = performance_window
        self.min_signals = min_signals
        self.top_n = top_n
        self.enable_auto_tune = enable_auto_tune
        self._performance: Dict[str, List[float]] = defaultdict(list)
        self._trades: Dict[str, int] = defaultdict(int)
        self._wins: Dict[str, int] = defaultdict(int)
        self._losses: Dict[str, int] = defaultdict(int)

    def record_outcome(self, strategy_name: str, pnl: float):
        """Record a trade outcome for a strategy."""
        self._performance[strategy_name].append(pnl)
        if len(self._performance[strategy_name]) > self.performance_window:
            self._performance[strategy_name].pop(0)
        self._trades[strategy_name] += 1
        if pnl > 0:
            self._wins[strategy_name] += 1
        else:
            self._losses[strategy_name] += 1

    def get_sharpe(self, strategy_name: str) -> float:
        """Compute rolling Sharpe ratio for a strategy."""
        pnls = self._performance.get(strategy_name, [])
        if len(pnls) < self.min_signals:
            return 0.0
        mean_pnl = np.mean(pnls)
        std_pnl = np.std(pnls)
        if std_pnl < 1e-10:
            return 0.0
        return float(mean_pnl / std_pnl) * np.sqrt(252)

    def get_win_rate(self, strategy_name: str) -> float:
        """Compute win rate for a strategy."""
        total = self._trades.get(strategy_name, 0)
        if total == 0:
            return 0.0
        return self._wins.get(strategy_name, 0) / total

    def _detect_category(self, strategy_name: str) -> str:
        """Detect strategy category from name or metadata."""
        try:
            meta = get_strategy_metadata(strategy_name)
            return meta.get("category", "pattern")
        except ValueError:
            pass
        name_lower = strategy_name.lower()
        if "mean" in name_lower or "reversion" in name_lower:
            return "mean_reversion"
        if "momentum" in name_lower or "trend" in name_lower:
            return "momentum"
        if "pairs" in name_lower:
            return "pairs_trading"
        if "volatility" in name_lower or "arb" in name_lower:
            return "volatility"
        if "market" in name_lower:
            return "market_making"
        if "regime" in name_lower:
            return "regime_detection"
        if "crypto" in name_lower or "btc" in name_lower:
            return "crypto"
        if "smc" in name_lower or "ict" in name_lower:
            return "pattern"
        if "support" in name_lower or "resistance" in name_lower or "sr" == name_lower:
            return "supply_demand"
        if "supply" in name_lower or "demand" in name_lower or "snd" == name_lower:
            return "supply_demand"
        if "wyckoff" in name_lower:
            return "wyckoff"
        if "cot" in name_lower:
            return "cot"
        if "fundamental" in name_lower or "fund" in name_lower:
            return "fundamental"
        return "pattern"

    def score_strategy(
        self,
        strategy_name: str,
        regime: str,
    ) -> float:
        """Score a strategy for current regime + performance."""
        category = self._detect_category(strategy_name)
        regime_score = self.REGIME_MATRIX.get(category, {}).get(regime, 0.3)

        sharpe = self.get_sharpe(strategy_name)
        perf_score = min(max(sharpe, 0), 2.0) / 2.0  # Normalize to 0-1

        win_rate = self.get_win_rate(strategy_name)
        wr_score = win_rate

        # Combined: 50% regime fit, 30% recent Sharpe, 20% win rate
        total = regime_score * 0.5 + perf_score * 0.3 + wr_score * 0.2
        return round(total, 3)

    def select(
        self,
        regime: str,
        available_strategies: Optional[List[str]] = None,
    ) -> List[Tuple[str, float]]:
        """Select top N strategies for current regime.

        Args:
            regime: Current market regime string.
            available_strategies: Subset to consider (default: all registered).

        Returns:
            List of (strategy_name, score) tuples sorted by score descending.
        """
        candidates = available_strategies or list_strategies()
        scored = []
        for name in candidates:
            score = self.score_strategy(name, regime)
            scored.append((name, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:self.top_n]

    def get_execution_weights(
        self,
        regime: str,
        available_strategies: Optional[List[str]] = None,
    ) -> Dict[str, float]:
        """Get execution weights for selected strategies.

        Returns dict of strategy_name -> allocation weight (sums to 1.0).
        """
        selected = self.select(regime, available_strategies)
        if not selected:
            return {}
        total_score = sum(s for _, s in selected)
        if total_score <= 0:
            return {name: 1.0 / len(selected) for name, _ in selected}
        weights = {}
        for name, score in selected:
            weights[name] = score / total_score
        return weights

    def get_performance_summary(self) -> Dict[str, Dict]:
        """Get performance summary for all tracked strategies."""
        summary = {}
        for name in list(self._performance.keys()):
            summary[name] = {
                "sharpe": round(self.get_sharpe(name), 3),
                "win_rate": round(self.get_win_rate(name), 3),
                "total_trades": self._trades.get(name, 0),
                "wins": self._wins.get(name, 0),
                "losses": self._losses.get(name, 0),
            }
        return summary


class AdaptiveStrategyEngine:
    """Combines strategy selector with multi-timeframe and regime detection.

    This is the top-level engine that:
    1. Gets current market regime
    2. Selects best strategies
    3. Runs them with multi-timeframe alignment
    4. Returns combined signals
    """

    def __init__(
        self,
        selector: Optional[StrategySelector] = None,
        regime_engine: Optional[object] = None,
    ):
        self.selector = selector or StrategySelector()
        self.regime_engine = regime_engine

    def get_regime(self, data: pd.DataFrame) -> str:
        """Get current market regime."""
        if self.regime_engine:
            try:
                state = self.regime_engine.detect(data)
                if hasattr(state, 'regime'):
                    return state.regime.lower()
                if isinstance(state, dict):
                    return state.get('regime', 'unknown').lower()
            except Exception as e:
                log.warning(f"Regime detection failed: {e}")

        # Fallback: simple trend detection
        close = data["close"].values
        if len(close) < 20:
            return "unknown"
        sma_short = np.mean(close[-5:])
        sma_long = np.mean(close[-20:])
        returns = np.diff(close[-20:]) / close[-20:-1]
        vol = np.std(returns)
        if vol > np.mean(returns) * 4:
            return "volatile"
        if sma_short > sma_long * 1.02:
            return "bullish"
        elif sma_short < sma_long * 0.98:
            return "bearish"
        return "ranging"

    def generate_signals(
        self,
        data: pd.DataFrame,
        htf_data: Optional[pd.DataFrame] = None,
        mtf_data: Optional[pd.DataFrame] = None,
    ) -> Dict[str, object]:
        """Generate signals using adaptive strategy selection.

        Args:
            data: Main timeframe data (used for regime + LTF).
            htf_data: Higher timeframe data (for MTF alignment).
            mtf_data: Medium timeframe data (for MTF alignment).

        Returns:
            Dict with selected strategies, signals, and regime info.
        """
        regime = self.get_regime(data)
        selected = self.selector.select(regime)

        signals = {}
        for name, score in selected:
            try:
                strategy = create_strategy(name)
                ltf_data = data

                if htf_data is not None and mtf_data is not None:
                    from quant_nanggroe.engine.strategy.multi_timeframe import (
                        MultiTimeframeStrategy,
                    )
                    mtf = MultiTimeframeStrategy(
                        strategy=strategy,
                        htf_data=htf_data,
                        mtf_data=mtf_data,
                        ltf_data=ltf_data,
                    )
                    signal = mtf.align_signals()
                else:
                    signal = strategy.generate_signal(data)

                if signal:
                    signals[name] = {
                        "signal": signal,
                        "score": score,
                        "regime": regime,
                    }
            except Exception as e:
                log.warning(f"Strategy {name} failed: {e}")

        return {
            "regime": regime,
            "selected_strategies": [n for n, _ in selected],
            "signals": signals,
            "num_signals": len(signals),
        }
