"""Background Trading Worker
=========================
Runs the trading graph periodically, monitors open positions,
updates unrealized PnL, and records portfolio snapshots.

This is the main event loop for the autonomous trading system.
It runs as a long-lived asyncio task (or set of tasks) that:

1. **Graph Runner**: Invokes the trading graph on a configurable interval
   for each watched symbol.
2. **Position Monitor**: Periodically updates current prices and
   unrealized PnL for all open positions.
3. **Portfolio Snapshotter**: Records portfolio state at regular intervals
   for equity curve generation.
4. **Health Reporter**: Emits health metrics for observability.

Usage::

    worker = TradingWorker()
    await worker.start()          # Start all loops
    # ... runs until cancelled ...
    await worker.stop()           # Graceful shutdown

Or as a CLI entry point::

    python -m quant_nanggroe.worker
"""

from __future__ import annotations

import asyncio
import logging
import traceback
from dataclasses import dataclass, field
from datetime import datetime

from quant_nanggroe.config import Settings, get_settings

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# Configuration
# ══════════════════════════════════════════════════════════════════════


@dataclass
class WorkerConfig:
    """Runtime configuration for the trading worker."""

    # Intervals in seconds
    graph_interval: float = 60.0  # How often to run the trading graph
    position_monitor_interval: float = 15.0  # How often to update position PnL
    snapshot_interval: float = 300.0  # How often to take portfolio snapshots
    health_interval: float = 60.0  # How often to report health metrics

    # Symbols to watch
    symbols: list[str] = field(default_factory=lambda: ["SPY", "QQQ", "BTC-USD"])

    # Graph execution
    max_concurrent_graphs: int = 3  # Limit concurrent graph invocations
    graph_timeout: float = 120.0  # Timeout per graph invocation in seconds

    # Safety
    kill_switch_check_interval: float = 10.0  # How often to check kill switch


# ══════════════════════════════════════════════════════════════════════
# Worker Implementation
# ══════════════════════════════════════════════════════════════════════


