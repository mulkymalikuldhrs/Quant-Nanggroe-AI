"""
Trader Agent — Execution: routes and executes approved trades.
================================================================
Routes to the appropriate execution backend based on asset class and
configuration: paper trading (default), Alpaca (equities), or Jupiter
(Solana DEX).  Handles order execution with proper error handling,
slippage tracking, and execution status reporting.

Responsibilities:
  - Route to appropriate execution backend (paper/alpaca/jupiter)
  - Handle order execution with proper error handling
  - Return execution_status, order_id, execution_price, slippage
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any

from quant_nanggroe_ai.agents.state import AgentState
from quant_nanggroe_ai.agents.tools.execution import ExecutionTool
from quant_nanggroe_ai.types import RiskClearance

logger = logging.getLogger(__name__)


async def trader_node(state: AgentState) -> dict[str, Any]:
    """
    Execution Agent node.

    Routes to the appropriate execution backend via ExecutionTool.
    Only executes if risk clearance is CLEAR.
    """
    symbol = state.symbol or "SPY"
    errors: list[str] = []
    now = datetime.now().isoformat()

    # ── 1. Early exit: risk clearance check ────────────────────────────
    if state.risk_clearance != RiskClearance.CLEAR:
        logger.info(
            "Trade execution SKIPPED for %s — risk clearance is %s",
            symbol, state.risk_clearance.value,
        )
        return {
            "execution_status": "SKIPPED",
            "order_id": "",
            "execution_price": 0.0,
            "slippage": 0.0,
            "errors": state.errors,
            "agent_trace": state.agent_trace + [
                {
                    "agent": "trader",
                    "status": "skipped",
                    "reason": f"Risk clearance is {state.risk_clearance.value}, not CLEAR",
                    "timestamp": now,
                }
            ],
        }

    # ── 2. Early exit: no signal ───────────────────────────────────────
    if state.strategy_signal not in ("BUY", "SELL", "LONG", "SHORT"):
        return {
            "execution_status": "SKIPPED",
            "order_id": "",
            "execution_price": 0.0,
            "slippage": 0.0,
            "errors": state.errors + [f"No actionable signal: {state.strategy_signal}"],
            "agent_trace": state.agent_trace + [
                {
                    "agent": "trader",
                    "status": "skipped",
                    "reason": f"No actionable signal: {state.strategy_signal}",
                    "timestamp": now,
                }
            ],
        }

    # ── 3. Determine execution parameters ─────────────────────────────
    direction = state.strategy_signal
    quantity = state.position_size if state.position_size > 0 else 0.01
    entry_price = state.entry_price
    stop_loss = state.stop_loss if state.stop_loss > 0 else None
    take_profit = state.take_profit[0] if state.take_profit else None
    order_type = "LIMIT" if entry_price > 0 else "MARKET"

    # ── 4. Execute trade via ExecutionTool ─────────────────────────────
    start_time = time.monotonic()
    execution_status = "PENDING"
    order_id = ""
    execution_price = 0.0
    slippage = 0.0

    try:
        exec_tool = ExecutionTool()
        result = await exec_tool.execute_order(
            symbol=symbol,
            side=direction,
            quantity=quantity,
            order_type=order_type,
            price=entry_price if entry_price > 0 else None,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )

        execution_status = result.get("status", "PENDING")
        order_id = result.get("order_id", "")
        execution_price = result.get("execution_price", 0.0)
        slippage = result.get("slippage", 0.0)

        logger.info(
            "Order executed: %s %s %s @ %s — status=%s, order_id=%s",
            direction, quantity, symbol, execution_price, execution_status, order_id,
        )

    except Exception as exc:
        logger.error("Execution failed for %s: %s", symbol, exc)
        execution_status = "REJECTED"
        errors.append(f"Execution: {exc}")

    execution_latency_ms = round((time.monotonic() - start_time) * 1000, 2)

    # ── Return state updates ────────────────────────────────────────────
    return {
        "execution_status": execution_status,
        "order_id": order_id,
        "execution_price": execution_price,
        "slippage": slippage,
        "errors": state.errors + errors,
        "agent_trace": state.agent_trace + [
            {
                "agent": "trader",
                "status": "completed",
                "action": "execute",
                "symbol": symbol,
                "direction": direction,
                "quantity": quantity,
                "order_id": order_id,
                "execution_price": execution_price,
                "slippage": slippage,
                "latency_ms": execution_latency_ms,
                "timestamp": now,
            }
        ],
    }
