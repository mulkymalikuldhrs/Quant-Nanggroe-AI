"""Shared adapter for Hedge-Fund DataFrame strategies -> QNA Strategy contract.

Why this exists (root-cause fix, not a symptom patch):
    The Hedge-Fund strategies migrated from /e/trading implement the
    ``generate_signals(df) -> pd.DataFrame`` interface (columns: 'entry'
    with 1/-1/0, plus optional 'sl'/'tp'). QNA's ``engine/strategies``
    registry requires the QNA ``Strategy`` contract:
        generate_signal(data, **kwargs) -> StrategySignal
    Those strategies subclassed ``Strategy`` (an ABC with abstract
    ``generate_signal``) but only defined ``generate_signals`` -> they were
    *abstract and uninstantiable*, so ``Registry.create_all()`` crashed and
    ZERO of the 19 registered strategies could be constructed.

    This mixin fixes the FLOW (routing), not the router: it keeps every
    HF strategy's original logic intact and provides the missing
    ``generate_signal`` bridge plus a parameter-storage shim that the QNA
    ``Strategy.__init__`` expects.

Contract produced:
    - ``generate_signal`` reads the LAST bar's 'entry' (HF convention:
      most-recent signal). Returns a ``StrategySignal`` (BUY/SELL/HOLD) with
      SL/TP/confidence when present, else HOLD.
    - ``params`` passed to ``__init__`` are stored both in QNA's
      ``StrategyParameters`` bag and as plain instance attributes so the
      original ``generate_signals`` bodies that read ``self.lookback`` etc.
      keep working unchanged.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import pandas as pd

from quant_nanggroe.engine.strategies.base import (
    SignalDirection,
    SignalStrength,
    StrategyParameters,
    StrategySignal,
)

log = logging.getLogger("qna.strategy.adapter")


class DFStrategyAdapter:
    """Mixin that bridges a ``generate_signals(df)`` strategy to QNA's API.

    Inherit leftmost alongside ``Strategy`` so this mixin's ``__init__`` and
    ``generate_signal`` win MRO resolution. Subclasses must still implement
    ``generate_signals(self, df)``.
    """

    name: str = "df_adapter"
    description: str = "Hedge-Fund DataFrame strategy adapted to QNA"

    def __init__(self, parameters: Any = None, *args, **kwargs) -> None:
        # QNA's registry calls ``StrategyClass(parameters=StrategyParameters())``.
        # We absorb that arg AND accept HF-style kwargs (lookback=, atr_mult=, ...).
        # Everything is stored both in the QNA ``StrategyParameters`` bag and as
        # plain instance attributes so the original ``generate_signals`` bodies
        # that read ``self.lookback`` etc. keep working unchanged.
        from quant_nanggroe.engine.strategies.base import Strategy

        # If a subclass forwarded ``parameters`` inside **kw (registry path via
        # an intermediate __init__), prefer the explicit arg and drop the dup.
        kw_params = kwargs.pop("parameters", None)
        if parameters is None and kw_params is not None:
            parameters = kw_params

        params: Dict[str, Any] = {}
        if isinstance(parameters, StrategyParameters):
            params.update(parameters.params)
        elif isinstance(parameters, dict):
            params.update(parameters)
        params.update(kwargs)

        Strategy.__init__(self, parameters=StrategyParameters(params=params))

        for k, v in params.items():
            setattr(self, k, v)

        self._post_init_adapter(parameters=parameters, **kwargs)

    def _post_init_adapter(self, **kwargs) -> None:
        """Hook for subclasses to run their own __init__ body after attributes
        are set. Override to build scanners / set model flags without
        re-calling super().__init__."""
        pass

    # ── QNA contract bridge ───────────────────────────────────────────────
    def generate_signal(self, data: Any, **kwargs) -> StrategySignal:
        """Bridge: run HF generate_signals() and emit the last-bar StrategySignal.

        Returns HOLD when input is invalid, too short, or last bar has no
        active entry. BUY/SELL with SL/TP/confidence when the HF 'entry'
        column flags 1 / -1 on the final bar.
        """
        try:
            if not isinstance(data, pd.DataFrame) or "close" not in data.columns:
                return self._hold("Unsupported data format (need OHLCV DataFrame)")
            if len(data) < 2:
                return self._hold("Insufficient data (need 2+ bars)")

            df = self.generate_signals(data)

            if "entry" not in df.columns or len(df) == 0:
                return self._hold("No 'entry' column from generate_signals")

            last = df.iloc[-1]
            entry = last.get("entry", 0)
            try:
                entry_val = int(entry)
            except (TypeError, ValueError):
                entry_val = 0

            if entry_val == 0:
                return self._hold("No active entry on last bar")

            price = float(last["close"])
            direction = (
                SignalDirection.BUY if entry_val > 0 else SignalDirection.SELL
            )

            sl = self._coerce(last.get("sl"))
            tp = self._coerce(last.get("tp"))

            confidence = 0.6
            if "confluence" in df.columns:
                try:
                    confidence = min(0.95, 0.4 + 0.1 * int(last["confluence"]))
                except (TypeError, ValueError):
                    confidence = 0.6

            strength = (
                SignalStrength.STRONG if confidence >= 0.7
                else SignalStrength.MODERATE
            )

            return StrategySignal(
                strategy_name=self.name,
                symbol=kwargs.get("symbol", ""),
                direction=direction,
                strength=strength,
                confidence=confidence,
                entry_price=price,
                stop_loss=sl,
                take_profit=tp,
                risk_reward_ratio=self.calculate_risk_reward(
                    price, sl or price, tp or price, direction
                ) if (sl and tp) else 0.0,
                reasoning=f"HF {self.name}: entry={entry_val} on last bar",
                indicators={"entry": entry_val, "sl": sl, "tp": tp},
                **({"timestamp": ts} if (ts := kwargs.get("timestamp")) else {}),
            )
        except Exception as exc:
            log.error("%s.generate_signal error: %s", self.name, exc)
            return self._hold(f"Error: {exc}")

    # ── helpers ───────────────────────────────────────────────────────────
    @staticmethod
    def _coerce(v: Any) -> Optional[float]:
        try:
            if v is None or (isinstance(v, float) and pd.isna(v)):
                return None
            return float(v)
        except (TypeError, ValueError):
            return None

    def _hold(self, reason: str, indicators: Optional[Dict] = None) -> StrategySignal:
        return StrategySignal(
            strategy_name=self.name,
            direction=SignalDirection.HOLD,
            reasoning=reason,
            indicators=indicators or {},
        )