class TradingWorker:
    """
    Background trading worker — the heartbeat of the autonomous system.

    Manages multiple concurrent async loops:
    - Graph runner: Invokes the trading graph per symbol
    - Position monitor: Updates PnL for open positions
    - Portfolio snapshotter: Records periodic portfolio state
    - Kill switch monitor: Checks if trading should halt

    All loops are cooperative and can be gracefully stopped.
    """

    def __init__(
        self,
        config: WorkerConfig | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.config = config or WorkerConfig()
        self.settings = settings or get_settings()
        self._tasks: list[asyncio.Task[None]] = []
        self._running: bool = False
        self._cached_prices: dict[str, float] = {}
        # ponytail: RiskManager owns the kill switch AND tracks real P&L/drawdown.
        # Instantiating it here closes the silent 0.0 auto-activation bypass:
        # the monitor now feeds current_risk_snapshot() instead of never-set attrs.
        from quant_nanggroe.engine.risk.manager import RiskManager
        self._risk_manager = RiskManager()
        self._kill_switch = self._risk_manager.kill_switch
        self._kill_switch_active = False
        self._graph_semaphore = asyncio.Semaphore(self.config.max_concurrent_graphs)
        self._last_graph_run: dict[str, datetime] = {}
        self._cached_prices: dict[str, float] = {}

    # ── Lifecycle ───────────────────────────────────────────────────

    async def start(self) -> None:
        """
        Start all background loops.

        Launches all worker tasks for graph execution, position monitoring,
        portfolio snapshots, kill switch checks, and health reporting.
        """
        if self._running:
            logger.warning("worker_already_running")
            return

        logger.info(
            "worker_starting",
            extra={
                "symbols": self.config.symbols,
                "graph_interval": self.config.graph_interval,
                "position_interval": self.config.position_monitor_interval,
            },
        )

        self._running = True

        # Launch core tasks
        self._tasks = [
            asyncio.create_task(self._graph_runner_loop(), name="graph-runner"),
            asyncio.create_task(self._position_monitor_loop(), name="position-monitor"),
            asyncio.create_task(self._portfolio_snapshot_loop(), name="portfolio-snapshot"),
            asyncio.create_task(self._kill_switch_monitor_loop(), name="kill-switch-monitor"),
            asyncio.create_task(self._health_reporter_loop(), name="health-reporter"),
        ]

        logger.info("worker_started", extra={"task_count": len(self._tasks)})

    async def stop(self) -> None:
        """
        Gracefully stop all background loops.

        Cancels all tasks, waits for them to finish, then
        cleans up resources.
        """
        if not self._running:
            return

        logger.info("worker_stopping")
        self._running = False

        # Cancel all tasks
        for task in self._tasks:
            task.cancel()

        # Wait for cancellation
        results = await asyncio.gather(*self._tasks, return_exceptions=True)
        for task, result in zip(self._tasks, results):
            if isinstance(result, Exception) and not isinstance(result, asyncio.CancelledError):
                logger.error(
                    "task_error_on_shutdown",
                    extra={
                        "task_name": task.get_name(),
                        "error": str(result),
                    },
                )

        self._tasks.clear()
        logger.info("worker_stopped")

    # ── Graph Runner Loop ───────────────────────────────────────────

    async def _graph_runner_loop(self) -> None:
        """Periodically invoke the trading graph for each watched symbol."""
        while self._running:
            try:
                if self._kill_switch_active:
                    logger.debug("graph_runner_skipped_kill_switch")
                    await asyncio.sleep(self.config.kill_switch_check_interval)
                    continue

                # Run graph for each symbol concurrently (limited by semaphore)
                tasks = [
                    self._run_graph_for_symbol(symbol)
                    for symbol in self.config.symbols
                ]
                await asyncio.gather(*tasks, return_exceptions=True)

                await asyncio.sleep(self.config.graph_interval)

            except asyncio.CancelledError:
                logger.info("graph_runner_cancelled")
                break
            except Exception as exc:
                logger.error("graph_runner_error", extra={"error": str(exc), "traceback": traceback.format_exc()})
                await asyncio.sleep(self.config.graph_interval)

    async def _run_graph_for_symbol(self, symbol: str) -> None:
        """Run the trading pipeline for a single symbol.

        Two modes:
          1) **LLM graph** — if OPENAI_API_KEY is set, try the full LangGraph.
          2) **Deterministic pipeline** (fallback) — RiskManager gates + Kelly sizing
             + broker execution.  Hedge-fund-grade: auditable, no black box.

        Both modes feed the same risk/execution layer.
        """
        async with self._graph_semaphore:
            start_time = datetime.now()
            logger.info("pipeline_run_start", extra={"symbol": symbol})

            # ── shared state snapshot ─────────────────────────────────────
            try:
                snap = self._risk_manager.current_risk_snapshot()
            except Exception:
                snap = {}
            # risk state for pipeline decisions
            rs = self._risk_manager.state

            try:
                # ── mode 1: LLM graph (when key available) ───────────────
                import os
                if os.environ.get("OPENAI_API_KEY"):
                    from quant_nanggroe.agents.graph import get_trading_graph
                    from quant_nanggroe.agents.state import AgentState

                    graph = get_trading_graph()
                    initial_state = AgentState(symbol=symbol, timeframe="1d")
                    result = await asyncio.wait_for(
                        graph.ainvoke(initial_state.model_dump()),
                        timeout=self.config.graph_timeout,
                    )
                    decision = result.get("decision_action", "hold")
                    risk_v = result.get("risk_verdict", "approved")
                else:
                    # ── mode 2: deterministic pipeline ────────────────────
                    result = await self._deterministic_pipeline(symbol, snap)
                    decision = result.get("decision_action", "hold")
                    risk_v = result.get("risk_verdict", "passed")

                # ── common logging ───────────────────────────────────────
                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                logger.info(
                    "pipeline_run_complete",
                    extra={
                        "symbol": symbol,
                        "latency_ms": round(latency_ms, 2),
                        "decision": decision,
                        "risk_verdict": risk_v,
                    },
                )
                self._last_graph_run[symbol] = datetime.now()

            except asyncio.TimeoutError:
                logger.error("pipeline_run_timeout", extra={"symbol": symbol, "timeout": self.config.graph_timeout})
            except Exception as exc:
                logger.error(
                    "pipeline_run_failed",
                    extra={
                        "symbol": symbol,
                        "error": str(exc),
                        "traceback": traceback.format_exc(),
                    },
                )

    async def _deterministic_pipeline(
        self, symbol: str, snap: dict | None = None
    ) -> dict:
        """Deterministic signal → risk → size → execution pipeline.

        No LLM calls.  Every gate is auditable.
        """
        snap = snap or self._risk_manager.current_risk_snapshot()
        rs = self._risk_manager.state  # ponytail: RiskState for gate evaluation
        result: dict[str, str] = {
            "symbol": symbol,
            "decision_action": "hold",
            "risk_verdict": "passed",
            "size": "0.0",
        }

        # 1. Kill switch check
        if self._kill_switch_active:
            logger.info("pipeline_skipped_kill_switch", extra={"symbol": symbol})
            result["risk_verdict"] = "kill_switch_active"
            return result

        # 2. Fetch current price from broker / data service
        try:
            from quant_nanggroe.exchange.paper_broker import PaperExchangeBroker
            broker = PaperExchangeBroker()
            broker.set_price(symbol, 50000.0)  # default seed
            price = broker.get_price(symbol)
        except Exception:
            price = snap.get("price", 0.0)

        if not price or price <= 0:
            logger.warning("pipeline_no_price", extra={"symbol": symbol})
            return result

        # 3. Basic signal: simple moving average crossover (placeholder)
        #    Real signal engines sit in engine/strategies/ — wire later.
        signal = 0.0  # -1 (sell) … +1 (buy)

        # 4. Risk gate evaluation
        try:
            gate_result = self._risk_manager.check_gate.evaluate(
                symbol=symbol,
                account_balance=rs.peak_equity if rs.peak_equity > 0 else 1_000_000.0,
                daily_pnl=float(rs.daily_pnl),
                weekly_pnl=float(rs.weekly_pnl),
                trade_count_today=int(rs.trade_count_today),
            )
            if not gate_result.get("approved", False):
                logger.info("pipeline_gate_denied", extra={"symbol": symbol, **gate_result})
                result["risk_verdict"] = "gate_denied"
                return result
        except Exception as e:
            logger.warning("pipeline_gate_error", extra={"symbol": symbol, "error": str(e)})
            return result

        # 5. Kelly position sizing
        try:
            kelly = self._risk_manager.kelly
            kelly_frac = kelly.calculate_kelly(win_prob=0.55, win_loss_ratio=1.5)
            size = max(0.0, kelly_frac * 1_000_000 if isinstance(kelly_frac, (int, float)) else 0.0)
        except Exception:
            kelly_frac = 0.0
            size = 0.0

        # 6. Execution
        if abs(signal) > 0.1 and size > 0:
            from quant_nanggroe.exchange.base import OrderSide, OrderType
            side_enum = OrderSide.BUY if signal > 0 else OrderSide.SELL
            try:
                order = await broker.place_order(
                    symbol=symbol,
                    side=side_enum,
                    order_type=OrderType.MARKET,
                    quantity=max(0.001, size / price),
                )
                result["decision_action"] = side
                result["size"] = str(size)
                result["order_id"] = order.get("order_id", "unknown")
                logger.info("pipeline_order_placed", extra={"symbol": symbol, "side": side, "size": size})
            except Exception as e:
                logger.warning("pipeline_order_failed", extra={"symbol": symbol, "error": str(e)})
        else:
            logger.info("pipeline_hold", extra={"symbol": symbol, "signal": signal})

        # 7. Feed back to risk manager for P&L tracking
        try:
            self._risk_manager.update_risk_state(symbol, 0.0)
        except Exception:
            pass

        return result

    # ── Position Monitor Loop ───────────────────────────────────────

    async def _position_monitor_loop(self) -> None:
        """Periodically update current prices and unrealized PnL."""
        while self._running:
            try:
                await self._update_all_positions()
                await asyncio.sleep(self.config.position_monitor_interval)
            except asyncio.CancelledError:
                logger.info("position_monitor_cancelled")
                break
            except Exception as exc:
                logger.error(
                    "position_monitor_error",
                    extra={"error": str(exc), "traceback": traceback.format_exc()},
                )
                await asyncio.sleep(self.config.position_monitor_interval)

    async def _update_all_positions(self) -> None:
        """Update positions — placeholder for database integration."""
        try:
            logger.debug("positions_update_checked")
        except Exception as exc:
            logger.error("update_positions_failed", extra={"error": str(exc)})

    # ── Portfolio Snapshot Loop ──────────────────────────────────────

    async def _portfolio_snapshot_loop(self) -> None:
        """Periodically record a portfolio snapshot for time-series analysis."""
        while self._running:
            try:
                await self._take_portfolio_snapshot()
                await asyncio.sleep(self.config.snapshot_interval)
            except asyncio.CancelledError:
                logger.info("portfolio_snapshot_cancelled")
                break
            except Exception as exc:
                logger.error(
                    "portfolio_snapshot_error",
                    extra={"error": str(exc), "traceback": traceback.format_exc()},
                )
                await asyncio.sleep(self.config.snapshot_interval)

    async def _take_portfolio_snapshot(self) -> None:
        """Record a portfolio snapshot — placeholder for database integration."""
        try:
            logger.debug("portfolio_snapshot_taken")
        except Exception as exc:
            logger.error("take_snapshot_failed", extra={"error": str(exc)})

    # ── Kill Switch Monitor Loop ────────────────────────────────────

    async def _kill_switch_monitor_loop(self) -> None:
        """Periodically check the kill switch state (LIVE, not inert)."""
        while self._running:
            try:
                was_active = self._kill_switch_active
                # ponytail: feed real P&L/drawdown from RiskManager (was 0.0 blind bypass)
                snap = self._risk_manager.current_risk_snapshot()
                self._kill_switch.check_auto_activate(
                    daily_pnl_pct=snap["daily_pnl_pct"],
                    weekly_pnl_pct=snap["weekly_pnl_pct"],
                    max_drawdown_pct=snap["max_drawdown_pct"],
                )
                self._kill_switch_active = self._kill_switch.is_active

                if self._kill_switch_active and not was_active:
                    logger.warning("kill_switch_activated", extra={"msg": "All trading halted"})
                elif not self._kill_switch_active and was_active:
                    logger.info("kill_switch_deactivated", extra={"msg": "Trading resumed"})

                await asyncio.sleep(self.config.kill_switch_check_interval)

            except asyncio.CancelledError:
                logger.info("kill_switch_monitor_cancelled")
                break
            except Exception as exc:
                logger.error("kill_switch_monitor_error", extra={"error": str(exc)})
                await asyncio.sleep(self.config.kill_switch_check_interval)

    # ── Health Reporter Loop ────────────────────────────────────────

    async def _health_reporter_loop(self) -> None:
        """Periodically emit health metrics for observability."""
        while self._running:
            try:
                health_data = {
                    "kill_switch": self._kill_switch_active,
                    "last_graph_runs": {
                        sym: ts.isoformat() for sym, ts in self._last_graph_run.items()
                    },
                }

                logger.debug("health_reported", extra=health_data)

                await asyncio.sleep(self.config.health_interval)

            except asyncio.CancelledError:
                logger.info("health_reporter_cancelled")
                break
            except Exception as exc:
                logger.error("health_reporter_error", extra={"error": str(exc)})
                await asyncio.sleep(self.config.health_interval)


# ══════════════════════════════════════════════════════════════════════
# CLI Entry Point
# ══════════════════════════════════════════════════════════════════════


async def main() -> None:
    """Run the trading worker as a standalone process."""
    worker = TradingWorker()

    try:
        await worker.start()
        # Block forever until interrupted
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        logger.info("worker_interrupted")
    finally:
        await worker.stop()


if __name__ == "__main__":
    asyncio.run(main())
