#!/usr/bin/env python3
"""
Darwinian Strategy Lifecycle (from Quant-Nanggroe-AI)
=====================================================
Strategy states: ACTIVE → HIBERNATING → KILLED
Auto-kill strategies with negative expectancy after 20+ trades.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List

logger = logging.getLogger("HermesQuantOS.StrategyLifecycle")


class StrategyLifecycleManager:
    """
    Darwinian strategy evolution: survival of the fittest.
    
    Source: Quant-Nanggroe-AI v15.2.0 Strategy Lifecycle
    Adapted for Hermes Quant OS.
    """

    # Strategy states
    ACTIVE = "ACTIVE"
    HIBERNATING = "HIBERNATING"
    KILLED = "KILLED"

    # Lifecycle thresholds
    MIN_TRADES_FOR_EVALUATION = 20
    HIBERNATE_MAX_DRAWDOWN = 0.15  # 15% max drawdown
    KILL_NEGATIVE_EXPECTANCY = True

    def __init__(self):
        self.strategies = {}  # name -> strategy state

    def register_strategy(self, name: str, description: str = "") -> Dict:
        """Register a new strategy for lifecycle tracking"""
        self.strategies[name] = {
            "name": name,
            "description": description,
            "state": self.ACTIVE,
            "trades_count": 0,
            "wins": 0,
            "losses": 0,
            "total_pnl": 0.0,
            "total_wins": 0.0,
            "total_losses": 0.0,
            "max_drawdown": 0.0,
            "expectancy": 0.0,
            "win_rate": 0.0,
            "registered_at": datetime.now().isoformat(),
            "last_evaluated": None,
            "state_history": [{"state": self.ACTIVE, "timestamp": datetime.now().isoformat()}]
        }
        return self.strategies[name]

    def update_strategy(self, name: str, pnl: float, is_win: bool,
                         current_drawdown: float = 0.0) -> Dict:
        """Update strategy performance after a trade"""
        if name not in self.strategies:
            self.register_strategy(name)

        strategy = self.strategies[name]
        strategy["trades_count"] += 1
        strategy["total_pnl"] += pnl
        strategy["max_drawdown"] = max(strategy["max_drawdown"], current_drawdown)

        if is_win:
            strategy["wins"] += 1
            strategy["total_wins"] += pnl
        else:
            strategy["losses"] += 1
            strategy["total_losses"] += abs(pnl)

        # Calculate expectancy
        if strategy["trades_count"] > 0:
            strategy["win_rate"] = strategy["wins"] / strategy["trades_count"]
            avg_win = strategy["total_wins"] / max(strategy["wins"], 1)
            avg_loss = strategy["total_losses"] / max(strategy["losses"], 1) if strategy["losses"] > 0 else 0
            strategy["expectancy"] = strategy["win_rate"] * avg_win - \
                                     (1 - strategy["win_rate"]) * abs(avg_loss)

        strategy["last_evaluated"] = datetime.now().isoformat()

        # Evaluate lifecycle
        self._evaluate_lifecycle(name)

        return strategy

    def _evaluate_lifecycle(self, name: str):
        """Evaluate strategy lifecycle state"""
        strategy = self.strategies[name]

        # Only evaluate after minimum trades
        if strategy["trades_count"] < self.MIN_TRADES_FOR_EVALUATION:
            return

        # Kill condition: negative expectancy
        if self.KILL_NEGATIVE_EXPECTANCY and strategy["expectancy"] < 0:
            self._transition(name, self.KILLED, "Negative expectancy after "
                           f"{strategy['trades_count']} trades")
            return

        # Hibernate condition: max drawdown exceeded
        if strategy["max_drawdown"] > self.HIBERNATE_MAX_DRAWDOWN:
            self._transition(name, self.HIBERNATING,
                           f"Max drawdown {strategy['max_drawdown']:.2%} > "
                           f"{self.HIBERNATE_MAX_DRAWDOWN:.2%}")
            return

        # If currently hibernating but recovered, reactivate
        if strategy["state"] == self.HIBERNATING and strategy["expectancy"] > 0:
            self._transition(name, self.ACTIVE, "Recovered - positive expectancy")

    def _transition(self, name: str, new_state: str, reason: str):
        """Transition strategy to new state"""
        strategy = self.strategies[name]
        old_state = strategy["state"]

        if old_state == new_state:
            return

        strategy["state"] = new_state
        strategy["state_history"].append({
            "state": new_state,
            "timestamp": datetime.now().isoformat(),
            "reason": reason
        })

        logger.info(f"STRATEGY LIFECYCLE: {name} {old_state} → {new_state} | {reason}")

    def get_active_strategies(self) -> List[str]:
        """Get list of active strategy names"""
        return [name for name, s in self.strategies.items() if s["state"] == self.ACTIVE]

    def get_strategy_report(self) -> str:
        """Get comprehensive strategy lifecycle report"""
        report = {
            "total_strategies": len(self.strategies),
            "active": len([s for s in self.strategies.values() if s["state"] == self.ACTIVE]),
            "hibernating": len([s for s in self.strategies.values() if s["state"] == self.HIBERNATING]),
            "killed": len([s for s in self.strategies.values() if s["state"] == self.KILLED]),
            "strategies": {}
        }

        for name, s in self.strategies.items():
            report["strategies"][name] = {
                "state": s["state"],
                "trades": s["trades_count"],
                "win_rate": f"{s['win_rate']:.1%}",
                "expectancy": round(s["expectancy"], 4),
                "max_dd": f"{s['max_drawdown']:.2%}",
                "total_pnl": round(s["total_pnl"], 2)
            }

        return json.dumps(report, indent=2)
