"""
Trading Plan Agent Tool
========================
Agent tool for trade planning, journaling, discipline tracking,
and AI-powered market analysis.

Ported from Trading-Plan-AI-Interactive v11.1.4 "Production Hardened":
  - Google Apps Script main.gs (journal, violations, weekly analysis)
  - Google Apps Script api_integrations.gs (technicals, news, COT, calendar)
  - Python client dhaher_ai_client.py (API interaction patterns)

Key Features:
  - Trade logging with AI validation
  - Rule violation tracking with emotional lockout (3-strike system)
  - AI-powered market summary generation
  - Multi-day forecast generation
  - COT (Commitment of Traders) institutional analysis
  - Economic calendar integration
  - Weekly performance analysis
  - WhatsApp notification triggers for discipline alerts

All import paths use the quant_nanggroe_ai package.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# Enums and Data Models
# ══════════════════════════════════════════════════════════════════════


class TradeDirection(str, Enum):
    BUY = "Buy"
    SELL = "Sell"


class TradeResult(str, Enum):
    WIN = "WIN"
    LOSS = "LOSS"
    BREAKEVEN = "BREAKEVEN"
    PENDING = "PENDING"


class Mood(str, Enum):
    CONFIDENT = "Confident"
    CAUTIOUS = "Cautious"
    ANXIOUS = "Anxious"
    FOMO = "FOMO"
    DISCIPLINED = "Disciplined"
    REVENGE = "Revenge"
    NEUTRAL = "Neutral"


class Bias(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class ViolationSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TradeEntry:
    """A single trade journal entry."""

    pair: str
    direction: TradeDirection
    entry: float
    sl: float
    tp: float
    rrr: float
    setup: str
    mood: Mood
    ai_status: str = "Pending"
    result: TradeResult = TradeResult.PENDING
    emotion_after: str = ""
    gpt_comment: str = ""
    pnl: float = 0.0
    trade_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if not self.trade_id:
            self.trade_id = f"TRADE-{int(self.timestamp.timestamp() * 1000)}"


@dataclass
class ViolationEntry:
    """A rule violation record."""

    trade_id: str
    rule_broken: str
    justification: str
    severity: ViolationSeverity = ViolationSeverity.MEDIUM
    violation_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if not self.violation_id:
            self.violation_id = f"V-{int(self.timestamp.timestamp() * 1000)}"


@dataclass
class AISignal:
    """AI-generated trading signal."""

    active: bool = False
    entry: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    bias: Bias = Bias.NEUTRAL
    confidence_score: int = 0  # 1-10
    technical_thesis: str = ""
    fundamental_thesis: str = ""
    positional_thesis: str = ""


@dataclass
class ForecastResult:
    """Multi-day forecast result."""

    pair: str
    bias: Bias = Bias.NEUTRAL
    entry_zone: str = ""
    confirmation: str = ""
    stop_loss: float | None = None
    take_profit: float | None = None
    probability: float = 0.0  # 0-100%
    is_tradeable: bool = False
    timeframe: str = "H4"
    days: int = 7
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class COTData:
    """Commitment of Traders report data."""

    symbol: str
    report_date: str = ""
    non_commercial_long: int = 0
    non_commercial_short: int = 0
    net_position: int = 0
    bias: Bias = Bias.NEUTRAL
    source: str = ""

    @property
    def long_short_ratio(self) -> float:
        """Ratio of long to short positions."""
        if self.non_commercial_short == 0:
            return float("inf") if self.non_commercial_long > 0 else 0.0
        return self.non_commercial_long / self.non_commercial_short


@dataclass
class EconomicEvent:
    """An economic calendar event."""

    event: str
    impact: str = "MEDIUM"
    time: str = ""
    country: str = ""


@dataclass
class WeeklySummary:
    """Weekly performance summary."""

    total_trades: int = 0
    win_rate: float = 0.0
    total_pnl: float = 0.0
    dominant_emotion: str = ""
    violation_count: int = 0
    best_setup: str = ""
    worst_setup: str = ""
    ai_feedback: str = ""
    week_start: datetime = field(default_factory=datetime.now)
    week_end: datetime = field(default_factory=datetime.now)


# ══════════════════════════════════════════════════════════════════════
# CFTC Symbol Mapping (from GAS api_integrations.gs)
# ══════════════════════════════════════════════════════════════════════

CFTC_SYMBOL_MAP: dict[str, str] = {
    "EUR/USD": "EURO CURRENCY",
    "GBP/USD": "BRITISH POUND STERLING",
    "JPY/USD": "JAPANESE YEN",
    "AUD/USD": "AUSTRALIAN DOLLAR",
    "NZD/USD": "NEW ZEALAND DOLLAR",
    "USD/CAD": "CANADIAN DOLLAR",
    "USD/CHF": "SWISS FRANC",
    "XAU/USD": "GOLD - COMMODITY EXCHANGE INC.",
    "GOLD": "GOLD - COMMODITY EXCHANGE INC.",
}


def normalize_symbol(symbol: str) -> str:
    """
    Normalize a symbol for COT lookup.

    Converts ``EURUSD`` → ``EUR/USD`` for CFTC mapping.
    """
    s = symbol.upper().strip()
    if len(s) == 6 and "/" not in s:
        return f"{s[:3]}/{s[3:]}"
    return s


# ══════════════════════════════════════════════════════════════════════
# Trading Plan Tool — Agent-Facing Interface
# ══════════════════════════════════════════════════════════════════════


class TradingPlanTool:
    """
    Agent tool for trade planning, journaling, and discipline tracking.

    This tool encapsulates all Trading Plan AI logic and can be used
    by agents to:
    - Log and validate trades
    - Track rule violations with emotional lockout
    - Generate AI market summaries and forecasts
    - Analyze weekly performance
    - Calculate position risk metrics

    The tool can work standalone (in-memory) or connect to the
    Google Apps Script backend via :class:`TradingPlanClient`.

    Args:
        client: Optional :class:`TradingPlanClient` for API mode.
        violation_lockout_threshold: Number of consecutive violations
            before emotional lockout triggers (default: 3).
        max_risk_pct: Maximum risk per trade as % of account (default: 2.0).
        min_rrr: Minimum risk-reward ratio required (default: 2.0).
    """

    def __init__(
        self,
        client: Any | None = None,
        violation_lockout_threshold: int = 3,
        max_risk_pct: float = 2.0,
        min_rrr: float = 2.0,
    ) -> None:
        self.client = client
        self.violation_lockout_threshold = violation_lockout_threshold
        self.max_risk_pct = max_risk_pct
        self.min_rrr = min_rrr

        # In-memory stores (when not using API backend)
        self._trades: list[TradeEntry] = []
        self._violations: list[ViolationEntry] = []
        self._forecasts: list[ForecastResult] = []
        self._weekly_summaries: list[WeeklySummary] = []

        # Emotional lockout state
        self._lockout_active: bool = False
        self._lockout_triggered_at: datetime | None = None
        self._consecutive_violations: int = 0

    # ------------------------------------------------------------------
    # Trade Logging
    # ------------------------------------------------------------------

    def log_trade(self, trade: TradeEntry) -> dict[str, Any]:
        """
        Log a trade to the journal.

        If a client is configured, also sends to the GAS backend.

        Args:
            trade: The trade entry to log.

        Returns:
            Dict with trade_id and status.
        """
        self._trades.append(trade)
        logger.info("Trade logged: %s %s @ %s", trade.direction.value, trade.pair, trade.entry)

        result: dict[str, Any] = {
            "trade_id": trade.trade_id,
            "status": "logged",
            "pair": trade.pair,
            "direction": trade.direction.value,
            "rrr": trade.rrr,
        }

        # Send to API backend if client is configured
        if self.client is not None:
            try:
                api_result = self.client.log_trade({
                    "pair": trade.pair,
                    "direction": trade.direction.value,
                    "entry": trade.entry,
                    "sl": trade.sl,
                    "tp": trade.tp,
                    "rrr": trade.rrr,
                    "setup": trade.setup,
                    "mood": trade.mood.value,
                    "ai_status": trade.ai_status,
                    "result": trade.result.value,
                    "emotion_after": trade.emotion_after,
                    "gpt_comment": trade.gpt_comment,
                    "pnl": trade.pnl,
                })
                result["api_status"] = api_result
            except Exception as exc:
                logger.warning("Failed to log trade via API: %s", exc)
                result["api_status"] = f"failed: {exc}"

        return result

    def get_trades(self, pair: str | None = None, limit: int = 50) -> list[TradeEntry]:
        """Get recent trades, optionally filtered by pair."""
        trades = self._trades
        if pair:
            trades = [t for t in trades if t.pair.upper() == pair.upper()]
        return trades[-limit:]

    # ------------------------------------------------------------------
    # Violation Tracking & Emotional Lockout
    # ------------------------------------------------------------------

    def log_violation(self, violation: ViolationEntry) -> dict[str, Any]:
        """
        Log a rule violation and check for emotional lockout.

        After ``violation_lockout_threshold`` consecutive violations,
        emotional lockout is triggered — the trader must take a
        mandatory break.

        Args:
            violation: The violation entry to log.

        Returns:
            Dict with violation_id, lockout status, and consecutive count.
        """
        self._violations.append(violation)
        self._consecutive_violations += 1

        lockout_triggered = False
        if self._consecutive_violations >= self.violation_lockout_threshold:
            self._lockout_active = True
            self._lockout_triggered_at = datetime.now()
            lockout_triggered = True
            logger.warning(
                "EMOTIONAL LOCKOUT: %d consecutive violations. Mandatory break!",
                self._consecutive_violations,
            )

        result: dict[str, Any] = {
            "violation_id": violation.violation_id,
            "trade_id": violation.trade_id,
            "rule_broken": violation.rule_broken,
            "severity": violation.severity.value,
            "consecutive_violations": self._consecutive_violations,
            "lockout_active": self._lockout_active,
            "lockout_triggered": lockout_triggered,
        }

        # Send to API backend if client is configured
        if self.client is not None:
            try:
                api_result = self.client.log_violation(
                    trade_id=violation.trade_id,
                    rule=violation.rule_broken,
                    justification=violation.justification,
                )
                result["api_status"] = api_result
            except Exception as exc:
                logger.warning("Failed to log violation via API: %s", exc)
                result["api_status"] = f"failed: {exc}"

        return result

    def is_lockout_active(self) -> bool:
        """Check if emotional lockout is currently active."""
        return self._lockout_active

    def reset_lockout(self) -> dict[str, Any]:
        """
        Reset the emotional lockout (after reflection period).

        Returns:
            Dict with reset confirmation.
        """
        was_active = self._lockout_active
        self._lockout_active = False
        self._lockout_triggered_at = None
        self._consecutive_violations = 0

        return {
            "reset": True,
            "was_active": was_active,
            "message": "Lockout reset. Reflect on your process before resuming.",
        }

    # ------------------------------------------------------------------
    # Trade Validation
    # ------------------------------------------------------------------

    def validate_trade(
        self,
        entry: float,
        sl: float,
        tp: float,
        direction: TradeDirection,
        account_balance: float = 10000.0,
    ) -> dict[str, Any]:
        """
        Validate a trade setup against risk rules.

        Checks:
        - Risk-reward ratio >= min_rrr
        - Risk per trade <= max_risk_pct of account
        - SL and TP are on correct sides relative to entry

        Args:
            entry: Entry price.
            sl: Stop loss price.
            tp: Take profit price.
            direction: Trade direction (Buy/Sell).
            account_balance: Current account balance.

        Returns:
            Dict with validation verdict and details.
        """
        checkpoints: dict[str, dict[str, Any]] = {}

        # Calculate risk and reward
        if direction == TradeDirection.BUY:
            risk = entry - sl
            reward = tp - entry
        else:
            risk = sl - entry
            reward = entry - tp

        rrr = reward / risk if risk > 0 else 0.0

        # Check RRR
        rrr_passed = rrr >= self.min_rrr
        checkpoints["rrr_check"] = {
            "value": f"{rrr:.2f}",
            "limit": f">= {self.min_rrr:.1f}",
            "passed": rrr_passed,
        }

        # Check risk percentage
        risk_amount = abs(risk) * (1.0)  # Assuming 1 lot for simplicity
        risk_pct = (risk_amount / account_balance) * 100
        risk_passed = risk_pct <= self.max_risk_pct
        checkpoints["risk_pct_check"] = {
            "value": f"{risk_pct:.2f}%",
            "limit": f"<= {self.max_risk_pct:.1f}%",
            "passed": risk_passed,
        }

        # Check SL/TP placement
        if direction == TradeDirection.BUY:
            sl_ok = sl < entry
            tp_ok = tp > entry
        else:
            sl_ok = sl > entry
            tp_ok = tp < entry

        checkpoints["sl_placement"] = {
            "value": "correct" if sl_ok else "incorrect",
            "limit": f"SL {'below' if direction == TradeDirection.BUY else 'above'} entry",
            "passed": sl_ok,
        }
        checkpoints["tp_placement"] = {
            "value": "correct" if tp_ok else "incorrect",
            "limit": f"TP {'above' if direction == TradeDirection.BUY else 'below'} entry",
            "passed": tp_ok,
        }

        all_passed = all(cp["passed"] for cp in checkpoints.values())
        veto_count = sum(1 for cp in checkpoints.values() if not cp["passed"])

        return {
            "verdict": "APPROVED" if all_passed else "VETOED",
            "rrr": round(rrr, 2),
            "risk_pct": round(risk_pct, 2),
            "checkpoints": checkpoints,
            "veto_count": veto_count,
            "lockout": self._lockout_active,
        }

    # ------------------------------------------------------------------
    # AI Analysis (via client or local logic)
    # ------------------------------------------------------------------

    def get_ai_summary(self, symbol: str = "EURUSD") -> dict[str, Any]:
        """
        Get AI master summary for a symbol.

        Uses the GAS backend if a client is configured, otherwise
        returns a placeholder.

        Args:
            symbol: Trading pair symbol.

        Returns:
            AI summary dict with bias, confidence, theses, signal.
        """
        if self.client is not None:
            return self.client.get_ai_summary(symbol)

        logger.warning("No API client configured; returning placeholder summary")
        return {
            "symbol": symbol,
            "final_bias": Bias.NEUTRAL.value,
            "confidence_score": 0,
            "technical_thesis": "No API client configured. Connect TradingPlanClient for live data.",
            "signal": {"active": False, "entry": None, "stop_loss": None, "take_profit": None},
        }

    def get_forecast(
        self,
        symbol: str = "EURUSD",
        timeframe: str = "H4",
        days: int = 7,
    ) -> dict[str, Any]:
        """
        Get multi-day forecast for a symbol.

        Args:
            symbol: Trading pair symbol.
            timeframe: Chart timeframe.
            days: Forecast horizon in days.

        Returns:
            Forecast dict with bias, zones, probability.
        """
        if self.client is not None:
            return self.client.get_forecast(symbol, timeframe, days)

        logger.warning("No API client configured; returning placeholder forecast")
        return {
            "pair": symbol,
            "bias": Bias.NEUTRAL.value,
            "entry_zone": "N/A",
            "stop_loss": None,
            "take_profit": None,
            "probability": 0.0,
            "is_tradeable": False,
        }

    # ------------------------------------------------------------------
    # Weekly Analysis
    # ------------------------------------------------------------------

    def analyze_weekly_performance(self) -> WeeklySummary:
        """
        Generate a weekly performance summary from in-memory trades.

        Returns:
            WeeklySummary with key metrics.
        """
        now = datetime.now()
        week_start = now - timedelta(days=now.weekday())
        week_end = week_start + timedelta(days=6)

        week_trades = [
            t for t in self._trades
            if week_start <= t.timestamp <= week_end
        ]

        wins = [t for t in week_trades if t.result == TradeResult.WIN]
        total_pnl = sum(t.pnl for t in week_trades)
        win_rate = (len(wins) / len(week_trades) * 100) if week_trades else 0.0

        # Mood analysis
        mood_counts: dict[str, int] = {}
        for t in week_trades:
            mood_counts[t.mood.value] = mood_counts.get(t.mood.value, 0) + 1
        dominant_emotion = max(mood_counts, key=mood_counts.get) if mood_counts else "N/A"

        week_violations = [
            v for v in self._violations
            if week_start <= v.timestamp <= week_end
        ]

        # Setup analysis
        setup_pnl: dict[str, list[float]] = {}
        for t in week_trades:
            setup_pnl.setdefault(t.setup, []).append(t.pnl)

        best_setup = ""
        worst_setup = ""
        if setup_pnl:
            best_setup = max(setup_pnl, key=lambda s: sum(setup_pnl[s]))
            worst_setup = min(setup_pnl, key=lambda s: sum(setup_pnl[s]))

        summary = WeeklySummary(
            total_trades=len(week_trades),
            win_rate=round(win_rate, 1),
            total_pnl=round(total_pnl, 2),
            dominant_emotion=dominant_emotion,
            violation_count=len(week_violations),
            best_setup=best_setup,
            worst_setup=worst_setup,
            week_start=week_start,
            week_end=week_end,
        )

        self._weekly_summaries.append(summary)
        return summary

    # ------------------------------------------------------------------
    # COT Data (from GAS api_integrations.gs logic)
    # ------------------------------------------------------------------

    def get_cot_analysis(self, symbol: str) -> COTData:
        """
        Get COT analysis for a symbol using the CFTC mapping.

        Note: Actual CFTC data fetching requires the GAS backend
        or a direct HTTP client. This returns the mapping and
        computed bias based on provided data.

        Args:
            symbol: Trading pair (e.g. ``EURUSD``, ``GOLD``).

        Returns:
            COTData with symbol mapping and bias logic.
        """
        normalized = normalize_symbol(symbol)
        cftc_name = CFTC_SYMBOL_MAP.get(normalized, "")

        return COTData(
            symbol=normalized,
            source=cftc_name or "Unknown",
            bias=Bias.NEUTRAL,
        )

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> dict[str, Any]:
        """Get aggregate trading statistics."""
        total = len(self._trades)
        wins = sum(1 for t in self._trades if t.result == TradeResult.WIN)
        losses = sum(1 for t in self._trades if t.result == TradeResult.LOSS)

        return {
            "total_trades": total,
            "wins": wins,
            "losses": losses,
            "win_rate": round(wins / total * 100, 1) if total > 0 else 0.0,
            "total_pnl": round(sum(t.pnl for t in self._trades), 2),
            "total_violations": len(self._violations),
            "consecutive_violations": self._consecutive_violations,
            "lockout_active": self._lockout_active,
            "forecasts_generated": len(self._forecasts),
            "weekly_summaries": len(self._weekly_summaries),
        }


# ══════════════════════════════════════════════════════════════════════
# Module-level convenience
# ══════════════════════════════════════════════════════════════════════

_default_tool: TradingPlanTool | None = None


def get_trading_plan_tool() -> TradingPlanTool:
    """Get or create the default TradingPlanTool singleton."""
    global _default_tool
    if _default_tool is None:
        _default_tool = TradingPlanTool()
    return _default_tool
