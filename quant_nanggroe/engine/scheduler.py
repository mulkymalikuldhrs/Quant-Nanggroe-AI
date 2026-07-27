"""Pipeline Scheduler — runs AutonomousPipeline periodically.

Wired into:
  - ``api/app.py`` lifespan (via ``QNA_SCHEDULER_ENABLED`` env var)
  - ``qna.py daemon`` mode (auto-starts when ``QNA_SCHEDULER_ENABLED`` is set)

Usage::

    from quant_nanggroe.engine.scheduler import PipelineScheduler

    scheduler = PipelineScheduler(interval_minutes=15)
    scheduler.start()
    ...
    scheduler.stop()
"""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)


class PipelineScheduler:
    """Periodic scheduler for the AutonomousPipeline.

    Runs ``AutonomousPipeline.run_batch()`` on a configurable interval.
    Uses a background thread with its own asyncio event loop so it works
    with or without a pre-existing event loop (e.g. inside the sync daemon).
    """

    def __init__(
        self,
        interval_minutes: int = 15,
        symbols: Optional[list[str]] = None,
    ):
        if interval_minutes < 1:
            raise ValueError("interval_minutes must be >= 1")

        self.interval_minutes = interval_minutes
        self.symbols = symbols or [
            "BTC-USD", "ETH-USD", "SOL-USD", "EURUSD", "USDJPY",
        ]

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._task: Optional[asyncio.Task] = None

    # ── public API ──────────────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        """Start the scheduler in a background daemon thread."""
        if self._running:
            logger.warning("PipelineScheduler already running")
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._run_event_loop,
            daemon=True,
            name="pipeline-scheduler",
        )
        self._thread.start()
        logger.info(
            "PipelineScheduler started (interval=%d min, symbols=%s)",
            self.interval_minutes,
            self.symbols,
        )

    def stop(self, timeout: float = 5.0) -> None:
        """Stop the scheduler gracefully."""
        self._running = False

        if self._loop is not None and not self._loop.is_closed():
            future = asyncio.run_coroutine_threadsafe(
                self._cancel_task(), self._loop,
            )
            try:
                future.result(timeout=timeout)
            except asyncio.TimeoutError:
                logger.warning("PipelineScheduler stop timed out")
            except Exception as exc:
                logger.warning("PipelineScheduler stop error: %s", exc)

        if self._thread is not None and self._thread.is_alive():
            self._thread.join(timeout=timeout)

        logger.info("PipelineScheduler stopped")

    # ── internals ───────────────────────────────────────────────────

    def _run_event_loop(self) -> None:
        """Run the async scheduler loop in a dedicated event loop."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._run_forever())
        except Exception:
            logger.exception("PipelineScheduler event loop failed")
        finally:
            try:
                self._loop.close()
            except Exception:
                pass

    async def _run_forever(self) -> None:
        """Wrap the scheduler loop as a task so it can be cancelled."""
        self._task = asyncio.create_task(self._run_loop())
        try:
            await self._task
        except asyncio.CancelledError:
            pass

    async def _cancel_task(self) -> None:
        """Cancel the running task from the event loop thread."""
        if self._task is not None and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _run_loop(self) -> None:
        """Main scheduler loop — cycle then sleep."""
        while self._running:
            await self._run_cycle()
            if self._running:
                await asyncio.sleep(self.interval_minutes * 60)

    async def _run_cycle(self) -> None:
        """Execute one pipeline cycle for all configured symbols."""
        logger.info(
            "Scheduler cycle starting (symbols=%s)",
            self.symbols,
        )

        try:
            from quant_nanggroe.engine.agentic import get_autonomous_pipeline

            pipeline = get_autonomous_pipeline()
            if not pipeline.list_available_strategies():
                pipeline.load_strategies()

            results = await pipeline.run_batch(symbols=self.symbols)
            success_count = sum(1 for r in results if r.success)

            logger.info(
                "Scheduler cycle complete: %d/%d succeeded",
                success_count,
                len(results),
            )

            for r in results:
                if not r.success:
                    logger.warning(
                        "Symbol %s failed: %s", r.symbol, r.reason,
                    )

        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Scheduler cycle failed: %s", exc)
            try:
                from quant_nanggroe.engine.agentic import SelfCorrection
                from quant_nanggroe.engine.agentic.autonomous import (
                    LessonSeverity,
                )
                sc = SelfCorrection()
                sc.record(
                    category="scheduler",
                    summary="Pipeline cycle failed",
                    detail=str(exc),
                    severity=LessonSeverity.ERROR,
                )
            except Exception as inner:
                logger.warning(
                    "Failed to record lesson for cycle failure: %s", inner,
                )


# ── module-level convenience ──────────────────────────────────────────

_default_scheduler: Optional[PipelineScheduler] = None


def start_default_scheduler(
    interval_minutes: int = 15,
    symbols: Optional[list[str]] = None,
) -> PipelineScheduler:
    """Create and start the default pipeline scheduler.

    The scheduler runs until ``stop_default_scheduler()`` is called.
    Subsequent calls return the same (running) instance.
    """
    global _default_scheduler
    if _default_scheduler is not None and _default_scheduler.is_running:
        logger.warning("Default scheduler already running, returning existing")
        return _default_scheduler
    _default_scheduler = PipelineScheduler(
        interval_minutes=interval_minutes,
        symbols=symbols,
    )
    _default_scheduler.start()
    return _default_scheduler


def stop_default_scheduler(timeout: float = 5.0) -> None:
    """Stop the default pipeline scheduler if running."""
    global _default_scheduler
    if _default_scheduler is not None:
        _default_scheduler.stop(timeout=timeout)
        _default_scheduler = None


__all__ = [
    "PipelineScheduler",
    "start_default_scheduler",
    "stop_default_scheduler",
]
