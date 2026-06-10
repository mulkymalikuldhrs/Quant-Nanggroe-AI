"""
Background Trading Worker
=========================
Runs the LangGraph trading graph periodically, monitors open positions,
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

    python -m quant_nanggroe_ai.worker
"""

from __future__ import annotations

import asyncio
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import structlog

from quant_nanggroe_ai.config import Settings, get_settings
from quant_nanggroe_ai.data.cache import cache_get, cache_set, init_redis, close_redis
from quant_nanggroe_ai.data.database import init_db, close_db, get_db_session
from quant_nanggroe_ai.data.models import (
    AgentLog,
    PortfolioSnapshot,
    Position,
    RiskEvent,
    Strategy,
    Trade,
)
from quant_nanggroe_ai.exceptions import DataError, KillSwitchActiveError

logger = structlog.get_logger(__name__)


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
    - Graph runner: Invokes the LangGraph trading graph per symbol
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
        self._running = False
        self._kill_switch_active = False
        self._graph_semaphore = asyncio.Semaphore(self.config.max_concurrent_graphs)
        self._last_graph_run: dict[str, datetime] = {}

    # ── Lifecycle ───────────────────────────────────────────────────

    async def start(self) -> None:
        """
        Start all background loops.

        Initializes database and Redis connections, then launches
        all worker tasks.
        """
        if self._running:
            logger.warning("worker_already_running")
            return

        logger.info(
            "worker_starting",
            symbols=self.config.symbols,
            graph_interval=self.config.graph_interval,
            position_interval=self.config.position_monitor_interval,
        )

        # Initialize data layer
        await init_db(self.settings)
        await init_redis(self.settings)

        self._running = True

        # Launch core tasks
        self._tasks = [
            asyncio.create_task(self._graph_runner_loop(), name="graph-runner"),
            asyncio.create_task(self._position_monitor_loop(), name="position-monitor"),
            asyncio.create_task(self._portfolio_snapshot_loop(), name="portfolio-snapshot"),
            asyncio.create_task(self._kill_switch_monitor_loop(), name="kill-switch-monitor"),
            asyncio.create_task(self._health_reporter_loop(), name="health-reporter"),
        ]

        logger.info("worker_started", task_count=len(self._tasks))

    async def stop(self) -> None:
        """
        Gracefully stop all background loops.

        Cancels all tasks, waits for them to finish, then
        closes database and Redis connections.
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
                    task_name=task.get_name(),
                    error=str(result),
                )

        self._tasks.clear()

        # Close connections
        await close_db()
        await close_redis()

        logger.info("worker_stopped")

    # ── Graph Runner Loop ───────────────────────────────────────────

    async def _graph_runner_loop(self) -> None:
        """
        Periodically invoke the trading graph for each watched symbol.

        Uses a semaphore to limit concurrent graph executions.
        Skips symbols if the kill switch is active.
        """
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
                logger.error("graph_runner_error", error=str(exc), traceback=traceback.format_exc())
                await asyncio.sleep(self.config.graph_interval)

    async def _run_graph_for_symbol(self, symbol: str) -> None:
        """
        Run the trading graph for a single symbol.

        Acquires the semaphore, invokes the graph, and records
        the result in the database.

        Args:
            symbol: Trading symbol (e.g., "SPY", "BTC-USD").
        """
        async with self._graph_semaphore:
            start_time = datetime.now()
            logger.info("graph_run_start", symbol=symbol)

            try:
                # Import here to avoid circular imports
                from quant_nanggroe_ai.agents.graph import get_trading_graph
                from quant_nanggroe_ai.agents.state import AgentState

                graph = get_trading_graph()
                initial_state = AgentState(symbol=symbol, timeframe="1d")

                # Run with timeout
                result = await asyncio.wait_for(
                    graph.ainvoke(initial_state.model_dump()),
                    timeout=self.config.graph_timeout,
                )

                latency_ms = (datetime.now() - start_time).total_seconds() * 1000
                logger.info(
                    "graph_run_complete",
                    symbol=symbol,
                    latency_ms=round(latency_ms, 2),
                    decision=result.get("decision_action", "unknown"),
                    risk_verdict=result.get("risk_verdict", "unknown"),
                )

                # Record agent trace to database
                await self._record_graph_result(symbol, result, latency_ms)

                # Cache the latest graph result
                await cache_set(
                    f"graph:result:{symbol}",
                    {
                        "symbol": symbol,
                        "decision": result.get("decision_action"),
                        "risk_verdict": result.get("risk_verdict"),
                        "latency_ms": latency_ms,
                        "timestamp": datetime.now().isoformat(),
                    },
                    ttl=300,
                )

                self._last_graph_run[symbol] = datetime.now()

            except asyncio.TimeoutError:
                logger.error("graph_run_timeout", symbol=symbol, timeout=self.config.graph_timeout)
                await self._record_agent_error(symbol, "timeout", "Graph execution timed out")
            except Exception as exc:
                logger.error(
                    "graph_run_failed",
                    symbol=symbol,
                    error=str(exc),
                    traceback=traceback.format_exc(),
                )
                await self._record_agent_error(symbol, "error", str(exc))

    # ── Position Monitor Loop ───────────────────────────────────────

    async def _position_monitor_loop(self) -> None:
        """
        Periodically update current prices and unrealized PnL
        for all open positions.
        """
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
                    error=str(exc),
                    traceback=traceback.format_exc(),
                )
                await asyncio.sleep(self.config.position_monitor_interval)

    async def _update_all_positions(self) -> None:
        """
        Fetch current prices for all open positions and update PnL.

        Uses the market data tools to get real-time prices, then
        calculates unrealized PnL for each position.
        """
        try:
            async with get_db_session() as session:
                from sqlalchemy import select

                result = await session.execute(
                    select(Position).where(Position.quantity > 0)
                )
                positions = result.scalars().all()

                if not positions:
                    return

                # Group positions by symbol for batch price fetching
                symbols = list({p.symbol for p in positions})

                # Fetch current prices
                prices = await self._fetch_current_prices(symbols)

                # Update each position
                for position in positions:
                    current_price = prices.get(position.symbol)
                    if current_price is None or current_price <= 0:
                        continue

                    position.current_price = current_price

                    # Calculate unrealized PnL
                    if position.direction in ("BUY", "LONG"):
                        position.unrealized_pnl = (
                            (current_price - position.avg_entry_price) * position.quantity
                        )
                    else:  # SELL / SHORT
                        position.unrealized_pnl = (
                            (position.avg_entry_price - current_price) * position.quantity
                        )

                    if position.avg_entry_price > 0:
                        position.unrealized_pnl_pct = (
                            position.unrealized_pnl
                            / (position.avg_entry_price * position.quantity)
                        )
                    else:
                        position.unrealized_pnl_pct = 0.0

                    position.updated_at = datetime.now()

                logger.debug(
                    "positions_updated",
                    count=len(positions),
                    symbols=symbols,
                )

        except Exception as exc:
            logger.error("update_positions_failed", error=str(exc))

    async def _fetch_current_prices(self, symbols: list[str]) -> dict[str, float]:
        """
        Fetch current prices for a list of symbols.

        Tries Redis cache first, falls back to market data tools.

        Args:
            symbols: List of trading symbols.

        Returns:
            Dict mapping symbol -> current price.
        """
        prices: dict[str, float] = {}

        # Try cache first
        for symbol in symbols:
            cached = await cache_get(f"price:{symbol}")
            if cached is not None:
                prices[symbol] = float(cached)

        # Fetch missing prices from market data
        missing = [s for s in symbols if s not in prices]
        if missing:
            try:
                from quant_nanggroe_ai.agents.tools.market_data import MarketDataTool

                market_tool = MarketDataTool()
                for symbol in missing:
                    try:
                        price = market_tool.get_current_price(symbol)
                        if price and price > 0:
                            prices[symbol] = price
                            # Cache for 30 seconds
                            await cache_set(f"price:{symbol}", price, ttl=30)
                    except Exception as exc:
                        logger.warning("price_fetch_failed", symbol=symbol, error=str(exc))
            except Exception as exc:
                logger.error("market_data_tool_failed", error=str(exc))

        return prices

    # ── Portfolio Snapshot Loop ──────────────────────────────────────

    async def _portfolio_snapshot_loop(self) -> None:
        """
        Periodically record a portfolio snapshot for time-series analysis.
        """
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
                    error=str(exc),
                    traceback=traceback.format_exc(),
                )
                await asyncio.sleep(self.config.snapshot_interval)

    async def _take_portfolio_snapshot(self) -> None:
        """
        Record a portfolio snapshot with current equity, PnL, and risk metrics.

        Aggregates data from all open positions and recent trades.
        """
        try:
            async with get_db_session() as session:
                from sqlalchemy import func, select

                # Aggregate position data
                pos_result = await session.execute(
                    select(
                        func.count(Position.id).label("num_positions"),
                        func.coalesce(func.sum(Position.unrealized_pnl), 0.0).label("unrealized_pnl"),
                        func.coalesce(func.sum(
                            Position.current_price * Position.quantity
                        ), 0.0).label("gross_exposure"),
                    ).where(Position.quantity > 0)
                )
                pos_row = pos_result.one()

                # Aggregate today's realized PnL from trades
                today_start = datetime.now().replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                trade_result = await session.execute(
                    select(
                        func.coalesce(func.sum(Trade.realized_pnl), 0.0).label("realized_pnl"),
                    ).where(
                        Trade.closed_at >= today_start,
                        Trade.realized_pnl.isnot(None),
                    )
                )
                trade_row = trade_result.one()

                # Calculate metrics
                unrealized_pnl = float(pos_row.unrealized_pnl or 0)
                realized_pnl = float(trade_row.realized_pnl or 0)
                total_pnl = unrealized_pnl + realized_pnl
                gross_exposure = float(pos_row.gross_exposure or 0)

                # Base equity (from cache or default)
                cached_equity = await cache_get("portfolio:base_equity")
                base_equity = float(cached_equity) if cached_equity else 100000.0
                total_equity = base_equity + total_pnl

                daily_pnl_pct = total_pnl / base_equity if base_equity > 0 else 0.0

                # Create snapshot (using first user for now — multi-user later)
                snapshot = PortfolioSnapshot(
                    user_id=await self._get_default_user_id(session),
                    total_equity=total_equity,
                    cash_balance=base_equity - gross_exposure,
                    unrealized_pnl=unrealized_pnl,
                    realized_pnl=realized_pnl,
                    daily_pnl=total_pnl,
                    daily_pnl_pct=daily_pnl_pct,
                    gross_exposure=gross_exposure,
                    net_exposure=unrealized_pnl,
                    num_positions=pos_row.num_positions or 0,
                )
                session.add(snapshot)

                # Cache current equity for fast access
                await cache_set("portfolio:current_equity", total_equity, ttl=600)
                await cache_set("portfolio:daily_pnl_pct", daily_pnl_pct, ttl=600)

                logger.debug(
                    "portfolio_snapshot_taken",
                    equity=total_equity,
                    daily_pnl_pct=f"{daily_pnl_pct:.4%}",
                    positions=pos_row.num_positions or 0,
                )

        except Exception as exc:
            logger.error("take_snapshot_failed", error=str(exc))

    # ── Kill Switch Monitor Loop ────────────────────────────────────

    async def _kill_switch_monitor_loop(self) -> None:
        """
        Periodically check the kill switch state in Redis.

        If the kill switch is activated, all graph execution is paused
        but position monitoring continues (for safety).
        """
        while self._running:
            try:
                kill_switch_state = await cache_get("system:kill_switch")
                was_active = self._kill_switch_active
                self._kill_switch_active = bool(kill_switch_state)

                if self._kill_switch_active and not was_active:
                    logger.warning("kill_switch_activated", msg="All trading halted")
                elif not self._kill_switch_active and was_active:
                    logger.info("kill_switch_deactivated", msg="Trading resumed")

                await asyncio.sleep(self.config.kill_switch_check_interval)

            except asyncio.CancelledError:
                logger.info("kill_switch_monitor_cancelled")
                break
            except Exception as exc:
                logger.error("kill_switch_monitor_error", error=str(exc))
                await asyncio.sleep(self.config.kill_switch_check_interval)

    # ── Health Reporter Loop ────────────────────────────────────────

    async def _health_reporter_loop(self) -> None:
        """
        Periodically emit health metrics for observability.

        Reports on: last graph run times, position count, equity,
        and data layer connectivity.
        """
        while self._running:
            try:
                from quant_nanggroe_ai.data.database import check_db_health
                from quant_nanggroe_ai.data.cache import check_redis_health

                db_health = await check_db_health()
                redis_health = await check_redis_health()

                current_equity = await cache_get("portfolio:current_equity")
                daily_pnl = await cache_get("portfolio:daily_pnl_pct")

                health_data = {
                    "db": db_health.get("status", "unknown"),
                    "redis": redis_health.get("status", "unknown"),
                    "kill_switch": self._kill_switch_active,
                    "current_equity": current_equity,
                    "daily_pnl_pct": daily_pnl,
                    "last_graph_runs": {
                        sym: ts.isoformat() for sym, ts in self._last_graph_run.items()
                    },
                }

                # Cache health for API endpoints
                await cache_set("system:worker_health", health_data, ttl=120)

                logger.debug("health_reported", **health_data)

                await asyncio.sleep(self.config.health_interval)

            except asyncio.CancelledError:
                logger.info("health_reporter_cancelled")
                break
            except Exception as exc:
                logger.error("health_reporter_error", error=str(exc))
                await asyncio.sleep(self.config.health_interval)

    # ── Helpers ─────────────────────────────────────────────────────

    async def _record_graph_result(
        self,
        symbol: str,
        result: dict[str, Any],
        latency_ms: float,
    ) -> None:
        """
        Persist graph execution results to the database.

        Records each agent in the trace as a separate AgentLog entry,
        and creates a Trade record if execution was successful.

        Args:
            symbol: Trading symbol.
            result: Graph output dict from LangGraph.
            latency_ms: Total graph execution latency.
        """
        try:
            async with get_db_session() as session:
                agent_trace = result.get("agent_trace", [])
                graph_run_id = result.get("order_id", str(datetime.now().timestamp()))
                user_id = await self._get_default_user_id(session)

                # Record each agent step
                for step in agent_trace:
                    agent_log = AgentLog(
                        user_id=user_id,
                        agent_name=step.get("agent", "unknown"),
                        graph_run_id=graph_run_id,
                        status=step.get("status", "unknown"),
                        symbol=symbol,
                        output_data=step,
                    )
                    session.add(agent_log)

                # Create trade record if executed
                execution_status = result.get("execution_status", "")
                if execution_status in ("FILLED", "PENDING"):
                    trade = Trade(
                        user_id=user_id,
                        order_id=result.get("order_id"),
                        symbol=symbol,
                        direction=result.get("strategy_signal", ""),
                        entry_price=result.get("entry_price", 0.0),
                        stop_loss=result.get("stop_loss"),
                        take_profit=result.get("take_profit"),
                        quantity=result.get("position_size", 0.0),
                        execution_status=execution_status,
                        slippage=result.get("slippage", 0.0),
                        risk_verdict=result.get("risk_verdict"),
                        risk_checkpoints=result.get("risk_checkpoints"),
                        agent_trace=agent_trace,
                        decision_action=str(result.get("decision_action", "")),
                        decision_reason=result.get("decision_reason", ""),
                        market_regime=str(result.get("regime", "")),
                        sentiment_score=result.get("sentiment_score"),
                    )
                    session.add(trade)

                # Record risk event if vetoed
                if result.get("risk_verdict") == "VETOED":
                    risk_event = RiskEvent(
                        user_id=user_id,
                        event_type="VETO",
                        severity="WARNING",
                        symbol=symbol,
                        direction=result.get("strategy_signal"),
                        verdict="VETOED",
                        risk_pct=result.get("risk_pct"),
                        checkpoints=result.get("risk_checkpoints"),
                        market_regime=str(result.get("regime", "")),
                    )
                    session.add(risk_event)

                logger.debug("graph_result_recorded", symbol=symbol)

        except Exception as exc:
            logger.error("record_graph_result_failed", symbol=symbol, error=str(exc))

    async def _record_agent_error(
        self,
        symbol: str,
        error_type: str,
        error_message: str,
    ) -> None:
        """
        Record a graph execution error as an AgentLog.

        Args:
            symbol: Trading symbol.
            error_type: Type of error (timeout, error).
            error_message: Error description.
        """
        try:
            async with get_db_session() as session:
                user_id = await self._get_default_user_id(session)
                agent_log = AgentLog(
                    user_id=user_id,
                    agent_name="trading_graph",
                    status="failed",
                    symbol=symbol,
                    error_message=error_message,
                )
                session.add(agent_log)
        except Exception as exc:
            logger.error("record_agent_error_failed", error=str(exc))

    async def _get_default_user_id(self, session: Any) -> Any:
        """
        Get the default system user ID.

        In production, this would be replaced by proper multi-tenancy.
        For now, returns the first user or creates a system user.

        Args:
            session: Database session.

        Returns:
            UUID of the default user.
        """
        from sqlalchemy import select
        from quant_nanggroe_ai.data.models import User

        result = await session.execute(select(User).limit(1))
        user = result.scalar_one_or_none()

        if user is not None:
            return user.id

        # Create system user if none exists
        import uuid

        system_user = User(
            id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            email="system@quant-nanggroe-ai.internal",
            username="system",
            hashed_password="no-login",
            is_active=True,
            is_admin=True,
        )
        session.add(system_user)
        return system_user.id


# ══════════════════════════════════════════════════════════════════════
# CLI Entry Point
# ══════════════════════════════════════════════════════════════════════


async def main() -> None:
    """Run the trading worker as a standalone process."""
    from quant_nanggroe_ai.logging import setup_logging

    setup_logging(log_level="INFO", json_output=False)

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
