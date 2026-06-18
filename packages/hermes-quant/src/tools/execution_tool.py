#!/usr/bin/env python3
"""
Execution Agent (L4 - Execution Layer)
Paper Trading / MT5 / OANDA / Binance execution
Risk Officer approval gate - blocks if VETOED

PRODUCTION FIX v4.0.0:
- Uses SharedState.risk_officer (no more fresh instances)
- Trades logged to SQLite via SharedState
- PnL state persists across restarts
"""

import json
import logging
from datetime import datetime
from typing import Optional, Dict, List, Any

logger = logging.getLogger("HermesQuantOS.Execution")


class ExecutionTool:
    """L4 Agent: Execution - Trade execution with Risk Officer gate"""

    MODES = ["paper", "mt5", "oanda", "binance"]

    def __init__(self, mode: str = "paper", shared_state: Optional[Any] = None) -> None:
        self.mode = mode
        self.pending_orders: List[Dict[str, Any]] = []
        self.executed_trades: List[Dict[str, Any]] = []
        self.rejected_trades: List[Dict[str, Any]] = []
        self.account_balance = 10000.0  # Default paper balance
        self._shared_state = shared_state

    @property
    def shared_state(self):
        """Lazy-load shared state to avoid circular imports"""
        if self._shared_state is None:
            from tools.shared_state import get_shared_state
            self._shared_state = get_shared_state()
        return self._shared_state

    def paper_trade(self, symbol: str, direction: str, lot_size: float,
                    entry: float, stop_loss: float, take_profit: float = None,
                    reason: str = "") -> str:
        """
        Execute a paper trade. ALWAYS checks Risk Officer first.
        Uses SHARED RiskOfficer instance — PnL state is always current.
        """
        # MANDATORY: Check Risk Officer (SHARED instance)
        risk_officer = self.shared_state.risk_officer
        risk_result = json.loads(risk_officer.check_trade(
            symbol, direction, lot_size, entry, stop_loss,
            self.account_balance, take_profit
        ))

        # Log risk check to SQLite
        self.shared_state.log_risk_check(
            symbol, direction, risk_result.get("verdict", "UNKNOWN"),
            risk_officer.daily_pnl, risk_officer.weekly_pnl
        )

        if risk_result.get("verdict") == "VETOED":
            self.rejected_trades.append({
                "symbol": symbol,
                "direction": direction,
                "reason": "Risk Officer VETO",
                "checkpoints_failed": [k for k, v in risk_result.get("checkpoints", {}).items()
                                       if not v.get("passed", True)],
                "timestamp": datetime.now().isoformat()
            })
            return json.dumps({
                "status": "REJECTED",
                "reason": "Risk Officer VETO - Trade not executed",
                "risk_check": risk_result,
                "note": "Risk Officer has FULL VETO. This cannot be overridden."
            }, indent=2)

        # Execute paper trade
        trade_id = f"T_{datetime.now().strftime('%Y%m%d%H%M%S')}_{symbol}"
        trade = {
            "trade_id": trade_id,
            "mode": "paper",
            "symbol": symbol,
            "direction": direction.upper(),
            "lot_size": lot_size,
            "entry": entry,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "reason": reason,
            "timestamp": datetime.now().isoformat(),
            "status": "OPEN",
            "pnl": 0.0
        }

        self.executed_trades.append(trade)

        # Log trade to SQLite
        self.shared_state.log_trade({
            "trade_id": trade_id,
            "symbol": symbol,
            "direction": direction.upper(),
            "entry": entry,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "lot_size": lot_size,
            "entry_time": datetime.now().isoformat(),
            "reason": reason
        })

        logger.info(f"PAPER TRADE EXECUTED: {symbol} {direction} @ {entry}")

        return json.dumps({
            "status": "EXECUTED",
            "mode": "paper",
            "trade": trade,
            "risk_check": risk_result,
            "message": f"Paper trade: {direction} {symbol} @ {entry} | SL: {stop_loss} | TP: {take_profit}"
        }, indent=2)

    def close_trade(self, symbol: str, close_price: float,
                    direction: str, entry: float, lot_size: float) -> str:
        """Close an open position and calculate PnL"""
        if direction.upper() == "BUY":
            pnl = (close_price - entry) * lot_size * 100000
        else:
            pnl = (entry - close_price) * lot_size * 100000

        pnl_pct = pnl / self.account_balance if self.account_balance > 0 else 0

        # Update Risk Officer PnL (SHARED instance — state persists!)
        risk_officer = self.shared_state.risk_officer
        risk_officer.update_pnl(pnl_pct)

        # Persist PnL state to SQLite
        self.shared_state.persist_risk_officer_state()

        # Auto-check kill switch
        kill_switch = self.shared_state.kill_switch
        kill_result = kill_switch.check_auto_trigger(risk_officer.daily_pnl, risk_officer.weekly_pnl)
        kill_data = json.loads(kill_result)

        if kill_data.get("status") == "ACTIVATED":
            self.shared_state.log_kill_switch_event(
                "ACTIVATED", kill_data.get("reason", "AUTO"),
                risk_officer.daily_pnl, risk_officer.weekly_pnl
            )
            self.shared_state.persist_kill_switch_state()

        return json.dumps({
            "status": "CLOSED",
            "symbol": symbol,
            "direction": direction,
            "entry": entry,
            "close": close_price,
            "lot_size": lot_size,
            "pnl": round(pnl, 2),
            "pnl_pct": f"{pnl_pct:.4f}",
            "kill_switch_status": kill_data.get("status", "OK"),
            "timestamp": datetime.now().isoformat()
        }, indent=2)

    def status(self) -> str:
        return json.dumps({
            "mode": self.mode,
            "account_balance": self.account_balance,
            "open_trades": len([t for t in self.executed_trades if t["status"] == "OPEN"]),
            "total_executed": len(self.executed_trades),
            "total_rejected": len(self.rejected_trades),
            "available_modes": self.MODES,
            "note": "Paper trading mode - no real money at risk"
        }, indent=2)
