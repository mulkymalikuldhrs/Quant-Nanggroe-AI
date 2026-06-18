#!/usr/bin/env python3
"""
Risk Officer Agent (L3 - Decision Layer)
FULL VETO AUTHORITY - Cannot be overridden by any other agent
9 Checkpoints before any trade execution
Risk Rules HARDCODED: 0.5%/trade, 1%/day, 3%/week
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List

logger = logging.getLogger("HermesQuantOS.RiskOfficer")

# HARDCODED RISK LIMITS - NO OVERRIDE POSSIBLE
MAX_RISK_PER_TRADE = 0.005    # 0.5% max risk per trade
MAX_DAILY_LOSS = 0.01         # 1% max daily loss
MAX_WEEKLY_LOSS = 0.03        # 3% max weekly loss
MIN_RISK_REWARD = 2.0         # Minimum 1:2 R:R ratio
MAX_CORRELATED_POSITIONS = 3  # Max correlated positions


class RiskOfficerTool:
    """L3 Agent: Risk Officer - FULL VETO, hardcoded risk rules"""

    def __init__(self) -> None:
        self.daily_pnl = 0.0
        self.weekly_pnl = 0.0
        self.trade_count_today = 0
        self.trade_count_week = 0
        self.active_positions: List[str] = []
        self.veto_count = 0
        self.approval_count = 0
        self.last_reset = datetime.now().date()

    def _reset_daily_if_needed(self) -> None:
        """Reset daily counters if new day"""
        today = datetime.now().date()
        if today > self.last_reset:
            self.daily_pnl = 0.0
            self.trade_count_today = 0
            self.last_reset = today

    def check_trade(self, symbol: str, direction: str, lot_size: float,
                    entry: float, stop_loss: float, account_balance: float = 10000.0,
                    take_profit: float = None) -> str:
        """
        9-checkpoint risk validation. Returns APPROVED or VETOED.
        """
        self._reset_daily_if_needed()

        checkpoints = {}
        all_passed = True

        # Checkpoint 1: Risk per trade limit
        risk_amount = abs(entry - stop_loss) * lot_size * 100000  # Forex lot sizing
        risk_pct = risk_amount / account_balance if account_balance > 0 else 1.0
        checkpoints["1_risk_per_trade"] = {
            "value": f"{risk_pct:.4f}",
            "limit": f"{MAX_RISK_PER_TRADE:.4f}",
            "passed": risk_pct <= MAX_RISK_PER_TRADE
        }
        if not checkpoints["1_risk_per_trade"]["passed"]:
            all_passed = False

        # Checkpoint 2: Daily loss limit
        daily_loss_pct = abs(min(0, self.daily_pnl)) if self.daily_pnl < 0 else 0
        checkpoints["2_daily_loss"] = {
            "value": f"{daily_loss_pct:.4f}",
            "limit": f"{MAX_DAILY_LOSS:.4f}",
            "passed": daily_loss_pct < MAX_DAILY_LOSS
        }
        if not checkpoints["2_daily_loss"]["passed"]:
            all_passed = False

        # Checkpoint 3: Weekly loss limit
        weekly_loss_pct = abs(min(0, self.weekly_pnl)) if self.weekly_pnl < 0 else 0
        checkpoints["3_weekly_loss"] = {
            "value": f"{weekly_loss_pct:.4f}",
            "limit": f"{MAX_WEEKLY_LOSS:.4f}",
            "passed": weekly_loss_pct < MAX_WEEKLY_LOSS
        }
        if not checkpoints["3_weekly_loss"]["passed"]:
            all_passed = False

        # Checkpoint 4: Risk:Reward ratio
        if take_profit and stop_loss:
            rr_ratio = abs(take_profit - entry) / abs(entry - stop_loss) if abs(entry - stop_loss) > 0 else 0
        else:
            rr_ratio = 0
        checkpoints["4_risk_reward"] = {
            "value": f"1:{rr_ratio:.1f}",
            "limit": f"1:{MIN_RISK_REWARD:.1f}",
            "passed": rr_ratio >= MIN_RISK_REWARD
        }
        if not checkpoints["4_risk_reward"]["passed"]:
            all_passed = False

        # Checkpoint 5: Stop loss exists
        checkpoints["5_stop_loss_exists"] = {
            "value": str(stop_loss is not None and stop_loss > 0),
            "limit": "True",
            "passed": stop_loss is not None and stop_loss > 0
        }
        if not checkpoints["5_stop_loss_exists"]["passed"]:
            all_passed = False

        # Checkpoint 6: Entry is valid
        checkpoints["6_valid_entry"] = {
            "value": str(entry > 0),
            "limit": "True",
            "passed": entry > 0
        }
        if not checkpoints["6_valid_entry"]["passed"]:
            all_passed = False

        # Checkpoint 7: Direction is valid
        valid_dirs = ["BUY", "SELL", "LONG", "SHORT"]
        checkpoints["7_valid_direction"] = {
            "value": direction.upper(),
            "limit": "BUY/SELL",
            "passed": direction.upper() in valid_dirs
        }
        if not checkpoints["7_valid_direction"]["passed"]:
            all_passed = False

        # Checkpoint 8: Not trading against daily loss trend
        checkpoints["8_not_overtrading"] = {
            "value": str(self.trade_count_today),
            "limit": "5",
            "passed": self.trade_count_today < 5
        }
        if not checkpoints["8_not_overtrading"]["passed"]:
            all_passed = False

        # Checkpoint 9: Correlated position check
        correlated = sum(1 for p in self.active_positions if self._is_correlated(p, symbol))
        checkpoints["9_correlation_check"] = {
            "value": str(correlated),
            "limit": str(MAX_CORRELATED_POSITIONS),
            "passed": correlated < MAX_CORRELATED_POSITIONS
        }
        if not checkpoints["9_correlation_check"]["passed"]:
            all_passed = False

        verdict = "APPROVED" if all_passed else "VETOED"
        if verdict == "VETOED":
            self.veto_count += 1
        else:
            self.approval_count += 1

        result = {
            "symbol": symbol,
            "direction": direction.upper(),
            "lot_size": lot_size,
            "entry": entry,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "risk_pct": f"{risk_pct:.4f}",
            "rr_ratio": f"1:{rr_ratio:.1f}" if rr_ratio > 0 else "N/A",
            "verdict": verdict,
            "checkpoints": checkpoints,
            "veto_count_total": self.veto_count,
            "approval_count_total": self.approval_count,
            "timestamp": datetime.now().isoformat()
        }

        # LOG EVERY RISK CHECK
        logger.info(f"RISK CHECK: {symbol} {direction} -> {verdict}")

        return json.dumps(result, indent=2)

    def _is_correlated(self, position_symbol: str, new_symbol: str) -> bool:
        """Check if two symbols are correlated"""
        correlated_groups = [
            {"EURUSD", "GBPUSD", "AUDUSD", "NZDUSD"},  # USD weakness basket
            {"USDJPY", "USDCHF", "USDCAD"},             # USD strength basket
            {"XAUUSD", "XAGUSD"},                        # Precious metals
            {"BTCUSDT", "ETHUSDT", "SHIB", "TRX"},     # Crypto basket
        ]

        for group in correlated_groups:
            if position_symbol.upper() in group and new_symbol.upper() in group:
                return True
        return False

    def calculate_lot_size(self, account_balance: float, risk_pct: float,
                           stop_loss_pips: float, pip_value: float = 10.0) -> str:
        """
        Calculate proper lot size based on risk parameters.
        Risk_pct is capped at MAX_RISK_PER_TRADE regardless of input.
        """
        # HARDCODED: Cap risk at maximum
        effective_risk = min(risk_pct, MAX_RISK_PER_TRADE)

        risk_amount = account_balance * effective_risk
        lot_size = risk_amount / (stop_loss_pips * pip_value) if stop_loss_pips > 0 else 0

        # Round down to 0.01
        lot_size = max(0.01, round(lot_size * 100) / 100)

        return json.dumps({
            "account_balance": account_balance,
            "requested_risk_pct": f"{risk_pct:.4f}",
            "effective_risk_pct": f"{effective_risk:.4f}",
            "capped": risk_pct > MAX_RISK_PER_TRADE,
            "max_risk_hardcoded": f"{MAX_RISK_PER_TRADE:.4f}",
            "risk_amount": round(risk_amount, 2),
            "stop_loss_pips": stop_loss_pips,
            "lot_size": lot_size,
            "note": "Risk percentage capped at hardcoded maximum. No override possible."
        }, indent=2)

    def update_pnl(self, trade_pnl: float) -> None:
        """Update daily and weekly PnL tracking"""
        self._reset_daily_if_needed()
        self.daily_pnl += trade_pnl
        self.weekly_pnl += trade_pnl
        self.trade_count_today += 1
        self.trade_count_week += 1

        # Auto-check if kill switch should activate
        if abs(min(0, self.daily_pnl)) >= MAX_DAILY_LOSS:
            logger.critical(f"DAILY LOSS LIMIT BREACHED: {self.daily_pnl:.2%} >= {MAX_DAILY_LOSS:.2%}")
        if abs(min(0, self.weekly_pnl)) >= MAX_WEEKLY_LOSS:
            logger.critical(f"WEEKLY LOSS LIMIT BREACHED: {self.weekly_pnl:.2%} >= {MAX_WEEKLY_LOSS:.2%}")

    def status(self) -> str:
        """Get current risk status"""
        self._reset_daily_if_needed()

        daily_status = "OK" if abs(min(0, self.daily_pnl)) < MAX_DAILY_LOSS else "LIMIT_REACHED"
        weekly_status = "OK" if abs(min(0, self.weekly_pnl)) < MAX_WEEKLY_LOSS else "LIMIT_REACHED"
        overall = "TRADING_ALLOWED" if daily_status == "OK" and weekly_status == "OK" else "KILL_SWITCH_ACTIVE"

        return json.dumps({
            "overall_status": overall,
            "daily_pnl": f"{self.daily_pnl:.2%}",
            "weekly_pnl": f"{self.weekly_pnl:.2%}",
            "daily_limit": f"{MAX_DAILY_LOSS:.2%}",
            "weekly_limit": f"{MAX_WEEKLY_LOSS:.2%}",
            "daily_status": daily_status,
            "weekly_status": weekly_status,
            "trades_today": self.trade_count_today,
            "trades_week": self.trade_count_week,
            "veto_count": self.veto_count,
            "approval_count": self.approval_count,
            "active_positions": len(self.active_positions),
            "hardcoded_limits": {
                "max_risk_per_trade": f"{MAX_RISK_PER_TRADE:.2%}",
                "max_daily_loss": f"{MAX_DAILY_LOSS:.2%}",
                "max_weekly_loss": f"{MAX_WEEKLY_LOSS:.2%}",
                "min_rr_ratio": f"1:{MIN_RISK_REWARD}",
                "override_possible": False
            }
        }, indent=2)
