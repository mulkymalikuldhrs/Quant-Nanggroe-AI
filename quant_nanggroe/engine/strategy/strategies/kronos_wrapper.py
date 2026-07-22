"""Kronos Wrapper — canonical QNA engine migration (degraded/fallback mode).

Migrated from ``E:/trading/strategies/kronos_wrapper.py`` (also in legacy
``quant_nanggroe/engine/strategies/kronos_wrapper.py``) to the canonical
``BaseStrategy`` interface.

IMPORTANT — missing dependency:
    The real Kronos financial foundation model package
    (``from model import KronosTokenizer, Kronos, KronosPredictor``) is NOT
    installed in QNA.  Per WAVE5_HF_MIGRATION.md we do NOT fake the model.
    Instead we run a documented, momentum-based degraded predictor
    (``_FallbackKronosPredictor``).  When the real package becomes importable
    (set the import path via ``KRONOS_PKG_PATH`` env and install the package),
    the full model path is used; otherwise the fallback is transparent.

Canonical interface:
    generate_signal(df) -> Optional[Signal]
    required_columns() -> List[str]
    warmup_period()    -> int
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

log = logging.getLogger("kronos")

# ─── Attempt real Kronos import ───────────────────────────────────────────────
# The Kronos Foundation Model package is external and absent in QNA.  We attempt
# a best-effort import only if the user points us at it via KRONOS_PKG_PATH.
KRONOS_AVAILABLE = False
_KronosTokenizer = _Kronos = _KronosPredictor = None

_kronos_pkg_path = os.environ.get("KRONOS_PKG_PATH")
if _kronos_pkg_path:
    try:
        sys.path.insert(0, str(_kronos_pkg_path))
        from model import KronosTokenizer, Kronos, KronosPredictor  # type: ignore

        _KronosTokenizer = KronosTokenizer
        _Kronos = Kronos
        _KronosPredictor = KronosPredictor
        KRONOS_AVAILABLE = True
        log.info("Kronos model package loaded from %s", _kronos_pkg_path)
    except Exception as e:  # pragma: no cover - depends on external pkg
        KRONOS_AVAILABLE = False
        log.warning("Kronos not available (%s) — using fallback momentum mode", e)


class _FallbackKronosPredictor:
    """Lightweight momentum-based fallback.

    Degraded mode used when the Kronos Foundation Model package is absent.
    It produces a forecast from recent weighted momentum + volatility — NOT a
    learned forecast.  Documented as a fallback; never presented as the model.
    """

    def __init__(self):
        self.price_cols = ["open", "high", "low", "close"]

    def predict(self, df: pd.DataFrame, pred_len: int = 10, **kw):
        c = df["close"].values.astype(float)
        if len(c) < 50:
            return np.zeros(pred_len), 0.0
        mom_short = c[-1] / c[-5] - 1 if len(c) >= 5 else 0.0
        mom_med = c[-1] / c[-20] - 1 if len(c) >= 20 else 0.0
        mom_long = c[-1] / c[-50] - 1 if len(c) >= 50 else 0.0
        returns = np.diff(c) / c[:-1]
        vol = float(np.std(returns[-20:])) if len(returns) >= 20 else 0.001
        bias = mom_short * 0.5 + mom_med * 0.3 + mom_long * 0.2
        forecast = c[-1] * (1 + bias * np.linspace(0.001, 0.01, pred_len))
        return forecast, vol


class KronosSignalProvider(BaseStrategy):
    """Kronos Signal Provider — forecasts price N bars ahead and signals on
    expected return. Runs the real Kronos model when available, otherwise the
    documented momentum-based fallback."""

    def __init__(self, params: Optional[dict] = None):
        super().__init__(name="KronosSignalProvider", params=params)
        self.model_name: str = self.params.get("model_name", "NeoQuasar/Kronos-small")
        self.tokenizer_name: str = self.params.get(
            "tokenizer_name", "NeoQuasar/Kronos-Tokenizer-base"
        )
        self.lookback: int = int(self.params.get("lookback", 200))
        self.pred_len: int = int(self.params.get("pred_len", 10))
        self.signal_threshold: float = float(self.params.get("signal_threshold", 0.0015))
        self.ensemble_count: int = int(self.params.get("ensemble_count", 3))
        self.fallback_momentum: bool = bool(self.params.get("fallback_momentum", True))
        self._predictor = None
        self._initialized = False
        self._using_fallback = not KRONOS_AVAILABLE

    def required_columns(self) -> List[str]:
        return ["open", "high", "low", "close"]

    def warmup_period(self) -> int:
        return self.lookback + self.pred_len

    def _init_model(self):
        if self._initialized:
            return
        self._initialized = True
        if KRONOS_AVAILABLE and _KronosPredictor is not None:
            try:  # pragma: no cover - needs external pkg
                tokenizer = _KronosTokenizer.from_pretrained(self.tokenizer_name)
                model = _Kronos.from_pretrained(self.model_name)
                self._predictor = _KronosPredictor(
                    model, tokenizer, max_context=min(self.lookback, 512), device="cpu"
                )
                self._using_fallback = False
                log.info("Kronos model loaded: %s", self.model_name)
                return
            except Exception as e:  # pragma: no cover
                log.warning("Kronos load failed (%s) — using fallback", e)
        if self.fallback_momentum:
            self._predictor = _FallbackKronosPredictor()
            self._using_fallback = True
        else:
            self._predictor = None
            self._using_fallback = True

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        self._init_model()
        n = len(data)
        if self._predictor is None:
            return None
        if n < self.lookback + self.pred_len:
            return None

        lookback = min(self.lookback, n - self.pred_len)
        x_df = data.iloc[-lookback - self.pred_len : -self.pred_len].copy()
        for col in ("volume", "amount"):
            if col not in x_df.columns:
                x_df[col] = 0.0

        price = float(data["close"].iloc[-1])

        if isinstance(self._predictor, _FallbackKronosPredictor):
            forecast, _vol = self._predictor.predict(x_df, pred_len=self.pred_len)
            forecast_close = forecast
            avg_ret = float(np.mean((forecast_close - price) / price))
        else:  # pragma: no cover - needs external pkg
            try:
                pred_df = self._predictor.predict(
                    x_df[["open", "high", "low", "close", "volume", "amount"]],
                    x_timestamp=pd.Series(x_df.index),
                    y_timestamp=pd.Series(data.index[-self.pred_len :]),
                    pred_len=self.pred_len,
                    T=0.8,
                    top_p=0.9,
                    sample_count=self.ensemble_count,
                    verbose=False,
                )
                forecast_close = pred_df["close"].values
                avg_ret = float(np.mean((forecast_close - price) / price))
            except Exception as e:
                log.error("Prediction error: %s", e)
                return None

        if avg_ret > self.signal_threshold:
            signal_type = SignalType.BUY
            confidence = round(min(abs(avg_ret) / (self.signal_threshold * 4), 0.95), 4)
        elif avg_ret < -self.signal_threshold:
            signal_type = SignalType.SELL
            confidence = round(min(abs(avg_ret) / (self.signal_threshold * 4), 0.95), 4)
        else:
            return None

        return Signal(
            symbol=self.name,
            signal_type=signal_type,
            confidence=confidence,
            price=round(price, 6),
            source_agent=self.name,
            source_strategy=self.name,
            reasoning=(
                f"Kronos expected_return={avg_ret:+.4f} "
                f"mode={'fallback' if self._using_fallback else 'model'}"
            ),
            evidence={
                "strategy": "kronos",
                "expected_return": round(avg_ret, 6),
                "mode": "fallback" if self._using_fallback else "model",
            },
            factors=["kronos", "foundation_model" if not self._using_fallback else "momentum_fallback"],
        )


class KronosEnsembleStrategy(BaseStrategy):
    """Kronos Ensemble — Kronos forecast + EMA trend filter + volatility filter."""

    def __init__(self, params: Optional[dict] = None):
        super().__init__(name="KronosEnsembleStrategy", params=params)
        self.lookback: int = int(self.params.get("lookback", 200))
        self.pred_len: int = int(self.params.get("pred_len", 10))
        self.signal_threshold: float = float(self.params.get("signal_threshold", 0.002))
        self.trend_filter: bool = bool(self.params.get("trend_filter", True))
        self.vol_filter: bool = bool(self.params.get("vol_filter", True))
        self._kronos = KronosSignalProvider(
            params={
                "lookback": self.lookback,
                "pred_len": self.pred_len,
                "signal_threshold": self.signal_threshold,
            }
        )

    def required_columns(self) -> List[str]:
        return ["open", "high", "low", "close"]

    def warmup_period(self) -> int:
        return self.lookback + self.pred_len

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None

        kronos_signal = self._kronos.generate_signal(data)
        if kronos_signal is None:
            return None

        i = len(data) - 1
        ema20 = data["close"].ewm(span=20).mean().iloc[i]
        ema50 = data["close"].ewm(span=50).mean().iloc[i]
        trend_up = ema20 > ema50
        trend_down = ema20 < ema50

        # Volatility chaos filter (ATR > 2x recent mean)
        atr = pd.concat(
            [
                data["high"] - data["low"],
                (data["high"] - data["close"].shift(1)).abs(),
                (data["low"] - data["close"].shift(1)).abs(),
            ],
            axis=1,
        ).max(axis=1)
        atr_mean = atr.rolling(20).mean().iloc[i]
        chaos = bool(atr.iloc[i] > atr_mean * 2.0) if atr_mean == atr_mean else False

        if chaos and self.vol_filter:
            return None
        if self.trend_filter:
            if kronos_signal.signal_type == SignalType.BUY and not trend_up:
                return None
            if kronos_signal.signal_type == SignalType.SELL and not trend_down:
                return None

        kronos_signal.evidence["mode"] = "ensemble"
        kronos_signal.factors = ["kronos_ensemble", "trend_filter"]
        return kronos_signal
