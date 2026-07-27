"""Worker agent base class and concrete trading workers.

Each worker has a role, a goal, and a toolset. Workers execute tasks
independently — one failure does not crash the colony.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, List, Optional

from quant_nanggroe.engine.colony.message_bus import Message, MessageBus
from quant_nanggroe.engine.colony.tasks import Task, TaskStatus


@dataclass
class Worker(ABC):
    """Base worker — override execute() with the actual logic."""

    role: str
    goal: str
    toolset: List[str] = field(default_factory=list)
    bus: Optional[MessageBus] = None

    @abstractmethod
    async def execute(self, task: Task) -> Any:
        """Run the task and return a result. One worker failure is isolated."""
        ...

    async def run(self, task: Task) -> Task:
        """Execute a task with lifecycle tracking and error isolation."""
        task.status = TaskStatus.RUNNING
        try:
            result = await self.execute(task)
            task.result = result
            task.status = TaskStatus.SUCCESS
        except Exception as e:
            task.error = f"[{self.role}] {e}"
            task.status = TaskStatus.FAILED
        task.completed_at = __import__("datetime").datetime.utcnow()
        if self.bus:
            await self.bus.publish(Message(
                topic=f"worker.{self.role}.done",
                payload=task,
                sender=self.role,
            ))
        return task


# ── Concrete workers ──────────────────────────────────────────────────


class StrategyWorker(Worker):
    """Runs trading strategies via StrategyRegistry."""

    async def execute(self, task: Task) -> Any:
        strategy_name = task.name
        params = task.params
        symbol = params.get("symbol", "UNKNOWN")
        df = params.get("dataframe")
        if df is None:
            return {"strategy": strategy_name, "signal": "hold", "confidence": 0.0, "error": "no_dataframe"}
        try:
            from quant_nanggroe.engine.strategies.registry import StrategyRegistry
            strategy = StrategyRegistry.create(strategy_name)
            if strategy is None:
                return {"strategy": strategy_name, "signal": "hold", "confidence": 0.0, "error": "unknown_strategy"}
            signal = strategy.generate_signal(df, symbol=symbol)
            return {
                "strategy": strategy_name,
                "signal": signal.direction.value if hasattr(signal, "direction") else "hold",
                "confidence": float(getattr(signal, "confidence", 0.0)),
                "reasoning": getattr(signal, "reasoning", ""),
            }
        except Exception as e:
            return {"strategy": strategy_name, "signal": "error", "confidence": 0.0, "error": str(e)}


class RiskWorker(Worker):
    """Runs risk checks via ConstitutionalRiskGuard."""

    async def execute(self, task: Task) -> Any:
        params = task.params
        try:
            from quant_nanggroe.engine.risk.checks import ConstitutionalRiskGuard
            guard = ConstitutionalRiskGuard()
            symbol = params.get("symbol", "UNKNOWN")
            side = params.get("side", "buy")
            size = params.get("size", 0.01)
            price = params.get("price", 0.0)
            result = guard.can_trade(symbol=symbol, side=side, size=size, price=price)
            return {
                "risk_check": task.name,
                "passed": bool(result),
                "reason": str(getattr(result, "reason", "")) if not isinstance(result, bool) else "",
            }
        except Exception as e:
            return {"risk_check": task.name, "passed": False, "error": str(e)}


class DataWorker(Worker):
    """Fetches market data via ExchangeManager."""

    async def execute(self, task: Task) -> Any:
        params = task.params
        symbol = params.get("symbol", "UNKNOWN")
        try:
            from quant_nanggroe.services import get_exchange_manager
            em = get_exchange_manager()
            from quant_nanggroe.types.market import TimeFrame as TF
            tf_str = params.get("timeframe", "1d")
            tf_map = {"1m": TF.M1, "5m": TF.M5, "15m": TF.M15, "1h": TF.H1, "4h": TF.H4, "1d": TF.D1}
            tf = tf_map.get(tf_str, TF.D1)
            limit = int(params.get("limit", 100))
            candles = await em.get_ohlcv(symbol=symbol, timeframe=tf, limit=limit)
            if not candles:
                return {"data": task.name, "rows": 0, "columns": [], "error": "no_data"}
            import pandas as pd
            df = pd.DataFrame([{"open": c.open, "high": c.high, "low": c.low, "close": c.close, "volume": c.volume} for c in candles])
            return {"data": task.name, "rows": len(df), "columns": list(df.columns), "dataframe": df}
        except Exception as e:
            return {"data": task.name, "rows": 0, "columns": [], "error": str(e)}


class ExecutionWorker(Worker):
    """Handles order placement via ProductionExecutionManager."""

    async def execute(self, task: Task) -> Any:
        params = task.params
        symbol = params.get("symbol", "UNKNOWN")
        side = params.get("side", "buy")
        try:
            from quant_nanggroe.engine_production_bridge import ProductionExecutionManager
            pem = ProductionExecutionManager()
            result = await pem.execute_signal(
                symbol=symbol,
                side=side,
                confidence=float(params.get("confidence", 0.5)),
                price=float(params.get("price", 0.0)),
                stop_loss=float(params.get("stop_loss", 0.0)),
                take_profit=float(params.get("take_profit", 0.0)),
            )
            return {
                "execution": task.name,
                "filled": bool(result.get("filled", False)),
                "order_id": result.get("order_id"),
                "detail": result,
            }
        except Exception as e:
            return {"execution": task.name, "filled": False, "order_id": None, "error": str(e)}
