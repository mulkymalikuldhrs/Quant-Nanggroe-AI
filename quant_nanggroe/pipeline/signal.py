"""
Unified Signal Engine
=====================
Generates trading signals by trying providers in priority order:
  1. Hedge fund signal providers (weighted voting)
  2. engine/strategies/ (ProductionStrategyRunner)
  3. engine/agentic signal generation (fallback)
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from quant_nanggroe.engine.causal.models import CausalContext
from quant_nanggroe.pipeline.macro_context import MacroContextProvider

log = logging.getLogger("QNA-Pipeline-Signal")

MIN_CONFIDENCE_THRESHOLD: float = 0.3


@dataclass
class Signal:
    symbol: str
    side: str  # buy / sell / hold / close
    confidence: float
    strategy: str
    price: float
    reason: str
    metadata: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class UnifiedSignalEngine:
    """Aggregates signals from multiple provider backends."""

    def __init__(self, macro_context: MacroContextProvider | None = None):
        self._hf_aggregate: Any = None
        self._hf_providers: list[Any] = []
        self._strategy_runner: Any = None
        self._price_provider: Any = None
        self._macro = macro_context or MacroContextProvider()
        self._causal_ctx: CausalContext | None = None

    def set_causal_context(self, ctx: CausalContext | None) -> None:
        """Provide a CausalContext for macro bias in signal aggregation.
        
        When set, it is forwarded to the hedge fund aggregator so each
        signal provider receives typed macro bias instead of env vars.
        """
        self._causal_ctx = ctx

    def _lazy_hf(self):
        if self._hf_aggregate is not None:
            return
        try:
            from quant_nanggroe.hedge_fund.hedge_fund import ALL_PROVIDERS, CORE_PROVIDERS, aggregate
            self._hf_aggregate = aggregate
            self._hf_providers = list(ALL_PROVIDERS or CORE_PROVIDERS or [])
        except Exception as e:
            log.debug("Hedge fund providers unavailable: %s", e)

    def _lazy_strategy_runner(self):
        if self._strategy_runner is not None:
            return self._strategy_runner
        try:
            from quant_nanggroe.engine_production_bridge import ProductionStrategyRunner
            self._strategy_runner = ProductionStrategyRunner()
        except Exception as e:
            log.debug("ProductionStrategyRunner unavailable: %s", e)
        return self._strategy_runner

    def generate_signals(self, symbol: str, data: Optional[dict] = None, ctx: Optional[CausalContext] = None) -> list[Signal]:
        signals: list[Signal] = []

        if ctx is not None:
            self._causal_ctx = ctx

        hf_signal = self._try_hedge_fund(symbol)
        if hf_signal is not None:
            signals.append(hf_signal)

        strategy_signals = self._try_strategies(symbol, data)
        signals.extend(strategy_signals)

        if not signals:
            fallback = self._try_agentic_signal(symbol, data)
            if fallback is not None:
                signals.append(fallback)

        filtered: list[Signal] = []
        for sig in signals:
            if sig.side in ("buy", "sell"):
                side, conf, reason = self._macro.apply_macro_filter(symbol, sig.side, sig.confidence, causal_ctx=self._causal_ctx)
                if side == "hold":
                    log.info("Macro filter blocked %s %s: %s", symbol, sig.side, reason)
                    continue
                sig.confidence = conf
                sig.reason = f"{sig.reason} | {reason}"
                sig.metadata["macro_weather"] = self._macro.weather.to_dict()

            if sig.side in ("buy", "sell") and sig.confidence < MIN_CONFIDENCE_THRESHOLD:
                log.warning(
                    "Confidence filter dropped %s %s: conf=%.3f < %.3f",
                    symbol, sig.side, sig.confidence, MIN_CONFIDENCE_THRESHOLD,
                )
                continue

            filtered.append(sig)

        if not filtered and any(s.side in ("buy", "sell") for s in signals):
            hold_reason = f"All {len(signals)} signals filtered below MIN_CONFIDENCE_THRESHOLD={MIN_CONFIDENCE_THRESHOLD}"
            log.warning("No trade for %s: %s", symbol, hold_reason)

        return filtered

    def _try_hedge_fund(self, symbol: str) -> Optional[Signal]:
        self._lazy_hf()
        if self._hf_aggregate is None:
            return None
        try:
            result = self._hf_aggregate(symbol, ctx=self._causal_ctx)
            bias = result.get("bias", "neutral")
            confidence = float(result.get("confidence", 0.0))
            if bias in ("buy", "sell") and confidence > 0:
                return Signal(
                    symbol=symbol,
                    side=bias,
                    confidence=confidence,
                    strategy="hedge_fund_v3",
                    price=float(result.get("price", 0.0)),
                    reason=f"HF weighted vote: {len(result.get('votes', []))} providers",
                    metadata={"votes": len(result.get("votes", [])), "total_conf": result.get("total_conf", 0)},
                )
        except Exception as e:
            log.debug("Hedge fund signal failed for %s: %s", symbol, e)
        return None

    @staticmethod
    def _ohlcv_data(data: Optional[dict]) -> Optional[dict]:
        if data is None or not isinstance(data, dict):
            return None
        price = data.get("close") or data.get("price")
        if price is None:
            return data
        price = float(price)
        if "close" not in data:
            data = dict(data)
            data["open"] = float(data.get("open", price))
            data["high"] = float(data.get("high", price))
            data["low"] = float(data.get("low", price))
            data["close"] = price
            data["volume"] = float(data.get("volume", 0))
        return data

    def _try_strategies(self, symbol: str, data: Optional[dict] = None) -> list[Signal]:
        runner = self._lazy_strategy_runner()
        if runner is None:
            return []
        signals: list[Signal] = []
        try:
            data = self._ohlcv_data(data)
            price = float(data.get("close", 0)) if data and isinstance(data, dict) else 0.0
            if hasattr(runner, "run_strategies"):
                raw_signals = runner.run_strategies(symbol, price)
                if isinstance(raw_signals, list):
                    for rs in raw_signals:
                        side = getattr(rs, "side", getattr(rs, "signal", "hold"))
                        conf = float(getattr(rs, "confidence", 0.5))
                        strategy = getattr(rs, "strategy", "engine")
                        price_val = float(getattr(rs, "price", price))
                        if side in ("buy", "sell") and conf > 0:
                            signals.append(Signal(
                                symbol=symbol,
                                side=side,
                                confidence=conf,
                                strategy=strategy,
                                price=price_val,
                                reason=getattr(rs, "reason", ""),
                            ))
            if not signals:
                if hasattr(runner, "strategies") and runner.strategies:
                    for name, strat in runner.strategies.items():
                        if hasattr(strat, "predict") or hasattr(strat, "generate_signal"):
                            try:
                                fn = strat.predict if hasattr(strat, "predict") else strat.generate_signal
                                result = fn(symbol, data)
                                if isinstance(result, dict):
                                    side = result.get("side", result.get("signal", "hold"))
                                    conf = float(result.get("confidence", 0.5))
                                    if side in ("buy", "sell") and conf > 0:
                                        signals.append(Signal(
                                            symbol=symbol,
                                            side=side,
                                            confidence=conf,
                                            strategy=name,
                                            price=float(result.get("price", price)),
                                            reason=result.get("reason", ""),
                                        ))
                            except Exception as e:
                                log.debug("Strategy %s failed for %s: %s", name, symbol, e)
        except Exception as e:
            log.debug("Strategy runner signal gen failed for %s: %s", symbol, e)
        return signals

    def _try_agentic_signal(self, symbol: str, data: Optional[dict] = None) -> Optional[Signal]:
        try:
            from quant_nanggroe.engine.agentic.autonomous import AutonomousPipeline
            ap = AutonomousPipeline()
            from quant_nanggroe.pipeline.orchestrator import _get_pipeline_loop
            loop = _get_pipeline_loop()
            raw = loop.run_until_complete(ap.run(symbol=symbol, use_llm=False))
            if hasattr(raw, "success") and raw.success:
                side = getattr(raw, "signal", "hold")
                confidence = float(getattr(raw, "confidence", 0.0))
                if side in ("buy", "sell") and confidence > 0:
                    strategy = "agentic"
                    if hasattr(raw, "decision") and isinstance(raw.decision, dict):
                        strategy = raw.decision.get("strategy", "agentic")
                    return Signal(
                        symbol=symbol,
                        side=side,
                        confidence=confidence,
                        strategy=strategy,
                        price=0.0,
                        reason=f"Agentic pipeline: {getattr(raw, 'reason', '')}",
                    )
        except Exception as e:
            log.debug("Agentic signal fallback failed for %s: %s", symbol, e)
        return None
