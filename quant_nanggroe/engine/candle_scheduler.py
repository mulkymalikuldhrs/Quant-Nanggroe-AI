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
import os
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
        # ── WAR-TIME GUARD (2026-08-25): NOTHING in-process may tear down
        # the shared MT5 IPC. Multiple components call mt5.shutdown()
        # (account_discovery, guardian, assistant...) which kills EVERY
        # consumer in this process — root cause of "scheduler sees empty
        # rates forever". The MetaTrader5 module is a process-global singleton;
        # shutdown anywhere = blackout everywhere. Neutralize it.
        try:
            import MetaTrader5 as _mt5mod
            if not getattr(_mt5mod, "_qna_shutdown_guarded", False):
                _orig_shutdown = _mt5mod.shutdown

                def _guarded_shutdown(*a, **kw):
                    logger.warning(
                        "mt5.shutdown() BLOCKED by scheduler guard "
                        "(shared IPC protected)")
                    return None

                _mt5mod.shutdown = _guarded_shutdown
                _mt5mod._qna_shutdown_guarded = True  # type: ignore[attr-defined]
                logger.info("MT5 shutdown guard installed (IPC protected)")
        except Exception as _guard_exc:
            logger.error("shutdown guard install failed: %s", _guard_exc)

        # ── MT5 INIT: reuse the builder's live session — NEVER re-init ──
        # HOTFIX (2026-08-25): calling mt5.initialize() a SECOND time (after
        # build_execution_manager already initialized the terminal) corrupts
        # the IPC channel — every copy_rates_from_pos then returned empty
        # ("Bar probe returning EMPTY for 64/64 pairs") and ZERO candle closes
        # were ever detected. The MetaTrader5 module is process-global.
        try:
            import MetaTrader5 as mt5

            info = mt5.account_info()
            if info is None:
                term = os.environ.get(
                    "MT5_TERMINAL_PATH",
                    r"C:\Program Files\MetaTrader 5\terminal64.exe")
                if not mt5.initialize(path=term, timeout=15000):
                    logger.error("MT5 initialize failed in scheduler thread — retrying in 10s")
                    await asyncio.sleep(10)
                    if not mt5.initialize(path=term, timeout=15000):
                        logger.error("MT5 initialize failed again — scheduler idle")
                        return
                info = mt5.account_info()
            if info:
                logger.info("MT5 ready in scheduler thread: login=%s server=%s",
                            info.login, info.server)
            else:
                logger.warning("MT5 initialized but no account info — proceeding anyway")
        except Exception as exc:
            logger.error("MT5 init in scheduler thread failed: %s", exc)
            return

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

        tick_count = 0
        total_closes = 0
        last_error_log = 0.0

        while self._running:
            try:
                # FIX (2026-08-25): MT5 C-API is NOT thread-safe.
                # run_in_executor spawns a fresh thread with NO MT5 handle —
                # copy_rates_from_pos returns None silently → zero closes.
                # Run the probe DIRECTLY in this thread (the scheduler thread)
                # which already called mt5.initialize() above.
                detected = self._check_all_closes_sync(symbols)
                total_closes += len(detected)
                for sym, tf, bar_time in sorted(
                    detected,
                    key=lambda x: TIMEFRAME_SECONDS.get(x[1], 0),
                    reverse=True,
                ):
                    await self._on_candle_close(sym, tf, bar_time)
            except Exception as exc:
                now_mono = time.monotonic()
                if now_mono - last_error_log > 300:
                    logger.warning("Tick check error: %s", exc)
                    last_error_log = now_mono
            tick_count += 1
            # Heartbeat every 5 min: proves the loop is ticking even when
            # nothing fires, and counts lifetime closes.
            if tick_count % 300 == 0:
                stats = getattr(self, "_last_probe_stats", {})
                logger.info(
                    "CandleScheduler heartbeat: ticks=%d, closes_total=%d, "
                    "states=%d, probe_empty=%s/%s",
                    tick_count, total_closes, len(self._candle_states),
                    stats.get("empty", "?"), stats.get("total", "?"),
                )
            # JournalSync every hour (3600 ticks at 1s interval).
            # Runs HERE in the scheduler thread where MT5 is initialized.
            if tick_count % 3600 == 0:
                try:
                    from quant_nanggroe.engine.journal_sync import async_sync_mt5_deals
                    res = await async_sync_mt5_deals()
                    logger.info("JournalSync: %s", res)
                except Exception as _je:
                    logger.warning("JournalSync failed: %s", _je)
            await asyncio.sleep(self.tick_interval)

    def _get_broker_mt5(self):
        """Return the LIVE MT5Broker whose session provably serves rates.

        HOTFIX (2026-08-25): bare-module copy_rates_from_pos inside the
        executor returned EMPTY for 64/64 pairs while the broker-owned handle
        served 500 bars in the same process. Prefer the broker session;
        fall back to bare module only when no live broker exists.
        """
        try:
            from quant_nanggroe.engine.execution.builder import (
                _em_singleton as _em,
            )
            if _em is not None:
                for b in _em.get_brokers().values():
                    h = getattr(b, "_mt5", None)
                    if h is not None and getattr(h, "connected", False):
                        return h
        except Exception:
            pass
        return None

    def _check_all_closes_sync(self, symbols: list[str]) -> list[tuple[str, str, float]]:
        """Synchronous bar-time scan returning detected closes.

        Runs in the scheduler thread (same thread that called mt5.initialize).

        v8.0.11 FIX: Use broker.get_rates() as primary data source — it routes
        through the broker's own MT5 handle (initialized once at startup) and
        resolves symbol suffixes (.vxc etc.) automatically. Bare MT5 module
        loses IPC connection between probes, causing 32/32 EMPTY.
        """
        now = time.time()
        closes_detected = []
        empty_count = 0

        broker = self._get_broker_mt5()
        use_broker = broker is not None and getattr(broker, "connected", False)

        for sym in symbols:
            for tf in self.timeframes:
                key = f"{sym}:{tf}"
                state = self._candle_states.get(key)
                if state is None:
                    continue

                tf_enum = MT5_TF_MAP.get(tf, 16408)
                try:
                    if use_broker:
                        rates = broker.get_rates(sym, tf_enum, count=2)
                    else:
                        import MetaTrader5 as mt5
                        mt5.symbol_select(sym, True)
                        rates = mt5.copy_rates_from_pos(sym, tf_enum, 0, 2)

                    if rates is None or len(rates) < 1:
                        empty_count += 1
                        continue

                    current_bar_time = float(rates[-1][0])
                    if state.last_close_time == 0:
                        state.last_close_time = current_bar_time
                    elif current_bar_time > state.last_close_time:
                        closes_detected.append((sym, tf, current_bar_time))
                        state.last_close_time = current_bar_time
                    state.last_check = now
                except Exception:
                    empty_count += 1

        self._last_probe_stats = {"empty": empty_count,
                                  "total": len(symbols) * len(self.timeframes)}
        if empty_count and not closes_detected:
            if not getattr(self, "_warned_empty", False):
                logger.warning(
                    "Bar probe returning EMPTY for %d/%d pairs — check "
                    "Market Watch symbol selection / terminal feed",
                    empty_count, len(symbols) * len(self.timeframes),
                )
                self._warned_empty = True
            # SELF-HEAL: re-init bare MT5 and probe single pair to verify IPC
            now_mono = time.monotonic()
            if now_mono - getattr(self, "_last_reinit", 0.0) > 60.0:
                self._last_reinit = now_mono
                try:
                    import MetaTrader5 as mt5
                    ok = mt5.initialize()
                    probe = mt5.copy_rates_from_pos(
                        symbols[0], MT5_TF_MAP.get("M15", 15), 0, 2)
                    got = None if probe is None else len(probe)
                    logger.warning(
                        "SELF-HEAL: re-init=%s, probe %s M15 -> %s bars",
                        ok, symbols[0], got,
                    )
                    if got:
                        self._warned_empty = False
                except Exception as _he:
                    logger.error("SELF-HEAL failed: %s", _he)
        return closes_detected

    async def _discover_symbols(self) -> list[str]:
        """Discover tradable symbols from the connected MT5 terminal."""
        if self.symbols:
            return self.symbols
        try:
            import MetaTrader5 as mt5
            raw = mt5.symbols_get() or []
            WANTED = {"EURUSD", "GBPUSD", "USDJPY", "USDCAD", "AUDUSD",
                      "NZDUSD", "USDCHF", "EURGBP"}
            # Collect all candidates per base name, prefer suffixed (tradeable)
            candidates: dict[str, list[str]] = {}
            for s in raw:
                if not s.visible:
                    continue
                base = s.name.split(".")[0] if "." in s.name else s.name
                if base.upper() in WANTED:
                    candidates.setdefault(base.upper(), []).append(s.name)
            found = []
            for base, names in candidates.items():
                # v8.0.11 FIX: On ValetaxIntl-Live2, .vx symbols have
                # trade_mode=4 (CFD data only, CANNOT trade). Bare symbols
                # (e.g. EURUSD) have trade_mode=0 (tradeable). Prefer BARE.
                bare = [n for n in names if "." not in n]
                suffixed = [n for n in names if "." in n]
                if bare:
                    found.append(bare[0])
                elif suffixed:
                    found.append(suffixed[0])
            if found:
                logger.info("CandleScheduler discovered %d symbols: %s", len(found), found)
                return found
        except Exception as exc:
            logger.warning("Symbol discovery failed: %s", exc)
        return ["EURUSD", "GBPUSD", "USDJPY", "USDCAD", "AUDUSD", "NZDUSD", "USDCHF", "EURGBP"]

    async def _init_candle_states(self, symbols: list[str]) -> None:
        """Initialize candle states with current bar close times.

        v8.0.11: Use broker.get_rates() which resolves suffixes and reconnects.
        """
        broker = self._get_broker_mt5()
        use_broker = broker is not None and getattr(broker, "connected", False)
        init_count = 0
        for sym in symbols:
            for tf in self.timeframes:
                key = f"{sym}:{tf}"
                tf_enum = MT5_TF_MAP.get(tf, 16408)
                try:
                    if use_broker:
                        rates = broker.get_rates(sym, tf_enum, count=2)
                    else:
                        import MetaTrader5 as mt5
                        mt5.symbol_select(sym, True)
                        rates = mt5.copy_rates_from_pos(sym, tf_enum, 0, 2)
                    if rates is not None and len(rates) >= 1:
                        last_close = float(rates[-1][0])
                        self._candle_states[key] = CandleState(
                            symbol=sym, timeframe=tf,
                            last_close_time=last_close,
                        )
                        init_count += 1
                    else:
                        self._candle_states[key] = CandleState(
                            symbol=sym, timeframe=tf, last_close_time=0,
                        )
                except Exception:
                    self._candle_states[key] = CandleState(
                        symbol=sym, timeframe=tf, last_close_time=0,
                    )
        logger.info("Initialized %d/%d candle states (broker=%s)",
                     init_count, len(symbols) * len(self.timeframes), use_broker)

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
                        logger.debug("No rates for %s %s — MT5 returned empty", sym, tf)
                        continue
                    current_bar_time = float(rates[-1][0])
                    # New candle closed if bar time changed
                    if current_bar_time > state.last_close_time and state.last_close_time > 0:
                        closes_detected.append((sym, tf, current_bar_time))
                    state.last_close_time = current_bar_time
                    state.last_check = now
                except Exception as exc:
                    logger.debug("Rate fetch failed %s %s: %s", sym, tf, exc)

        # Process closes (higher TFs first for context)
        for sym, tf, bar_time in sorted(
            closes_detected,
            key=lambda x: TIMEFRAME_SECONDS.get(x[1], 0),
            reverse=True,
        ):
            await self._on_candle_close(sym, tf, bar_time)

        return len(closes_detected)

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
        self._publish_event(result)

    def _publish_event(self, result: "CycleResult") -> None:
        """Push candle-close event to the WS event bus (never blocks)."""
        try:
            from quant_nanggroe.engine.candle_events import publish_candle_event
            publish_candle_event({
                "id": f"{result.symbol}:{result.timeframe}:{result.timestamp}",
                "type": "trade" if result.traded else ("signal" if result.signal != "hold" else "system"),
                "symbol": result.symbol,
                "timeframe": result.timeframe,
                "signal": result.signal,
                "confidence": result.confidence,
                "traded": result.traded,
                "duration_ms": round(result.duration_ms, 1),
                "error": result.error or "",
                "timestamp": result.timestamp,
            })
        except Exception as exc:
            logger.debug("candle event publish skipped: %s", exc)

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
                # Last 50 results so /api/candle-monitor has real events to serve
                "events": [
                    {
                        "symbol": r.symbol,
                        "timeframe": r.timeframe,
                        "timestamp": r.timestamp,
                        "signal": r.signal,
                        "confidence": r.confidence,
                        "traded": r.traded,
                        "notified": r.notified,
                        "error": r.error,
                        "duration_ms": round(r.duration_ms, 1),
                    }
                    for r in self._results[-50:]
                ],
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
            # R3 hotfix: traded must come from the ACTUAL execution verdict,
            # not pipeline success (a risk-vetoed/rejected order reported
            # success and produced fake "TRADE EXECUTED" alerts).
            exec_info = result.decision.get("execution", {}) if hasattr(result, "decision") else {}
            traded = isinstance(exec_info, dict) and exec_info.get("execution") == "filled"

            logger.info(
                "Pipeline %s %s: signal=%s conf=%.2f success=%s execution=%s",
                symbol, timeframe, signal, confidence, result.success,
                (exec_info.get("execution") if isinstance(exec_info, dict) else "?"),
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
