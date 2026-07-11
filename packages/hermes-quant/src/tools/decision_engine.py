#!/usr/bin/env python3
"""
Decision Synthesis Engine (from Quant-Nanggroe-AI)
===================================================
Machine-readable Decision Table for deterministic entry logic.
Compresses signals → 1 Entry, 1 SL, 1-3 TPs.
Risk Clearance: CLEAR / BLOCKED / PAUSE
"""

import json
import logging
from datetime import datetime
from typing import Dict, List

logger = logging.getLogger("HermesQuantOS.DecisionSynthesis")


class DecisionSynthesisEngine:
    """
    Deterministic decision table that synthesizes pressure + regime → trade decision.
    
    Source: Quant-Nanggroe-AI v15.2.0 Decision Synthesis Engine
    Adapted for Hermes Quant OS.
    """

    # Machine-readable decision rules
    DECISION_TABLE = [
        {
            "id": "DT001",
            "regime_allowed": ["TRENDING", "RANGE", "MEAN_REVERT"],
            "min_buy_pressure": 0.70,
            "max_sell_pressure": 0.30,
            "allowed_volatility": ["LOW", "NORMAL"],
            "min_confidence": 0.60,
            "action": "ALLOW_LONG",
            "description": "Strong bullish pressure in safe regime"
        },
        {
            "id": "DT002",
            "regime_allowed": ["TRENDING", "RANGE", "MEAN_REVERT"],
            "min_sell_pressure": 0.70,
            "max_buy_pressure": 0.30,
            "allowed_volatility": ["LOW", "NORMAL"],
            "min_confidence": 0.60,
            "action": "ALLOW_SHORT",
            "description": "Strong bearish pressure in safe regime"
        },
        {
            "id": "DT003",
            "regime_allowed": ["TRENDING"],
            "min_buy_pressure": 0.60,
            "max_sell_pressure": 0.40,
            "allowed_volatility": ["LOW", "NORMAL", "HIGH"],
            "min_confidence": 0.55,
            "action": "ALLOW_LONG_TRENDING",
            "description": "Moderate bullish in trending regime"
        },
        {
            "id": "DT004",
            "regime_allowed": ["TRENDING"],
            "min_sell_pressure": 0.60,
            "max_buy_pressure": 0.40,
            "allowed_volatility": ["LOW", "NORMAL", "HIGH"],
            "min_confidence": 0.55,
            "action": "ALLOW_SHORT_TRENDING",
            "description": "Moderate bearish in trending regime"
        },
        {
            "id": "DT005",
            "regime_allowed": ["PANIC", "RISK_OFF", "NO_TRADE"],
            "min_buy_pressure": 1.10,  # Impossible threshold = always blocked
            "action": "NO_TRADE",
            "description": "Dangerous regime - all trading blocked"
        },
        {
            "id": "DT006",
            "regime_allowed": ["TRENDING", "RANGE", "MEAN_REVERT"],
            "min_buy_pressure": 0.55,
            "max_buy_pressure": 0.69,
            "allowed_volatility": ["LOW", "NORMAL"],
            "min_confidence": 0.55,
            "action": "WATCH_LONG",
            "description": "Weak bullish - monitor but don't enter"
        },
        {
            "id": "DT007",
            "regime_allowed": ["TRENDING", "RANGE", "MEAN_REVERT"],
            "min_sell_pressure": 0.55,
            "max_sell_pressure": 0.69,
            "allowed_volatility": ["LOW", "NORMAL"],
            "min_confidence": 0.55,
            "action": "WATCH_SHORT",
            "description": "Weak bearish - monitor but don't enter"
        }
    ]

    def __init__(self):
        self.last_decision = None

    def evaluate(self, regime: str, buy_pressure: float, sell_pressure: float,
                 confidence: float, volatility: str = "NORMAL",
                 daily_pnl_pct: float = 0.0) -> Dict:
        """
        Evaluate market state against decision table.
        
        Args:
            regime: Market regime (TRENDING, RANGE, MEAN_REVERT, RISK_OFF, PANIC, NO_TRADE)
            buy_pressure: Normalized buy pressure (0-1)
            sell_pressure: Normalized sell pressure (0-1)
            confidence: Signal confidence (0-1)
            volatility: Market volatility (LOW, NORMAL, HIGH)
            daily_pnl_pct: Current daily P&L percentage
            
        Returns:
            Decision dict with action, risk_clearance, and details
        """
        matched_rules = []

        for rule in self.DECISION_TABLE:
            # Check regime
            if regime not in rule.get("regime_allowed", []):
                continue

            # Check pressure thresholds
            if buy_pressure < rule.get("min_buy_pressure", 0):
                continue
            if sell_pressure > rule.get("max_sell_pressure", 1.0):
                continue
            if sell_pressure < rule.get("min_sell_pressure", 0):
                continue
            if buy_pressure > rule.get("max_buy_pressure", 1.0):
                continue

            # Check volatility
            if volatility not in rule.get("allowed_volatility", ["LOW", "NORMAL", "HIGH"]):
                continue

            # Check confidence
            if confidence < rule.get("min_confidence", 0):
                continue

            matched_rules.append(rule)

        # Determine action
        if not matched_rules:
            action = "NO_TRADE"
            risk_clearance = "BLOCKED"
            reason = "No decision rule matched - conditions not met"
        else:
            best_rule = matched_rules[0]
            action = best_rule["action"]

            # Additional risk clearance check
            from tools.risk_officer_tool import MAX_DAILY_LOSS
            if abs(min(0, daily_pnl_pct)) >= MAX_DAILY_LOSS:
                risk_clearance = "BLOCKED"
                reason = f"Daily loss limit reached: {daily_pnl_pct:.2%}"
                action = "NO_TRADE"
            elif "ALLOW" in action:
                risk_clearance = "CLEAR"
                reason = best_rule["description"]
            elif "WATCH" in action:
                risk_clearance = "PAUSE"
                reason = f"Monitoring: {best_rule['description']}"
            else:
                risk_clearance = "BLOCKED"
                reason = best_rule["description"]

        decision = {
            "action": action,
            "risk_clearance": risk_clearance,
            "reason": reason,
            "regime": regime,
            "buy_pressure": round(buy_pressure, 4),
            "sell_pressure": round(sell_pressure, 4),
            "confidence": round(confidence, 4),
            "volatility": volatility,
            "matched_rules": [r["id"] for r in matched_rules],
            "timestamp": datetime.now().isoformat()
        }

        self.last_decision = decision
        logger.info(f"DECISION: {action} | Clearance: {risk_clearance} | Regime: {regime}")

        return decision

    def synthesize(self, symbol: str = "XAUUSD") -> str:
        """
        Synthesize a decision for the given symbol by auto-detecting regime
        and calculating pressure from technical analysis.
        """
        try:
            from tools.shared_state import SharedState
            ss = SharedState()

            mse = ss.market_state_engine
            regime_result = mse.auto_detect(symbol)
            regime = regime_result.get("regime", "UNKNOWN")

            tat = ss.technical_analysis
            analysis = json.loads(tat.analyze(symbol, "1h"))
            indicators = analysis.get("indicators", {})
            smc = analysis.get("smc_structure", {})

            trend = smc.get("trend", "neutral")
            rsi = indicators.get("rsi_14", 50)
            atr_pct_str = indicators.get("atr_pct", "1.0")
            atr_pct = float(atr_pct_str.replace("%", "")) if isinstance(atr_pct_str, str) else atr_pct_str or 1.0

            # Derive pressure
            buy_pressure = 0.5
            sell_pressure = 0.5
            if trend == "bullish":
                buy_pressure = 0.65 + (min(rsi, 70) / 70) * 0.15
                sell_pressure = 1.0 - buy_pressure
            elif trend == "bearish":
                sell_pressure = 0.65 + ((100 - max(rsi, 30)) / 70) * 0.15
                buy_pressure = 1.0 - sell_pressure

            confidence = max(buy_pressure, sell_pressure)
            volatility = regime_result.get("volatility", "NORMAL")

            decision = self.evaluate(regime, buy_pressure, sell_pressure, confidence, volatility, 0.0)
            return json.dumps(decision, indent=2)

        except Exception as e:
            return json.dumps({"error": str(e), "action": "NO_TRADE"})

    def status(self) -> str:
        """Get current decision engine status"""
        return json.dumps({
            "last_decision": self.last_decision,
            "available_actions": ["ALLOW_LONG", "ALLOW_SHORT", "NO_TRADE", "WATCH_LONG", "WATCH_SHORT"],
            "decision_rules": len(self.DECISION_TABLE),
            "timestamp": datetime.now().isoformat()
        }, indent=2)
