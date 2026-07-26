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

log = logging.getLogger("QNA-Pipeline-Signal")


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

    def __init__(self):
        self._hf_aggregate: Any = None
        self._hf_providers: list[Any] = []
        self._strategy_runner: Any = None
        self._price_provider: Any = None

    def _lazy_hf(self):
        if self._hf_aggregate is not None:
            return
        try:
            from quant_nanggroe.hedge_fund.hedge_fund import aggregate, ALL_PROVIDERS, CORE_PROVIDERS
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

    def generate_signals(self, symbol: str, data: Optional[dict] = None) -> list[Signal]:
        signals: list[Signal] = []

        hf_signal = self._try_hedge_fund(symbol)
        if hf_signal is not None:
            signals.append(hf_signal)

        strategy_signals = self._try_strategies(symbol, data)
        signals.extend(strategy_signals)

        if not signals:
            fallback = self._try_agentic_signal(symbol, data)
            if fallback is not None:
                signals.append(fallback)

        return signals

    def _try_hedge_fund(self, symbol: str) -> Optional[Signal]:
        self._lazy_hf()
        if self._hf_aggregate is None:
            return None
        try:
            result = self._hf_aggregate(symbol)
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

    def _try_strategies(self, symbol: str, data: Optional[dict] = None) -> list[Signal]:
        runner = self._lazy_strategy_runner()
        if runner is None:
            return []
        signals: list[Signal] = []
        try:
            price = float(data.get("price", 0)) if data and isinstance(data, dict) and data.get("price") else 0.0
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
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                raw = loop.run_until_complete(ap.run(symbol=symbol, use_llm=False))
            finally:
                loop.close()
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
