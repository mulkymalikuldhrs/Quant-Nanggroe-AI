#!/usr/bin/env python3
"""
Journal Agent (L5 - Learning Layer)
Trade logging, PnL calculation, performance stats
"""

import json
import logging
from datetime import datetime
from typing import Dict, List

logger = logging.getLogger("HermesQuantOS.Journal")


class JournalTool:
    """L5 Agent: Journal - Complete trade audit trail"""

    def __init__(self):
        self.trades = []
        self.daily_summaries = {}

    def log_trade(self, symbol: str, direction: str, entry: float,
                  exit_price: float, stop_loss: float, take_profit: float = None,
                  lot_size: float = 0.01, reason: str = "",
                  result: str = "") -> str:
        """Log a completed trade with full details"""
        # Calculate PnL
        if direction.upper() in ["BUY", "LONG"]:
            pnl_pips = exit_price - entry
            pnl = (exit_price - entry) * lot_size * 100000
        else:
            pnl_pips = entry - exit_price
            pnl = (entry - exit_price) * lot_size * 100000

        rr_achieved = abs(exit_price - entry) / abs(entry - stop_loss) if abs(entry - stop_loss) > 0 else 0

        trade = {
            "id": len(self.trades) + 1,
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "direction": direction.upper(),
            "entry": entry,
            "exit": exit_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "lot_size": lot_size,
            "pnl": round(pnl, 2),
            "pnl_pips": round(pnl_pips, 5),
            "rr_achieved": round(rr_achieved, 2),
            "result": "WIN" if pnl > 0 else "LOSS" if pnl < 0 else "BREAKEVEN",
            "reason": reason,
            "notes": result,
            "plan_vs_execution": "pending_audit"
        }

        self.trades.append(trade)

        # Update daily summary
        today = datetime.now().strftime('%Y-%m-%d')
        if today not in self.daily_summaries:
            self.daily_summaries[today] = {
                "trades": 0, "wins": 0, "losses": 0,
                "total_pnl": 0.0, "pnl_pips": 0.0
            }

        ds = self.daily_summaries[today]
        ds["trades"] += 1
        ds["total_pnl"] += pnl
        ds["pnl_pips"] += pnl_pips
        if pnl > 0:
            ds["wins"] += 1
        elif pnl < 0:
            ds["losses"] += 1

        return json.dumps({
            "status": "LOGGED",
            "trade_id": trade["id"],
            "result": trade["result"],
            "pnl": round(pnl, 2),
            "rr_achieved": round(rr_achieved, 2)
        }, indent=2)

    def get_stats(self) -> str:
        """Get comprehensive trading statistics"""
        if not self.trades:
            return json.dumps({"message": "No trades logged yet", "total_trades": 0})

        total = len(self.trades)
        wins = sum(1 for t in self.trades if t["result"] == "WIN")
        losses = sum(1 for t in self.trades if t["result"] == "LOSS")
        win_rate = (wins / total * 100) if total > 0 else 0

        total_pnl = sum(t["pnl"] for t in self.trades)
        avg_win = sum(t["pnl"] for t in self.trades if t["pnl"] > 0) / max(wins, 1)
        avg_loss = sum(t["pnl"] for t in self.trades if t["pnl"] < 0) / max(losses, 1)

        profit_factor = abs(sum(t["pnl"] for t in self.trades if t["pnl"] > 0)) / \
                        max(abs(sum(t["pnl"] for t in self.trades if t["pnl"] < 0)), 0.01)

        # Streaks
        current_streak = 0
        max_win_streak = 0
        max_loss_streak = 0
        temp_streak = 0

        for t in self.trades[-50:]:
            if t["result"] == "WIN":
                temp_streak = temp_streak + 1 if temp_streak > 0 else 1
                max_win_streak = max(max_win_streak, temp_streak)
            else:
                temp_streak = temp_streak - 1 if temp_streak < 0 else -1
                max_loss_streak = min(max_loss_streak, temp_streak)

        return json.dumps({
            "total_trades": total,
            "wins": wins,
            "losses": losses,
            "win_rate": f"{win_rate:.1f}%",
            "total_pnl": round(total_pnl, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "profit_factor": round(profit_factor, 2),
            "max_win_streak": max_win_streak,
            "max_loss_streak": abs(max_loss_streak),
            "avg_rr_achieved": round(sum(t["rr_achieved"] for t in self.trades) / total, 2),
            "recent_results": [t["result"] for t in self.trades[-10:]],
            "daily_summaries": {k: {kk: round(vv, 2) if isinstance(vv, float) else vv
                                    for kk, vv in v.items()}
                                for k, v in list(self.daily_summaries.items())[-7:]}
        }, indent=2)
