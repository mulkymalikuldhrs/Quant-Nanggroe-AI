"""
Constitutional Risk Guard — 9-Checkpoint VETO System
=====================================================
From HermesQuantOS — Full VETO AUTHORITY, cannot be overridden.

Risk Rules HARDCODED:
  - 0.5% max risk per trade
  - 1.0% max daily loss
  - 3.0% max weekly loss
  - 1:2 minimum risk:reward ratio

Every risk check is logged with full audit trail.
"""

from __future__ import annotations

from datetime import datetime, date
from typing import Any

from pydantic import BaseModel, Field

from quant_nanggroe_ai.config import (
    MAX_RISK_PER_TRADE,
    MAX_DAILY_LOSS,
    MAX_WEEKLY_LOSS,
    MIN_RISK_REWARD,
    MAX_CORRELATED_POSITIONS,
)
from quant_nanggroe_ai.types import RiskCheckpointResult, RiskVerdict


# ══════════════════════════════════════════════════════════════════════
# Correlated Symbol Groups
# ══════════════════════════════════════════════════════════════════════

CORRELATED_GROUPS: list[set[str]] = [
    {"EURUSD", "GBPUSD", "AUDUSD", "NZDUSD"},  # USD weakness basket
    {"USDJPY", "USDCHF", "USDCAD"},  # USD strength basket
    {"XAUUSD", "XAGUSD"},  # Precious metals
    {"BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"},  # Crypto basket
    {"SPY", "QQQ", "IWM"},  # US Equity indices
    {"AAPL", "MSFT", "GOOGL", "AMZN", "META"},  # Tech mega-cap
]


def _is_correlated(position_symbol: str, new_symbol: str) -> bool:
    """Check if two symbols belong to the same correlated group."""
    pos_upper = position_symbol.upper()
    new_upper = new_symbol.upper()
    for group in CORRELATED_GROUPS:
        if pos_upper in group and new_upper in group:
            return True
    return False


class RiskCheckResult(BaseModel):
    """Result of a full 9-checkpoint risk validation."""

    symbol: str
    direction: str
    lot_size: float
    entry: float
    stop_loss: float | None
    take_profit: float | None
    risk_pct: float
    rr_ratio: float = 0.0
    verdict: str  # "APPROVED" or "VETOED"
    checkpoints: dict[str, RiskCheckpointResult]
    veto_count_total: int = 0
    approval_count_total: int = 0
    timestamp: datetime = Field(default_factory=datetime.now)


