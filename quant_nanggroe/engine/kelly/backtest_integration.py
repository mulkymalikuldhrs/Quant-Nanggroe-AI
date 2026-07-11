"""
Kelly-Backtest Integration Module
Bridges position sizing strategies with backtest execution engine.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.kelly.base import KellyParameters, KellyResult
from quant_nanggroe.engine.kelly.bayesian import BayesianKelly
from quant_nanggroe.engine.kelly.drawdown import DrawdownControlledKelly
from quant_nanggroe.engine.kelly.fractional import FractionalKelly

logger = logging.getLogger(__name__)


@dataclass
class KellySignal:
    """Output from Kelly calculator for a single period."""
    timestamp: datetime
    symbol: str
    raw_kelly_fraction: float
    capped_fraction: float
    conviction: float
    regime: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class KellyBacktestBridge:
    """
    Bridge that injects Kelly position sizing into a backtest strategy.

    Wraps any base strategy and:
    1. Computes optimal Kelly fraction at each step
    2. Adjusts position sizes accordingly
    3. Tracks Kelly-derived risk metrics
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        self.config = config or {}
        self.default_fraction = self.config.get("default_fraction", 0.5)
        self.window = self.config.get("window", 63)
        self.min_samples = self.config.get("min_samples", 30)
        self.max_leverage = self.config.get("max_leverage", 1.0)
        self.regime_multipliers: Dict[str, float] = {
            "bull": self.config.get("bull_multiplier", 1.0),
            "bear": self.config.get("bear_multiplier", 0.5),
            "drawdown": self.config.get("drawdown_multiplier", 0.25),
            "high_volatility": self.config.get("high_vol_multiplier", 0.3),
            "sideways": self.config.get("sideways_multiplier", 0.6),
        }

        self._fractional = FractionalKelly(fraction=self.default_fraction)
        self._bayesian = BayesianKelly()
        self._drawdown = DrawdownControlledKelly(base_fraction=self.default_fraction)

        self._history: List[KellySignal] = []

    def compute_signals(
        self,
        prices: pd.DataFrame,
        returns: pd.Series,
        equity: float,
        regime: Optional[str] = None,
    ) -> List[KellySignal]:
        """
        Compute Kelly-based position sizing signals.

        Args:
            prices: Price DataFrame with DatetimeIndex and symbol columns.
            returns: Return Series for the primary asset.
            equity: Current portfolio equity.
            regime: Optional market regime label.

        Returns:
            List of KellySignal objects, one per symbol in prices.
        """
        if prices.empty or returns.empty:
            logger.warning("Empty price/returns data — returning empty signals")
            return []

        symbols = list(prices.columns)
        signals: List[KellySignal] = []

        for symbol in symbols:
            signal = self._compute_single_signal(
                symbol=symbol,
                prices=prices[symbol] if symbol in prices.columns else pd.Series(),
                returns=returns,
                equity=equity,
                regime=regime,
            )
            signals.append(signal)

        self._history.extend(signals)
        return signals

    def _compute_single_signal(
        self,
        symbol: str,
        prices: pd.Series,
        returns: pd.Series,
        equity: float,
        regime: Optional[str] = None,
    ) -> KellySignal:
        """Compute a single KellySignal for one symbol."""
        n = len(returns)
        if n < 2:
            return self._fallback_signal(symbol, equity, regime or "unknown")

        recent = returns.iloc[-self.window:] if n > self.window else returns
        n_effective = len(recent)

        wins = recent[recent > 0]
        losses = recent[recent < 0]

        win_rate = len(wins) / n_effective if n_effective > 0 else 0.0
        avg_win = float(wins.mean()) if len(wins) > 0 else 0.0
        avg_loss = float(abs(losses.mean())) if len(losses) > 0 else 1.0

        regime_label = regime or self._infer_regime(recent)
        regime_mult = self.regime_multipliers.get(regime_label, 1.0)

        params = KellyParameters(
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            fraction=self.default_fraction,
            leverage_max=self.max_leverage,
            regime_multiplier=regime_mult,
            volatility=float(recent.std()) if n_effective > 1 else None,
        )

        result: KellyResult

        if regime_label == "drawdown":
            drawdown = self._estimate_drawdown(prices)
            params.current_drawdown = drawdown
            self._drawdown.base_fraction = self.default_fraction
            result = self._drawdown.compute(params)
            conviction = self._conviction_score(n_effective, regime_label, win_rate)
        elif n_effective < self.min_samples:
            result = self._bayesian.compute(params)
            conviction = self._conviction_score(n_effective, regime_label, win_rate)
        else:
            result = self._fractional.compute(params)
            conviction = self._conviction_score(n_effective, regime_label, win_rate)

        raw = result.f_star
        capped = max(0.0, min(raw, self.max_leverage))

        metadata = {
            "win_rate": round(win_rate, 4),
            "avg_win": round(avg_win, 6),
            "avg_loss": round(avg_loss, 6),
            "method": result.method.value,
            "growth_rate": round(result.growth_rate, 6) if result.growth_rate != -np.inf else None,
            "n_samples": n_effective,
        }

        ts = prices.index[-1] if isinstance(prices.index, pd.DatetimeIndex) and len(prices) > 0 else datetime.now()

        return KellySignal(
            timestamp=ts,
            symbol=symbol,
            raw_kelly_fraction=raw,
            capped_fraction=capped,
            conviction=conviction,
            regime=regime_label,
            metadata=metadata,
        )

    def _fallback_signal(
        self, symbol: str, equity: float, regime: str
    ) -> KellySignal:
        """Return a safe fallback signal when data is insufficient."""
        return KellySignal(
            timestamp=datetime.now(),
            symbol=symbol,
            raw_kelly_fraction=0.0,
            capped_fraction=0.0,
            conviction=0.0,
            regime=regime,
            metadata={"reason": "insufficient_data"},
        )

    def _infer_regime(self, returns: pd.Series) -> str:
        """Infer market regime from recent returns."""
        if len(returns) < 10:
            return "sideways"

        recent = returns.iloc[-10:]
        cumulative = recent.sum()
        vol = recent.std() * np.sqrt(252)

        if cumulative > 0.05:
            return "bull"
        elif cumulative < -0.05:
            return "bear"
        elif vol > 0.4:
            return "high_volatility"
        else:
            return "sideways"

    def _estimate_drawdown(self, prices: pd.Series) -> float:
        """Estimate current drawdown from peak."""
        if len(prices) < 2:
            return 0.0
        rolling_max = prices.expanding().max()
        dd = (prices - rolling_max) / rolling_max
        return float(abs(dd.iloc[-1])) if not dd.empty else 0.0

    def _conviction_score(
        self, n_samples: int, regime: str, win_rate: float
    ) -> float:
        """
        Compute a 0.0-1.0 conviction score.

        Factors: sample size, regime clarity, win rate stability.
        """
        sample_score = min(1.0, n_samples / 252)
        regime_penalty = 0.3 if regime in ("drawdown", "high_volatility") else 0.0
        wr_score = 0.5 + abs(win_rate - 0.5)
        score = (sample_score * 0.5 + wr_score * 0.3) * (1.0 - regime_penalty * 0.4)
        return max(0.0, min(1.0, score))

    @property
    def signal_history(self) -> List[KellySignal]:
        """Return all computed signals."""
        return list(self._history)

    def reset_history(self) -> None:
        """Clear signal history."""
        self._history.clear()


class StrategyKellyMixin:
    """Mixin to add Kelly position sizing to any backtest strategy."""

    kelly_bridge: KellyBacktestBridge

    def __init__(self, kelly_config: Optional[Dict[str, Any]] = None, **kwargs: Any) -> None:
        self.kelly_bridge = KellyBacktestBridge(config=kelly_config or {})
        super().__init__(**kwargs)

    def adjust_position_size(
        self,
        base_size: float,
        prices: pd.DataFrame,
        returns: pd.Series,
        equity: float,
    ) -> float:
        """
        Adjust a base position size using the Kelly bridge.

        Args:
            base_size: Original position size (notional or shares).
            prices: Price DataFrame for Kelly signal computation.
            returns: Return Series for Kelly signal computation.
            equity: Current portfolio equity.

        Returns:
            Adjusted position size scaled by the Kelly capped fraction.
        """
        signals = self.kelly_bridge.compute_signals(prices, returns, equity)
        if signals:
            return base_size * signals[0].capped_fraction
        return base_size
