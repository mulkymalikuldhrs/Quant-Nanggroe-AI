#!/usr/bin/env python3
"""
Portfolio Manager Agent (L3 - Decision Layer)
Portfolio assessment, allocation, position sizing
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any

logger = logging.getLogger("HermesQuantOS.Portfolio")


class PortfolioTool:
    """L3 Agent: Portfolio Manager - Allocation & position sizing"""

    def __init__(self) -> None:
        self.account_balance = 10000.0
        self.positions: List[Dict[str, Any]] = []
        self.allocations: Dict[str, float] = {}

    def assess(self) -> str:
        """Assess current portfolio state"""
        total_risk = sum(p.get("risk_pct", 0) for p in self.positions)
        total_exposure = sum(p.get("notional", 0) for p in self.positions)
        leverage = total_exposure / self.account_balance if self.account_balance > 0 else 0

        return json.dumps({
            "account_balance": self.account_balance,
            "open_positions": len(self.positions),
            "total_risk": f"{total_risk:.2%}",
            "total_exposure": round(total_exposure, 2),
            "leverage": f"{leverage:.1f}x",
            "available_margin": round(self.account_balance * 0.9 - total_exposure, 2),
            "positions": self.positions,
            "timestamp": datetime.now().isoformat()
        }, indent=2)

    def suggest_allocation(self, risk_tolerance: str = "conservative") -> str:
        """Suggest portfolio allocation based on risk profile"""
        profiles = {
            "conservative": {
                "forex_major": 0.40, "gold": 0.25, "indices": 0.15,
                "crypto": 0.05, "cash": 0.15
            },
            "moderate": {
                "forex_major": 0.30, "gold": 0.20, "indices": 0.20,
                "crypto": 0.15, "cash": 0.15
            },
            "aggressive": {
                "forex_major": 0.25, "gold": 0.15, "indices": 0.25,
                "crypto": 0.25, "cash": 0.10
            }
        }

        allocation = profiles.get(risk_tolerance, profiles["conservative"])

        return json.dumps({
            "risk_profile": risk_tolerance,
            "allocation": allocation,
            "dollar_amounts": {k: round(self.account_balance * v, 2)
                              for k, v in allocation.items()},
            "note": "Allocation suggestions only. Apply Risk Officer checks before any trade."
        }, indent=2)

    def status(self) -> str:
        return self.assess()
