"""
finance_skills.py — Trading Finance Skills
Adapted from mnemosyne stock-analysis-skill + finance skill for trading platform.

Provides structured stock analysis, dividend analysis, rumor scanning,
and watchlist management for the trading agent system.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Models ──────────────────────────────────────────────────────

class PositionInfo(BaseModel):
    """User position information for a stock."""
    status: str = "empty"  # "empty" or "holding"
    cost: Optional[float] = None
    shares: Optional[float] = None


class StockAnalysisRequest(BaseModel):
    """Request for stock analysis."""
    symbol: str
    position: Optional[PositionInfo] = None
    mode: str = "full"  # "full" or "quote"
    include_market_review: bool = False
    include_global_macro: bool = True
    include_dividend: bool = False


class DividendMetrics(BaseModel):
    """Dividend analysis metrics."""
    ticker: str
    safety_score: float = Field(ge=0, le=100, description="0-100 composite score")
    income_rating: str = "moderate"  # excellent/good/moderate/poor
    payout_ratio_status: str = "moderate"  # safe/moderate/high/unsustainable
    five_year_cagr: Optional[float] = None
    consecutive_growth_years: Optional[int] = None
    current_yield: Optional[float] = None
    ex_dividend_date: Optional[str] = None


class RumorSignal(BaseModel):
    """A market rumor or early signal."""
    symbol: str
    signal_type: str  # ma/insider/analyst/regulatory/earnings
    impact_score: int = Field(ge=1, le=5)
    headline: str
    source: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class WatchlistEntry(BaseModel):
    """A watchlist entry with alerts."""
    symbol: str
    target_price: Optional[float] = None
    stop_price: Optional[float] = None
    alert_on_signal: bool = True
    notes: str = ""
    last_signal: Optional[str] = None
    added_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class StockDecision(BaseModel):
    """Stock analysis decision output."""
    symbol: str
    conclusion: str  # strong_buy/buy/hold/sell/strong_sell
    one_liner: str = ""
    empty_advice: str = ""
    holding_advice: str = ""
    pnl_if_holding: Optional[str] = None
    current_price: Optional[float] = None
    technical_score: Optional[float] = None
    fundamental_score: Optional[float] = None
    sentiment_score: Optional[float] = None
    risk_flags: list[str] = Field(default_factory=list)


class MarketReview(BaseModel):
    """Market overview/review data."""
    indices: dict[str, Any] = Field(default_factory=dict)
    sector_performance: dict[str, float] = Field(default_factory=dict)
    top_movers: list[dict[str, Any]] = Field(default_factory=list)
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ── Finance Skills Engine ──────────────────────────────────────

class FinanceSkillsEngine:
    """
    Finance skills engine providing structured analysis workflows
    for the trading agent system.
    """

    SIGNAL_TYPE_IMPACT = {
        "ma": 5,       # M&A / acquisition
        "insider": 4,  # CEO/director buying/selling
        "analyst": 3,  # Rating upgrades/downgrades
        "regulatory": 3,  # SEC investigation/compliance
        "earnings": 2,    # Earnings warnings/upgrades
    }

    def __init__(self, watchlist_path: Optional[str] = None):
        self.watchlist_path = Path(
            watchlist_path or "~/.quant_nanggroe_ai/watchlist.json"
        ).expanduser()
        self._watchlist: dict[str, WatchlistEntry] = {}
        self._load_watchlist()

    # ── Stock Analysis ────────────────────────────────────────

    def build_analysis_prompt(
        self,
        request: StockAnalysisRequest,
        market_data: dict[str, Any],
        technical_data: dict[str, Any],
        fundamental_data: dict[str, Any],
        sentiment_data: dict[str, Any],
    ) -> str:
        """
        Build a structured LLM prompt for stock analysis.

        Args:
            request: Analysis request with symbol and options
            market_data: Current market data for the symbol
            technical_data: Technical indicator data
            fundamental_data: Fundamental analysis data
            sentiment_data: News/sentiment data

        Returns:
            Formatted prompt string for LLM analysis
        """
        position_info = ""
        if request.position and request.position.status == "holding":
            position_info = f"""
