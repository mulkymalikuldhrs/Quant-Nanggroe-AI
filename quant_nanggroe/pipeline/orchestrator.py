"""
Pipeline Orchestrator — UnifiedPipeline
========================================
Routes each symbol to the right execution mode:
  - forex (EURUSD, GBPUSD, ...)  → hedge_fund pipeline
  - crypto (BTCUSDT, ETHUSDT, ...) → live_engine path
  - default / agentic            → engine/agentic autonomous pipeline

Graceful degradation: if primary mode fails, falls through to next.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional

from quant_nanggroe.pipeline.data import UnifiedDataProvider
from quant_nanggroe.pipeline.signal import UnifiedSignalEngine
from quant_nanggroe.pipeline.execution import UnifiedExecutionRouter

log = logging.getLogger("QNA-Pipeline")

FOREX_SYMBOLS = {
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD",
    "AUDUSD", "NZDUSD", "EURGBP", "EURJPY", "GBPJPY",
    "XAUUSD", "XAGUSD", "GBPAUD", "GBPNZD", "EURAUD",
    "AUDCAD", "AUDJPY", "AUDNZD", "CADJPY", "CHFJPY",
    "EURNZD", "EURCAD", "EURCHF", "GBPCAD", "GBPCHF",
    "NZDCAD", "NZDJPY", "NZDCHF",
}

CRYPTO_SUFFIXES = {"USDT", "USD", "BTC", "ETH", "BUSD", "USDC"}


@dataclass
class PipelineResult:
    symbol: str
    signal: str  # buy / sell / hold
    confidence: float
    executed: bool
    fill_price: float
    fill_id: str
    strategy: str
    mode: str  # hedge / crypto / agentic
    error: Optional[str]
    sla_ms: float
    timestamp: float

    @classmethod
    def empty(cls, symbol: str, mode: str = "auto", error: Optional[str] = None):
        return cls(
            symbol=symbol,
            signal="hold",
            confidence=0.0,
            executed=False,
            fill_price=0.0,
            fill_id="",
            strategy="",
            mode=mode,
            error=error,
            sla_ms=0.0,
            timestamp=time.time(),
        )


def _detect_mode(symbol: str, mode_hint: str = "auto") -> str:
    if mode_hint != "auto":
        return mode_hint
    sym_upper = symbol.upper()
    if sym_upper in FOREX_SYMBOLS or sym_upper.startswith("XAU") or sym_upper.startswith("XAG"):
        return "hedge"
    for suffix in CRYPTO_SUFFIXES:
        if sym_upper.endswith(suffix) and len(sym_upper) > len(suffix):
            return "crypto"
    return "agentic"


class UnifiedPipeline:
    """Single orchestrator that delegates to the right pipeline implementation."""

    def __init__(
        self,
        data_provider: Optional[UnifiedDataProvider] = None,
        signal_engine: Optional[UnifiedSignalEngine] = None,
        execution_router: Optional[UnifiedExecutionRouter] = None,
        mode_resolver: Optional[Callable[[str, str], str]] = None,
    ):
        self._data = data_provider or UnifiedDataProvider()
        self._signal = signal_engine or UnifiedSignalEngine()
        self._execution = execution_router or UnifiedExecutionRouter()
        self._mode_resolver = mode_resolver or _detect_mode
        self._autonomous: Any = None
        self._hedge_run_once: Any = None
        self._live_engine_runner: Any = None

    def _lazy_autonomous(self):
        if self._autonomous is not None:
            return self._autonomous
        try:
            from quant_nanggroe.engine.agentic.autonomous import AutonomousPipeline
            self._autonomous = AutonomousPipeline()
            # ponytail: synchronous wrapper — AutonomousPipeline.run is async,
            # so we run it via asyncio.run() inside a single-thread context.
            # Upgrade path: make UnifiedPipeline fully async when all consumers
            # can handle it.
        except Exception as e:
            log.warning("AutonomousPipeline unavailable: %s", e)
            self._autonomous = None
        return self._autonomous

    def _run_agentic(self, symbol: str) -> PipelineResult:
        t0 = time.perf_counter()
        ap = self._lazy_autonomous()
        if ap is None:
            return PipelineResult.empty(symbol, mode="agentic", error="AutonomousPipeline not available")

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                raw = loop.run_until_complete(ap.run(symbol=symbol, use_llm=False))
            finally:
                loop.close()

            sla_ms = (time.perf_counter() - t0) * 1000
            signal = getattr(raw, "signal", "hold")
            confidence = getattr(raw, "confidence", 0.0)
            executed = raw.success and signal in ("buy", "sell")
            return PipelineResult(
                symbol=symbol,
                signal=signal,
                confidence=confidence,
                executed=executed,
                fill_price=raw.decision.get("price", 0.0) if hasattr(raw, "decision") and isinstance(raw.decision, dict) else 0.0,
                fill_id=raw.decision.get("fill_id", "") if hasattr(raw, "decision") and isinstance(raw.decision, dict) else "",
                strategy=raw.decision.get("strategy", "agentic") if hasattr(raw, "decision") and isinstance(raw.decision, dict) else "agentic",
                mode="agentic",
                error=None if raw.success else raw.reason,
                sla_ms=sla_ms,
                timestamp=time.time(),
            )
        except Exception as e:
            return PipelineResult.empty(symbol, mode="agentic", error=str(e))

    def _run_hedge(self, symbol: str) -> PipelineResult:
        t0 = time.perf_counter()
        try:
            from quant_nanggroe.hedge_fund.hedge_fund import run_once, aggregate, calc_atr
            if self._hedge_run_once is None:
                self._hedge_run_once = run_once
            # run_once has no return value — it executes inline.
            # We capture state by calling aggregate() for the signal first.
            signal = aggregate(symbol)
            bias = signal.get("bias", "neutral")
            confidence = float(signal.get("confidence", 0.0))
            price = float(signal.get("price", 0.0)) or self._data.get_price(symbol) or 0.0
            self._hedge_run_once(target_symbol=symbol)
            sla_ms = (time.perf_counter() - t0) * 1000
            return PipelineResult(
                symbol=symbol,
                signal=bias,
                confidence=confidence,
                executed=bias in ("buy", "sell"),
                fill_price=price,
                fill_id="",
                strategy="hedge_fund_v3",
                mode="hedge",
                error=None,
                sla_ms=sla_ms,
                timestamp=time.time(),
            )
        except Exception as e:
            return PipelineResult.empty(symbol, mode="hedge", error=str(e))

    def _run_crypto(self, symbol: str) -> PipelineResult:
        t0 = time.perf_counter()
        try:
            price_data = self._data.get_price(symbol)
            if price_data is None:
                return PipelineResult.empty(symbol, mode="crypto", error="No price data")
            price = float(price_data) if not isinstance(price_data, dict) else float(price_data.get("close", price_data.get("price", 0.0)))

            sig_result = self._signal.generate_signals(symbol, {"price": price})
            signal = "hold"
            confidence = 0.0
            strategy = "live_engine"
            if sig_result:
                best = max(sig_result, key=lambda s: s.confidence)
                signal = best.side
                confidence = best.confidence
                strategy = best.strategy

            if signal in ("buy", "sell"):
                exec_result = self._execution.execute(symbol, signal, price, confidence)
            else:
                exec_result = {"fill_price": 0.0, "fill_id": "", "executed": False}

            sla_ms = (time.perf_counter() - t0) * 1000
            return PipelineResult(
                symbol=symbol,
                signal=signal,
                confidence=confidence,
                executed=bool(exec_result and exec_result.get("executed", exec_result.get("fill_id") is not None)),
                fill_price=float(exec_result.get("fill_price", exec_result.get("price", 0.0)) if exec_result else 0.0),
                fill_id=str(exec_result.get("fill_id", "") if exec_result else ""),
                strategy=strategy,
                mode="crypto",
                error=None,
                sla_ms=sla_ms,
                timestamp=time.time(),
            )
        except Exception as e:
            return PipelineResult.empty(symbol, mode="crypto", error=str(e))

    def run(self, symbol: str, mode: str = "auto") -> PipelineResult:
        chosen = self._mode_resolver(symbol, mode)
        log.info("Pipeline run: symbol=%s mode=%s resolved=%s", symbol, mode, chosen)

        if chosen == "hedge":
            result = self._run_hedge(symbol)
            if result.error is None:
                return result
            log.warning("Hedge mode failed (%s) — falling through to crypto", result.error)
            result2 = self._run_crypto(symbol)
            if result2.error is None:
                return result2
            result3 = self._run_agentic(symbol)
            return result3

        if chosen == "crypto":
            result = self._run_crypto(symbol)
            if result.error is None:
                return result
            log.warning("Crypto mode failed (%s) — falling through to agentic", result.error)
            return self._run_agentic(symbol)

        return self._run_agentic(symbol)

    def run_batch(self, symbols: list[str], mode: str = "auto") -> dict[str, PipelineResult]:
        results: dict[str, PipelineResult] = {}
        for sym in symbols:
            results[sym] = self.run(sym, mode=mode)
        return results
