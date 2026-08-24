"""Real-time Candle-Close Multi-Timeframe Scheduler.

Replaces the old timer-based scheduler with event-driven candle-close detection.
Monitors MT5 real-time ticks and triggers analysis on every candle close across
multiple timeframes (M15, H1, H4, D1).

Architecture:
    Tick Stream → Candle Close Detector → Per-TF Analysis Trigger →
    → Pipeline (multi-TF data + news + sentiment) → Trade → Notify → Eval → Evolve

The scheduler watches ALL tradable symbols and fires on candle close for ANY
timeframe. Each close triggers a full pipeline run for that symbol+TF combination,
with higher-TF data for alignment context.

Usage:
    from quant_nanggroe.engine.candle_scheduler import CandleScheduler
    scheduler = CandleScheduler()
    scheduler.start()  # runs in background thread
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# ── Timeframe definitions ────────────────────────────────────────────
# MT5 timeframe constants → seconds
TIMEFRAME_SECONDS = {
    "M1": 60, "M5": 300, "M15": 900, "M30": 1800,
    "H1": 3600, "H4": 14400, "D1": 86400, "W1": 604800, "MN1": 2592000,
}

# Active timeframes for analysis (M15 → D1 pyramid)
ANALYSIS_TIMEFRAMES = ["M15", "H1", "H4", "D1"]

# MT5 timeframe enum mapping
MT5_TF_MAP = {
    "M1": 1, "M5": 5, "M15": 15, "M30": 30,
    "H1": 16385, "H4": 16388, "D1": 16408, "W1": 32769, "MN1": 49153,
}


@dataclass
class CandleState:
    """Tracks the last closed candle timestamp per symbol per timeframe."""
    symbol: str
    timeframe: str
    last_close_time: float = 0.0  # unix timestamp of last known closed candle
    last_check: float = 0.0
    bars_processed: int = 0


@dataclass
class CycleResult:
    """Result of one analysis cycle."""
    symbol: str
    timeframe: str
    timestamp: str
    signal: str = "hold"
    confidence: float = 0.0
    traded: bool = False
    notified: bool = False
    error: Optional[str] = None
    duration_ms: float = 0.0


class CandleScheduler:
    """Real-time candle-close scheduler that monitors MT5 tick stream.

    On each tick, checks if a new candle has closed for any symbol+TF pair.
    When a close is detected, triggers the full analysis pipeline for that
    symbol using multi-timeframe data.

    Timeframe hierarchy:
        D1 close → run full analysis with D1+H4+H1+M15 data
        H4 close → run with H4+H1+M15 data
        H1 close → run with H1+M15 data
        M15 close → run with M15 data only

    The pipeline uses HTF data for bias/alignment and LTF for entry timing.
    """

    def __init__(
        self,
        symbols: Optional[list[str]] = None,
        timeframes: Optional[list[str]] = None,
        tick_interval: float = 1.0,
        min_confidence: float = 0.30,
    ):
        self.symbols = symbols  # None = discover from MT5
        self.timeframes = timeframes or ANALYSIS_TIMEFRAMES
        self.tick_interval = tick_interval  # seconds between tick checks
        self.min_confidence = min_confidence

        self._running = False
        self._start_time = time.time()
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._task: Optional[asyncio.Task] = None
        self._candle_states: dict[str, CandleState] = {}
        self._results: list[CycleResult] = []
        self._max_results = 500

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def recent_results(self) -> list[dict]:
        return [
            {
                "symbol": r.symbol, "timeframe": r.timeframe,
                "signal": r.signal, "confidence": r.confidence,
                "traded": r.traded, "notified": r.notified,
                "error": r.error, "timestamp": r.timestamp,
                "duration_ms": r.duration_ms,
            }
            for r in self._results[-50:]
        ]

    # ── Public API ──────────────────────────────────────────────────

    def start(self) -> None:
        """Start the candle scheduler in a background daemon thread."""
        if self._running:
            logger.warning("CandleScheduler already running")
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._run_event_loop,
            daemon=True,
            name="candle-scheduler",
        )
        self._thread.start()
        logger.info(
            "CandleScheduler started (TFs=%s, tick_interval=%.1fs)",
            self.timeframes, self.tick_interval,
        )

    def stop(self, timeout: float = 5.0) -> None:
        """Stop the scheduler gracefully."""
        self._running = False
        if self._loop and not self._loop.is_closed():
            future = asyncio.run_coroutine_threadsafe(
                self._cancel_task(), self._loop,
            )
            try:
                future.result(timeout=timeout)
            except (asyncio.TimeoutError, Exception):
                pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
        logger.info("CandleScheduler stopped")

    # ── Event loop ──────────────────────────────────────────────────

    def _run_event_loop(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._run_forever())
        except Exception:
            logger.exception("CandleScheduler event loop failed")
        finally:
            self._running = False
            try:
                self._loop.close()
            except Exception:
                pass

    async def _run_forever(self) -> None:
        self._task = asyncio.create_task(self._tick_loop())
        try:
            await self._task
        except asyncio.CancelledError:
            pass

    async def _cancel_task(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    # ── Core tick loop ──────────────────────────────────────────────

    async def _tick_loop(self) -> None:
        """Main loop: check for candle closes on every tick interval."""
        # Initial discovery
        symbols = await self._discover_symbols()
        if not symbols:
            logger.error("No tradable symbols found — scheduler idle")
            return

        # Initialize candle states
        await self._init_candle_states(symbols)

        logger.info(
            "CandleScheduler monitoring %d symbols x %d TFs = %d checks per tick",
            len(symbols), len(self.timeframes), len(symbols) * len(self.timeframes),
        )

        while self._running:
            try:
                await self._check_all_closes(symbols)
            except Exception as exc:
                logger.debug("Tick check error: %s", exc)
            await asyncio.sleep(self.tick_interval)

    async def _discover_symbols(self) -> list[str]:
        """Discover tradable symbols from the connected MT5 terminal."""
        if self.symbols:
            return self.symbols
        try:
            import MetaTrader5 as mt5
            raw = mt5.symbols_get() or []
            WANTED = {"EURUSD", "GBPUSD", "USDJPY", "USDCAD", "AUDUSD",
                      "NZDUSD", "XAUUSD", "XAGUSD", "USOIL", "UKOIL"}
            found = []
            for s in raw:
                base = s.name.split(".")[0] if "." in s.name else s.name
                if base.upper() in WANTED:
                    found.append(s.name)
            if found:
                logger.info("CandleScheduler discovered %d symbols: %s", len(found), found)
                return found
        except Exception as exc:
            logger.debug("Symbol discovery failed: %s", exc)
        return ["EURUSD", "GBPUSD", "XAUUSD"]

    async def _init_candle_states(self, symbols: list[str]) -> None:
        """Initialize candle states with current bar close times."""
        try:
            import MetaTrader5 as mt5
            from quant_nanggroe.connectors.mt5_broker import MT5Broker
            for sym in symbols:
                for tf in self.timeframes:
                    key = f"{sym}:{tf}"
                    tf_enum = MT5_TF_MAP.get(tf, 16408)  # default D1
                    try:
                        rates = mt5.copy_rates_from_pos(sym, tf_enum, 0, 2)
                        if rates and len(rates) >= 1:
                            # Last closed candle time
                            last_close = float(rates[-1][0])  # time column
                            self._candle_states[key] = CandleState(
                                symbol=sym, timeframe=tf,
                                last_close_time=last_close,
                            )
                        else:
                            self._candle_states[key] = CandleState(
                                symbol=sym, timeframe=tf, last_close_time=0,
                            )
                    except Exception:
                        self._candle_states[key] = CandleState(
                            symbol=sym, timeframe=tf, last_close_time=0,
                        )
            logger.info("Initialized %d candle states", len(self._candle_states))
        except Exception as exc:
            logger.warning("Candle state init failed: %s", exc)

    async def _check_all_closes(self, symbols: list[str]) -> None:
        """Check all symbol+TF pairs for candle closes."""
        import MetaTrader5 as mt5

        now = time.time()
        closes_detected = []

        for sym in symbols:
            for tf in self.timeframes:
                key = f"{sym}:{tf}"
                state = self._candle_states.get(key)
                if state is None:
                    continue

                tf_enum = MT5_TF_MAP.get(tf, 16408)
                try:
                    rates = mt5.copy_rates_from_pos(sym, tf_enum, 0, 2)
                    if not rates or len(rates) < 1:
                        continue
                    current_bar_time = float(rates[-1][0])
                    # New candle closed if bar time changed
                    if current_bar_time > state.last_close_time and state.last_close_time > 0:
                        closes_detected.append((sym, tf, current_bar_time))
                    state.last_close_time = current_bar_time
                    state.last_check = now
                except Exception:
                    pass

        # Process closes (higher TFs first for context)
        for sym, tf, bar_time in sorted(
            closes_detected,
            key=lambda x: TIMEFRAME_SECONDS.get(x[1], 0),
            reverse=True,
        ):
            await self._on_candle_close(sym, tf, bar_time)

    async def _on_candle_close(self, symbol: str, timeframe: str, bar_time: float) -> None:
        """Handle a candle close event — run full analysis pipeline."""
        t0 = time.perf_counter()
        key = f"{symbol}:{timeframe}"
        state = self._candle_states.get(key)
        if state:
            state.bars_processed += 1

        logger.info(
            "🕯️ CANDLE CLOSE: %s %s (bar_time=%.0f, #%d)",
            symbol, timeframe, bar_time,
            state.bars_processed if state else 0,
        )

        result = CycleResult(
            symbol=symbol, timeframe=timeframe,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

        try:
            # Run multi-TF analysis pipeline
            signal, confidence, traded = await self._run_analysis(symbol, timeframe)
            result.signal = signal
            result.confidence = confidence
            result.traded = traded

            # Notify on trade or high-confidence signal
            if traded or (confidence >= self.min_confidence and signal != "hold"):
                await self._notify(symbol, timeframe, signal, confidence, traded)

        except Exception as exc:
            result.error = str(exc)
            logger.warning("Analysis failed for %s %s: %s", symbol, timeframe, exc)

        result.duration_ms = (time.perf_counter() - t0) * 1000
        self._results.append(result)
        if len(self._results) > self._max_results:
            self._results = self._results[-self._max_results:]
        self._save_state()
        self._log_to_history(result)

    def _save_state(self) -> None:
        """Persist scheduler state to JSON for dashboard consumption."""
        try:
            import json
            from pathlib import Path
            state_dir = Path("data")
            state_dir.mkdir(exist_ok=True)
            state_file = state_dir / "candle_scheduler_state.json"
            events_file = state_dir / "notifications.json"

            state = {
                "running": self._running,
                "symbols": self.symbols or [],
                "timeframes": self.timeframes,
                "total_events": len(self._results),
                "last_event": self._results[-1].timestamp if self._results else None,
                "uptime_seconds": time.time() - (self._start_time if hasattr(self, "_start_time") else time.time()),
            }
            state_file.write_text(json.dumps(state, default=str), encoding="utf-8")

            # Also write notifications for the notifications page
            notifications = []
            for r in self._results:
                notifications.append({
                    "id": f"{r.symbol}:{r.timeframe}:{r.timestamp}",
                    "type": "trade" if r.traded else ("signal" if r.signal != "hold" else "system"),
                    "symbol": r.symbol,
                    "timeframe": r.timeframe,
                    "message": f"{r.signal.upper()} @ {r.confidence:.0%}" + (" [TRADED]" if r.traded else "") + (f" ERR: {r.error}" if r.error else ""),
                    "signal": r.signal,
                    "confidence": r.confidence,
                    "traded": r.traded,
                    "timestamp": r.timestamp,
                })
            events_file.write_text(json.dumps({"notifications": notifications}, default=str), encoding="utf-8")
        except Exception as exc:
            logger.debug("State save failed: %s", exc)

    def _log_to_history(self, result: "CycleResult") -> None:
        """Log event to SQLite trade history for unlimited persistence."""
        try:
            from quant_nanggroe.engine.trade_history import get_trade_history, TradeEvent
            history = get_trade_history()
            event = TradeEvent(
                symbol=result.symbol,
                timeframe=result.timeframe,
                signal=result.signal,
                confidence=result.confidence,
                traded=result.traded,
                notified=result.notified,
                error=result.error or "",
                duration_ms=result.duration_ms,
                timestamp=result.timestamp,
            )
            history.add_event(event)
        except Exception as exc:
            logger.debug("History log failed: %s", exc)

    async def _run_analysis(
        self, symbol: str, timeframe: str,
    ) -> tuple[str, float, bool]:
        """Run analysis for a symbol after candle close.

        Delegates to the autonomous pipeline which handles:
        data fetch, regime detection, signal generation, risk checks, execution.

        Returns (signal, confidence, traded).
        """
        try:
            import MetaTrader5 as mt5
            from quant_nanggroe.engine.agentic import get_autonomous_pipeline
            pipeline = get_autonomous_pipeline()
            if not pipeline.list_available_strategies():
                pipeline.load_strategies()

            # Run the full pipeline — it fetches its own data, generates signals,
            # runs risk checks, and executes trades
            result = await pipeline.run(
                symbol=symbol,
                strategy_name=None,
                data=None,
                timeframe=timeframe,
            )

            signal = result.signal if hasattr(result, "signal") else "hold"
            confidence = result.decision.get("confidence", 0.0) if hasattr(result, "decision") else 0.0
            traded = result.success and signal in ("buy", "sell")

            logger.info(
                "Pipeline %s %s: signal=%s conf=%.2f success=%s",
                symbol, timeframe, signal, confidence, result.success,
            )

            return signal, confidence, traded

        except Exception as exc:
            logger.debug("Pipeline failed for %s %s: %s", symbol, timeframe, exc)
            return "hold", 0.0, False

    def _check_mtf_alignment(
        self, tf_data: dict, primary_tf: str,
    ) -> dict:
        """Check if multiple timeframes are aligned in the same direction."""
        import pandas as pd
        biases = {}
        for tf, df in tf_data.items():
            if len(df) < 50:
                continue
            try:
                closes = df["close"]
                sma20 = closes.rolling(20).mean().iloc[-1]
                sma50 = closes.rolling(50).mean().iloc[-1] if len(closes) >= 50 else sma20
                current = closes.iloc[-1]
                if current > sma20 > sma50:
                    biases[tf] = "bullish"
                elif current < sma20 < sma50:
                    biases[tf] = "bearish"
                else:
                    biases[tf] = "neutral"
            except Exception:
                biases[tf] = "neutral"

        bullish = sum(1 for b in biases.values() if b == "bullish")
        bearish = sum(1 for b in biases.values() if b == "bearish")
        total = len(biases) or 1

        aligned = bullish >= total * 0.6 or bearish >= total * 0.6
        direction = "bullish" if bullish > bearish else "bearish" if bearish > bullish else "neutral"

        return {
            "aligned": aligned,
            "direction": direction,
            "biases": biases,
            "bullish_count": bullish,
            "bearish_count": bearish,
        }

    async def _notify(
        self, symbol: str, timeframe: str, signal: str,
        confidence: float, traded: bool,
    ) -> None:
        """Send notification about signal/trade."""
        try:
            from quant_nanggroe.notifier import send_telegram
            emoji = "🟢" if signal == "buy" else "🔴" if signal == "sell" else "⚪"
            trade_tag = " | TRADE EXECUTED ✅" if traded else ""
            msg = (
                f"{emoji} *QNA Signal*{trade_tag}\n"
                f"*{symbol}* [{timeframe}]\n"
                f"Signal: `{signal.upper()}` @ `{confidence:.0%}`\n"
                f"Time: {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}"
            )
            send_telegram(msg)
        except Exception as exc:
            logger.debug("Notification failed: %s", exc)


# ── Module-level singleton ───────────────────────────────────────────

_default_scheduler: Optional[CandleScheduler] = None


def start_candle_scheduler(
    symbols: Optional[list[str]] = None,
    timeframes: Optional[list[str]] = None,
    tick_interval: float = 1.0,
) -> CandleScheduler:
    """Create and start the default candle-close scheduler."""
    global _default_scheduler
    if _default_scheduler is not None and _default_scheduler.is_running:
        logger.warning("Default candle scheduler already running")
        return _default_scheduler
    _default_scheduler = CandleScheduler(
        symbols=symbols,
        timeframes=timeframes,
        tick_interval=tick_interval,
    )
    _default_scheduler.start()
    return _default_scheduler


def stop_candle_scheduler(timeout: float = 5.0) -> None:
    """Stop the default candle scheduler."""
    global _default_scheduler
    if _default_scheduler is not None:
        _default_scheduler.stop(timeout=timeout)
        _default_scheduler = None


__all__ = [
    "CandleScheduler",
    "start_candle_scheduler",
    "stop_candle_scheduler",
]
