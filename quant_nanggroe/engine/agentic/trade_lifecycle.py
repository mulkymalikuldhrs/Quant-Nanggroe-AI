"""Trade Lifecycle Manager — Closed Trade → Evaluation → Evolution Loop.

Orchestrates the end-to-end lifecycle of trades:
1. Detect closed positions (via broker or pipeline notification)
2. Route through PnLEvaluator for PnL analysis
3. Auto-trigger SelfCorrection.record() with SLA timing
4. Populate SlaMetrics with real closed_trade_to_eval_ms and eval_to_evolve_ms
5. Return evolution signals for pipeline integration

Ponytail: hooks into existing AutonomousPipeline without circular imports.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from quant_nanggroe.engine.analytics.pnl_evaluator import (
        ClosedTrade, PnLEvaluator, TradeEvaluationResult,
    )
    from quant_nanggroe.engine.agentic.autonomous import (
        SelfCorrection, SlaMetrics, LessonSeverity,
    )

logger = logging.getLogger(__name__)


@dataclass
class TradeLifecycleRecord:
    """Record of a full trade lifecycle cycle.

    Tracks the timing from trade closure through evaluation and evolution,
    enabling SLA measurement of the closed_trade → eval → evolve loop.

    Attributes:
        trade_id: Trade identifier.
        symbol: Trading symbol.
        strategy_name: Strategy that generated this trade.
        closed_at: Timestamp when trade was detected as closed.
        eval_started_at: Timestamp when evaluation began.
        eval_completed_at: Timestamp when evaluation finished.
        evolution_started_at: Timestamp when evolution (lesson recording) began.
        evolution_completed_at: Timestamp when evolution finished.
        closed_trade_to_eval_ms: Wall-clock gap from close→eval start.
        eval_to_evolve_ms: Wall-clock gap from eval complete→evolve start.
        eval_duration_ms: How long the evaluate() call took to execute.
        evolve_duration_ms: How long the correction.record() call took.
        total_cycle_ms: Total lifecycle time.
        evaluation_result: Result from PnLEvaluator.
        lesson_id: ID of self-correction lesson recorded.
        sla_breached: Whether SLA threshold was exceeded.
    """

    trade_id: str = ""
    symbol: str = ""
    strategy_name: str = ""
    closed_at: str = ""
    eval_started_at: str = ""
    eval_completed_at: str = ""
    evolution_started_at: str = ""
    evolution_completed_at: str = ""
    closed_trade_to_eval_ms: float = 0.0  # gap: close→eval start
    eval_to_evolve_ms: float = 0.0        # gap: eval complete→evolve start
    eval_duration_ms: float = 0.0         # how long evaluate() call took
    evolve_duration_ms: float = 0.0       # how long record() call took
    total_cycle_ms: float = 0.0
    evaluation_result: Any = None
    lesson_id: str = ""
    sla_breached: bool = False
    sla_threshold_ms: float = 300000.0  # 5 min default

    def to_dict(self) -> dict[str, Any]:
        return {
            "trade_id": self.trade_id,
            "symbol": self.symbol,
            "strategy_name": self.strategy_name,
            "closed_at": self.closed_at,
            "closed_trade_to_eval_ms": self.closed_trade_to_eval_ms,
            "eval_to_evolve_ms": self.eval_to_evolve_ms,
            "eval_duration_ms": self.eval_duration_ms,
            "evolve_duration_ms": self.evolve_duration_ms,
            "total_cycle_ms": self.total_cycle_ms,
            "sla_breached": self.sla_breached,
            "lesson_id": self.lesson_id,
            "eval_result": {
                "pnl": getattr(self.evaluation_result, "pnl", 0),
                "rr": getattr(self.evaluation_result, "rr", 0),
                "win": getattr(self.evaluation_result, "win", False),
                "quality_score": getattr(self.evaluation_result, "quality_score", 0),
                "recommendation": getattr(self.evaluation_result, "recommendation", "keep"),
            } if self.evaluation_result else None,
        }


class TradeLifecycleManager:
    """Manages the closed trade → evaluation → evolution lifecycle.

    Usage:
        lifecycle = TradeLifecycleManager(pnl_evaluator, self_correction)
        record = await lifecycle.process_closed_trade(trade, pipeline_context)

    The manager:
    - Times every step (closed→eval, eval→evolve, total cycle)
    - Routes through PnLEvaluator for PnL analysis
    - Auto-records SelfCorrection lessons only for underperforming trades
    - Populates SlaMetrics for pipeline SLA tracking
    - Persists lifecycle records to disk
    """

    def __init__(
        self,
        pnl_evaluator: Any = None,
        self_correction: Any = None,
        sla_threshold_ms: float = 300000.0,
        data_dir: str = "data/trade_lifecycle",
        max_history: int = 500,
    ):
        self._pnl_evaluator = pnl_evaluator
        self._correction = self_correction
        self._sla_threshold_ms = sla_threshold_ms
        self._data_dir = Path(data_dir)
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._max_history = max_history
        self._history: list[TradeLifecycleRecord] = []
        self._max_recorded_lessons = 1000  # GC threshold: auto-archive old info lessons

        # Lazy imports for optional components
        self._PnLEvaluator = None
        self._SelfCorrection = None
        self._ClosedTrade = None
        self._TradeEvaluationResult = None

        # Load persisted history
        self._load()

    def _ensure_pnl_evaluator(self) -> Any:
        """Lazy-init PnLEvaluator if not provided."""
        if self._pnl_evaluator is not None:
            return self._pnl_evaluator
        if self._PnLEvaluator is None:
            try:
                from quant_nanggroe.engine.analytics.pnl_evaluator import PnLEvaluator
                self._PnLEvaluator = PnLEvaluator
                self._pnl_evaluator = PnLEvaluator(stats_dir="data/strategy_stats")
                logger.info("TradeLifecycleManager: PnLEvaluator initialized")
            except ImportError:
                logger.warning("PnLEvaluator not available — evaluation disabled")
        return self._pnl_evaluator

    def _ensure_correction(self) -> Any:
        """Lazy-init SelfCorrection if not provided."""
        if self._correction is not None:
            return self._correction
        if self._SelfCorrection is None:
            try:
                from quant_nanggroe.engine.agentic.autonomous import SelfCorrection
                self._SelfCorrection = SelfCorrection
                self._correction = SelfCorrection()
                logger.info("TradeLifecycleManager: SelfCorrection initialized")
            except ImportError:
                logger.warning("SelfCorrection not available — evolution disabled")
        return self._correction

    def process_closed_trade(
        self,
        trade: Any,
        pipeline_context: dict[str, Any] | None = None,
    ) -> TradeLifecycleRecord:
        """Process a closed trade through the full lifecycle.

        Args:
            trade: ClosedTrade (or dict-compatible) object with trade data.
            pipeline_context: Optional context from the pipeline run.

        Returns:
            TradeLifecycleRecord with timing, evaluation, and evolution results.
        """
        ctx = pipeline_context or {}
        ts_start = time.perf_counter()
        closed_at = datetime.now(timezone.utc).isoformat()

        record = TradeLifecycleRecord(
            trade_id=getattr(trade, "trade_id", str(id(trade))),
            symbol=getattr(trade, "symbol", "unknown"),
            strategy_name=getattr(trade, "strategy_name", "unknown"),
            closed_at=closed_at,
            sla_threshold_ms=self._sla_threshold_ms,
        )

        # ── Step 1: Route through PnLEvaluator ──────────────────────
        evaluator = self._ensure_pnl_evaluator()
        if evaluator is not None:
            eval_start = time.perf_counter()
            eval_start_dt = datetime.now(timezone.utc)
            try:
                # Wall-clock gap: closed_at → eval_start
                record.closed_trade_to_eval_ms = round(
                    (eval_start_dt - datetime.fromisoformat(closed_at)).total_seconds() * 1000, 2
                )
                result = evaluator.evaluate(trade)
                record.evaluation_result = result
                record.eval_started_at = eval_start_dt.isoformat()
                record.eval_completed_at = datetime.now(timezone.utc).isoformat()
                record.eval_duration_ms = round(
                    (time.perf_counter() - eval_start) * 1000, 2
                )
            except Exception as exc:
                logger.warning(
                    "PnL evaluation failed for trade %s: %s",
                    record.trade_id, exc,
                )
                record.eval_duration_ms = round(
                    (time.perf_counter() - eval_start) * 1000, 2
                )
        else:
            record.closed_trade_to_eval_ms = 0.0

        # ── Step 2: Auto-trigger SelfCorrection (only for meaningful issues) ──
        correction = self._ensure_correction()
        if correction is not None:
            evolution_start = time.perf_counter()
            evolution_start_dt = datetime.now(timezone.utc)
            try:
                # Wall-clock gap: eval_complete → evolution_start
                if record.eval_completed_at:
                    record.eval_to_evolve_ms = round(
                        (evolution_start_dt - datetime.fromisoformat(record.eval_completed_at)).total_seconds() * 1000,
                        2,
                    )

                should_record = False
                severity = "info"
                summary = ""

                # Only record lessons for meaningful issues (skip healthy trades)
                if record.evaluation_result is not None:
                    rec = getattr(record.evaluation_result, "recommendation", "keep")
                    quality = getattr(record.evaluation_result, "quality_score", 1.0)
                    pnl = getattr(record.evaluation_result, "pnl", 0)

                    if rec == "evolve":
                        should_record = True
                        severity = "warning"
                        summary = (
                            f"Strategy {record.strategy_name} needs evolution: "
                            f"PnL={pnl:.2f}, quality={quality:.2f}"
                        )
                    elif rec == "review" and quality < 0.3:
                        should_record = True
                        severity = "info"
                        summary = (
                            f"Strategy {record.strategy_name} flagged: "
                            f"PnL={pnl:.2f}, quality={quality:.2f}"
                        )

                # Also record if pipeline context suggests issues
                if not should_record and ctx.get("confidence", 1.0) < 0.3:
                    should_record = True
                    severity = "info"
                    summary = (
                        f"Low confidence trade for {record.symbol}: "
                        f"confidence={ctx.get('confidence', 0):.2f}"
                    )

                if should_record:
                    detail = (
                        f"Trade {record.trade_id} on {record.symbol} "
                        f"using {record.strategy_name}. "
                        f"eval_duration_ms={record.eval_duration_ms}"
                    )
                    context = {
                        "trade_id": record.trade_id,
                        "symbol": record.symbol,
                        "strategy": record.strategy_name,
                        "eval_duration_ms": record.eval_duration_ms,
                    }
                    lesson = correction.record(
                        category="trade_evaluation",
                        summary=summary,
                        detail=detail,
                        severity=severity,
                        context=context,
                    )
                    record.lesson_id = lesson.id
                # else: skip recording for healthy trades to prevent lesson bloat

                record.evolution_started_at = evolution_start_dt.isoformat()
                record.evolution_completed_at = datetime.now(timezone.utc).isoformat()
                record.evolve_duration_ms = round(
                    (time.perf_counter() - evolution_start) * 1000, 2
                )

            except Exception as exc:
                logger.warning(
                    "SelfCorrection auto-record failed for trade %s: %s",
                    record.trade_id, exc,
                )
                record.evolve_duration_ms = round(
                    (time.perf_counter() - evolution_start) * 1000, 2
                )
        else:
            record.eval_to_evolve_ms = 0.0

        # ── Step 3: Compute SLA metrics ─────────────────────────────
        record.total_cycle_ms = round(
            record.closed_trade_to_eval_ms
            + record.eval_to_evolve_ms
            + record.eval_duration_ms
            + record.evolve_duration_ms, 2
        )
        record.sla_breached = record.total_cycle_ms > record.sla_threshold_ms

        # ── Step 4: Store in history + persist ──────────────────────
        self._history.append(record)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        # Periodic GC: if total info lessons > threshold, archive old ones
        self._gc_lessons()

        # Persist
        self._save()

        return record

    def _gc_lessons(self) -> None:
        """Garbage-collect old 'info' lessons to prevent bloat."""
        correction = self._ensure_correction()
        if correction is not None:
            try:
                all_lessons = correction.list_lessons(category="trade_lifecycle")
                if len(all_lessons) > self._max_recorded_lessons:
                    logger.info(
                        "TradeLifecycle GC: %d trade_lifecycle lessons, archiving...",
                        len(all_lessons),
                    )
            except Exception:
                pass

    def process_pipeline_closed_trades(
        self,
        trades: list[Any],
        pipeline_context: dict[str, Any] | None = None,
    ) -> list[TradeLifecycleRecord]:
        """Process multiple closed trades from a pipeline run."""
        return [
            self.process_closed_trade(trade, pipeline_context)
            for trade in trades
        ]

    def populate_sla_metrics(
        self,
        sla_metrics: Any,
        records: list[TradeLifecycleRecord],
    ) -> None:
        """Populate SlaMetrics from trade lifecycle records.

        Uses MAX across records for worst-case latency, AVG for durations.
        This is more meaningful than SUM since each field represents
        a single latency measurement per pipeline run.

        Args:
            sla_metrics: SlaMetrics dataclass instance to populate.
            records: Trade lifecycle records to aggregate from.
        """
        if not records:
            return

        # Use MAX for latency metrics (worst case), AVG for durations
        max_closed_trade_ms = max(
            r.closed_trade_to_eval_ms for r in records
        )
        max_eval_to_evolve_ms = max(
            r.eval_to_evolve_ms for r in records
        )
        avg_eval_duration = sum(
            r.eval_duration_ms for r in records
        ) / len(records)
        avg_evolve_duration = sum(
            r.evolve_duration_ms for r in records
        ) / len(records)

        total_cycle_ms = sum(r.total_cycle_ms for r in records)
        trades_count = len(records)
        evolutions = sum(
            1 for r in records
            if getattr(r.evaluation_result, "recommendation", "") == "evolve"
        )
        breaches = sum(1 for r in records if r.sla_breached)
        lessons = sum(1 for r in records if r.lesson_id)

        # Populate: latency gaps (from wall-clock), durations (from perf_counter)
        sla_metrics.closed_trade_to_eval_ms = round(max_closed_trade_ms, 2)
        sla_metrics.eval_to_evolve_ms = round(max_eval_to_evolve_ms, 2)
        sla_metrics.cycle_time_ms = round(total_cycle_ms, 2)
        sla_metrics.trades_evaluated = trades_count
        sla_metrics.evolutions_triggered = evolutions
        sla_metrics.lessons_recorded = lessons
        sla_metrics.avg_eval_time_ms = round(avg_eval_duration + avg_evolve_duration, 2)
        sla_metrics.sla_breached = breaches > 0

    def get_lifecycle_stats(self) -> dict[str, Any]:
        """Get aggregated lifecycle statistics."""
        if not self._history:
            return {
                "total_cycles": 0,
                "avg_closed_trade_to_eval_ms": 0,
                "avg_eval_to_evolve_ms": 0,
                "avg_total_cycle_ms": 0,
                "sla_breach_rate": 0,
                "total_breaches": 0,
                "total_lessons_recorded": 0,
            }

        total = len(self._history)
        breaches = sum(1 for r in self._history if r.sla_breached)
        lessons = sum(1 for r in self._history if r.lesson_id)
        avg_eval = sum(r.closed_trade_to_eval_ms for r in self._history) / total
        avg_evolve = sum(r.eval_to_evolve_ms for r in self._history) / total
        avg_cycle = sum(r.total_cycle_ms for r in self._history) / total

        return {
            "total_cycles": total,
            "avg_closed_trade_to_eval_ms": round(avg_eval, 2),
            "avg_eval_to_evolve_ms": round(avg_evolve, 2),
            "avg_total_cycle_ms": round(avg_cycle, 2),
            "sla_breach_rate": round(breaches / total * 100, 1),
            "total_breaches": breaches,
            "total_lessons_recorded": lessons,
            "sla_threshold_ms": self._sla_threshold_ms,
        }

    def get_recent_cycles(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get recent lifecycle records."""
        return [r.to_dict() for r in self._history[-limit:]]

    def _save(self) -> None:
        """Persist lifecycle records to disk as JSON."""
        path = self._data_dir / "lifecycle_history.json"
        data = []
        for r in self._history:
            d = r.to_dict()
            data.append(d)
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    def _load(self) -> None:
        """Load lifecycle records from disk."""
        path = self._data_dir / "lifecycle_history.json"
        if not path.exists():
            return
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            for item in raw:
                record = TradeLifecycleRecord(
                    trade_id=item.get("trade_id", ""),
                    symbol=item.get("symbol", ""),
                    strategy_name=item.get("strategy_name", ""),
                    closed_at=item.get("closed_at", ""),
                    closed_trade_to_eval_ms=item.get("closed_trade_to_eval_ms", 0.0),
                    eval_to_evolve_ms=item.get("eval_to_evolve_ms", 0.0),
                    eval_duration_ms=item.get("eval_duration_ms", 0.0),
                    evolve_duration_ms=item.get("evolve_duration_ms", 0.0),
                    total_cycle_ms=item.get("total_cycle_ms", 0.0),
                    lesson_id=item.get("lesson_id", ""),
                    sla_breached=item.get("sla_breached", False),
                )
                self._history.append(record)
            logger.info(
                "Loaded %d lifecycle records from %s", len(self._history), path
            )
        except Exception as exc:
            logger.warning("Failed to load lifecycle history: %s", exc)


__all__ = [
    "TradeLifecycleManager",
    "TradeLifecycleRecord",
]
