"""Regime-Based Strategy.

HMM-driven regime detection with per-regime strategy switching,
transaction cost modeling, and trade frequency controls.

Regimes: 0=bull, 1=bear, 2=range_bound, 3=high_vol.

References:
    - Hamilton, J.D. (1989). "A New Approach to the Economic Analysis of
      Nonstationary Time Series and the Business Cycle." Econometrica.
    - Rabiner, L.R. (1989). "A Tutorial on Hidden Markov Models."
      Proceedings of the IEEE, 77(2), 257-286.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)

try:
    from hmmlearn import hmm
    HMM_AVAILABLE = True
except ImportError:
    HMM_AVAILABLE = False

REGIME_LABELS = {0: "bull", 1: "bear", 2: "range_bound", 3: "high_vol"}


class RegimeBasedStrategy(BaseStrategy):
    """HMM-driven regime detection with per-regime switching and cost controls.

    Signal: float in [-1, 1] -> SignalType + confidence. >0 = BUY, <0 = SELL, 0 = flat.

    Parameters:
        n_regimes: 2-4 (default 3). hmm_lookback: training window (default 252).
        covariance_type: HMM cov type (default "full").
        regime_stability_bars: min bars before regime switch acted on (default 5).
        bull_strategy/bear_strategy/range_strategy/high_vol_strategy: per-regime behavior.
        max_position: max |position| in [-1,1] (default 1.0).
        transaction_cost_bps: one-way cost bps (default 10.0).
        min_trade_interval_bars: min bars between trades (default 3).
        symbol: for Signal (default "ASSET").
    """

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="RegimeBased", params=params)
        p = self.params
        self.n_regimes: int = max(2, min(int(p.get("n_regimes", 3)), 4))
        self.hmm_lookback: int = int(p.get("hmm_lookback", 252))
        self.covariance_type: str = str(p.get("covariance_type", "full"))
        self.regime_stability_bars: int = int(p.get("regime_stability_bars", 5))
        self.bull_strategy: str = str(p.get("bull_strategy", "momentum"))
        self.bear_strategy: str = str(p.get("bear_strategy", "defensive"))
        self.range_strategy: str = str(p.get("range_strategy", "mean_reversion"))
        self.high_vol_strategy: str = str(p.get("high_vol_strategy", "reduce"))
        self.max_position: float = float(p.get("max_position", 1.0))
        self.transaction_cost_bps: float = float(p.get("transaction_cost_bps", 10.0))
        self.min_trade_interval_bars: int = int(p.get("min_trade_interval_bars", 3))
        self.symbol: str = str(p.get("symbol", "ASSET"))

        self._hmm_model: Optional[hmm.GaussianHMM] = None
        self._regime_history: List[int] = []
        self._state_to_regime: Optional[Dict[int, int]] = None
        self._last_trade_bar: int = -self.min_trade_interval_bars
        self._current_position: float = 0.0

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return self.hmm_lookback + 10

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None

        regime = self.detect_regime(data)
        raw_signal = self._regime_signal(regime, data)
        cost = self.transaction_cost_bps / 10000.0

        if abs(raw_signal) < cost * 2 or abs(raw_signal) < 1e-10:
            if abs(raw_signal) < 1e-10 and self._current_position != 0.0:
                return self._exit_signal(data)
            return None

        idx = len(data) - 1
        if idx - self._last_trade_bar < self.min_trade_interval_bars:
            return None
        if abs(raw_signal - self._current_position) < 0.01:
            return None

        self._last_trade_bar = idx
        self._current_position = raw_signal

        return Signal(
            symbol=self.symbol,
            signal_type=SignalType.BUY if raw_signal > 0 else SignalType.SELL,
            confidence=round(min(abs(raw_signal), 1.0), 4),
            price=round(float(data["close"].iloc[-1]), 6),
            source_agent=self.name,
            source_strategy=self.name,
            reasoning=f"Regime {REGIME_LABELS.get(regime, '?')}: signal={raw_signal:.4f} cost={cost:.4f}",
            evidence={
                "regime": REGIME_LABELS.get(regime, "unknown"),
                "raw_signal": round(raw_signal, 4),
                "transaction_cost_bps": self.transaction_cost_bps,
            },
            factors=["regime_based", REGIME_LABELS.get(regime, "unknown")],
        )

    def detect_regime(self, data: pd.DataFrame) -> int:
        regime = self._detect_hmm(data) if HMM_AVAILABLE else self._detect_fallback(data)
        self._regime_history.append(regime)

        limit = 2 * self.regime_stability_bars
        if len(self._regime_history) > limit:
            self._regime_history = self._regime_history[-limit:]

        if len(self._regime_history) < self.regime_stability_bars:
            return regime

        recent = self._regime_history[-self.regime_stability_bars:]
        if len(set(recent)) == 1:
            return recent[0]
        return max(set(recent), key=recent.count)

    def _detect_hmm(self, data: pd.DataFrame) -> int:
        if self._hmm_model is None and not self._fit_hmm(data):
            return self._detect_fallback(data)

        features = self._compute_features(data)
        if len(features) < 10:
            return 2

        try:
            state = int(self._hmm_model.predict(features)[-1])
            return self._state_to_regime.get(state, 2) if self._state_to_regime else state
        except Exception as exc:
            logger.warning("HMM predict failed: %s", exc)
            return self._detect_fallback(data)

    def _detect_fallback(self, data: pd.DataFrame) -> int:
        close = data["close"]
        returns = close.pct_change().dropna()
        if len(returns) < 20:
            return 2

        r = float(returns.iloc[-20:].mean()) * 252
        v = float(returns.iloc[-20:].std()) * np.sqrt(252)
        lt_v = float(returns.std()) * np.sqrt(252) if len(returns) > 50 else v
        hv = v > lt_v * 1.5

        if hv and self.n_regimes >= 4:
            return 3
        if r > 0.05 and not hv:
            return 0
        if r < -0.05 and not hv:
            return 1
        return 2

    def _compute_features(self, data: pd.DataFrame) -> np.ndarray:
        close = data["close"]
        returns = close.pct_change().dropna()
        if len(returns) < 20:
            return np.array([]).reshape(0, 2)
        log_ret = np.log(1 + returns)
        vol = log_ret.rolling(21, min_periods=10).std()
        features = pd.DataFrame({"ret": log_ret, "vol": vol}).dropna()
        return features.values if len(features) >= 10 else np.array([]).reshape(0, 2)

    def _fit_hmm(self, data: pd.DataFrame) -> bool:
        features = self._compute_features(data)
        if len(features) < 30:
            return False
        try:
            model = hmm.GaussianHMM(
                n_components=self.n_regimes,
                covariance_type=self.covariance_type,
                n_iter=100, random_state=42, tol=1e-4,
            )
            model.startprob_ = np.ones(self.n_regimes) / self.n_regimes
            model.transmat_ = np.full((self.n_regimes, self.n_regimes), 0.05)
            np.fill_diagonal(model.transmat_, 0.9)
            model.transmat_ /= model.transmat_.sum(axis=1, keepdims=True)

            nf = features.shape[1]
            model.means_ = np.zeros((self.n_regimes, nf))
            if nf >= 1:
                for i in range(self.n_regimes):
                    t = i / (self.n_regimes - 1) if self.n_regimes > 1 else 0.5
                    model.means_[i, 0] = -0.001 + t * 0.002

            model.fit(features)
            self._hmm_model = model
            self._label_regimes(features)
            return True
        except Exception as exc:
            logger.warning("HMM fit failed: %s", exc)
            return False

    def _label_regimes(self, features: np.ndarray) -> None:
        """Map HMM states to semantic regimes by sorting on mean return."""
        try:
            states = self._hmm_model.predict(features)
            state_returns = {s: [] for s in range(self.n_regimes)}
            for t, s in enumerate(states):
                state_returns[s].append(features[t, 0])
            means = {s: np.mean(v) for s, v in state_returns.items() if v}
            sorted_states = sorted(means, key=means.get, reverse=True)

            m = {sorted_states[0]: 0, sorted_states[-1]: 1}
            if self.n_regimes >= 3:
                m[sorted_states[1]] = 2
            if self.n_regimes >= 4:
                m[(sorted_states[2:-1] or [sorted_states[2]])[0]] = 3
            self._state_to_regime = m
        except Exception as exc:
            logger.warning("Regime labeling failed: %s", exc)
            self._state_to_regime = {i: min(i, 3) if i < 4 else 2 for i in range(self.n_regimes)}

    def _regime_signal(self, regime: int, data: pd.DataFrame) -> float:
        close = data["close"]
        if regime == 0:
            sma = self.compute_sma(close, 20)
            if len(sma) < 2 or np.isnan(sma.iloc[-1]):
                return 0.0
            ratio = float(close.iloc[-1]) / sma.iloc[-1]
            return self.max_position * min((ratio - 1.0) * 10, 1.0) if ratio > 1.0 else 0.0
        if regime == 1:
            sma = self.compute_sma(close, 20)
            if len(sma) < 2 or np.isnan(sma.iloc[-1]):
                return 0.0
            ratio = float(close.iloc[-1]) / sma.iloc[-1]
            return -self.max_position * min((1.0 - ratio) * 10, 1.0) if ratio < 1.0 else 0.0
        if regime == 2:
            rsi = self.compute_rsi(close, 14)
            if len(rsi) < 1 or np.isnan(rsi.iloc[-1]):
                return 0.0
            crsi = float(rsi.iloc[-1])
            if crsi < 30:
                return self.max_position * 0.5
            if crsi > 70:
                return -self.max_position * 0.5
        return 0.0

    def _exit_signal(self, data: pd.DataFrame) -> Signal:
        exit_type = SignalType.CLOSE_LONG if self._current_position > 0 else SignalType.CLOSE_SHORT
        prior = self._current_position
        self._current_position = 0.0
        self._last_trade_bar = len(data) - 1
        return Signal(
            symbol=self.symbol, signal_type=exit_type, confidence=0.7,
            price=round(float(data["close"].iloc[-1]), 6),
            source_agent=self.name, source_strategy=self.name,
            reasoning=f"RegimeBased EXIT (prior={prior:.3f})",
            evidence={"prior_position": round(float(prior), 4)},
            factors=["regime_based", "exit"],
        )
