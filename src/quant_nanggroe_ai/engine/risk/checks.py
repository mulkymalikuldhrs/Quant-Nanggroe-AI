"""9-Checkpoint Risk Gate — from HermesQuantOS.

Implements the full 9-checkpoint risk validation system that every
trade must pass before execution. If ANY checkpoint fails, the trade
is VETOED and cannot be overridden by any agent.

Checkpoints:
1. Risk per trade limit (≤0.5%)
2. Daily loss limit (≤1%)
3. Weekly loss limit (≤3%)
4. Risk:Reward ratio (≥1:2)
5. Stop loss exists
6. Valid entry price
7. Valid direction
8. Not overtrading (max 5 trades/day)
9. Correlated position check

Extracted from HermesQuantOS's RiskOfficerTool.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from quant_nanggroe_ai.engine.risk.correlation import CorrelationMonitor
from quant_nanggroe_ai.engine.risk.constants import (
    MAX_RISK_PER_TRADE,
    MAX_DAILY_LOSS,
    MAX_WEEKLY_LOSS,
    MIN_RISK_REWARD,
    MAX_CORRELATED_POSITIONS,
    MAX_DAILY_TRADES,
)

logger = logging.getLogger(__name__)


class RiskCheckGate:
    """9-Checkpoint Risk Gate with FULL VETO authority.

    No agent can override a VETO from this gate. All constitutional
    limits are hardcoded and cannot be bypassed.
    """

    def __init__(self) -> None:
        self.correlation_monitor = CorrelationMonitor()

    def evaluate(
        self,
        symbol: str,
        direction: str,
        lot_size: float,
        entry: float,
        stop_loss: float,
        account_balance: float = 1_000_000.0,
        take_profit: Optional[float] = None,
        daily_pnl: float = 0.0,
        weekly_pnl: float = 0.0,
        trade_count_today: int = 0,
        active_positions: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Evaluate a trade proposal through all 9 checkpoints.

        Args:
            symbol: Trading symbol.
            direction: BUY/SELL/LONG/SHORT.
            lot_size: Proposed lot size.
            entry: Entry price.
            stop_loss: Stop loss price.
            account_balance: Current account balance.
            take_profit: Optional take profit price.
            daily_pnl: Today's accumulated P&L.
            weekly_pnl: This week's accumulated P&L.
            trade_count_today: Number of trades today.
            active_positions: List of currently held symbols.

        Returns:
            Dict with verdict (APPROVED/VETOED) and checkpoint details.
        """
        active_positions = active_positions or []
        checkpoints = {}
        all_passed = True

        # ── Checkpoint 1: Risk per trade limit ──
        risk_amount = abs(entry - stop_loss) * lot_size * 100000  # Forex lot sizing
        risk_pct = risk_amount / account_balance if account_balance > 0 else 1.0
        checkpoints["1_risk_per_trade"] = {
            "value": f"{risk_pct:.4f}",
            "limit": f"{MAX_RISK_PER_TRADE:.4f}",
            "passed": risk_pct <= MAX_RISK_PER_TRADE,
        }
        if not checkpoints["1_risk_per_trade"]["passed"]:
            all_passed = False

        # ── Checkpoint 2: Daily loss limit ──
        daily_loss_pct = abs(min(0, daily_pnl)) / account_balance if account_balance > 0 and daily_pnl < 0 else 0
        checkpoints["2_daily_loss"] = {
            "value": f"{daily_loss_pct:.4f}",
            "limit": f"{MAX_DAILY_LOSS:.4f}",
            "passed": daily_loss_pct < MAX_DAILY_LOSS,
        }
        if not checkpoints["2_daily_loss"]["passed"]:
            all_passed = False

        # ── Checkpoint 3: Weekly loss limit ──
        weekly_loss_pct = abs(min(0, weekly_pnl)) / account_balance if account_balance > 0 and weekly_pnl < 0 else 0
        checkpoints["3_weekly_loss"] = {
            "value": f"{weekly_loss_pct:.4f}",
            "limit": f"{MAX_WEEKLY_LOSS:.4f}",
            "passed": weekly_loss_pct < MAX_WEEKLY_LOSS,
        }
        if not checkpoints["3_weekly_loss"]["passed"]:
            all_passed = False

        # ── Checkpoint 4: Risk:Reward ratio ──
        if take_profit and stop_loss and abs(entry - stop_loss) > 0:
            rr_ratio = abs(take_profit - entry) / abs(entry - stop_loss)
        else:
            rr_ratio = 0
        checkpoints["4_risk_reward"] = {
            "value": f"1:{rr_ratio:.1f}",
            "limit": f"1:{MIN_RISK_REWARD:.1f}",
            "passed": rr_ratio >= MIN_RISK_REWARD,
        }
        if not checkpoints["4_risk_reward"]["passed"]:
            all_passed = False

        # ── Checkpoint 5: Stop loss exists ──
        checkpoints["5_stop_loss_exists"] = {
            "value": str(stop_loss is not None and stop_loss > 0),
            "limit": "True",
            "passed": stop_loss is not None and stop_loss > 0,
        }
        if not checkpoints["5_stop_loss_exists"]["passed"]:
            all_passed = False

        # ── Checkpoint 6: Valid entry price ──
        checkpoints["6_valid_entry"] = {
            "value": str(entry > 0),
            "limit": "True",
            "passed": entry > 0,
        }
        if not checkpoints["6_valid_entry"]["passed"]:
            all_passed = False

        # ── Checkpoint 7: Valid direction ──
        valid_dirs = ["BUY", "SELL", "LONG", "SHORT"]
        checkpoints["7_valid_direction"] = {
            "value": direction.upper(),
            "limit": "BUY/SELL",
            "passed": direction.upper() in valid_dirs,
        }
        if not checkpoints["7_valid_direction"]["passed"]:
            all_passed = False

        # ── Checkpoint 8: Not overtrading ──
        checkpoints["8_not_overtrading"] = {
            "value": str(trade_count_today),
            "limit": str(MAX_DAILY_TRADES),
            "passed": trade_count_today < MAX_DAILY_TRADES,
        }
        if not checkpoints["8_not_overtrading"]["passed"]:
            all_passed = False

        # ── Checkpoint 9: Correlated position check ──
        correlated = self.correlation_monitor.count_correlated_positions(symbol, active_positions)
        checkpoints["9_correlation_check"] = {
            "value": str(correlated),
            "limit": str(MAX_CORRELATED_POSITIONS),
            "passed": correlated < MAX_CORRELATED_POSITIONS,
        }
        if not checkpoints["9_correlation_check"]["passed"]:
            all_passed = False

        verdict = "APPROVED" if all_passed else "VETOED"
        failed = [name for name, cp in checkpoints.items() if not cp["passed"]]

        return {
            "symbol": symbol,
            "direction": direction.upper(),
            "verdict": verdict,
            "checkpoints": checkpoints,
            "failed_checkpoints": failed,
            "risk_pct": f"{risk_pct:.4f}",
            "rr_ratio": f"1:{rr_ratio:.1f}" if rr_ratio > 0 else "N/A",
        }