User is HOLDING this stock:
- Cost basis: ${request.position.cost}
- Shares: {request.position.shares}
MUST include P&L analysis and holding-specific advice.
"""
        elif request.position and request.position.status == "empty":
            position_info = "User has NO position. Provide entry-level advice."

        prompt = f"""# Stock Analysis: {request.symbol}

## Current Market Data
{json.dumps(market_data, indent=2, default=str)}

## Technical Analysis
{json.dumps(technical_data, indent=2, default=str)}

## Fundamental Analysis
{json.dumps(fundamental_data, indent=2, default=str)}

## Sentiment & News
{json.dumps(sentiment_data, indent=2, default=str)}

{position_info}

## Instructions
Provide a structured analysis with:
1. Key Information Summary (risks, catalysts, latest developments)
2. Core Conclusion (strong_buy/buy/hold/sell/strong_sell)
3. One-liner summary
4. Entry advice (for non-holders)
5. Holding advice (for holders, with P&L if applicable)
6. Technical/Fundamental/Sentiment scores (0-100)
7. Risk flags

RULES:
- If deviation from MA > 5%, conclusion must NOT be buy/strong_buy
- If data is missing, mark as "N/A" — NEVER fabricate data
- If user has position, MUST provide P&L analysis
- If no position, provide BOTH empty and holding scenarios
"""
        return prompt

    def parse_decision(self, llm_response: str, symbol: str) -> StockDecision:
        """Parse LLM analysis response into structured StockDecision."""
        # Simple parsing — in production, use structured output
        conclusion = "hold"
        response_lower = llm_response.lower()
        if "strong_buy" in response_lower:
            conclusion = "strong_buy"
        elif "strong sell" in response_lower:
            conclusion = "strong_sell"
        elif "buy" in response_lower and "strong" not in response_lower:
            conclusion = "buy"
        elif "sell" in response_lower and "strong" not in response_lower:
            conclusion = "sell"

        return StockDecision(
            symbol=symbol,
            conclusion=conclusion,
            one_liner=llm_response.split("\n")[0][:200],
        )

    # ── Dividend Analysis ─────────────────────────────────────

    def analyze_dividend(
        self,
        ticker: str,
        payout_ratio: float,
        dividend_yield: float,
        five_year_cagr: Optional[float] = None,
        consecutive_growth_years: Optional[int] = None,
    ) -> DividendMetrics:
        """
        Analyze dividend safety and income quality.

        Args:
            ticker: Stock ticker
            payout_ratio: Current payout ratio (0.0 - 1.0+)
            dividend_yield: Current dividend yield (e.g. 0.03 for 3%)
            five_year_cagr: 5-year dividend CAGR
            consecutive_growth_years: Years of consecutive dividend growth

        Returns:
            DividendMetrics with safety scores and ratings
        """
        # Safety score: 0-100
        safety_score = 50.0  # baseline

        # Payout ratio contribution (0-30 points)
        if payout_ratio < 0.4:
            safety_score += 30
            payout_status = "safe"
        elif payout_ratio < 0.6:
            safety_score += 20
            payout_status = "moderate"
        elif payout_ratio < 0.8:
            safety_score += 10
            payout_status = "high"
        else:
            safety_score += 0
            payout_status = "unsustainable"

        # Growth contribution (0-30 points)
        if five_year_cagr and five_year_cagr > 0.05:
            safety_score += 30
        elif five_year_cagr and five_year_cagr > 0:
            safety_score += 20
        elif five_year_cagr is not None:
            safety_score += 5

        # Consecutive years contribution (0-20 points)
        if consecutive_growth_years and consecutive_growth_years >= 25:
            safety_score += 20  # Dividend Aristocrat
        elif consecutive_growth_years and consecutive_growth_years >= 10:
            safety_score += 15
        elif consecutive_growth_years and consecutive_growth_years >= 5:
            safety_score += 10

        # Yield contribution (0-20 points)
        if dividend_yield and dividend_yield > 0.03:
            safety_score += 15
        elif dividend_yield and dividend_yield > 0.01:
            safety_score += 10

        safety_score = min(100, max(0, safety_score))

        # Income rating
        if safety_score >= 80:
            income_rating = "excellent"
        elif safety_score >= 60:
            income_rating = "good"
        elif safety_score >= 40:
            income_rating = "moderate"
        else:
            income_rating = "poor"

        return DividendMetrics(
            ticker=ticker,
            safety_score=safety_score,
            income_rating=income_rating,
            payout_ratio_status=payout_status,
            five_year_cagr=five_year_cagr,
            consecutive_growth_years=consecutive_growth_years,
            current_yield=dividend_yield,
        )

    # ── Rumor Scanner ─────────────────────────────────────────

    def build_rumor_scan_prompt(self, news_items: list[dict]) -> str:
        """Build prompt for scanning market rumors and early signals."""
        news_text = "\n".join(
            f"- [{n.get('source', 'Unknown')}] {n.get('title', '')} ({n.get('date', '')})"
            for n in news_items[:30]
        )
        return f"""# Market Rumor Scanner