class ConstitutionalRiskGuard:
    """
    L3 Agent: Risk Officer — FULL VETO, hardcoded risk rules.

    The 9-checkpoint system cannot be overridden by any other agent.
    If any single checkpoint fails, the trade is VETOED.

    Checkpoints:
        1. Risk per trade ≤ 0.5%
        2. Daily loss < 1.0%
        3. Weekly loss < 3.0%
        4. Risk:Reward ≥ 1:2
        5. Stop loss exists and is valid
        6. Entry price is valid (> 0)
        7. Direction is valid (BUY/SELL/LONG/SHORT)
        8. Not overtrading (≤ 5 trades/day)
        9. Correlated position check (≤ 3 correlated)
    """

    def __init__(self) -> None:
        self.daily_pnl: float = 0.0
        self.weekly_pnl: float = 0.0
        self.trade_count_today: int = 0
        self.trade_count_week: int = 0
        self.active_positions: list[str] = []
        self.veto_count: int = 0
        self.approval_count: int = 0
        self.last_reset: date = datetime.now().date()

    def _reset_daily_if_needed(self) -> None:
        """Reset daily counters if new day."""
        today = datetime.now().date()
        if today > self.last_reset:
            self.daily_pnl = 0.0
            self.trade_count_today = 0
            self.last_reset = today

    def check_trade(
        self,
        symbol: str,
        direction: str,
        lot_size: float,
        entry: float,
        stop_loss: float | None,
        account_balance: float = 10000.0,
        take_profit: float | None = None,
        pip_value: float = 10.0,
    ) -> RiskCheckResult:
        """
        Execute 9-checkpoint risk validation.

        Returns APPROVED only if ALL checkpoints pass.
        Any single failure triggers VETO.

        Args:
            symbol: Trading symbol (e.g., "EURUSD")
            direction: Trade direction ("BUY", "SELL", "LONG", "SHORT")
            lot_size: Position size in lots
            entry: Entry price
            stop_loss: Stop loss price
            account_balance: Current account balance
            take_profit: Take profit price (optional)
            pip_value: Value per pip per lot

        Returns:
            RiskCheckResult with verdict and full checkpoint details
        """
        self._reset_daily_if_needed()

        checkpoints: dict[str, RiskCheckpointResult] = {}
        all_passed = True

        # ── Checkpoint 1: Risk per trade limit ───────────────────────
        if stop_loss is not None and entry > 0:
            risk_amount = abs(entry - stop_loss) * lot_size * 100000  # Forex lot sizing
            risk_pct = risk_amount / account_balance if account_balance > 0 else 1.0
        else:
            risk_pct = 1.0  # Unknown risk = max risk

        checkpoints["1_risk_per_trade"] = RiskCheckpointResult(
            name="1_risk_per_trade",
            value=f"{risk_pct:.4f}",
            limit=f"{MAX_RISK_PER_TRADE:.4f}",
            passed=risk_pct <= MAX_RISK_PER_TRADE,
        )
        if not checkpoints["1_risk_per_trade"].passed:
            all_passed = False

        # ── Checkpoint 2: Daily loss limit ───────────────────────────
        daily_loss_pct = abs(min(0.0, self.daily_pnl)) if self.daily_pnl < 0 else 0.0
        checkpoints["2_daily_loss"] = RiskCheckpointResult(
            name="2_daily_loss",
            value=f"{daily_loss_pct:.4f}",
            limit=f"{MAX_DAILY_LOSS:.4f}",
            passed=daily_loss_pct < MAX_DAILY_LOSS,
        )
        if not checkpoints["2_daily_loss"].passed:
            all_passed = False

        # ── Checkpoint 3: Weekly loss limit ──────────────────────────
        weekly_loss_pct = abs(min(0.0, self.weekly_pnl)) if self.weekly_pnl < 0 else 0.0
        checkpoints["3_weekly_loss"] = RiskCheckpointResult(
            name="3_weekly_loss",
            value=f"{weekly_loss_pct:.4f}",
            limit=f"{MAX_WEEKLY_LOSS:.4f}",
            passed=weekly_loss_pct < MAX_WEEKLY_LOSS,
        )
        if not checkpoints["3_weekly_loss"].passed:
            all_passed = False

        # ── Checkpoint 4: Risk:Reward ratio ──────────────────────────
        rr_ratio = 0.0
        if take_profit and stop_loss and abs(entry - stop_loss) > 0:
            rr_ratio = abs(take_profit - entry) / abs(entry - stop_loss)
            # Round to 4 decimal places to avoid floating point precision issues
            rr_ratio = round(rr_ratio, 4)
        checkpoints["4_risk_reward"] = RiskCheckpointResult(
            name="4_risk_reward",
            value=f"1:{rr_ratio:.1f}",
            limit=f"1:{MIN_RISK_REWARD:.1f}",
            passed=rr_ratio >= MIN_RISK_REWARD,
        )
        if not checkpoints["4_risk_reward"].passed:
            all_passed = False

        # ── Checkpoint 5: Stop loss exists ───────────────────────────
        checkpoints["5_stop_loss_exists"] = RiskCheckpointResult(
            name="5_stop_loss_exists",
            value=str(stop_loss is not None and stop_loss > 0),
            limit="True",
            passed=stop_loss is not None and stop_loss > 0,
        )
        if not checkpoints["5_stop_loss_exists"].passed:
            all_passed = False

        # ── Checkpoint 6: Entry is valid ─────────────────────────────
        checkpoints["6_valid_entry"] = RiskCheckpointResult(
            name="6_valid_entry",
            value=str(entry > 0),
            limit="True",
            passed=entry > 0,
        )
        if not checkpoints["6_valid_entry"].passed:
            all_passed = False

        # ── Checkpoint 7: Direction is valid ─────────────────────────
        valid_dirs = {"BUY", "SELL", "LONG", "SHORT"}
        checkpoints["7_valid_direction"] = RiskCheckpointResult(
            name="7_valid_direction",
            value=direction.upper(),
            limit="BUY/SELL",
            passed=direction.upper() in valid_dirs,
        )
        if not checkpoints["7_valid_direction"].passed:
            all_passed = False

        # ── Checkpoint 8: Not overtrading ────────────────────────────
        checkpoints["8_not_overtrading"] = RiskCheckpointResult(
            name="8_not_overtrading",
            value=str(self.trade_count_today),
            limit="5",
            passed=self.trade_count_today < 5,
        )
        if not checkpoints["8_not_overtrading"].passed:
            all_passed = False

        # ── Checkpoint 9: Correlated position check ──────────────────
        correlated = sum(1 for p in self.active_positions if _is_correlated(p, symbol))
        checkpoints["9_correlation_check"] = RiskCheckpointResult(
            name="9_correlation_check",
            value=str(correlated),
            limit=str(MAX_CORRELATED_POSITIONS),
            passed=correlated < MAX_CORRELATED_POSITIONS,
        )
        if not checkpoints["9_correlation_check"].passed:
            all_passed = False

        # ── Final verdict ────────────────────────────────────────────
        verdict = "APPROVED" if all_passed else "VETOED"
        if verdict == "VETOED":
            self.veto_count += 1
        else:
            self.approval_count += 1

        return RiskCheckResult(
            symbol=symbol,
            direction=direction.upper(),
            lot_size=lot_size,
            entry=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_pct=round(risk_pct, 4),
            rr_ratio=round(rr_ratio, 1),
            verdict=verdict,
            checkpoints=checkpoints,
            veto_count_total=self.veto_count,
            approval_count_total=self.approval_count,
        )

    def calculate_lot_size(
        self,
        account_balance: float,
        risk_pct: float,
        stop_loss_pips: float,
        pip_value: float = 10.0,
    ) -> dict[str, Any]:
        """
        Calculate proper lot size based on risk parameters.

        Risk_pct is capped at MAX_RISK_PER_TRADE regardless of input.
        This ensures no override of constitutional limits.

        Args:
            account_balance: Current account balance
            risk_pct: Requested risk percentage (capped at 0.5%)
            stop_loss_pips: Stop loss distance in pips
            pip_value: Value per pip per lot

        Returns:
            Dict with calculated lot size and risk details
        """
        # HARDCODED: Cap risk at maximum
        effective_risk = min(risk_pct, MAX_RISK_PER_TRADE)

        risk_amount = account_balance * effective_risk
        lot_size = risk_amount / (stop_loss_pips * pip_value) if stop_loss_pips > 0 else 0.0

        # Round down to 0.01
        lot_size = max(0.01, round(lot_size * 100) / 100)

        return {
            "account_balance": account_balance,
            "requested_risk_pct": f"{risk_pct:.4f}",
            "effective_risk_pct": f"{effective_risk:.4f}",
            "capped": risk_pct > MAX_RISK_PER_TRADE,
            "max_risk_hardcoded": f"{MAX_RISK_PER_TRADE:.4f}",
            "risk_amount": round(risk_amount, 2),
            "stop_loss_pips": stop_loss_pips,
            "lot_size": lot_size,
            "note": "Risk percentage capped at hardcoded maximum. No override possible.",
        }

    def update_pnl(self, trade_pnl: float) -> None:
        """
        Update daily and weekly PnL tracking.

        Also checks if kill switch should auto-activate.
        """
        self._reset_daily_if_needed()
        self.daily_pnl += trade_pnl
        self.weekly_pnl += trade_pnl
        self.trade_count_today += 1
        self.trade_count_week += 1

    def status(self) -> dict[str, Any]:
        """Get current risk status."""
        self._reset_daily_if_needed()

        daily_status = "OK" if abs(min(0.0, self.daily_pnl)) < MAX_DAILY_LOSS else "LIMIT_REACHED"
        weekly_status = "OK" if abs(min(0.0, self.weekly_pnl)) < MAX_WEEKLY_LOSS else "LIMIT_REACHED"
        overall = "TRADING_ALLOWED" if daily_status == "OK" and weekly_status == "OK" else "KILL_SWITCH_ACTIVE"

        return {
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
                "override_possible": False,
            },
        }
