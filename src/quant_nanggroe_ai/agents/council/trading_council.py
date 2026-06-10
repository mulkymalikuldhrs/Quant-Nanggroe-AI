"""
Trading Council — 9-Agent CrewAI Trading Council
==================================================
Orchestrates 9 specialized trading agents via CrewAI when available,
falling back to a deterministic internal implementation otherwise.

The 9 agents are organized into three tiers that run sequentially,
with parallel execution within each tier:

    Tier 1 — RESEARCH (parallel):
        ResearcherAgent, MacroAgent, CryptoAgent, ForexAgent

    Tier 2 — ANALYSIS (parallel):
        StrategistAgent, RiskAgent, PortfolioAgent

    Tier 3 — EXECUTION (sequential):
        TraderAgent, ExecutionAgent

Council Process:
    1. All Tier 1 agents gather data and context in parallel
    2. Tier 2 agents analyze the consolidated Tier 1 output in parallel
    3. A debate/voting round determines the council's direction
    4. RiskAgent can VETO any trade regardless of consensus
    5. Tier 3 agents handle final execution decisions
    6. CouncilResult is produced with full reasoning trace

Graceful Degradation:
    If ``crewai`` is not installed, the council falls back to a
    fully deterministic internal implementation that uses the same
    agent interfaces and produces identical output shapes.

Example:
    council = TradingCouncil()
    result = await council.run(symbol="BTCUSDT", timeframe="1h", data={...})
    print(result.action, result.confidence, result.risk_score)
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# CREWAI LAZY IMPORT
# ══════════════════════════════════════════════════════════════════════

_CREWAI_AVAILABLE: bool | None = None


def _is_crewai_available() -> bool:
    """Check if the ``crewai`` package is importable (cached)."""
    global _CREWAI_AVAILABLE
    if _CREWAI_AVAILABLE is None:
        try:
            import crewai  # noqa: F401
            _CREWAI_AVAILABLE = True
            logger.info("CrewAI detected — using CrewAI-backed trading council")
        except ImportError:
            _CREWAI_AVAILABLE = False
            logger.info("CrewAI not installed — using internal trading council implementation")
    return _CREWAI_AVAILABLE


# ══════════════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════════════


class CouncilAction(str, Enum):
    """Possible council actions."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class AgentVote(str, Enum):
    """Individual agent vote."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class AssetClass(str, Enum):
    """Asset class for agent routing."""

    CRYPTO = "CRYPTO"
    FOREX = "FOREX"
    EQUITY = "EQUITY"
    COMMODITY = "COMMODITY"
    UNKNOWN = "UNKNOWN"


# ══════════════════════════════════════════════════════════════════════
# DATACLASSES
# ══════════════════════════════════════════════════════════════════════


@dataclass
class CouncilConfig:
    """Configuration for the TradingCouncil.

    Attributes:
        max_debate_rounds: Maximum number of debate rounds before forcing
            a decision.  Each round allows agents to revise their votes
            after seeing other agents' arguments.
        consensus_threshold: Fraction of agents (weighted) that must agree
            on a direction for it to be considered a consensus.  Range [0, 1].
        risk_veto_enabled: When True, the RiskAgent can unilaterally VETO
            any BUY/SELL action, forcing a HOLD regardless of consensus.
    """

    max_debate_rounds: int = 3
    consensus_threshold: float = 0.7
    risk_veto_enabled: bool = True


@dataclass
class CouncilResult:
    """Final result from the trading council.

    Attributes:
        action: The council's final decision (BUY/SELL/HOLD).
        confidence: Confidence in the decision, range [0, 1].
        reasoning: Human-readable explanation of how the council arrived
            at this decision.
        risk_score: Overall risk assessment, range [0, 1] where 1 = highest.
        position_size_pct: Recommended position size as a fraction of
            portfolio equity, range [0, 1].
        agent_votes: Mapping of agent name to their individual vote.
    """

    action: str  # BUY / SELL / HOLD
    confidence: float
    reasoning: str
    risk_score: float
    position_size_pct: float
    agent_votes: dict[str, str] = field(default_factory=dict)


# ══════════════════════════════════════════════════════════════════════
# AGENT PROTOCOL
# ══════════════════════════════════════════════════════════════════════


@runtime_checkable
class CouncilAgent(Protocol):
    """Protocol that all 9 council agents must satisfy."""

    name: str

    async def analyze(
        self,
        symbol: str,
        timeframe: str,
        data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> AgentOpinion:
        """Produce an opinion for the council."""
        ...


@dataclass
class AgentOpinion:
    """Opinion produced by a single council agent.

    Attributes:
        agent_name: Name of the agent that produced this opinion.
        vote: The agent's directional vote.
        confidence: The agent's confidence in its vote, range [0, 1].
        reasoning: The agent's argument for its vote.
        risk_contribution: How much risk this agent perceives, range [0, 1].
        position_size_recommendation: Agent's recommended position size
            as fraction of equity, range [0, 1].  0 means no position.
        metadata: Additional structured data from the agent.
    """

    agent_name: str
    vote: str  # BUY / SELL / HOLD
    confidence: float
    reasoning: str
    risk_contribution: float = 0.5
    position_size_recommendation: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


# ══════════════════════════════════════════════════════════════════════
# HELPER UTILITIES
# ══════════════════════════════════════════════════════════════════════


def _classify_symbol(symbol: str) -> AssetClass:
    """Return a coarse asset-class label for routing decisions."""
    upper = symbol.upper()
    crypto_bases = {"BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE", "AVAX", "DOT", "MATIC", "LINK"}
    if any(upper.startswith(c) for c in crypto_bases) or "USDT" in upper or "USDC" in upper:
        return AssetClass.CRYPTO
    forex_currencies = {"USD", "EUR", "GBP", "JPY", "CHF", "AUD", "NZD", "CAD"}
    if len(upper) >= 6:
        base, quote = upper[:3], upper[3:6]
        if base in forex_currencies and quote in forex_currencies:
            return AssetClass.FOREX
    if upper in {"XAUUSD", "XAGUSD"} or upper.startswith("XAU") or upper.startswith("XAG"):
        return AssetClass.COMMODITY
    return AssetClass.EQUITY


def _safe_get(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    """Safely navigate nested dicts."""
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
        if current is None:
            return default
    return current


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp a value to [lo, hi]."""
    return max(lo, min(hi, value))


# ══════════════════════════════════════════════════════════════════════
# 9 SPECIALIZED AGENTS
# ══════════════════════════════════════════════════════════════════════


