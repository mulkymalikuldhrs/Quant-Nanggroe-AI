"""Regime-Based Strategy.

Implements production-quality regime detection and strategy switching using:
1. Hidden Markov Model (HMM) for regime identification
2. 3 regimes: trending up, trending down, mean-reverting
3. Strategy switching based on detected regime
4. Transition probability estimation
5. Viterbi algorithm for most likely state sequence

Academic References:
    - Hamilton, J.D. (1989). "A New Approach to the Economic Analysis of
      Nonstationary Time Series and the Business Cycle." Econometrica, 57(2), 357-384.
    - Hamilton, J.D. (1990). "Analysis of Time Series Subject to Structural Change."
      Journal of Policy Modeling, 12(2), 347-365.
    - Rabiner, L.R. (1989). "A Tutorial on Hidden Markov Models and Selected
      Applications in Speech Recognition." Proceedings of the IEEE, 77(2), 257-286.
    - Ang, A. & Bekaert, G. (2002). "Regime Switches in Interest Rates."
      Journal of Business & Economic Statistics, 20(2), 163-182.
"""

from __future__ import annotations

import logging

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

try:
    from hmmlearn.hmm import GaussianHMM
    HAS_HMMLEARN = True
except ImportError:
    HAS_HMMLEARN = False


class RegimeBasedStrategy(BaseStrategy):
    """Regime-based strategy using Hidden Markov Models.

    Detects market regimes using HMM on return features, then applies
    strategy logic appropriate for each regime:
    - Trending Up: momentum / trend following
    - Trending Down: short / defensive
    - Mean-Reverting: mean reversion / contrarian

    Parameters:
        n_regimes: Number of HMM regimes (default 3).
        lookback: Window for feature computation (default 60).
        hmm_iterations: Max iterations for HMM fitting (default 100).
        retrain_frequency: How often to retrain HMM, in bars (default 100).
        stop_loss_pct: Stop loss fraction (default 0.04).
        take_profit_pct: Take profit fraction (default 0.10).
        confidence_threshold: Minimum regime probability for signal (default 0.6).
        symbol: Trading symbol (default "ASSET").
    """

    # Regime labels
    TRENDING_UP = 0
    TRENDING_DOWN = 1
    MEAN_REVERTING = 2

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="RegimeBased", params=params)
        self.n_regimes: int = self.params.get("n_regimes", 3)
        self.lookback: int = self.params.get("lookback", 60)
        self.hmm_iterations: int = self.params.get("hmm_iterations", 100)
        self.retrain_frequency: int = self.params.get("retrain_frequency", 100)
        self.stop_loss_pct: float = self.params.get("stop_loss_pct", 0.04)
        self.take_profit_pct: float = self.params.get("take_profit_pct", 0.10)
        self.confidence_threshold: float = self.params.get("confidence_threshold", 0.6)
        self.symbol: str = self.params.get("symbol", "ASSET")

        self._hmm_model: Optional[GaussianHMM] = None
        self._last_train_idx: int = 0
        self._current_regime: int = -1
        self._regime_probs: Optional[np.ndarray] = None

    def required_columns(self) -> List[str]:
        return ["open", "high", "low", "close", "volume"]

    def warmup_period(self) -> int:
        return self.lookback + 30

    def _compute_features(self, data: pd.DataFrame) -> np.ndarray:
        """Compute features for HMM regime detection.

        Features:
        1. Returns (log)
        2. Realized volatility (rolling)
        3. Return skewness (rolling)
        4. Volume change (log)

        Args:
            data: OHLCV DataFrame.

        Returns:
            Feature matrix (n_samples x n_features).
        """
        close = data["close"]
        returns = close.pct_change().dropna()

        if len(returns) < 20:
            return np.array([]).reshape(0, 4)

        # Log returns
        log_returns = np.log(1 + returns)

        # Rolling realized volatility (21-day)
        rolling_vol = log_returns.rolling(21, min_periods=10).std()

        # Rolling skewness (21-day)
        rolling_skew = log_returns.rolling(21, min_periods=10).skew()

        # Volume change
        if "volume" in data.columns:
            volume = data["volume"]
            vol_change = np.log(1 + volume.pct_change().clip(-0.99, 10))
        else:
            vol_change = pd.Series(0, index=returns.index)

        # Align all features
        features = pd.DataFrame({
            "returns": log_returns,
            "volatility": rolling_vol,
            "skewness": rolling_skew,
            "volume_change": vol_change,
        }).dropna()

        if len(features) < 10:
            return np.array([]).reshape(0, 4)

        return features.values

    def fit_hmm(self, data: pd.DataFrame) -> bool:
        """Fit Hidden Markov Model on return features.

        Uses Gaussian HMM with full covariance matrices.
        Initializes means to encourage separation:
        - Regime 0 (Trending Up): positive mean return
        - Regime 1 (Trending Down): negative mean return
        - Regime 2 (Mean-Reverting): near-zero mean, lower vol

        Reference:
            Hamilton (1989), Econometrica, 57(2), 357-384.

        Args:
            data: OHLCV DataFrame.

        Returns:
            True if model was fitted successfully.
        """
        if not HAS_HMMLEARN:
            # Fallback: use simple regime detection
            return self._fit_simple_regime(data)

        features = self._compute_features(data)
        if len(features) < 30:
            return False

        try:
            model = GaussianHMM(
                n_components=self.n_regimes,
                covariance_type="full",
                n_iter=self.hmm_iterations,
                random_state=42,
                tol=1e-4,
            )

            # Initialize with reasonable starting values
            n_features = features.shape[1]
            model.startprob_ = np.ones(self.n_regimes) / self.n_regimes
            model.transmat_ = np.ones((self.n_regimes, self.n_regimes)) * 0.05
            np.fill_diagonal(model.transmat_, 0.9)
            # Normalize rows
            model.transmat_ /= model.transmat_.sum(axis=1, keepdims=True)

            model.means_ = np.zeros((self.n_regimes, n_features))
            if n_features >= 1:
                model.means_[0, 0] = 0.001   # Trending up: positive return
                model.means_[1, 0] = -0.001  # Trending down: negative return
                model.means_[2, 0] = 0.0     # Mean-reverting: flat
            if n_features >= 2:
                model.means_[2, 1] = float(np.mean(features[:, 1])) * 0.5

            model.fit(features)
            self._hmm_model = model
            return True

        except Exception:
            return self._fit_simple_regime(data)

    def _fit_simple_regime(self, data: pd.DataFrame) -> bool:
        """Simple regime detection without hmmlearn.

        Uses rolling return and volatility to classify regimes.

        Args:
            data: OHLCV DataFrame.

        Returns:
            True (always succeeds).
        """
        self._hmm_model = None
        return True

    def detect_regime(self, data: pd.DataFrame) -> Tuple[int, np.ndarray]:
        """Detect the current market regime.

        Uses Viterbi algorithm to find the most likely state sequence,
        then returns the current state and state probabilities.

        Reference:
            Rabiner (1989), Proceedings of the IEEE, 77(2), 257-286.

        Args:
            data: OHLCV DataFrame.

        Returns:
            Tuple of (current_regime, regime_probabilities).
        """
        features = self._compute_features(data)

        if len(features) < 10:
            probs = np.ones(self.n_regimes) / self.n_regimes
            return 2, probs  # Default: mean-reverting

        if self._hmm_model is not None and HAS_HMMLEARN:
            try:
                # Predict current state using Viterbi
                states = self._hmm_model.predict(features)
                current_state = int(states[-1])

                # Compute state probabilities using forward algorithm
                post_probs = self._hmm_model.predict_proba(features)
                current_probs = post_probs[-1]

                self._current_regime = current_state
                self._regime_probs = current_probs
                return current_state, current_probs
            except Exception:
                logger.exception("unhandled_error")
                pass

        # Fallback: simple regime detection based on recent returns and volatility
        close = data["close"]
        returns = close.pct_change().dropna()

        if len(returns) < 20:
            return self.n_regimes - 1, np.ones(self.n_regimes) / self.n_regimes

        # Recent return
        recent_return = float(returns.iloc[-20:].mean()) * 252  # Annualized
        # Recent volatility
        recent_vol = float(returns.iloc[-20:].std()) * np.sqrt(252)
        # Long-term volatility
        lt_vol = float(returns.std()) * np.sqrt(252) if len(returns) > 50 else recent_vol

        # Classify
        probs = np.zeros(self.n_regimes)

        if self.n_regimes == 2:
            # Two regimes: trending up (0) and trending down (1)
            if recent_return > 0:
                probs[self.TRENDING_UP] = 0.7
                probs[self.TRENDING_DOWN] = 0.3
            else:
                probs[self.TRENDING_UP] = 0.3
                probs[self.TRENDING_DOWN] = 0.7
        else:
            # Three regimes: trending up, trending down, mean-reverting
            mr_idx = min(self.MEAN_REVERTING, self.n_regimes - 1)
            if recent_return > 0.05 and recent_vol < lt_vol * 1.2:
                # Trending up: positive return, normal or low vol
                probs[self.TRENDING_UP] = 0.6
                probs[mr_idx] = 0.3
                probs[self.TRENDING_DOWN] = 0.1
            elif recent_return < -0.05 and recent_vol < lt_vol * 1.2:
                # Trending down: negative return, normal or low vol
                probs[self.TRENDING_DOWN] = 0.6
                probs[mr_idx] = 0.3
                probs[self.TRENDING_UP] = 0.1
            elif recent_vol > lt_vol * 1.5:
                # High volatility: mean-reverting regime
                probs[mr_idx] = 0.5
                if recent_return > 0:
                    probs[self.TRENDING_UP] = 0.3
                    probs[self.TRENDING_DOWN] = 0.2
                else:
                    probs[self.TRENDING_DOWN] = 0.3
                    probs[self.TRENDING_UP] = 0.2
            else:
                # Default: mean-reverting
                probs[mr_idx] = 0.4
                probs[self.TRENDING_UP] = 0.3
                probs[self.TRENDING_DOWN] = 0.3

        current_regime = int(np.argmax(probs))
        self._current_regime = current_regime
        self._regime_probs = probs
        return current_regime, probs

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        """Generate regime-based trading signal.

        Applies strategy logic appropriate for the detected regime:
        - Trending Up: Buy on momentum
        - Trending Down: Sell / go short
        - Mean-Reverting: Buy oversold, sell overbought

        Only generates signals when regime probability exceeds threshold.

        Args:
            data: OHLCV DataFrame.

        Returns:
            Signal appropriate for the current regime, or None.
        """
        if not self.validate_data(data):
            return None

        # Retrain HMM periodically
        if self._hmm_model is None or (
            len(data) - self._last_train_idx >= self.retrain_frequency
        ):
            self.fit_hmm(data)
            self._last_train_idx = len(data)

        # Detect current regime
        regime, probs = self.detect_regime(data)

        # Check confidence threshold
        max_prob = float(np.max(probs))
        if max_prob < self.confidence_threshold:
            return None

        close = data["close"]
        current_price = float(close.iloc[-1])

        # Compute indicators based on regime
        if regime == self.TRENDING_UP:
            # Trend following: buy if above MA
            sma = self.compute_sma(close, 20)
            ema = self.compute_ema(close, 20)

            if len(sma) > 1 and not np.isnan(sma.iloc[-1]):
                if current_price > sma.iloc[-1] and close.iloc[-2] <= sma.iloc[-2]:
                    confidence = max_prob * 0.9
                    return Signal(
                        symbol=self.symbol,
                        signal_type=SignalType.BUY,
                        confidence=round(confidence, 4),
                        price=round(current_price, 6),
                        stop_loss=round(current_price * (1 - self.stop_loss_pct), 6),
                        take_profit=round(current_price * (1 + self.take_profit_pct), 6),
                        source_agent=self.name,
                        source_strategy=self.name,
                        reasoning=(
                            f"Regime TRENDING_UP: prob={max_prob:.2f}, "
                            f"price={current_price:.4f} crossed above SMA20"
                        ),
                        evidence={
                            "regime": "trending_up",
                            "regime_probs": [round(float(p), 4) for p in probs],
                            "sma20": round(float(sma.iloc[-1]), 4),
                        },
                        factors=["regime_based", "trend_following"],
                    )

        elif regime == self.TRENDING_DOWN:
            # Short on downtrend
            sma = self.compute_sma(close, 20)

            if len(sma) > 1 and not np.isnan(sma.iloc[-1]):
                if current_price < sma.iloc[-1] and close.iloc[-2] >= sma.iloc[-2]:
                    confidence = max_prob * 0.9
                    return Signal(
                        symbol=self.symbol,
                        signal_type=SignalType.SELL,
                        confidence=round(confidence, 4),
                        price=round(current_price, 6),
                        stop_loss=round(current_price * (1 + self.stop_loss_pct), 6),
                        take_profit=round(current_price * (1 - self.take_profit_pct), 6),
                        source_agent=self.name,
                        source_strategy=self.name,
                        reasoning=(
                            f"Regime TRENDING_DOWN: prob={max_prob:.2f}, "
                            f"price={current_price:.4f} crossed below SMA20"
                        ),
                        evidence={
                            "regime": "trending_down",
                            "regime_probs": [round(float(p), 4) for p in probs],
                            "sma20": round(float(sma.iloc[-1]), 4),
                        },
                        factors=["regime_based", "trend_following"],
                    )

        elif regime == self.MEAN_REVERTING:
            # Mean reversion: RSI extremes
            rsi = self.compute_rsi(close, 14)

            if len(rsi) > 0 and not np.isnan(rsi.iloc[-1]):
                current_rsi = float(rsi.iloc[-1])

                if current_rsi < 30:
                    # Oversold: buy
                    confidence = max_prob * 0.8
                    return Signal(
                        symbol=self.symbol,
                        signal_type=SignalType.BUY,
                        confidence=round(confidence, 4),
                        price=round(current_price, 6),
                        stop_loss=round(current_price * (1 - self.stop_loss_pct), 6),
                        take_profit=round(current_price * (1 + self.take_profit_pct), 6),
                        source_agent=self.name,
                        source_strategy=self.name,
                        reasoning=(
                            f"Regime MEAN_REVERTING: prob={max_prob:.2f}, "
                            f"RSI={current_rsi:.1f} (oversold)"
                        ),
                        evidence={
                            "regime": "mean_reverting",
                            "regime_probs": [round(float(p), 4) for p in probs],
                            "rsi": round(current_rsi, 2),
                        },
                        factors=["regime_based", "mean_reversion"],
                    )

                elif current_rsi > 70:
                    # Overbought: sell
                    confidence = max_prob * 0.8
                    return Signal(
                        symbol=self.symbol,
                        signal_type=SignalType.SELL,
                        confidence=round(confidence, 4),
                        price=round(current_price, 6),
                        stop_loss=round(current_price * (1 + self.stop_loss_pct), 6),
                        take_profit=round(current_price * (1 - self.take_profit_pct), 6),
                        source_agent=self.name,
                        source_strategy=self.name,
                        reasoning=(
                            f"Regime MEAN_REVERTING: prob={max_prob:.2f}, "
                            f"RSI={current_rsi:.1f} (overbought)"
                        ),
                        evidence={
                            "regime": "mean_reverting",
                            "regime_probs": [round(float(p), 4) for p in probs],
                            "rsi": round(current_rsi, 2),
                        },
                        factors=["regime_based", "mean_reversion"],
                    )

        return None