## Today's News Feed
{news_text}

## Instructions
Scan the above news for early market signals. For each signal found, classify:
- **ma**: M&A / acquisition / tender offer (impact: +5)
- **insider**: CEO/director buying/selling (impact: +4)
- **analyst**: Rating upgrades/downgrades/target changes (impact: +3)
- **regulatory**: SEC investigation/compliance risks (impact: +3)
- **earnings**: Earnings warnings/upgrades (impact: +2)

For each signal, provide: symbol, type, impact_score, headline, source.
"""

    def parse_rumor_signals(
        self, llm_response: str
    ) -> list[RumorSignal]:
        """Parse LLM rumor scan response into structured signals."""
        signals = []
        for line in llm_response.split("\n"):
            line = line.strip()
            if any(t in line.lower() for t in ["ma:", "insider:", "analyst:", "regulatory:", "earnings:"]):
                try:
                    parts = line.split("|")
                    if len(parts) >= 3:
                        signals.append(RumorSignal(
                            symbol=parts[0].strip().split(":")[-1].strip(),
                            signal_type=parts[0].strip().split(":")[0].strip().lower(),
                            impact_score=int(parts[1].strip()),
                            headline=parts[2].strip(),
                        ))
                except (IndexError, ValueError):
                    continue
        return signals

    # ── Watchlist Management ──────────────────────────────────

    def add_to_watchlist(self, entry: WatchlistEntry) -> None:
        """Add a stock to the watchlist."""
        self._watchlist[entry.symbol] = entry
        self._save_watchlist()

    def remove_from_watchlist(self, symbol: str) -> bool:
        """Remove a stock from the watchlist."""
        if symbol in self._watchlist:
            del self._watchlist[symbol]
            self._save_watchlist()
            return True
        return False

    def get_watchlist(self) -> list[WatchlistEntry]:
        """Get all watchlist entries."""
        return list(self._watchlist.values())

    def check_alerts(
        self, symbol: str, current_price: float, current_signal: Optional[str] = None
    ) -> list[str]:
        """
        Check if any watchlist alerts are triggered.

        Returns list of alert messages.
        """
        entry = self._watchlist.get(symbol)
        if not entry:
            return []

        alerts = []
        if entry.target_price and current_price >= entry.target_price:
            alerts.append(
                f"TARGET REACHED: {symbol} at ${current_price:.2f} >= target ${entry.target_price:.2f}"
            )

        if entry.stop_price and current_price <= entry.stop_price:
            alerts.append(
                f"STOP LOSS TRIGGERED: {symbol} at ${current_price:.2f} <= stop ${entry.stop_price:.2f}"
            )

        if entry.alert_on_signal and current_signal and current_signal != entry.last_signal:
            alerts.append(
                f"SIGNAL CHANGED: {symbol} from '{entry.last_signal}' to '{current_signal}'"
            )
            entry.last_signal = current_signal

        if alerts:
            self._save_watchlist()

        return alerts

    def _load_watchlist(self) -> None:
        """Load watchlist from disk."""
        if self.watchlist_path.exists():
            try:
                data = json.loads(self.watchlist_path.read_text())
                self._watchlist = {
                    k: WatchlistEntry(**v) for k, v in data.items()
                }
            except (json.JSONDecodeError, Exception):
                self._watchlist = {}

    def _save_watchlist(self) -> None:
        """Save watchlist to disk."""
        self.watchlist_path.parent.mkdir(parents=True, exist_ok=True)
        data = {k: v.model_dump() for k, v in self._watchlist.items()}
        self.watchlist_path.write_text(json.dumps(data, indent=2, default=str))