class ResearcherAgent:
    """
    Market Research Agent — Data gathering, news analysis, and context building.

    Scours available market data, news feeds, and sentiment sources to build
    a comprehensive research context for downstream agents.  This agent does
    not produce a directional vote on its own; instead it votes based on
    aggregated sentiment and data quality signals.
    """

    name: str = "ResearcherAgent"

    async def analyze(
        self,
        symbol: str,
        timeframe: str,
        data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> AgentOpinion:
        sentiment = _safe_get(data, "sentiment", "overall_score", default=0.0)
        news_count = len(_safe_get(data, "sentiment", "news_items", default=[]))
        data_quality = _safe_get(data, "data_quality", default=0.5)

        # Sentiment-driven vote with quality gating
        if data_quality < 0.2:
            vote = AgentVote.HOLD.value
            confidence = 0.2
            reasoning = "Insufficient data quality for directional bet — HOLD"
        elif sentiment > 0.3:
            vote = AgentVote.BUY.value
            confidence = _clamp(abs(sentiment) * data_quality)
            reasoning = (
                f"Positive sentiment ({sentiment:.2f}) from {news_count} sources "
                f"with data quality {data_quality:.2f} supports bullish bias"
            )
        elif sentiment < -0.3:
            vote = AgentVote.SELL.value
            confidence = _clamp(abs(sentiment) * data_quality)
            reasoning = (
                f"Negative sentiment ({sentiment:.2f}) from {news_count} sources "
                f"with data quality {data_quality:.2f} supports bearish bias"
            )
        else:
            vote = AgentVote.HOLD.value
            confidence = 0.4
            reasoning = (
                f"Neutral sentiment ({sentiment:.2f}) — no strong directional "
                f"signal from research data"
            )

        return AgentOpinion(
            agent_name=self.name,
            vote=vote,
            confidence=confidence,
            reasoning=reasoning,
            risk_contribution=0.3,
            position_size_recommendation=0.0,
            metadata={
                "sentiment": sentiment,
                "news_count": news_count,
                "data_quality": data_quality,
            },
        )


class TraderAgent:
    """
    Trade Execution Agent — Timing and execution decisions.

    Evaluates the optimal timing for trade entry/exit based on
    momentum signals, volume profile, and intraday patterns.
    """

    name: str = "TraderAgent"

    async def analyze(
        self,
        symbol: str,
        timeframe: str,
        data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> AgentOpinion:
        indicators = _safe_get(data, "indicators", default={})
        price_data = _safe_get(data, "price", default={})

        rsi = indicators.get("rsi_14", 50.0)
        macd_hist = _safe_get(indicators, "macd", "histogram", default=0.0)
        volume_ratio = data.get("volume_ratio", 1.0)
        current_price = price_data.get("current", 0.0)

        # Momentum-based vote
        buy_signals = 0
        sell_signals = 0

        if rsi < 35:
            buy_signals += 2
        elif rsi < 45:
            buy_signals += 1
        elif rsi > 65:
            sell_signals += 2
        elif rsi > 55:
            sell_signals += 1

        if macd_hist > 0:
            buy_signals += 1
        elif macd_hist < 0:
            sell_signals += 1

        if volume_ratio > 1.3:
            # High volume confirms direction
            if buy_signals > sell_signals:
                buy_signals += 1
            else:
                sell_signals += 1

        if buy_signals > sell_signals + 1:
            vote = AgentVote.BUY.value
            confidence = _clamp(buy_signals / 5.0)
            reasoning = (
                f"Momentum favors long entry: RSI={rsi:.1f}, MACD_hist={macd_hist:.4f}, "
                f"volume_ratio={volume_ratio:.2f}, buy_signals={buy_signals}"
            )
        elif sell_signals > buy_signals + 1:
            vote = AgentVote.SELL.value
            confidence = _clamp(sell_signals / 5.0)
            reasoning = (
                f"Momentum favors short entry: RSI={rsi:.1f}, MACD_hist={macd_hist:.4f}, "
                f"volume_ratio={volume_ratio:.2f}, sell_signals={sell_signals}"
            )
        else:
            vote = AgentVote.HOLD.value
            confidence = 0.4
            reasoning = (
                f"Conflicting momentum signals: RSI={rsi:.1f}, MACD_hist={macd_hist:.4f} "
                f"— wait for confirmation"
            )

        position_rec = 0.005 if vote != AgentVote.HOLD.value else 0.0

        return AgentOpinion(
            agent_name=self.name,
            vote=vote,
            confidence=confidence,
            reasoning=reasoning,
            risk_contribution=0.4,
            position_size_recommendation=position_rec,
            metadata={
                "rsi": rsi,
                "macd_histogram": macd_hist,
                "volume_ratio": volume_ratio,
            },
        )


class StrategistAgent:
    """
    Strategy Agent — Strategy selection and parameter optimization.

    Selects the most appropriate strategy for the current market regime
    and optimizes its parameters.  Integrates with PressureNormalization
    and DecisionSynthesis engines when available.
    """

    name: str = "StrategistAgent"

    async def analyze(
        self,
        symbol: str,
        timeframe: str,
        data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> AgentOpinion:
        indicators = _safe_get(data, "indicators", default={})
        regime = data.get("regime", "UNKNOWN")
        ema_trend = data.get("ema_trend", "neutral")

        adx_val = _safe_get(indicators, "adx", "adx", default=20.0)
        atr_pct = indicators.get("atr_pct", 1.0)
        rsi = indicators.get("rsi_14", 50.0)

        # Strategy selection based on regime and indicators
        if regime in ("TRENDING_UP", "TRENDING_DOWN", "TRENDING"):
            strategy_type = "trend_following"
            if ema_trend == "bullish" and adx_val > 25:
                vote = AgentVote.BUY.value
                confidence = _clamp(adx_val / 60.0)
                reasoning = (
                    f"Trending regime ({regime}) with bullish EMA alignment and "
                    f"ADX={adx_val:.1f} — trend following strategy recommends BUY"
                )
            elif ema_trend == "bearish" and adx_val > 25:
                vote = AgentVote.SELL.value
                confidence = _clamp(adx_val / 60.0)
                reasoning = (
                    f"Trending regime ({regime}) with bearish EMA alignment and "
                    f"ADX={adx_val:.1f} — trend following strategy recommends SELL"
                )
            else:
                vote = AgentVote.HOLD.value
                confidence = 0.3
                reasoning = (
                    f"Trending regime but weak trend (ADX={adx_val:.1f}) — "
                    f"wait for trend confirmation"
                )
        elif regime in ("RANGE", "MEAN_REVERT", "CALM"):
            strategy_type = "mean_reversion"
            if rsi < 30:
                vote = AgentVote.BUY.value
                confidence = _clamp((30 - rsi) / 30.0)
                reasoning = (
                    f"Range/mean-revert regime with oversold RSI ({rsi:.1f}) — "
                    f"mean reversion strategy recommends BUY at support"
                )
            elif rsi > 70:
                vote = AgentVote.SELL.value
                confidence = _clamp((rsi - 70) / 30.0)
                reasoning = (
                    f"Range/mean-revert regime with overbought RSI ({rsi:.1f}) — "
                    f"mean reversion strategy recommends SELL at resistance"
                )
            else:
                vote = AgentVote.HOLD.value
                confidence = 0.4
                reasoning = (
                    f"Range regime with neutral RSI ({rsi:.1f}) — "
                    f"no clear mean reversion signal"
                )
        elif regime in ("VOLATILE", "RISK_OFF", "PANIC"):
            strategy_type = "defensive"
            vote = AgentVote.HOLD.value
            confidence = 0.7
            reasoning = (
                f"Defensive regime ({regime}) — strategy set to HOLD. "
                f"Capital preservation is the priority."
            )
        else:
            strategy_type = "unknown"
            vote = AgentVote.HOLD.value
            confidence = 0.3
            reasoning = f"Unknown regime ({regime}) — defaulting to HOLD"

        position_rec = 0.005 * (1.0 if vote != AgentVote.HOLD.value else 0.0)
        if atr_pct > 2.0 and vote != AgentVote.HOLD.value:
            position_rec *= 0.5  # Reduce size in high volatility

        return AgentOpinion(
            agent_name=self.name,
            vote=vote,
            confidence=confidence,
            reasoning=reasoning,
            risk_contribution=0.5,
            position_size_recommendation=position_rec,
            metadata={
                "strategy_type": strategy_type,
                "regime": regime,
                "adx": adx_val,
                "atr_pct": atr_pct,
            },
        )


class RiskAgent:
    """
    Risk Assessment Agent — Risk assessment and position sizing.

    Performs comprehensive risk evaluation across volatility, portfolio
    heat, stop loss placement, and regime risk.  Has VETO authority
    over any trade when risk_veto_enabled is True.
    """

    name: str = "RiskAgent"

    async def analyze(
        self,
        symbol: str,
        timeframe: str,
        data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> AgentOpinion:
        indicators = _safe_get(data, "indicators", default={})
        portfolio = data.get("portfolio", {})
        regime = data.get("regime", "UNKNOWN")
        trade_data = data.get("trade", {})

        atr_pct = indicators.get("atr_pct", 1.0)
        adx_val = _safe_get(indicators, "adx", "adx", default=20.0)
        rsi = indicators.get("rsi_14", 50.0)

        open_positions = portfolio.get("open_positions", 0)
        max_positions = portfolio.get("max_positions", 10)
        total_exposure_pct = portfolio.get("total_exposure_pct", 0.0)
        daily_pnl_pct = portfolio.get("daily_pnl_pct", 0.0)
        weekly_pnl_pct = portfolio.get("weekly_pnl_pct", 0.0)

        risk_factors: list[str] = []
        risk_score = 0.0
        veto_triggered = False

        # ── Volatility risk ───────────────────────────────────────────
        if atr_pct > 3.0:
            risk_score += 0.35
            risk_factors.append(f"Extreme volatility (ATR%={atr_pct:.1f}%)")
        elif atr_pct > 2.0:
            risk_score += 0.2
            risk_factors.append(f"Elevated volatility (ATR%={atr_pct:.1f}%)")
        elif atr_pct < 0.5:
            risk_score -= 0.1
            risk_factors.append(f"Low volatility (ATR%={atr_pct:.1f}%) — favorable")

        # ── Portfolio heat ────────────────────────────────────────────
        if open_positions >= max_positions:
            risk_score += 0.3
            risk_factors.append(f"Max positions reached ({open_positions}/{max_positions})")
            veto_triggered = True
        elif total_exposure_pct > 0.8:
            risk_score += 0.25
            risk_factors.append(f"High exposure ({total_exposure_pct:.0%})")
        elif total_exposure_pct < 0.3:
            risk_score -= 0.05
            risk_factors.append(f"Low exposure ({total_exposure_pct:.0%}) — room available")

        # ── Drawdown risk ────────────────────────────────────────────
        if daily_pnl_pct < -0.01:
            risk_score += 0.4
            risk_factors.append(f"Daily loss limit hit ({daily_pnl_pct:.2%})")
            veto_triggered = True
        elif daily_pnl_pct < -0.005:
            risk_score += 0.15
            risk_factors.append(f"Approaching daily loss limit ({daily_pnl_pct:.2%})")

        if weekly_pnl_pct < -0.03:
            risk_score += 0.4
            risk_factors.append(f"Weekly loss limit hit ({weekly_pnl_pct:.2%})")
            veto_triggered = True

        # ── Regime risk ──────────────────────────────────────────────
        if regime in ("PANIC", "RISK_OFF", "NO_TRADE"):
            risk_score += 0.5
            risk_factors.append(f"Hostile regime ({regime})")
            veto_triggered = True
        elif regime == "VOLATILE":
            risk_score += 0.15
            risk_factors.append("Volatile regime — increased caution")

        # ── Stop loss check ──────────────────────────────────────────
        entry_price = trade_data.get("entry_price", 0)
        stop_loss = trade_data.get("stop_loss")
        if entry_price > 0 and stop_loss and stop_loss > 0:
            stop_distance_pct = abs(entry_price - stop_loss) / entry_price
            if stop_distance_pct > 0.02:
                risk_score += 0.2
                risk_factors.append(f"Stop too wide ({stop_distance_pct:.2%})")
            elif stop_distance_pct < 0.003:
                risk_score += 0.15
                risk_factors.append(f"Stop too tight ({stop_distance_pct:.2%}) — likely whipsaw")

        risk_score = _clamp(risk_score)

        # ── Vote ─────────────────────────────────────────────────────
        if veto_triggered:
            vote = AgentVote.HOLD.value
            confidence = 0.95
            reasoning = (
                f"RISK VETO — Trade blocked due to: {'; '.join(risk_factors[:3])}. "
                f"Risk score: {risk_score:.2f}"
            )
        elif risk_score > 0.6:
            vote = AgentVote.HOLD.value
            confidence = _clamp(risk_score)
            reasoning = (
                f"Elevated risk ({risk_score:.2f}) — recommending HOLD. "
                f"Factors: {'; '.join(risk_factors[:3])}"
            )
        elif risk_score > 0.4:
            # Moderate risk: allow trade but with reduced size
            # Let other agents decide direction
            vote = AgentVote.HOLD.value
            confidence = 0.5
            reasoning = (
                f"Moderate risk ({risk_score:.2f}) — conditionally allowing trade "
                f"with reduced position size. Factors: {'; '.join(risk_factors[:3])}"
            )
        else:
            # Low risk: defer to other agents for direction
            # Risk agent votes HOLD in low risk because it doesn't have a directional view;
            # it just approves or blocks the risk dimension.
            vote = AgentVote.HOLD.value
            confidence = _clamp(1.0 - risk_score)
            reasoning = (
                f"Acceptable risk ({risk_score:.2f}) — no veto. "
                f"Deferring to directional agents for vote."
            )

        # Position sizing based on risk
        if risk_score < 0.3:
            position_rec = 0.01
        elif risk_score < 0.5:
            position_rec = 0.005
        elif risk_score < 0.7:
            position_rec = 0.002
        else:
            position_rec = 0.0

        return AgentOpinion(
            agent_name=self.name,
            vote=vote,
            confidence=confidence,
            reasoning=reasoning,
            risk_contribution=risk_score,
            position_size_recommendation=position_rec,
            metadata={
                "risk_score": risk_score,
                "veto_triggered": veto_triggered,
                "risk_factors": risk_factors,
            },
        )


class PortfolioAgent:
    """
    Portfolio Optimization Agent — Asset allocation and portfolio constraints.

    Evaluates portfolio-level constraints including concentration, correlation,
    total exposure, and Kelly Criterion position sizing.
    """

    name: str = "PortfolioAgent"

    async def analyze(
        self,
        symbol: str,
        timeframe: str,
        data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> AgentOpinion:
        portfolio = data.get("portfolio", {})
        positions = portfolio.get("positions", [])

        open_positions = len(positions)
        max_positions = portfolio.get("max_positions", 10)
        total_exposure_pct = portfolio.get("total_exposure_pct", 0.0)
        correlation_score = portfolio.get("avg_correlation", 0.0)
        win_rate = portfolio.get("win_rate", 0.5)
        sharpe = portfolio.get("sharpe_ratio", 0.0)

        # Concentration check for the proposed symbol
        symbol_concentration = 0.0
        for pos in positions:
            if isinstance(pos, dict) and pos.get("ticker", "").upper() == symbol.upper():
                symbol_concentration += pos.get("weight", 0.0)

        rejection_reasons: list[str] = []
        allows_trade = True

        if open_positions >= max_positions:
            rejection_reasons.append(
                f"Max positions reached ({open_positions}/{max_positions})"
            )
            allows_trade = False

        if symbol_concentration > 0.10:
            rejection_reasons.append(
                f"Concentration limit exceeded for {symbol} ({symbol_concentration:.0%})"
            )
            allows_trade = False

        if total_exposure_pct > 0.80:
            rejection_reasons.append(
                f"Total exposure too high ({total_exposure_pct:.0%})"
            )
            allows_trade = False

        if correlation_score > 0.7:
            rejection_reasons.append(
                f"High portfolio correlation ({correlation_score:.2f})"
            )
            allows_trade = False

        # Kelly criterion position sizing
        if win_rate > 0 and sharpe > 0:
            kelly_pct = min(0.02, (win_rate * 2 - 1) * 0.25)  # Quarter-Kelly
        else:
            kelly_pct = 0.005  # Conservative default

        if not allows_trade:
            vote = AgentVote.HOLD.value
            confidence = 0.85
            reasoning = (
                f"Portfolio constraints block trade: {'; '.join(rejection_reasons)}"
            )
        else:
            # Portfolio allows it — defer direction to other agents
            vote = AgentVote.HOLD.value
            confidence = _clamp(0.5 + sharpe * 0.1) if sharpe > 0 else 0.5
            reasoning = (
                f"Portfolio allows trade. Positions: {open_positions}/{max_positions}, "
                f"Exposure: {total_exposure_pct:.0%}, Kelly size: {kelly_pct:.3f}"
            )

        return AgentOpinion(
            agent_name=self.name,
            vote=vote,
            confidence=confidence,
            reasoning=reasoning,
            risk_contribution=0.4 if not allows_trade else 0.2,
            position_size_recommendation=kelly_pct if allows_trade else 0.0,
            metadata={
                "open_positions": open_positions,
                "total_exposure_pct": total_exposure_pct,
                "correlation_score": correlation_score,
                "kelly_pct": kelly_pct,
                "allows_trade": allows_trade,
                "rejection_reasons": rejection_reasons,
            },
        )


class ExecutionAgent:
    """
    Execution Agent — Order execution and slippage management.

    Evaluates execution feasibility, expected slippage, and optimal
    order type for the proposed trade.
    """

    name: str = "ExecutionAgent"

    async def analyze(
        self,
        symbol: str,
        timeframe: str,
        data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> AgentOpinion:
        liquidity = data.get("liquidity", "NORMAL")
        spread = data.get("spread", 0.0001)
        volume = data.get("volume", 0)
        avg_volume = data.get("avg_volume", 1)

        # Execution quality assessment
        volume_ratio = volume / avg_volume if avg_volume > 0 else 1.0
        slippage_estimate = spread * 2  # Conservative slippage estimate

        if liquidity in ("THIN",) or volume_ratio < 0.5:
            vote = AgentVote.HOLD.value
            confidence = 0.7
            reasoning = (
                f"Poor execution conditions — liquidity={liquidity}, "
                f"volume_ratio={volume_ratio:.2f}. Slippage risk too high."
            )
            position_rec = 0.0
        elif liquidity == "DEEP" and volume_ratio > 1.5:
            # Good execution conditions — defer direction to others
            vote = AgentVote.HOLD.value
            confidence = 0.8
            reasoning = (
                f"Excellent execution conditions — liquidity={liquidity}, "
                f"volume_ratio={volume_ratio:.2f}, est. slippage={slippage_estimate:.4f}"
            )
            position_rec = 0.01
        else:
            vote = AgentVote.HOLD.value
            confidence = 0.6
            reasoning = (
                f"Normal execution conditions — liquidity={liquidity}, "
                f"spread={spread:.4f}, slippage_est={slippage_estimate:.4f}"
            )
            position_rec = 0.005

        return AgentOpinion(
            agent_name=self.name,
            vote=vote,
            confidence=confidence,
            reasoning=reasoning,
            risk_contribution=0.3,
            position_size_recommendation=position_rec,
            metadata={
                "liquidity": liquidity,
                "spread": spread,
                "volume_ratio": volume_ratio,
                "slippage_estimate": slippage_estimate,
            },
        )


class MacroAgent:
    """
    Macroeconomic Agent — Macroeconomic analysis and regime detection.

    Analyzes FRED economic indicators, monetary policy stance,
    economic calendar events, and macro regime shifts.
    """

    name: str = "MacroAgent"

    async def analyze(
        self,
        symbol: str,
        timeframe: str,
        data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> AgentOpinion:
        macro = data.get("macro", {})
        policy_stance = macro.get("policy_stance", "neutral")
        macro_risk = macro.get("risk_level", "MEDIUM")
        upcoming_events = macro.get("upcoming_events", [])
        yield_curve = macro.get("yield_curve_spread", None)

        # High-impact event within 24h
        imminent_event = any(
            e.get("days_until", 99) <= 1 and e.get("impact") == "HIGH"
            for e in upcoming_events
        )

        risk_contribution = 0.3
        if macro_risk == "EXTREME":
            vote = AgentVote.HOLD.value
            confidence = 0.9
            risk_contribution = 0.9
            reasoning = (
                f"EXTREME macro risk — policy={policy_stance}, "
                f"events_imminent={imminent_event}. Holding all positions."
            )
        elif macro_risk == "HIGH":
            vote = AgentVote.HOLD.value
            confidence = 0.7
            risk_contribution = 0.7
            reasoning = (
                f"HIGH macro risk — policy={policy_stance}. "
                f"Reducing exposure recommended."
            )
        elif macro_risk == "MEDIUM" and imminent_event:
            vote = AgentVote.HOLD.value
            confidence = 0.6
            risk_contribution = 0.5
            reasoning = (
                f"MEDIUM macro risk but high-impact event within 24h — "
                f"cautious stance recommended."
            )
        elif policy_stance == "easing":
            vote = AgentVote.BUY.value
            confidence = 0.55
            risk_contribution = 0.2
            reasoning = (
                f"Accommodative monetary policy (easing) — favorable for "
                f"risk assets. Macro headwinds minimal."
            )
        elif policy_stance == "tightening":
            vote = AgentVote.SELL.value
            confidence = 0.5
            risk_contribution = 0.5
            reasoning = (
                f"Tightening monetary policy — headwinds for risk assets. "
                f"Consider defensive positioning."
            )
        else:
            vote = AgentVote.HOLD.value
            confidence = 0.4
            risk_contribution = 0.3
            reasoning = (
                f"Neutral macro environment — policy={policy_stance}, "
                f"risk={macro_risk}. No macro edge detected."
            )

        # Yield curve signal
        if yield_curve is not None and yield_curve < -0.5:
            risk_contribution = max(risk_contribution, 0.6)
            reasoning += " Inverted yield curve adds recession risk."

        return AgentOpinion(
            agent_name=self.name,
            vote=vote,
            confidence=confidence,
            reasoning=reasoning,
            risk_contribution=risk_contribution,
            position_size_recommendation=0.0,
            metadata={
                "policy_stance": policy_stance,
                "macro_risk": macro_risk,
                "imminent_event": imminent_event,
                "yield_curve": yield_curve,
            },
        )


class CryptoAgent:
    """
    Cryptocurrency Specialist Agent — Crypto-specific analysis.

    Provides crypto-specific signals including on-chain metrics,
    BTC dominance, funding rates, and DeFi TVL analysis.
    """

    name: str = "CryptoAgent"

    async def analyze(
        self,
        symbol: str,
        timeframe: str,
        data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> AgentOpinion:
        crypto_data = data.get("crypto", {})
        asset_class = _classify_symbol(symbol)

        # If not a crypto asset, this agent defers with low confidence
        if asset_class != AssetClass.CRYPTO:
            return AgentOpinion(
                agent_name=self.name,
                vote=AgentVote.HOLD.value,
                confidence=0.1,
                reasoning=f"{symbol} is not a crypto asset — deferring to other agents",
                risk_contribution=0.1,
                position_size_recommendation=0.0,
                metadata={"asset_class": asset_class.value, "active": False},
            )

        btc_dominance = crypto_data.get("btc_dominance", 50.0)
        funding_rate = crypto_data.get("funding_rate", 0.0)
        on_chain_bullish = crypto_data.get("on_chain_bullish_signals", 0)
        on_chain_bearish = crypto_data.get("on_chain_bearish_signals", 0)
        defi_tvl_change = crypto_data.get("defi_tvl_change_24h", 0.0)
        exchange_netflow = crypto_data.get("exchange_netflow", 0.0)

        buy_score = 0.0
        sell_score = 0.0

        # Funding rate signal (contrarian at extremes)
        if funding_rate > 0.05:
            sell_score += 0.3  # Overleveraged longs
        elif funding_rate < -0.05:
            buy_score += 0.3  # Overleveraged shorts
        elif funding_rate > 0.01:
            sell_score += 0.1
        elif funding_rate < -0.01:
            buy_score += 0.1

        # On-chain signals
        if on_chain_bullish > on_chain_bearish + 2:
            buy_score += 0.3
        elif on_chain_bearish > on_chain_bullish + 2:
            sell_score += 0.3

        # DeFi TVL growth
        if defi_tvl_change > 5.0:
            buy_score += 0.2
        elif defi_tvl_change < -5.0:
            sell_score += 0.2

        # Exchange netflow (negative = withdrawal = bullish)
        if exchange_netflow < -100:
            buy_score += 0.2
        elif exchange_netflow > 100:
            sell_score += 0.2

        # BTC dominance effect on alts
        symbol_upper = symbol.upper()
        if symbol_upper != "BTCUSDT" and "BTC" not in symbol_upper:
            if btc_dominance > 55:
                sell_score += 0.1  # BTC dominance rising = alts suffer
            elif btc_dominance < 40:
                buy_score += 0.1  # Alt season

        if buy_score > sell_score + 0.2:
            vote = AgentVote.BUY.value
            confidence = _clamp(buy_score)
            reasoning = (
                f"Crypto metrics bullish: funding={funding_rate:.4f}, "
                f"on_chain_buy={on_chain_bullish}, TVL_change={defi_tvl_change:.1f}%, "
               "netflow={exchange_netflow:.0f}"
            )
        elif sell_score > buy_score + 0.2:
            vote = AgentVote.SELL.value
            confidence = _clamp(sell_score)
            reasoning = (
                f"Crypto metrics bearish: funding={funding_rate:.4f}, "
                f"on_chain_sell={on_chain_bearish}, TVL_change={defi_tvl_change:.1f}%, "
               "netflow={exchange_netflow:.0f}"
            )
        else:
            vote = AgentVote.HOLD.value
            confidence = 0.3
            reasoning = (
                f"Crypto metrics neutral: buy_score={buy_score:.2f}, "
                f"sell_score={sell_score:.2f}. No clear crypto edge."
            )

        return AgentOpinion(
            agent_name=self.name,
            vote=vote,
            confidence=confidence,
            reasoning=reasoning,
            risk_contribution=0.5,
            position_size_recommendation=0.005 if vote != AgentVote.HOLD.value else 0.0,
            metadata={
                "asset_class": asset_class.value,
                "active": True,
                "btc_dominance": btc_dominance,
                "funding_rate": funding_rate,
                "buy_score": buy_score,
                "sell_score": sell_score,
            },
        )


class ForexAgent:
    """
    Forex Specialist Agent — Forex-specific analysis.

    Provides forex-specific signals including central bank divergence,
    carry trade conditions, and currency strength analysis.
    """

    name: str = "ForexAgent"

    async def analyze(
        self,
        symbol: str,
        timeframe: str,
        data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> AgentOpinion:
        forex_data = data.get("forex", {})
        asset_class = _classify_symbol(symbol)

        # If not a forex asset, this agent defers with low confidence
        if asset_class != AssetClass.FOREX:
            return AgentOpinion(
                agent_name=self.name,
                vote=AgentVote.HOLD.value,
                confidence=0.1,
                reasoning=f"{symbol} is not a forex pair — deferring to other agents",
                risk_contribution=0.1,
                position_size_recommendation=0.0,
                metadata={"asset_class": asset_class.value, "active": False},
            )

        # Extract base and quote currencies
        upper = symbol.upper()
        base = upper[:3]
        quote = upper[3:6] if len(upper) >= 6 else ""

        base_strength = forex_data.get(f"{base}_strength", 50.0)
        quote_strength = forex_data.get(f"{quote}_strength", 50.0)
        interest_diff = forex_data.get("interest_rate_differential", 0.0)
        carry_favorable = forex_data.get("carry_favorable", False)
        dxy_trend = forex_data.get("dxy_trend", "neutral")

        # Central bank divergence signal
        strength_diff = base_strength - quote_strength

        buy_score = 0.0
        sell_score = 0.0

        # Currency strength
        if strength_diff > 15:
            buy_score += 0.3
        elif strength_diff > 5:
            buy_score += 0.15
        elif strength_diff < -15:
            sell_score += 0.3
        elif strength_diff < -5:
            sell_score += 0.15

        # Interest rate differential
        if interest_diff > 1.0:
            buy_score += 0.2
        elif interest_diff < -1.0:
            sell_score += 0.2

        # Carry trade
        if carry_favorable:
            buy_score += 0.15
        else:
            sell_score += 0.1

        # DXY effect
        if base == "USD" and dxy_trend == "bullish":
            buy_score += 0.2
        elif quote == "USD" and dxy_trend == "bullish":
            sell_score += 0.2
        elif base == "USD" and dxy_trend == "bearish":
            sell_score += 0.2
        elif quote == "USD" and dxy_trend == "bearish":
            buy_score += 0.2

        if buy_score > sell_score + 0.2:
            vote = AgentVote.BUY.value
            confidence = _clamp(buy_score)
            reasoning = (
                f"Forex metrics favor {base} over {quote}: "
                f"strength_diff={strength_diff:.1f}, rate_diff={interest_diff:.2f}%, "
                f"carry={carry_favorable}, DXY={dxy_trend}"
            )
        elif sell_score > buy_score + 0.2:
            vote = AgentVote.SELL.value
            confidence = _clamp(sell_score)
            reasoning = (
                f"Forex metrics favor {quote} over {base}: "
                f"strength_diff={strength_diff:.1f}, rate_diff={interest_diff:.2f}%, "
                f"carry={carry_favorable}, DXY={dxy_trend}"
            )
        else:
            vote = AgentVote.HOLD.value
            confidence = 0.3
            reasoning = (
                f"Forex metrics neutral for {symbol}: "
                f"buy_score={buy_score:.2f}, sell_score={sell_score:.2f}"
            )

        return AgentOpinion(
            agent_name=self.name,
            vote=vote,
            confidence=confidence,
            reasoning=reasoning,
            risk_contribution=0.4,
            position_size_recommendation=0.005 if vote != AgentVote.HOLD.value else 0.0,
            metadata={
                "asset_class": asset_class.value,
                "active": True,
                "base": base,
                "quote": quote,
                "strength_diff": strength_diff,
                "interest_diff": interest_diff,
            },
        )


# ══════════════════════════════════════════════════════════════════════
# DEBATE / VOTING ENGINE
# ══════════════════════════════════════════════════════════════════════


class DebateEngine:
    """
    Multi-round debate and voting engine for the trading council.

    Runs debate rounds where agents can see each other's opinions and
    revise their votes.  Implements weighted voting, consensus detection,
    and RiskAgent VETO authority.

    Agent weights reflect their importance in the final decision:
        - RiskAgent: 2.0 (highest — safety first)
        - StrategistAgent: 1.5 (strategy expertise)
        - TraderAgent: 1.2 (execution timing)
        - PortfolioAgent: 1.2 (portfolio constraints)
        - MacroAgent: 1.0 (macro context)
        - ResearcherAgent: 0.8 (data quality varies)
        - CryptoAgent: 0.8 (niche expertise)
        - ForexAgent: 0.8 (niche expertise)
        - ExecutionAgent: 0.6 (execution quality)
    """

    AGENT_WEIGHTS: dict[str, float] = {
        "RiskAgent": 2.0,
        "StrategistAgent": 1.5,
        "TraderAgent": 1.2,
        "PortfolioAgent": 1.2,
        "MacroAgent": 1.0,
        "ResearcherAgent": 0.8,
        "CryptoAgent": 0.8,
        "ForexAgent": 0.8,
        "ExecutionAgent": 0.6,
    }

    def __init__(self, config: CouncilConfig) -> None:
        self._config = config

    def run_debate(
        self,
        opinions: list[AgentOpinion],
        risk_opinion: AgentOpinion | None = None,
    ) -> tuple[str, float, dict[str, str]]:
        """
        Run the debate and voting process.

        Args:
            opinions: All agent opinions from the current round.
            risk_opinion: The RiskAgent's opinion (extracted separately
                for VETO authority).

        Returns:
            Tuple of (action, confidence, agent_votes).
        """
        # ── Step 1: Check for RiskAgent VETO ─────────────────────────
        if (
            self._config.risk_veto_enabled
            and risk_opinion is not None
            and risk_opinion.metadata.get("veto_triggered", False)
        ):
            agent_votes = {op.agent_name: op.vote for op in opinions}
            agent_votes[risk_opinion.agent_name] = risk_opinion.vote
            logger.warning(
                "RISK VETO applied: %s", risk_opinion.reasoning,
            )
            return (
                CouncilAction.HOLD.value,
                0.95,
                agent_votes,
            )

        # ── Step 2: Weighted voting ──────────────────────────────────
        all_opinions = list(opinions)
        if risk_opinion is not None:
            all_opinions.append(risk_opinion)

        weighted_buy = 0.0
        weighted_sell = 0.0
        weighted_hold = 0.0
        total_weight = 0.0
        agent_votes: dict[str, str] = {}

        for opinion in all_opinions:
            weight = self.AGENT_WEIGHTS.get(opinion.agent_name, 1.0)
            adjusted_weight = weight * opinion.confidence
            agent_votes[opinion.agent_name] = opinion.vote

            if opinion.vote == AgentVote.BUY.value:
                weighted_buy += adjusted_weight
            elif opinion.vote == AgentVote.SELL.value:
                weighted_sell += adjusted_weight
            else:
                weighted_hold += adjusted_weight

            total_weight += adjusted_weight

        if total_weight == 0:
            return CouncilAction.HOLD.value, 0.3, agent_votes

        # ── Step 3: Determine winner ────────────────────────────────
        buy_pct = weighted_buy / total_weight
        sell_pct = weighted_sell / total_weight
        hold_pct = weighted_hold / total_weight

        # Check for consensus
        if buy_pct >= self._config.consensus_threshold:
            action = CouncilAction.BUY.value
            confidence = buy_pct
        elif sell_pct >= self._config.consensus_threshold:
            action = CouncilAction.SELL.value
            confidence = sell_pct
        elif hold_pct >= self._config.consensus_threshold:
            action = CouncilAction.HOLD.value
            confidence = hold_pct
        else:
            # No consensus — default to HOLD
            action = CouncilAction.HOLD.value
            confidence = max(buy_pct, sell_pct, hold_pct)

        # ── Step 4: RiskAgent soft veto ─────────────────────────────
        # Even without a hard veto, if RiskAgent is very concerned,
        # downgrade the confidence
        if (
            risk_opinion is not None
            and action != CouncilAction.HOLD.value
            and risk_opinion.risk_contribution > 0.6
        ):
            confidence *= 0.6
            logger.info(
                "RiskAgent high risk_contribution (%.2f) — confidence reduced to %.2f",
                risk_opinion.risk_contribution, confidence,
            )

        return action, _clamp(confidence), agent_votes

    def refine_opinions(
        self,
        opinions: list[AgentOpinion],
        round_number: int,
    ) -> list[AgentOpinion]:
        """
        Allow agents to revise their opinions based on other agents' views.

        In each debate round, agents that are in the minority may moderate
        their confidence.  Agents with strong convictions maintain them.

        This is a simplified debate model — a full LLM-backed implementation
        would use CrewAI's delegation and task system.
        """
        if round_number <= 0:
            return opinions

        # Count votes
        buy_count = sum(1 for o in opinions if o.vote == AgentVote.BUY.value)
        sell_count = sum(1 for o in opinions if o.vote == AgentVote.SELL.value)
        hold_count = sum(1 for o in opinions if o.vote == AgentVote.HOLD.value)
        total = len(opinions)

        if total == 0:
            return opinions

        majority_vote = max(
            (AgentVote.BUY.value, buy_count),
            (AgentVote.SELL.value, sell_count),
            (AgentVote.HOLD.value, hold_count),
            key=lambda x: x[1],
        )[0]

        refined = []
        for opinion in opinions:
            # RiskAgent never moderates
            if opinion.agent_name == "RiskAgent":
                refined.append(opinion)
                continue

            # If in minority, reduce confidence slightly
            if opinion.vote != majority_vote:
                new_confidence = _clamp(opinion.confidence * 0.85)
                # If very low confidence, switch to HOLD
                if new_confidence < 0.2 and opinion.vote != AgentVote.HOLD.value:
                    refined.append(AgentOpinion(
                        agent_name=opinion.agent_name,
                        vote=AgentVote.HOLD.value,
                        confidence=new_confidence,
                        reasoning=(
                            f"[Round {round_number}] Revised to HOLD after "
                            f"debate — insufficient conviction against majority "
                            f"({majority_vote})"
                        ),
                        risk_contribution=opinion.risk_contribution,
                        position_size_recommendation=0.0,
                        metadata={**opinion.metadata, "debate_revised": True},
                    ))
                else:
                    refined.append(AgentOpinion(
                        agent_name=opinion.agent_name,
                        vote=opinion.vote,
                        confidence=new_confidence,
                        reasoning=opinion.reasoning,
                        risk_contribution=opinion.risk_contribution,
                        position_size_recommendation=opinion.position_size_recommendation,
                        metadata={**opinion.metadata, "debate_confidence_reduced": True},
                    ))
            else:
                # Majority — slight confidence boost
                refined.append(AgentOpinion(
                    agent_name=opinion.agent_name,
                    vote=opinion.vote,
                    confidence=_clamp(opinion.confidence * 1.05),
                    reasoning=opinion.reasoning,
                    risk_contribution=opinion.risk_contribution,
                    position_size_recommendation=opinion.position_size_recommendation,
                    metadata=opinion.metadata,
                ))

        return refined


# ══════════════════════════════════════════════════════════════════════
# CREWAI ADAPTER (when crewai is available)
# ══════════════════════════════════════════════════════════════════════


class CrewAIAdapter:
    """
    Adapter that creates CrewAI agents from our agent definitions.

    Only used when the ``crewai`` package is available.  Converts
    each CouncilAgent into a CrewAI Agent with appropriate role,
    goal, and backstory, then runs them via a Crew kickoff.
    """

    def __init__(self, config: CouncilConfig) -> None:
        self._config = config
        self._agents = self._create_crewai_agents()
        self._crew = self._create_crew()

    def _create_crewai_agents(self) -> list[Any]:
        """Create CrewAI Agent objects for each of the 9 agents."""
        try:
            from crewai import Agent
        except ImportError:
            return []

        agent_defs = [
            {
                "role": "Market Researcher",
                "goal": "Gather comprehensive market data, news, and sentiment for informed trading decisions",
                "backstory": (
                    "You are a seasoned market researcher with 15 years of experience "
                    "analyzing financial markets. You excel at synthesizing news, sentiment, "
                    "and fundamental data into actionable research summaries."
                ),
            },
            {
                "role": "Trade Execution Strategist",
                "goal": "Determine optimal trade timing and execution decisions based on momentum and volume",
                "backstory": (
                    "You are an expert trader specializing in market timing. You analyze "
                    "momentum indicators, volume profiles, and price action to identify "
                    "the best entry and exit points for trades."
                ),
            },
            {
                "role": "Trading Strategist",
                "goal": "Select the optimal trading strategy and parameters for the current market regime",
                "backstory": (
                    "You are a quantitative strategist who designs and optimizes trading "
                    "strategies. You understand regime-dependent strategy selection and "
                    "parameter tuning for maximum risk-adjusted returns."
                ),
            },
            {
                "role": "Risk Manager",
                "goal": "Assess risk comprehensively and veto any trade that exceeds risk limits",
                "backstory": (
                    "You are a conservative risk manager with full VETO authority. Your "
                    "primary duty is capital preservation. You enforce strict risk limits "
                    "and never compromise on safety, regardless of potential profit."
                ),
            },
            {
                "role": "Portfolio Optimizer",
                "goal": "Ensure portfolio-level constraints are met and optimize asset allocation",
                "backstory": (
                    "You are a portfolio manager focused on optimal asset allocation and "
                    "constraint satisfaction. You use Kelly Criterion and modern portfolio "
                    "theory to size positions and manage concentration risk."
                ),
            },
            {
                "role": "Execution Specialist",
                "goal": "Manage order execution quality and minimize slippage",
                "backstory": (
                    "You are an execution specialist who ensures trades are filled at "
                    "the best possible prices. You monitor liquidity, spreads, and "
                    "market impact to optimize execution quality."
                ),
            },
            {
                "role": "Macro Economist",
                "goal": "Analyze macroeconomic conditions and detect regime shifts",
                "backstory": (
                    "You are a macroeconomist who studies central bank policies, economic "
                    "indicators, and geopolitical events. You identify macro regime shifts "
                    "that affect all asset classes."
                ),
            },
            {
                "role": "Crypto Analyst",
                "goal": "Provide cryptocurrency-specific analysis including on-chain metrics and DeFi trends",
                "backstory": (
                    "You are a crypto-native analyst who understands on-chain metrics, "
                    "funding rates, BTC dominance dynamics, and DeFi TVL flows. You "
                    "specialize in digital asset markets."
                ),
            },
            {
                "role": "Forex Analyst",
                "goal": "Provide forex-specific analysis including central bank divergence and carry trades",
                "backstory": (
                    "You are a forex specialist who analyzes currency strength, interest "
                    "rate differentials, central bank divergence, and carry trade "
                    "opportunities across G7 and emerging market currencies."
                ),
            },
        ]

        agents = []
        for defn in agent_defs:
            agent = Agent(
                role=defn["role"],
                goal=defn["goal"],
                backstory=defn["backstory"],
                verbose=False,
                allow_delegation=False,
            )
            agents.append(agent)

        return agents

    def _create_crew(self) -> Any:
        """Create a CrewAI Crew with the 9 agents."""
        try:
            from crewai import Crew, Process
        except ImportError:
            return None

        if not self._agents:
            return None

        return Crew(
            agents=self._agents,
            process=Process.sequential,
            verbose=False,
        )

    async def run(
        self,
        symbol: str,
        timeframe: str,
        data: dict[str, Any],
    ) -> CouncilResult:
        """
        Run the council via CrewAI.

        Falls back to the internal implementation if CrewAI execution fails.
        """
        try:
            from crewai import Task

            if self._crew is None or not self._agents:
                raise RuntimeError("CrewAI crew not initialized")

            # Create a task for the crew
            task_description = (
                f"Analyze the trading opportunity for {symbol} on {timeframe} timeframe. "
                f"Market data: {data}. Provide a consolidated BUY/SELL/HOLD recommendation "
                f"with confidence score, risk assessment, and position sizing."
            )

            task = Task(
                description=task_description,
                agent=self._agents[0],
                expected_output="A structured trading decision with action, confidence, risk score, and position size.",
            )

            result = self._crew.kickoff(tasks=[task])

            # Parse the CrewAI output into our CouncilResult format
            # CrewAI returns a CrewOutput object
            raw_output = str(result)

            # Attempt to extract action from the output
            action = CouncilAction.HOLD.value
            for act in (CouncilAction.BUY.value, CouncilAction.SELL.value, CouncilAction.HOLD.value):
                if act in raw_output.upper():
                    action = act
                    break

            return CouncilResult(
                action=action,
                confidence=0.5,
                reasoning=f"CrewAI council decision: {raw_output[:500]}",
                risk_score=0.5,
                position_size_pct=0.005,
                agent_votes={"crewai": action},
            )

        except Exception as exc:
            logger.warning(
                "CrewAI execution failed, falling back to internal implementation: %s",
                exc,
            )
            # Fall through to internal implementation
            raise


# ══════════════════════════════════════════════════════════════════════
# TRADING COUNCIL — MAIN ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════


class TradingCouncil:
    """
    9-Agent Trading Council — Orchestrates specialized agents for
    consensus-based trading decisions.

    The council runs 9 specialized agents in a tiered architecture:
        Tier 1 — RESEARCH (parallel): Researcher, Macro, Crypto, Forex
        Tier 2 — ANALYSIS (parallel): Strategist, Risk, Portfolio
        Tier 3 — EXECUTION (sequential): Trader, Execution

    After all agents produce opinions, a multi-round debate/voting
    process determines the final decision.  The RiskAgent has VETO
    authority to block any trade regardless of consensus.

    If ``crewai`` is installed, the council will attempt to use CrewAI's
    orchestration.  Otherwise, it falls back to a deterministic internal
    implementation that follows the same agent interfaces and produces
    identical output shapes.

    Args:
        config: Council configuration.  Defaults to ``CouncilConfig()``.

    Example::

        council = TradingCouncil()
        result = await council.run(
            symbol="BTCUSDT",
            timeframe="1h",
            data={
                "indicators": {"rsi_14": 35, "macd": {"histogram": 0.05}},
                "sentiment": {"overall_score": 0.4},
                "regime": "TRENDING_UP",
            },
        )
        print(result.action, result.confidence, result.risk_score)
    """

    def __init__(self, config: CouncilConfig | None = None) -> None:
        self._config = config or CouncilConfig()
        self._debate_engine = DebateEngine(self._config)
        self._crewai_adapter: CrewAIAdapter | None = None

        # ── Initialize the 9 agents ──────────────────────────────────
        self._agents: dict[str, CouncilAgent] = {
            "ResearcherAgent": ResearcherAgent(),
            "TraderAgent": TraderAgent(),
            "StrategistAgent": StrategistAgent(),
            "RiskAgent": RiskAgent(),
            "PortfolioAgent": PortfolioAgent(),
            "ExecutionAgent": ExecutionAgent(),
            "MacroAgent": MacroAgent(),
            "CryptoAgent": CryptoAgent(),
            "ForexAgent": ForexAgent(),
        }

        # ── Tier definitions for parallel execution ──────────────────
        self._tier1_agents = ["ResearcherAgent", "MacroAgent", "CryptoAgent", "ForexAgent"]
        self._tier2_agents = ["StrategistAgent", "RiskAgent", "PortfolioAgent"]
        self._tier3_agents = ["TraderAgent", "ExecutionAgent"]

        logger.info(
            "TradingCouncil initialized with %d agents, "
            "max_debate_rounds=%d, consensus_threshold=%.2f, risk_veto=%s",
            len(self._agents),
            self._config.max_debate_rounds,
            self._config.consensus_threshold,
            self._config.risk_veto_enabled,
        )

    # ──────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ──────────────────────────────────────────────────────────────────

    async def run(
        self,
        symbol: str,
        timeframe: str = "1d",
        data: dict[str, Any] | None = None,
    ) -> CouncilResult:
        """
        Run the full 9-agent trading council.

        Executes all agents in tiered parallel batches, runs the
        debate/voting process, and produces a final CouncilResult.

        Args:
            symbol: Trading symbol (e.g., "BTCUSDT", "EURUSD", "AAPL").
            timeframe: Chart timeframe (e.g., "1m", "5m", "1h", "1d").
            data: Market data dict containing indicators, price data,
                sentiment, regime, portfolio, crypto/forex-specific data.

        Returns:
            CouncilResult with the council's final decision.
        """
        data = data or {}
        start_time = time.monotonic()

        logger.info(
            "TradingCouncil starting for %s/%s with %d data keys",
            symbol, timeframe, len(data),
        )

        # ── Try CrewAI first if available ────────────────────────────
        if _is_crewai_available():
            try:
                if self._crewai_adapter is None:
                    self._crewai_adapter = CrewAIAdapter(self._config)
                result = await self._crewai_adapter.run(symbol, timeframe, data)
                elapsed = time.monotonic() - start_time
                logger.info("CrewAI council completed in %.2fs", elapsed)
                return result
            except Exception:
                logger.info("Falling back to internal implementation")

        # ── Internal implementation ──────────────────────────────────
        result = await self._run_internal(symbol, timeframe, data)

        elapsed = time.monotonic() - start_time
        logger.info(
            "TradingCouncil completed for %s: action=%s, confidence=%.2f, "
            "risk=%.2f, elapsed=%.2fs",
            symbol, result.action, result.confidence, result.risk_score, elapsed,
        )

        return result

    async def run_single_agent(
        self,
        agent_name: str,
        symbol: str,
        timeframe: str = "1d",
        data: dict[str, Any] | None = None,
    ) -> AgentOpinion:
        """
        Run a single named agent and return its opinion.

        Useful for debugging or for composing custom workflows.

        Args:
            agent_name: Name of the agent (must be one of the 9 agents).
            symbol: Trading symbol.
            timeframe: Chart timeframe.
            data: Market data dict.

        Returns:
            AgentOpinion from the specified agent.

        Raises:
            ValueError: If the agent name is not recognized.
        """
        agent = self._agents.get(agent_name)
        if agent is None:
            raise ValueError(
                f"Unknown agent '{agent_name}'. "
                f"Available: {list(self._agents.keys())}"
            )
        return await agent.analyze(symbol, timeframe, data or {})

    # ──────────────────────────────────────────────────────────────────
    # INTERNAL EXECUTION
    # ──────────────────────────────────────────────────────────────────

    async def _run_internal(
        self,
        symbol: str,
        timeframe: str,
        data: dict[str, Any],
    ) -> CouncilResult:
        """
        Run the internal (non-CrewAI) council implementation.

        Executes agents in tiered parallel batches:
            1. Tier 1 (Research): Researcher, Macro, Crypto, Forex
            2. Tier 2 (Analysis): Strategist, Risk, Portfolio
            3. Tier 3 (Execution): Trader, Execution

        Then runs multi-round debate and produces the final result.
        """
        all_opinions: list[AgentOpinion] = []
        risk_opinion: AgentOpinion | None = None
        tier_context: dict[str, Any] = {}

        # ── Tier 1: RESEARCH (parallel) ─────────────────────────────
        tier1_opinions = await self._run_agent_tier(
            self._tier1_agents, symbol, timeframe, data,
        )
        all_opinions.extend(tier1_opinions)

        # Build Tier 1 context for Tier 2
        tier_context["tier1_summary"] = {
            op.agent_name: {"vote": op.vote, "confidence": op.confidence, "reasoning": op.reasoning}
            for op in tier1_opinions
        }

        # Enrich data with Tier 1 findings for Tier 2 consumption
        enriched_data = {**data, "tier1_context": tier_context}

        # ── Tier 2: ANALYSIS (parallel) ─────────────────────────────
        tier2_opinions = await self._run_agent_tier(
            self._tier2_agents, symbol, timeframe, enriched_data,
        )

        # Separate RiskAgent opinion for VETO handling
        for opinion in tier2_opinions:
            if opinion.agent_name == "RiskAgent":
                risk_opinion = opinion
            else:
                all_opinions.append(opinion)

        # ── Tier 3: EXECUTION (parallel) ────────────────────────────
        tier3_opinions = await self._run_agent_tier(
            self._tier3_agents, symbol, timeframe, enriched_data,
        )
        all_opinions.extend(tier3_opinions)

        # Ensure risk opinion is included
        if risk_opinion is not None:
            all_opinions.append(risk_opinion)

        # ── Multi-round Debate ──────────────────────────────────────
        current_opinions = list(all_opinions)
        action = CouncilAction.HOLD.value
        confidence = 0.3
        agent_votes: dict[str, str] = {}

        for round_num in range(1, self._config.max_debate_rounds + 1):
            # Run debate
            action, confidence, agent_votes = self._debate_engine.run_debate(
                opinions=current_opinions,
                risk_opinion=risk_opinion,
            )

            # If we have a strong consensus, no need for more rounds
            if confidence >= self._config.consensus_threshold:
                logger.info(
                    "Consensus reached in round %d: %s (%.2f)",
                    round_num, action, confidence,
                )
                break

            # Refine opinions for next round
            if round_num < self._config.max_debate_rounds:
                current_opinions = self._debate_engine.refine_opinions(
                    current_opinions, round_num,
                )

        # ── Calculate final metrics ─────────────────────────────────
        risk_score = self._calculate_risk_score(all_opinions, risk_opinion)
        position_size_pct = self._calculate_position_size(
            all_opinions, action, risk_score,
        )

        # ── Build reasoning string ──────────────────────────────────
        reasoning = self._build_reasoning(
            action, confidence, risk_score, all_opinions, agent_votes,
        )

        return CouncilResult(
            action=action,
            confidence=round(confidence, 4),
            reasoning=reasoning,
            risk_score=round(risk_score, 4),
            position_size_pct=round(position_size_pct, 6),
            agent_votes=agent_votes,
        )

    async def _run_agent_tier(
        self,
        agent_names: list[str],
        symbol: str,
        timeframe: str,
        data: dict[str, Any],
    ) -> list[AgentOpinion]:
        """
        Run a tier of agents in parallel.

        All agents in a tier execute concurrently via asyncio.gather.
        Failed agents produce a HOLD opinion with error details.
        """
        tasks = []
        for name in agent_names:
            agent = self._agents.get(name)
            if agent is None:
                logger.warning("Agent %s not found, skipping", name)
                continue
            tasks.append(self._safe_analyze(agent, symbol, timeframe, data))

        if not tasks:
            return []

        results = await asyncio.gather(*tasks, return_exceptions=True)

        opinions: list[AgentOpinion] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                agent_name = agent_names[i] if i < len(agent_names) else f"unknown_{i}"
                logger.error(
                    "Agent %s failed: %s", agent_name, result,
                )
                opinions.append(AgentOpinion(
                    agent_name=agent_name,
                    vote=AgentVote.HOLD.value,
                    confidence=0.1,
                    reasoning=f"Agent error: {result}",
                    risk_contribution=0.5,
                    metadata={"error": str(result)},
                ))
            else:
                opinions.append(result)

        return opinions

    @staticmethod
    async def _safe_analyze(
        agent: CouncilAgent,
        symbol: str,
        timeframe: str,
        data: dict[str, Any],
    ) -> AgentOpinion:
        """Safely run an agent's analyze method with timeout and error handling."""
        try:
            result = await asyncio.wait_for(
                agent.analyze(symbol, timeframe, data),
                timeout=30.0,
            )
            return result
        except asyncio.TimeoutError:
            return AgentOpinion(
                agent_name=agent.name,
                vote=AgentVote.HOLD.value,
                confidence=0.1,
                reasoning="Agent timed out after 30s — defaulting to HOLD",
                risk_contribution=0.5,
                metadata={"error": "timeout"},
            )
        except Exception as exc:
            return AgentOpinion(
                agent_name=agent.name,
                vote=AgentVote.HOLD.value,
                confidence=0.1,
                reasoning=f"Agent error: {exc}",
                risk_contribution=0.5,
                metadata={"error": str(exc)},
            )

    # ──────────────────────────────────────────────────────────────────
    # METRICS CALCULATION
    # ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _calculate_risk_score(
        opinions: list[AgentOpinion],
        risk_opinion: AgentOpinion | None,
    ) -> float:
        """
        Calculate the overall risk score from agent opinions.

        Weighted average of all agents' risk_contribution, with extra
        weight given to the RiskAgent.
        """
        if not opinions:
            return 0.5

        total_weight = 0.0
        weighted_risk = 0.0

        for opinion in opinions:
            weight = DebateEngine.AGENT_WEIGHTS.get(opinion.agent_name, 1.0)
            if opinion.agent_name == "RiskAgent":
                weight *= 2.0  # Double weight for risk agent in risk calculation
            weighted_risk += opinion.risk_contribution * weight
            total_weight += weight

        if total_weight == 0:
            return 0.5

        base_risk = weighted_risk / total_weight

        # If risk agent flagged a veto, push risk score higher
        if risk_opinion is not None and risk_opinion.metadata.get("veto_triggered"):
            base_risk = max(base_risk, 0.8)

        return _clamp(base_risk)

    @staticmethod
    def _calculate_position_size(
        opinions: list[AgentOpinion],
        action: str,
        risk_score: float,
    ) -> float:
        """
        Calculate the recommended position size as a fraction of equity.

        Uses the median of agents' position_size_recommendations,
        scaled by risk and action.
        """
        if action == CouncilAction.HOLD.value:
            return 0.0

        # Collect non-zero position recommendations
        recs = [
            op.position_size_recommendation
            for op in opinions
            if op.position_size_recommendation > 0
        ]

        if not recs:
            # Default position size
            base_size = 0.005
        else:
            # Use median recommendation
            sorted_recs = sorted(recs)
            mid = len(sorted_recs) // 2
            base_size = sorted_recs[mid]

        # Scale by inverse risk (higher risk = smaller position)
        risk_multiplier = max(0.1, 1.0 - risk_score)

        return _clamp(base_size * risk_multiplier, 0.0, 0.02)

    @staticmethod
    def _build_reasoning(
        action: str,
        confidence: float,
        risk_score: float,
        opinions: list[AgentOpinion],
        agent_votes: dict[str, str],
    ) -> str:
        """
        Build a comprehensive reasoning string from agent opinions.
        """
        parts: list[str] = []

        parts.append(
            f"Council Decision: {action} (confidence: {confidence:.2f}, "
            f"risk: {risk_score:.2f})"
        )

        # Vote breakdown
        buy_count = sum(1 for v in agent_votes.values() if v == AgentVote.BUY.value)
        sell_count = sum(1 for v in agent_votes.values() if v == AgentVote.SELL.value)
        hold_count = sum(1 for v in agent_votes.values() if v == AgentVote.HOLD.value)
        parts.append(
            f"Votes: {buy_count} BUY, {sell_count} SELL, {hold_count} HOLD"
        )

        # Top agent reasoning (sorted by confidence, top 5)
        sorted_opinions = sorted(opinions, key=lambda o: o.confidence, reverse=True)
        for opinion in sorted_opinions[:5]:
            parts.append(
                f"  [{opinion.agent_name}] {opinion.vote} ({opinion.confidence:.2f}): "
                f"{opinion.reasoning[:200]}"
            )

        return "\n".join(parts)
