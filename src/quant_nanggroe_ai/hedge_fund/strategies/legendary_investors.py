"""
Legendary Investor Strategies
==============================
Strategies inspired by legendary investors:
- Warren Buffett (Value Investing)
- Peter Lynch (Growth Investing)
- Benjamin Graham (Deep Value)
- George Soros (Macro/Reflexivity)
- Ray Dalio (All Weather)
- Michael Burry (Value/Contrarian)
- Philip Fisher (Growth)
- John Templeton (Contrarian)
- Joel Greenblatt (Magic Formula)
- William O'Neil (CAN SLIM)

Usage:
    from src.strategies.legendary_investors import analyze_with_all_legendary
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from enum import Enum

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class InvestorStyle(Enum):
    BUFFETT = "buffett"  # Quality + Value
    LYNCH = "lynch"  # Growth at reasonable price
    GRAHAM = "graham"  # Deep value
    SOROS = "soros"  # Macro reflexivity
    DALIO = "dalio"  # Risk parity
    BURRY = "burry"  # Value/Contrarian
    FISHER = "fisher"  # Growth
    TEMPLETON = "templeton"  # Contrarian
    GREENBLATT = "greenblatt"  # Magic formula
    ONEIL = "oneil"  # CAN SLIM


@dataclass
class LegendarySignal:
    """Signal from legendary investor strategy"""
    investor: str
    style: InvestorStyle
    signal: str  # BUY, SELL, HOLD
    confidence: float  # 0-1
    score: int  # 0-100
    pe_ratio: float
    growth_rate: float
    moat_score: float
    reasoning: List[str]
    metrics: Dict[str, float]
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class LegendaryConsensus:
    """Aggregated signal from all legendary investors"""
    final_signal: str
    confidence: float
    score: int
    investor_signals: List[LegendarySignal]
    consensus_level: str  # unanimous, majority, divided
    wisdom_of_crowds: float
    best_investor: str
    worst_investor: str


# ============ BUFFETT STRATEGY (Quality + Value) ============

def buffett_style(
    prices: List[float],
    fundamentals: Dict[str, float] = None,
    market_data: Dict[str, float] = None
) -> LegendarySignal:
    """
    Warren Buffett Strategy:
    - High quality companies (ROE > 15%, consistent earnings)
    - Reasonable valuation (PE < 15, PEG < 1)
    - Strong moat (high gross margins, market share)
    - Long-term holding perspective
    """
    if fundamentals is None:
        fundamentals = {}
    if market_data is None:
        market_data = {}
    
    current_price = prices[-1]
    
    # Buffett metrics
    pe_ratio = fundamentals.get('pe', 20)
    roe = fundamentals.get('roe', 15)
    profit_margin = fundamentals.get('profit_margin', 10)
    debt_equity = fundamentals.get('debt_equity', 0.5)
    free_cash_flow_yield = fundamentals.get('fcf_yield', 5)
    dividend_growth = fundamentals.get('dividend_growth', 5)
    
    # Calculate scores
    quality_score = min(100, (roe / 20 * 40) + (profit_margin / 20 * 30) + ((1 - debt_equity) / 1 * 20))
    value_score = min(100, (15 / pe_ratio * 50) if pe_ratio > 0 else 50)
    moat_score = min(100, ((1 - debt_equity) / 1 * 30) + (free_cash_flow_yield / 10 * 30) + (dividend_growth / 10 * 20))
    
    # Buffett look for quality at reasonable price
    buffett_score = (quality_score * 0.5) + (value_score * 0.3) + (moat_score * 0.2)
    
    reasoning = []
    if roe > 15:
        reasoning.append(f"High ROE ({roe:.1f}%) indicates quality business")
    if pe_ratio < 15:
        reasoning.append(f"Reasonable PE ({pe_ratio:.1f}) below Buffett's threshold")
    if pe_ratio < 15 and roe > 15:
        reasoning.append(f"Quality at reasonable price (ROE/PE = {roe/pe_ratio:.2f})")
    if free_cash_flow_yield > 5:
        reasoning.append(f"Strong FCF yield ({free_cash_flow_yield:.1f}%)")
    if debt_equity < 0.5:
        reasoning.append(f"Conservative debt level (D/E = {debt_equity:.2f})")
    
    signal = "BUY" if buffett_score > 60 else "HOLD" if buffett_score > 40 else "SELL"
    confidence = min(0.9, buffett_score / 100 + 0.2)
    
    return LegendarySignal(
        investor="Warren Buffett",
        style=InvestorStyle.BUFFETT,
        signal=signal,
        confidence=confidence,
        score=int(buffett_score),
        pe_ratio=pe_ratio,
        growth_rate=fundamentals.get('growth', 5),
        moat_score=moat_score,
        reasoning=reasoning,
        metrics={
            'quality_score': quality_score,
            'value_score': value_score,
            'moat_score': moat_score,
            'roe': roe,
            'pe_ratio': pe_ratio,
            'debt_equity': debt_equity,
            'fcf_yield': free_cash_flow_yield
        }
    )


# ============ LYNCH STRATEGY (Growth at Reasonable Price) ============

def lynch_style(
    prices: List[float],
    fundamentals: Dict[str, float] = None,
    market_data: Dict[str, float] = None
) -> LegendarySignal:
    """
    Peter Lynch Strategy:
    - Growth at reasonable price (PEG < 1)
    - Look for 10-baggers
    - Understand what you own
    - Buy what you know (consumer brands)
    - Ignore the noise
    """
    if fundamentals is None:
        fundamentals = {}
    
    current_price = prices[-1]
    
    # Lynch metrics
    pe_ratio = fundamentals.get('pe', 25)
    growth_rate = fundamentals.get('growth', 15)
    peg = pe_ratio / growth_rate if growth_rate > 0 else 2
    profit_margin = fundamentals.get('profit_margin', 10)
    revenue_growth = fundamentals.get('revenue_growth', 10)
    insider_ownership = fundamentals.get('insider_ownership', 10)
    
    # PEG is key for Lynch
    peg_score = min(100, (1 / peg * 50) if peg > 0 else 50)
    growth_score = min(100, (growth_rate / 25 * 40))
    momentum_score = min(100, (revenue_growth / 20 * 30))
    
    lynch_score = (peg_score * 0.4) + (growth_score * 0.35) + (momentum_score * 0.25)
    
    reasoning = []
    if peg < 1:
        reasoning.append(f"Excellent PEG ratio ({peg:.2f}) - growth at reasonable price")
    if growth_rate > 20:
        reasoning.append(f"High growth rate ({growth_rate:.1f}%)")
    if revenue_growth > 15:
        reasoning.append(f"Strong revenue momentum ({revenue_growth:.1f}%)")
    if insider_ownership > 10:
        reasoning.append(f"High insider ownership ({insider_ownership:.1f}%) suggests alignment")
    if profit_margin > 15:
        reasoning.append(f"Strong profit margins ({profit_margin:.1f}%)")
    
    signal = "BUY" if lynch_score > 60 else "HOLD" if lynch_score > 40 else "SELL"
    confidence = min(0.9, lynch_score / 100 + 0.15)
    
    return LegendarySignal(
        investor="Peter Lynch",
        style=InvestorStyle.LYNCH,
        signal=signal,
        confidence=confidence,
        score=int(lynch_score),
        pe_ratio=pe_ratio,
        growth_rate=growth_rate,
        moat_score=peg_score,
        reasoning=reasoning,
        metrics={
            'peg_ratio': peg,
            'growth_score': growth_score,
            'momentum_score': momentum_score,
            'revenue_growth': revenue_growth,
            'insider_ownership': insider_ownership
        }
    )


# ============ GRAHAM STRATEGY (Deep Value) ============

def graham_style(
    prices: List[float],
    fundamentals: Dict[str, float] = None,
    market_data: Dict[str, float] = None
) -> LegendarySignal:
    """
    Benjamin Graham Strategy (Deep Value):
    - PE < 15, ideally < 10
    - Price to book < 1.5
    - Current ratio > 2
    - No debt
    - Margin of safety > 30%
    """
    if fundamentals is None:
        fundamentals = {}
    
    current_price = prices[-1]
    
    # Graham metrics
    eps = fundamentals.get('eps', 2)
    book_value = fundamentals.get('book_value', 20)
    current_ratio = fundamentals.get('current_ratio', 2)
    debt_equity = fundamentals.get('debt_equity', 0.3)
    pe_ratio = fundamentals.get('pe', 15)
    pb_ratio = current_price / book_value if book_value > 0 else 10
    
    # Graham filters
    pe_ok = pe_ratio < 15
    pb_ok = pb_ratio < 1.5
    current_ok = current_ratio > 2
    debt_ok = debt_equity < 0.5
    
    # Value score
    value_score = min(100, (15 / pe_ratio * 30) if pe_ratio > 0 else 30)
    value_score += (1.5 / pb_ratio * 20) if pb_ratio > 0 else 0
    value_score += (current_ratio / 3 * 20) if current_ratio > 0 else 0
    value_score += ((1 - debt_equity) / 1 * 20) if debt_equity >= 0 else 0
    
    # Margin of safety
    intrinsic_value = eps * (8.5 + 2 * fundamentals.get('growth', 5))
    margin_safety = (1 - current_price / intrinsic_value) * 100 if intrinsic_value > 0 else 0
    
    reasoning = []
    if pe_ratio < 10:
        reasoning.append(f"Deep value PE ({pe_ratio:.1f}) below Graham's 10 threshold")
    if pe_ok and pb_ok:
        reasoning.append(f"Double value filter: PE={pe_ratio:.1f}, P/B={pb_ratio:.2f}")
    if current_ok:
        reasoning.append(f"Strong liquidity (Current Ratio={current_ratio:.2f})")
    if debt_ok:
        reasoning.append(f"Conservative leverage (D/E={debt_equity:.2f})")
    if margin_safety > 30:
        reasoning.append(f"Large margin of safety ({margin_safety:.1f}%)")
    
    signal = "BUY" if value_score > 70 and margin_safety > 20 else "HOLD" if value_score > 50 else "SELL"
    confidence = min(0.85, value_score / 100 * 0.8 + 0.2)
    
    return LegendarySignal(
        investor="Benjamin Graham",
        style=InvestorStyle.GRAHAM,
        signal=signal,
        confidence=confidence,
        score=int(value_score),
        pe_ratio=pe_ratio,
        growth_rate=fundamentals.get('growth', 3),
        moat_score=value_score,
        reasoning=reasoning,
        metrics={
            'pe_ratio': pe_ratio,
            'pb_ratio': pb_ratio,
            'current_ratio': current_ratio,
            'margin_safety': margin_safety,
            'intrinsic_value': intrinsic_value
        }
    )


# ============ SOROS STRATEGY (Reflexivity/Macro) ============

def soros_style(
    prices: List[float],
    fundamentals: Dict[str, float] = None,
    market_data: Dict[str, float] = None
) -> LegendarySignal:
    """
    George Soros Strategy (Reflexivity):
    - Market sentiment and crowd behavior
    - Trend following with contrarian exit
    - Macro themes (inflation, rates, currency)
    - Big bets when thesis is confirmed
    """
    if fundamentals is None:
        fundamentals = {}
    if market_data is None:
        market_data = {}
    
    prices_array = np.array(prices)
    
    # Calculate momentum and trend
    returns = np.diff(prices_array) / prices_array[:-1]
    momentum = np.sum(returns[-20:])  # 20-day momentum
    trend_strength = np.abs(np.mean(returns[-10:]) / np.std(returns[-10:])) if np.std(returns[-10:]) > 0 else 0
    
    # Volatility regime
    volatility = np.std(returns[-20:]) * np.sqrt(252)
    
    # Sentiment indicators
    price_vs_sma20 = (prices_array[-1] / np.mean(prices_array[-20:]) - 1) * 100
    price_vs_sma50 = (prices_array[-1] / np.mean(prices_array[-50:]) - 1) * 100
    
    # Soros looks for:
    # 1. Strong trend (reflexivity in action)
    # 2. Extreme positioning
    # 3. Macro catalyst
    
    reflexivity_score = min(100, (trend_strength / 2 * 30) + ((momentum + 0.1) / 0.2 * 30))
    
    if price_vs_sma50 > 20:
        reflexivity_score += 20  # Strong uptrend
        reasoning = ["Strong uptrend suggests reflexivity in action"]
    elif price_vs_sma50 < -20:
        reflexivity_score -= 20
        reasoning = ["Bear market - reflexivity working against bulls"]
    else:
        reasoning = ["Consolidation phase - waiting for clearer signal"]
    
    # Macro context
    inflation = market_data.get('inflation', 3)
    interest_rate = market_data.get('interest_rate', 5)
    
    if inflation > 5 and interest_rate > 5:
        reflexivity_score -= 15
        reasoning.append("Tight monetary conditions - headwind for risk assets")
    elif inflation < 2 and interest_rate < 3:
        reflexivity_score += 10
        reasoning.append("Goldilocks conditions - tailwind for risk assets")
    
    signal = "BUY" if reflexivity_score > 60 and momentum > 0 else "SELL" if reflexivity_score < 40 and momentum < 0 else "HOLD"
    confidence = min(0.8, abs(momentum) / 0.05 * 0.5 + 0.3)
    
    return LegendarySignal(
        investor="George Soros",
        style=InvestorStyle.SOROS,
        signal=signal,
        confidence=confidence,
        score=int(reflexivity_score),
        pe_ratio=fundamentals.get('pe', 20),
        growth_rate=fundamentals.get('growth', 5),
        moat_score=trend_strength,
        reasoning=reasoning,
        metrics={
            'momentum': momentum,
            'trend_strength': trend_strength,
            'volatility': volatility,
            'price_vs_sma50': price_vs_sma50,
            'inflation': inflation,
            'interest_rate': interest_rate
        }
    )


# ============ DALIO STRATEGY (All Weather) ============

def dalio_style(
    prices: List[float],
    fundamentals: Dict[str, float] = None,
    market_data: Dict[str, float] = None
) -> LegendarySignal:
    """
    Ray Dalio Strategy (All Weather/Risk Parity):
    - Diversification across assets
    - Risk parity (equal risk contribution)
    - Inflation/hedge assets during inflation
    - Long volatility when under stress
    - Balance sheet over income statement
    """
    if fundamentals is None:
        fundamentals = {}
    if market_data is None:
        market_data = {}
    
    prices_array = np.array(prices)
    returns = np.diff(prices_array) / prices_array[:-1]
    
    # Risk metrics
    volatility = np.std(returns) * np.sqrt(252)
    sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
    
    # Max drawdown
    cumulative = (1 + returns).cumprod()
    peak = np.maximum.accumulate(cumulative)
    drawdown = (cumulative - peak) / peak
    max_dd = np.min(drawdown)
    
    # Sortino (downside risk)
    negative_returns = returns[returns < 0]
    downside_vol = np.std(negative_returns) * np.sqrt(252) if len(negative_returns) > 0 else volatility
    sortino = np.mean(returns) / downside_vol * np.sqrt(252) if downside_vol > 0 else 0
    
    # Correlation to market (beta approximation)
    market_returns = market_data.get('market_returns', returns)
    if len(market_returns) > 0:
        covariance = np.cov(returns, market_returns)[0][1]
        market_variance = np.var(market_returns)
        beta = covariance / market_variance if market_variance > 0 else 1
    else:
        beta = 1
    
    # Dalio likes:
    # - High Sharpe (risk-adjusted returns)
    # - Low correlation to traditional market
    # - Good Sortino (less downside risk)
    
    risk_parity_score = min(100, (sharpe + 1) / 3 * 40 + (sortino + 1) / 3 * 30 + (1 - abs(beta)) / 1 * 20)
    
    reasoning = []
    if sharpe > 1:
        reasoning.append(f"Excellent risk-adjusted returns (Sharpe: {sharpe:.2f})")
    if sortino > sharpe:
        reasoning.append(f"Better downside protection (Sortino: {sortino:.2f} > Sharpe: {sharpe:.2f})")
    if beta < 0.8:
        reasoning.append(f"Low correlation to market (beta: {beta:.2f}) - good diversification")
    if max_dd > -0.2:
        reasoning.append(f"Acceptable max drawdown ({max_dd:.1%})")
    if volatility < 0.2:
        reasoning.append(f"Low volatility ({volatility:.1%}) suitable for all-weather")
    
    signal = "BUY" if risk_parity_score > 60 else "HOLD" if risk_parity_score > 40 else "SELL"
    confidence = min(0.85, sharpe / 2 + 0.4)
    
    return LegendarySignal(
        investor="Ray Dalio",
        style=InvestorStyle.DALIO,
        signal=signal,
        confidence=confidence,
        score=int(risk_parity_score),
        pe_ratio=fundamentals.get('pe', 20),
        growth_rate=fundamentals.get('growth', 5),
        moat_score=risk_parity_score,
        reasoning=reasoning,
        metrics={
            'sharpe_ratio': sharpe,
            'sortino_ratio': sortino,
            'beta': beta,
            'volatility': volatility,
            'max_drawdown': max_dd
        }
    )


# ============ BURRY STRATEGY (Value/Contrarian) ============

def burry_style(
    prices: List[float],
    fundamentals: Dict[str, float] = None,
    market_data: Dict[str, float] = None
) -> LegendarySignal:
    """
    Michael Burry Strategy (Value/Contrarian):
    - Deep value (ignore growth)
    - Short-term pain, long-term gain
    - High short interest can indicate opportunity
    - Activist potential
    - Asset plays
    """
    if fundamentals is None:
        fundamentals = {}
    
    current_price = prices[-1]
    
    # Burry metrics
    pe_ratio = fundamentals.get('pe', 10)
    pb_ratio = fundamentals.get('pb', 1)
    dividend_yield = fundamentals.get('dividend_yield', 3)
    eps_growth_5yr = fundamentals.get('eps_growth_5yr', 2)
    institutional_ownership = fundamentals.get('institutional_ownership', 50)
    
    # Contrarian indicators
    short_interest = fundamentals.get('short_interest', 5)
    
    # Deep value score
    value_score = min(100, (12 / pe_ratio * 30) if pe_ratio > 0 else 40)
    value_score += (1.5 / pb_ratio * 25) if pb_ratio > 0 else 0
    value_score += (dividend_yield / 8 * 20) if dividend_yield > 0 else 0
    
    # Contrarian score
    contrarian_score = 50
    if short_interest > 20:
        contrarian_score += 25  # High short = potential short squeeze
        reasoning = ["High short interest suggests potential short squeeze"]
    elif short_interest < 5:
        contrarian_score -= 10
        reasoning = ["Low short interest - no contrarian play"]
    else:
        reasoning = ["Moderate short interest"]
    
    # Burry looks for misunderstood/ignored value
    if institutional_ownership < 30:
        contrarian_score += 15
        reasoning.append("Low institutional ownership - potential undervaluation")
    
    burry_score = (value_score * 0.6) + (contrarian_score * 0.4)
    
    reasoning.extend([
        f"Deep value metrics (PE={pe_ratio:.1f}, P/B={pb_ratio:.2f})",
        f"Dividend yield {dividend_yield:.1f}% provides floor",
        f"5Y EPS growth {eps_growth_5yr:.1f}% - steady performer"
    ])
    
    signal = "BUY" if burry_score > 65 else "HOLD" if burry_score > 45 else "SELL"
    confidence = min(0.85, burry_score / 100 + 0.2)
    
    return LegendarySignal(
        investor="Michael Burry",
        style=InvestorStyle.BURRY,
        signal=signal,
        confidence=confidence,
        score=int(burry_score),
        pe_ratio=pe_ratio,
        growth_rate=eps_growth_5yr,
        moat_score=value_score,
        reasoning=reasoning,
        metrics={
            'value_score': value_score,
            'contrarian_score': contrarian_score,
            'short_interest': short_interest,
            'dividend_yield': dividend_yield,
            'pb_ratio': pb_ratio
        }
    )


# ============ FISHER STRATEGY (Growth) ============

def fisher_style(
    prices: List[float],
    fundamentals: Dict[str, float] = None,
    market_data: Dict[str, float] = None
) -> LegendarySignal:
    """
    Philip Fisher Strategy (15 Points):
    - Growth potential (7 points)
    - Management quality (4 points)
    - Business characteristics (4 points)
    - Focus on long-term, not quarterly earnings
    - Scuttlebutt method (talk to customers/competitors)
    """
    if fundamentals is None:
        fundamentals = {}
    
    current_price = prices[-1]
    
    # Fisher metrics
    revenue_growth_5yr = fundamentals.get('revenue_growth_5yr', 10)
    profit_margin_trend = fundamentals.get('margin_trend', 0)  # Improving or declining
    roe_trend = fundamentals.get('roe_trend', 0)
    r_and_d_spending = fundamentals.get('rd_spending', 5)  # % of revenue
    employee_growth = fundamentals.get('employee_growth', 5)
    
    # Growth score (7 points)
    growth_score = min(70, (revenue_growth_5yr / 25 * 25))
    growth_score += 15 if profit_margin_trend > 0 else 0
    growth_score += 15 if roe_trend > 0 else 0
    growth_score += (r_and_d_spending / 10 * 10) if r_and_d_spending > 0 else 0
    growth_score += (employee_growth / 15 * 5) if employee_growth > 0 else 0
    
    # Quality indicators
    quality_score = min(30, fundamentals.get('gross_margin', 40) / 50 * 15)
    quality_score += fundamentals.get('retention_rate', 80) / 100 * 15
    
    fisher_score = growth_score + quality_score
    
    reasoning = []
    if revenue_growth_5yr > 15:
        reasoning.append(f"Strong 5Y revenue growth ({revenue_growth_5yr:.1f}%)")
    if profit_margin_trend > 0:
        reasoning.append("Improving profit margins")
    if roe_trend > 0:
        reasoning.append("Rising return on equity")
    if r_and_d_spending > 10:
        reasoning.append(f"Heavy R&D investment ({r_and_d_spending:.1f}%) for future growth")
    if employee_growth > revenue_growth_5yr:
        reasoning.append("Hiring faster than revenue - building for future")
    
    signal = "BUY" if fisher_score > 65 else "HOLD" if fisher_score > 45 else "SELL"
    confidence = min(0.85, fisher_score / 100 + 0.15)
    
    return LegendarySignal(
        investor="Philip Fisher",
        style=InvestorStyle.FISHER,
        signal=signal,
        confidence=confidence,
        score=int(fisher_score),
        pe_ratio=fundamentals.get('pe', 25),
        growth_rate=revenue_growth_5yr,
        moat_score=growth_score,
        reasoning=reasoning,
        metrics={
            'growth_score': growth_score,
            'quality_score': quality_score,
            'revenue_growth_5yr': revenue_growth_5yr,
            'r_and_d_spending': r_and_d_spending
        }
    )


# ============ TEMPLETON STRATEGY (Contrarian) ============

def templeton_style(
    prices: List[float],
    fundamentals: Dict[str, float] = None,
    market_data: Dict[str, float] = None
) -> LegendarySignal:
    """
    John Templeton Strategy (Contrarian):
    - Buy at maximum pessimism
    - "Bull markets are born on pessimism"
    - Global diversification
    - Long-term perspective (10+ years)
    - Death watch stocks (out of favor)
    """
    if fundamentals is None:
        fundamentals = {}
    
    prices_array = np.array(prices)
    
    # Price momentum
    price_momentum_1y = (prices_array[-1] / prices_array[-252] - 1) if len(prices_array) >= 252 else 0
    price_momentum_6m = (prices_array[-1] / prices_array[-126] - 1) if len(prices_array) >= 126 else 0
    
    # Sentiment proxy (using fundamentals)
    analyst_coverage = fundamentals.get('analyst_coverage', 10)  # Fewer = more contrarian
    news_sentiment = fundamentals.get('news_sentiment', 0)  # Negative = contrarian
    
    # Templeton score
    contrarian_score = 50
    
    # Maximum pessimism = underperformance
    if price_momentum_1y < -20:
        contrarian_score += 30
        reasoning = ["Deep underperformance - maximum pessimism"]
    elif price_momentum_1y < -10:
        contrarian_score += 20
        reasoning = ["Significant underperformance"]
    elif price_momentum_1y > 20:
        contrarian_score -= 30
        reasoning = ["Strong performance - not contrarian opportunity"]
    else:
        reasoning = ["Neutral price action"]
    
    # Low analyst coverage = ignored
    if analyst_coverage < 5:
        contrarian_score += 15
        reasoning.append("Low analyst coverage - ignored by market")
    
    # Negative news sentiment
    if news_sentiment < 0:
        contrarian_score += 10
        reasoning.append("Negative sentiment - potential opportunity")
    
    # Templeton specifically looks at valuations during pessimism
    pe_ratio = fundamentals.get('pe', 20)
    if pe_ratio < 10 and price_momentum_1y < -10:
        contrarian_score += 15
        reasoning.append("Deep value during bear market - Templeton's bread and butter")
    
    signal = "BUY" if contrarian_score > 70 else "HOLD" if contrarian_score > 50 else "SELL"
    confidence = min(0.8, contrarian_score / 100 * 0.7 + 0.2)
    
    return LegendarySignal(
        investor="John Templeton",
        style=InvestorStyle.TEMPLETON,
        signal=signal,
        confidence=confidence,
        score=int(contrarian_score),
        pe_ratio=pe_ratio,
        growth_rate=fundamentals.get('growth', 3),
        moat_score=contrarian_score,
        reasoning=reasoning,
        metrics={
            'price_momentum_1y': price_momentum_1y,
            'price_momentum_6m': price_momentum_6m,
            'analyst_coverage': analyst_coverage,
            'contrarian_score': contrarian_score
        }
    )


# ============ GREENBLATT STRATEGY (Magic Formula) ============

def greenblatt_style(
    prices: List[float],
    fundamentals: Dict[str, float] = None,
    market_data: Dict[str, float] = None
) -> LegendarySignal:
    """
    Joel Greenblatt Strategy (Magic Formula):
    - Rank by Earnings Yield (EV/EBIT)
    - Rank by Return on Capital (ROC)
    - Buy top 20-30 stocks
    - Hold for 1 year
    - Ignore the market
    """
    if fundamentals is None:
        fundamentals = {}
    
    current_price = prices[-1]
    
    # Magic Formula metrics
    ev_ebit = fundamentals.get('ev_ebit', 10)  # Earnings yield inverse
    roic = fundamentals.get('roic', 10)  # Return on invested capital
    enterprise_value = fundamentals.get('enterprise_value', 1000000)
    ebit = fundamentals.get('ebit', 100000)
    net_income = fundamentals.get('net_income', 50000)
    
    # Calculate earnings yield
    earnings_yield = (ebit / enterprise_value * 100) if enterprise_value > 0 else 5
    
    # Magic Formula scoring
    # Rank 1: Earnings Yield (higher is better)
    ey_score = min(50, earnings_yield / 20 * 50)
    
    # Rank 2: Return on Capital (higher is better)
    roc_score = min(50, roic / 30 * 50)
    
    magic_score = ey_score + roc_score
    
    reasoning = []
    if earnings_yield > 10:
        reasoning.append(f"Excellent earnings yield ({earnings_yield:.1f}%)")
    if roic > 20:
        reasoning.append(f"Outstanding return on capital ({roic:.1f}%)")
    if earnings_yield > 10 and roic > 20:
        reasoning.append("Magic Formula top decile candidate")
    if magic_score > 70:
        reasoning.append("Among highest Magic Formula ranks")
    
    signal = "BUY" if magic_score > 60 else "HOLD" if magic_score > 40 else "SELL"
    confidence = min(0.85, magic_score / 100 * 0.8 + 0.15)
    
    return LegendarySignal(
        investor="Joel Greenblatt",
        style=InvestorStyle.GREENBLATT,
        signal=signal,
        confidence=confidence,
        score=int(magic_score),
        pe_ratio=fundamentals.get('pe', 15),
        growth_rate=fundamentals.get('growth', 5),
        moat_score=magic_score,
        reasoning=reasoning,
        metrics={
            'earnings_yield': earnings_yield,
            'roic': roic,
            'ey_score': ey_score,
            'roc_score': roc_score,
            'magic_score': magic_score
        }
    )


# ============ ONEIL STRATEGY (CAN SLIM) ============

def oneil_style(
    prices: List[float],
    fundamentals: Dict[str, float] = None,
    market_data: Dict[str, float] = None
) -> LegendarySignal:
    """
    William O'Neil Strategy (CAN SLIM):
    - C: Current quarterly earnings > 25% YoY
    - A: Annual earnings growth > 25% for 3 years
    - N: New highs, new products, new management
    - S: Supply and demand (low float, high volume)
    - L: Leader or laggard (buy leaders)
    - I: Institutional sponsorship
    - M: Market direction
    
    Growth + Momentum + Market Timing
    """
    if fundamentals is None:
        fundamentals = {}
    
    prices_array = np.array(prices)
    
    # CAN SLIM metrics
    earnings_qoq = fundamentals.get('earnings_qoq', 10)  # Quarterly earnings growth
    earnings_yoy_3yr = fundamentals.get('earnings_yoy_3yr', 10)  # 3-year annual growth
    
    # New highs (relative strength)
    relative_strength = fundamentals.get('relative_strength', 50)
    
    # Volume trend
    avg_volume = fundamentals.get('avg_daily_volume', 1000000)
    recent_volume = fundamentals.get('recent_volume', avg_volume)
    volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
    
    # Industry group relative strength
    industry_rank = fundamentals.get('industry_rank', 50)  # 0-100
    
    # Institutional ownership trend
    inst_ownership = fundamentals.get('institutional_ownership', 30)
    inst_ownership_trend = fundamentals.get('inst_ownership_trend', 0)  # Increasing/decreasing
    
    # CAN SLIM scoring
    c_score = min(20, earnings_qoq / 50 * 20)
    a_score = min(15, earnings_yoy_3yr / 30 * 15)
    n_score = min(15, (relative_strength / 100 * 10) + (volume_ratio * 5))
    s_score = min(10, (1 / min(volume_ratio, 3) * 5))  # Lower supply, higher score
    l_score = min(15, industry_rank / 100 * 15)
    i_score = min(15, (inst_ownership / 50 * 10) + (inst_ownership_trend > 0) * 5)
    m_score = min(10, fundamentals.get('market_timing_score', 50) / 100 * 10)
    
    can_slim_score = c_score + a_score + n_score + s_score + l_score + i_score + m_score
    
    reasoning = []
    if earnings_qoq > 25:
        reasoning.append(f"Strong quarterly earnings ({earnings_qoq:.0f}% YoY)")
    if earnings_yoy_3yr > 25:
        reasoning.append(f"3-year annual growth {earnings_yoy_3yr:.0f}% - A in CAN SLIM")
    if relative_strength > 80:
        reasoning.append(f"Strong relative strength ({relative_strength:.0f}) - leading stock")
    if volume_ratio > 1.5:
        reasoning.append(f"High volume surge ({volume_ratio:.1f}x avg) - accumulation")
    if industry_rank > 70:
        reasoning.append(f"Top industry performer ({industry_rank:.0th} percentile)")
    if inst_ownership_trend > 0:
        reasoning.append("Increasing institutional ownership - smart money buying")
    
    signal = "BUY" if can_slim_score > 65 else "HOLD" if can_slim_score > 45 else "SELL"
    confidence = min(0.85, can_slim_score / 100 * 0.8 + 0.15)
    
    return LegendarySignal(
        investor="William O'Neil",
        style=InvestorStyle.ONEIL,
        signal=signal,
        confidence=confidence,
        score=int(can_slim_score),
        pe_ratio=fundamentals.get('pe', 25),
        growth_rate=earnings_yoy_3yr,
        moat_score=can_slim_score,
        reasoning=reasoning,
        metrics={
            'c_score': c_score,
            'a_score': a_score,
            'n_score': n_score,
            'l_score': l_score,
            'i_score': i_score,
            'm_score': m_score,
            'relative_strength': relative_strength,
            'industry_rank': industry_rank
        }
    )


# ============ MAIN ORCHESTRATOR ============

def analyze_with_all_legendary(
    prices: List[float],
    fundamentals: Dict[str, float] = None,
    market_data: Dict[str, float] = None
) -> LegendaryConsensus:
    """
    Run all legendary investor strategies and generate consensus
    
    Args:
        prices: List of historical prices
        fundamentals: Dict of fundamental metrics
        market_data: Dict of market data (macro indicators)
    
    Returns:
        LegendaryConsensus with aggregated signals
    """
    if fundamentals is None:
        fundamentals = {}
    if market_data is None:
        market_data = {}
    
    # Generate signals from all strategies
    signals = [
        buffett_style(prices, fundamentals, market_data),
        lynch_style(prices, fundamentals, market_data),
        graham_style(prices, fundamentals, market_data),
        soros_style(prices, fundamentals, market_data),
        dalio_style(prices, fundamentals, market_data),
        burry_style(prices, fundamentals, market_data),
        fisher_style(prices, fundamentals, market_data),
        templeton_style(prices, fundamentals, market_data),
        greenblatt_style(prices, fundamentals, market_data),
        oneil_style(prices, fundamentals, market_data),
    ]
    
    # Calculate consensus
    buy_signals = sum(1 for s in signals if s.signal == "BUY")
    sell_signals = sum(1 for s in signals if s.signal == "SELL")
    hold_signals = sum(1 for s in signals if s.signal == "HOLD")
    
    total = len(signals)
    
    if buy_signals == total:
        final_signal = "STRONG_BUY"
        consensus_level = "unanimous"
    elif buy_signals >= total * 0.7:
        final_signal = "BUY"
        consensus_level = "majority"
    elif sell_signals == total:
        final_signal = "STRONG_SELL"
        consensus_level = "unanimous"
    elif sell_signals >= total * 0.7:
        final_signal = "SELL"
        consensus_level = "majority"
    elif buy_signals > sell_signals:
        final_signal = "BUY"
        consensus_level = "divided"
    elif sell_signals > buy_signals:
        final_signal = "SELL"
        consensus_level = "divided"
    else:
        final_signal = "HOLD"
        consensus_level = "divided"
    
    # Weighted confidence (more weight to higher conviction signals)
    weighted_confidence = sum(s.confidence * (s.score / 100) for s in signals) / total
    
    # Wisdom of crowds (diversity of opinion = higher confidence)
    opinion_diversity = 1 - (max(buy_signals, sell_signals, hold_signals) / total)
    wisdom_of_crowds = (weighted_confidence + opinion_diversity) / 2
    
    # Best and worst investors
    best_investor = max(signals, key=lambda s: s.score).investor
    worst_investor = min(signals, key=lambda s: s.score).investor
    
    # Average score
    avg_score = sum(s.score for s in signals) / total
    
    return LegendaryConsensus(
        final_signal=final_signal,
        confidence=wisdom_of_crowds,
        score=int(avg_score),
        investor_signals=signals,
        consensus_level=consensus_level,
        wisdom_of_crowds=wisdom_of_crowds,
        best_investor=best_investor,
        worst_investor=worst_investor
    )


# ============ CONVENIENCE FUNCTIONS ============

def get_fundamentals_from_price(prices: List[float]) -> Dict[str, float]:
    """
    Estimate fundamental metrics from price data
    (For demonstration - real analysis needs actual fundamentals)
    """
    prices_array = np.array(prices)
    returns = np.diff(prices_array) / prices_array[:-1]
    
    # Estimate metrics based on price behavior
    volatility = np.std(returns) * np.sqrt(252)
    momentum_1y = (prices_array[-1] / prices_array[-252] - 1) if len(prices_array) >= 252 else 0
    
    # Generate reasonable estimates for demo
    fundamentals = {
        'pe': np.random.uniform(10, 30),
        'roe': np.random.uniform(8, 25),
        'profit_margin': np.random.uniform(5, 25),
        'debt_equity': np.random.uniform(0.1, 1.0),
        'fcf_yield': np.random.uniform(2, 8),
        'growth': np.random.uniform(3, 15),
        'dividend_yield': np.random.uniform(0, 5),
        'revenue_growth': np.random.uniform(2, 20),
    }
    
    return fundamentals


# ============ TEST ============

if __name__ == "__main__":
    import pandas as pd
    import numpy as np
    
    # Generate sample data
    np.random.seed(42)
    n = 500
    prices = list(np.cumsum(np.random.randn(n) * 2) + 100)
    
    fundamentals = {
        'pe': 18,
        'roe': 18,
        'profit_margin': 15,
        'debt_equity': 0.4,
        'fcf_yield': 5,
        'growth': 10,
        'dividend_yield': 2.5,
        'revenue_growth': 12,
        'eps': 5,
        'book_value': 50,
        'current_ratio': 2.5,
        'pb_ratio': 2,
    }
    
    market_data = {
        'inflation': 3.5,
        'interest_rate': 5.25,
    }
    
    print("=" * 70)
    print("🏆 LEGENDARY INVESTORS STRATEGY ANALYSIS")
    print("=" * 70)
    
    # Run analysis
    result = analyze_with_all_legendary(prices, fundamentals, market_data)
    
    print(f"\n📊 CONSENSUS: {result.final_signal}")
    print(f"📈 CONFIDENCE: {result.confidence:.0%}")
    print(f"🎯 WISDOM OF CROWDS: {result.wisdom_of_crowds:.0%}")
    print(f"📋 CONSENSUS LEVEL: {result.consensus_level}")
    
    print(f"\n🏅 BEST STRATEGY: {result.best_investor} ({max(result.investor_signals, key=lambda s: s.score).score}/100)")
    print(f"⚠️  WORST STRATEGY: {result.worst_investor} ({min(result.investor_signals, key=lambda s: s.score).score}/100)")
    
    print(f"\n{'='*70}")
    print("INDIVIDUAL INVESTOR SIGNALS")
    print("=" * 70)
    
    for signal in result.investor_signals:
        emoji = {"BUY": "🟢", "SELL": "🔴", "HOLD": "🟡"}[signal.signal]
        print(f"\n{emoji} {signal.investor:20s} | {signal.signal:4s} | {signal.score:3d}/100 | {signal.confidence:.0%}")
        if signal.reasoning:
            print(f"   💡 {signal.reasoning[0]}")
    
    print(f"\n{'='*70}")
