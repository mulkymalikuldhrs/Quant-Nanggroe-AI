"""New strategy proposals — research gap fill (QNA v4.5.3).

Implants the 10 strategies from research/NEW_STRATEGY_PROPOSALS.md that close
gaps in the existing 108-strategy library: microstructure (VPIN), liquidity-
adjusted reversal (Amihud), cross-asset dispersion, vol-of-vol regime, CAPM
idiosyncratic momentum, calendar anomaly, vol-targeted breakout, return-skew
tail, drawdown-regime overlay, short-term volume-weighted reversal.

All classes subclass BaseStrategy and end in "Strategy" so the loader's
create_strategy() discovers them. Strategies requiring benchmark_close /
market_close guard on column presence (no crash, just no signal when absent).
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from quant_nanggroe.engine.strategy.strategies.base_strategy import BaseStrategy
from quant_nanggroe.types.signals import Signal, SignalType

logger = logging.getLogger(__name__)


class VPINToxicityStrategy(BaseStrategy):
    """Volume-Synchronized Probability of Informed Trading (flow toxicity)."""
    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="VPINToxicity", params=params)
        self.window = int(self.params.get("window", 50))
        self.tox_thr = float(self.params.get("tox_thr", 0.6))

    def required_columns(self) -> List[str]:
        return ["high", "low", "close", "volume"]

    def warmup_period(self) -> int:
        return self.window + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        ret = data["close"].pct_change()
        sign = np.sign(ret.fillna(0.0))
        signed_vol = (sign * data["volume"]).rolling(self.window).sum().abs()
        total_vol = data["volume"].rolling(self.window).sum()
        vpin = (signed_vol / total_vol).iloc[-1]
        price = float(data["close"].iloc[-1])
        if np.isnan(vpin):
            return None
        if vpin > self.tox_thr:
            return Signal(symbol=self.name, signal_type=SignalType.SELL,
                confidence=min(vpin, 1.0), price=price, source_agent=self.name,
                source_strategy=self.name,
                reasoning=f"VPIN {vpin:.2f}: high flow toxicity",
                evidence={"vpin": round(float(vpin), 3)}, factors=["microstructure", "vpin"])
        return None


class AmihudReversalStrategy(BaseStrategy):
    """Amihud illiquidity-adjusted short-horizon mean reversion."""
    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="AmihudReversal", params=params)
        self.window = int(self.params.get("window", 40))
        self.z_thr = float(self.params.get("z_thr", 2.0))

    def required_columns(self) -> List[str]:
        return ["close", "volume"]

    def warmup_period(self) -> int:
        return self.window + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        ret = data["close"].pct_change()
        illiq = (ret.abs() / (data["volume"] + 1.0)).rolling(self.window)
        mean, std = illiq.mean().iloc[-1], illiq.std().iloc[-1]
        illiq_z = ((ret.abs().iloc[-1] / (data["volume"].iloc[-1] + 1.0)) - mean) / (std + 1e-10)
        price = float(data["close"].iloc[-1])
        if np.isnan(illiq_z):
            return None
        if illiq_z > self.z_thr and ret.iloc[-1] < 0:
            return Signal(symbol=self.name, signal_type=SignalType.BUY,
                confidence=min(illiq_z / 3.0, 1.0), price=price, source_agent=self.name,
                source_strategy=self.name, reasoning="Illiquid selloff exhaustion",
                evidence={"illiq_z": round(float(illiq_z), 3)}, factors=["sta", "amihud"])
        if illiq_z > self.z_thr and ret.iloc[-1] > 0:
            return Signal(symbol=self.name, signal_type=SignalType.SELL,
                confidence=min(illiq_z / 3.0, 1.0), price=price, source_agent=self.name,
                source_strategy=self.name, reasoning="Illiquid rally exhaustion",
                evidence={"illiq_z": round(float(illiq_z), 3)}, factors=["sta", "amihud"])
        return None


class DispersionStrategy(BaseStrategy):
    """Cross-asset dispersion: trade when correlation to benchmark breaks down."""
    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="Dispersion", params=params)
        self.window = int(self.params.get("window", 60))
        self.corr_thr = float(self.params.get("corr_thr", 0.2))

    def required_columns(self) -> List[str]:
        return ["close", "benchmark_close"]

    def warmup_period(self) -> int:
        return self.window + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data) or "benchmark_close" not in data.columns:
            return None
        a = data["close"].pct_change()
        b = data["benchmark_close"].pct_change()
        corr = a.rolling(self.window).corr(b).iloc[-1]
        price = float(data["close"].iloc[-1])
        if np.isnan(corr):
            return None
        if corr < self.corr_thr:
            mom = float(data["close"].iloc[-1] / data["close"].iloc[-20] - 1.0)
            if mom > 0:
                return Signal(symbol=self.name, signal_type=SignalType.BUY,
                    confidence=min(0.4 + abs(corr), 1.0), price=price, source_agent=self.name,
                source_strategy=self.name, reasoning=f"Dispersion, corr={corr:.2f}, long mom",
                    evidence={"corr": round(float(corr), 3)}, factors=["macro", "dispersion"])
            if mom < 0:
                return Signal(symbol=self.name, signal_type=SignalType.SELL,
                    confidence=min(0.4 + abs(corr), 1.0), price=price, source_agent=self.name,
                source_strategy=self.name, reasoning=f"Dispersion, corr={corr:.2f}, short mom",
                    evidence={"corr": round(float(corr), 3)}, factors=["macro", "dispersion"])
        return None


class VolOfVolRegimeStrategy(BaseStrategy):
    """Vol-of-vol regime: variance of realized volatility."""
    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="VolOfVolRegime", params=params)
        self.vol_win = int(self.params.get("vol_win", 20))
        self.vov_win = int(self.params.get("vov_win", 30))
        self.z_thr = float(self.params.get("z_thr", 1.0))

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return self.vol_win + self.vov_win + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        rv = data["close"].pct_change().rolling(self.vol_win).std()
        vov = rv.rolling(self.vov_win)
        vov_z = (rv.iloc[-1] - vov.mean().iloc[-1]) / (vov.std().iloc[-1] + 1e-10)
        price = float(data["close"].iloc[-1])
        if np.isnan(vov_z):
            return None
        if vov_z > self.z_thr:
            return Signal(symbol=self.name, signal_type=SignalType.SELL,
                confidence=min(vov_z / 3.0, 1.0), price=price, source_agent=self.name,
                source_strategy=self.name, reasoning=f"Vol-of-vol high {vov_z:.2f}",
                evidence={"vov_z": round(float(vov_z), 3)}, factors=["vol", "vov"])
        if vov_z < -self.z_thr:
            return Signal(symbol=self.name, signal_type=SignalType.BUY,
                confidence=min(abs(vov_z) / 3.0, 1.0), price=price, source_agent=self.name,
                source_strategy=self.name, reasoning=f"Vol-of-vol low {vov_z:.2f}",
                evidence={"vov_z": round(float(vov_z), 3)}, factors=["vol", "vov"])
        return None


class IdiosyncraticMomentumStrategy(BaseStrategy):
    """CAPM residual (idiosyncratic) momentum — market-neutral alpha."""
    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="IdiosyncraticMomentum", params=params)
        self.window = int(self.params.get("window", 60))
        self.k = int(self.params.get("k", 10))

    def required_columns(self) -> List[str]:
        return ["close", "market_close"]

    def warmup_period(self) -> int:
        return self.window + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data) or "market_close" not in data.columns:
            return None
        a = data["close"].pct_change()
        m = data["market_close"].pct_change()
        win = slice(-self.window, None)
        beta = np.polyfit(m[win], a[win], 1)[0]
        resid = (a - beta * m).dropna().iloc[-self.k:].sum()
        price = float(data["close"].iloc[-1])
        if np.isnan(resid):
            return None
        if resid > 0:
            return Signal(symbol=self.name, signal_type=SignalType.BUY,
                confidence=min(abs(resid) * 50, 1.0), price=price, source_agent=self.name,
                source_strategy=self.name, reasoning=f"Idio residual mom {resid:.4f}",
                evidence={"residual_mom": round(float(resid), 4), "beta": round(float(beta), 3)},
                factors=["factor", "idiosyncratic"])
        if resid < 0:
            return Signal(symbol=self.name, signal_type=SignalType.SELL,
                confidence=min(abs(resid) * 50, 1.0), price=price, source_agent=self.name,
                source_strategy=self.name, reasoning=f"Idio residual mom {resid:.4f}",
                evidence={"residual_mom": round(float(resid), 4), "beta": round(float(beta), 3)},
                factors=["factor", "idiosyncratic"])
        return None


class CalendarAnomalyStrategy(BaseStrategy):
    """Turn-of-month seasonal anomaly (requires DatetimeIndex)."""
    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="CalendarAnomaly", params=params)
        self.window = int(self.params.get("window", 120))
        self.lead = int(self.params.get("lead", 3))

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return self.window + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        ret = data["close"].pct_change()
        idx = data.index[-self.window:]
        r = ret.iloc[-self.window:]
        tom = [i for i, d in enumerate(idx) if getattr(d, "day", 99) <= self.lead]
        tom_avg = r.iloc[tom].mean() if tom else 0.0
        today = data.index[-1]
        price = float(data["close"].iloc[-1])
        if np.isnan(tom_avg):
            return None
        if getattr(today, "day", 99) <= self.lead and tom_avg > 0:
            return Signal(symbol=self.name, signal_type=SignalType.BUY,
                confidence=min(0.4 + tom_avg * 20, 1.0), price=price, source_agent=self.name,
                source_strategy=self.name, reasoning=f"TOM avg {tom_avg:.3%}, long",
                evidence={"tom_avg": round(float(tom_avg), 4)}, factors=["anomaly", "calendar"])
        if getattr(today, "day", 99) > self.lead and tom_avg < 0:
            return Signal(symbol=self.name, signal_type=SignalType.SELL,
                confidence=min(0.4 + abs(tom_avg) * 20, 1.0), price=price, source_agent=self.name,
                source_strategy=self.name, reasoning=f"TOM avg {tom_avg:.3%}, short",
                evidence={"tom_avg": round(float(tom_avg), 4)}, factors=["anomaly", "calendar"])
        return None


class VolTargetedBreakoutStrategy(BaseStrategy):
    """Breakout entry gated on low realized vol, sized inversely to vol."""
    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="VolTargetedBreakout", params=params)
        self.n = int(self.params.get("n", 20))
        self.vol_thr = float(self.params.get("vol_thr", 0.02))

    def required_columns(self) -> List[str]:
        return ["high", "low", "close"]

    def warmup_period(self) -> int:
        return self.n + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        vol = float(data["close"].pct_change().rolling(self.n).std().iloc[-1])
        hh = float(data["high"].rolling(self.n).max().iloc[-2])
        ll = float(data["low"].rolling(self.n).min().iloc[-2])
        price = float(data["close"].iloc[-1])
        if np.isnan(vol) or vol == 0 or vol > self.vol_thr:
            return None
        size = min(1.0 / (vol * 100), 1.0)
        if price > hh:
            return Signal(symbol=self.name, signal_type=SignalType.BUY,
                confidence=size, price=price, source_agent=self.name,
                source_strategy=self.name, reasoning="Calm-vol breakout long",
                evidence={"vol": round(vol, 4)}, factors=["vol", "breakout"])
        if price < ll:
            return Signal(symbol=self.name, signal_type=SignalType.SELL,
                confidence=size, price=price, source_agent=self.name,
                source_strategy=self.name, reasoning="Calm-vol breakout short",
                evidence={"vol": round(vol, 4)}, factors=["vol", "breakout"])
        return None


class ReturnSkewTailStrategy(BaseStrategy):
    """Return-skew tail signal — fade extreme skewness."""
    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="ReturnSkewTail", params=params)
        self.window = int(self.params.get("window", 60))
        self.skew_thr = float(self.params.get("skew_thr", 1.2))

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return self.window + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        skew = data["close"].pct_change().rolling(self.window).skew().iloc[-1]
        price = float(data["close"].iloc[-1])
        if np.isnan(skew):
            return None
        if skew < -self.skew_thr:
            return Signal(symbol=self.name, signal_type=SignalType.BUY,
                confidence=min(abs(skew) / 3.0, 1.0), price=price, source_agent=self.name,
                source_strategy=self.name, reasoning=f"Neg skew {skew:.2f}, fade",
                evidence={"skew": round(float(skew), 3)}, factors=["vol", "skew"])
        if skew > self.skew_thr:
            return Signal(symbol=self.name, signal_type=SignalType.SELL,
                confidence=min(skew / 3.0, 1.0), price=price, source_agent=self.name,
                source_strategy=self.name, reasoning=f"Pos skew {skew:.2f}, fade",
                evidence={"skew": round(float(skew), 3)}, factors=["vol", "skew"])
        return None


class DrawdownRegimeStrategy(BaseStrategy):
    """Drawdown-from-peak regime overlay."""
    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="DrawdownRegime", params=params)
        self.max_dd = float(self.params.get("max_dd", 0.10))
        self.recover = float(self.params.get("recover", 0.03))

    def required_columns(self) -> List[str]:
        return ["close"]

    def warmup_period(self) -> int:
        return 30

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        peak = data["close"].cummax()
        dd = float((data["close"].iloc[-1] / peak.iloc[-1]) - 1.0)
        price = float(data["close"].iloc[-1])
        if dd < -self.max_dd:
            return Signal(symbol=self.name, signal_type=SignalType.SELL,
                confidence=min(abs(dd) / self.max_dd, 1.0), price=price, source_agent=self.name,
                source_strategy=self.name, reasoning=f"Drawdown {dd:.1%}: defensive",
                evidence={"drawdown": round(dd, 4)}, factors=["risk", "drawdown"])
        if dd > -self.recover:
            return Signal(symbol=self.name, signal_type=SignalType.BUY,
                confidence=0.5, price=price, source_agent=self.name,
                source_strategy=self.name, reasoning=f"Recovered from DD {dd:.1%}",
                evidence={"drawdown": round(dd, 4)}, factors=["risk", "drawdown"])
        return None


class VolumeWeightedReversalStrategy(BaseStrategy):
    """Fast short-term, volume-weighted mean reversion."""
    def __init__(self, params: Optional[Dict] = None):
        super().__init__(name="VolumeWeightedReversal", params=params)
        self.k = int(self.params.get("k", 5))
        self.vol_win = int(self.params.get("vol_win", 20))
        self.thr = float(self.params.get("thr", 0.5))

    def required_columns(self) -> List[str]:
        return ["close", "volume"]

    def warmup_period(self) -> int:
        return self.k + self.vol_win + 5

    def generate_signal(self, data: pd.DataFrame) -> Optional[Signal]:
        if not self.validate_data(data):
            return None
        r = float(data["close"].iloc[-1] / data["close"].iloc[-self.k] - 1.0)
        vol = data["volume"].rolling(self.vol_win)
        vol_z = (data["volume"].iloc[-1] - vol.mean().iloc[-1]) / (vol.std().iloc[-1] + 1e-10)
        signal = -r * float(np.tanh(vol_z))
        price = float(data["close"].iloc[-1])
        if np.isnan(signal) or abs(signal) < self.thr:
            return None
        if signal > 0:
            return Signal(symbol=self.name, signal_type=SignalType.BUY,
                confidence=min(abs(signal), 1.0), price=price, source_agent=self.name,
                source_strategy=self.name, reasoning=f"Vol-wtd reversal {signal:.3f}",
                evidence={"signal": round(signal, 4)}, factors=["mrv", "vwap_reversal"])
        return Signal(symbol=self.name, signal_type=SignalType.SELL,
            confidence=min(abs(signal), 1.0), price=price, source_agent=self.name,
                source_strategy=self.name, reasoning=f"Vol-wtd reversal {signal:.3f}",
            evidence={"signal": round(signal, 4)}, factors=["mrv", "vwap_reversal"])
