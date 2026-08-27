"""Financial prompt templates for NVIDIA NIM inference.

Structured prompt templates for quantitative trading tasks including
market analysis, strategy generation, risk assessment, portfolio
rebalancing, sentiment analysis, trade execution decisions, and
backtest result interpretation.

Each template function returns a ``(system_prompt, user_prompt)`` tuple
or a single formatted user prompt string, designed for optimal
performance with NVIDIA NIM models.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# System prompts (shared across task types)
# ---------------------------------------------------------------------------

FINANCIAL_ANALYST_SYSTEM = (
    "You are a senior quantitative financial analyst with expertise in "
    "equity markets, derivatives, macro-economics, and algorithmic trading. "
    "Provide precise, data-driven analysis. Use specific numbers and "
    "percentages. Always cite data sources when possible. Avoid vague "
    "statements. Structure your response with clear sections."
)

STRATEGIST_SYSTEM = (
    "You are an elite quantitative strategy designer. You create "
    "systematic, rule-based trading strategies with clearly defined "
    "entry/exit signals, position sizing rules, and risk management "
    "constraints. Every strategy must be backtestable. Specify parameters "
    "as exact numeric values. Include edge cases and failure modes."
)

RISK_ANALYST_SYSTEM = (
    "You are a senior risk management analyst specializing in "
    "portfolio risk, market risk, and operational risk for quantitative "
    "trading systems. You are conservative and thorough. Always quantify "
    "risk in numeric terms (VaR, CVaR, max drawdown, correlation). "
    "Flag any scenario where constitutional risk limits could be breached."
)

SENTIMENT_ANALYST_SYSTEM = (
    "You are a financial sentiment analysis expert. Analyze text for "
    "market sentiment (bearish, neutral, bullish) with a confidence "
    "score from -1.0 to +1.0. Consider context, source credibility, "
    "and potential market impact. Be concise and structured."
)

CODE_GENERATOR_SYSTEM = (
    "You are a quantitative Python developer. Write clean, type-annotated "
    "Python 3.12+ code using pandas, numpy, and standard quantitative "
    "libraries. Follow PEP 8. Include docstrings. Prefer vectorised "
    "operations over loops. Handle edge cases and include input validation."
)


# ---------------------------------------------------------------------------
# Market Analysis
# ---------------------------------------------------------------------------

def market_analysis_prompt(
    symbol: str,
    current_price: float,
    period_data: str,
    additional_context: Optional[str] = None,
) -> tuple[str, str]:
    """Generate a market analysis prompt.

    Args:
        symbol: Ticker symbol (e.g. 'AAPL').
        current_price: Current market price.
        period_data: Recent market data summary (OHLCV, indicators).
        additional_context: Extra context (earnings, news, etc.).

    Returns:
        (system_prompt, user_prompt) tuple.
    """
    user = (
        f"Analyze the current market conditions for {symbol}.\n\n"
        f"**Current Price**: ${current_price:.2f}\n\n"
        f"**Recent Data**:\n{period_data}\n\n"
    )
    if additional_context:
        user += f"**Additional Context**:\n{additional_context}\n\n"

    user += (
        "Provide:\n"
        "1. **Trend Assessment** — Current trend direction and strength\n"
        "2. **Support/Resistance** — Key price levels\n"
        "3. **Momentum Signals** — Overbought/oversold, divergence\n"
        "4. **Volatility Assessment** — Current and expected volatility\n"
        "5. **Risk/Reward** — Asymmetric opportunity assessment\n"
        "6. **Actionable Signal** — BUY / SELL / HOLD with confidence (0-100%)"
    )
    return FINANCIAL_ANALYST_SYSTEM, user


# ---------------------------------------------------------------------------
# Strategy Generation
# ---------------------------------------------------------------------------

def strategy_generation_prompt(
    universe: List[str],
    strategy_type: str,
    risk_constraints: Optional[Dict[str, Any]] = None,
    performance_target: Optional[Dict[str, Any]] = None,
) -> tuple[str, str]:
    """Generate a strategy design prompt.

    Args:
        universe: List of ticker symbols.
        strategy_type: Type of strategy (e.g. 'mean_reversion', 'momentum').
        risk_constraints: Risk limits (max_drawdown, max_position_size, etc.).
        performance_target: Target metrics (sharpe_ratio, annual_return, etc.).

    Returns:
        (system_prompt, user_prompt) tuple.
    """
    risk_str = ""
    if risk_constraints:
        risk_str = "\n".join(f"- {k}: {v}" for k, v in risk_constraints.items())

    target_str = ""
    if performance_target:
        target_str = "\n".join(f"- {k}: {v}" for k, v in performance_target.items())

    user = (
        f"Design a systematic {strategy_type} trading strategy.\n\n"
        f"**Universe**: {', '.join(universe)}\n\n"
        f"**Strategy Type**: {strategy_type}\n\n"
    )
    if risk_str:
        user += f"**Risk Constraints**:\n{risk_str}\n\n"
    if target_str:
        user += f"**Performance Targets**:\n{target_str}\n\n"

    user += (
        "Define:\n"
        "1. **Entry Signal** — Exact conditions with parameters\n"
        "2. **Exit Signal** — Take-profit and stop-loss rules\n"
        "3. **Position Sizing** — Capital allocation formula\n"
        "4. **Filters** — Regime/volatility filters\n"
        "5. **Risk Management** — Max position, correlation check\n"
        "6. **Expected Metrics** — Estimated Sharpe, max drawdown, win rate"
    )
    return STRATEGIST_SYSTEM, user


# ---------------------------------------------------------------------------
# Risk Assessment
# ---------------------------------------------------------------------------

def risk_assessment_prompt(
    portfolio_state: Dict[str, Any],
    proposed_trade: Optional[Dict[str, Any]] = None,
    market_conditions: Optional[str] = None,
) -> tuple[str, str]:
    """Generate a risk assessment prompt.

    Args:
        portfolio_state: Current portfolio (positions, equity, P&L).
        proposed_trade: Optional trade to evaluate before execution.
        market_conditions: Current market regime and conditions.

    Returns:
        (system_prompt, user_prompt) tuple.
    """
    user = (
        "Assess the current portfolio risk profile.\n\n"
        f"**Portfolio State**:\n{_format_dict(portfolio_state)}\n\n"
    )
    if proposed_trade:
        user += (
            f"**Proposed Trade**:\n{_format_dict(proposed_trade)}\n\n"
        )
    if market_conditions:
        user += f"**Market Conditions**: {market_conditions}\n\n"

    user += (
        "Evaluate:\n"
        "1. **Portfolio VaR** — 1-day 95% and 99% VaR\n"
        "2. **Concentration Risk** — Position concentration analysis\n"
        "3. **Correlation Risk** — Cross-asset correlation concerns\n"
        "4. **Drawdown Risk** — Current and projected drawdown\n"
        "5. **Liquidity Risk** — Ability to exit positions\n"
        "6. **Constitutional Compliance** — Are risk limits being respected?\n"
        "7. **Trade Approval** — APPROVE / REJECT the proposed trade (if any)"
    )
    return RISK_ANALYST_SYSTEM, user


# ---------------------------------------------------------------------------
# Portfolio Rebalancing
# ---------------------------------------------------------------------------

def portfolio_rebalancing_prompt(
    current_allocation: Dict[str, float],
    target_allocation: Dict[str, float],
    total_equity: float,
    constraints: Optional[Dict[str, Any]] = None,
) -> tuple[str, str]:
    """Generate a portfolio rebalancing prompt.

    Args:
        current_allocation: Current weights by asset.
        target_allocation: Target weights by asset.
        total_equity: Total portfolio equity in USD.
        constraints: Rebalancing constraints (min_trade, tax, etc.).

    Returns:
        (system_prompt, user_prompt) tuple.
    """
    user = (
        f"Generate a portfolio rebalancing plan.\n\n"
        f"**Current Allocation**:\n{_format_dict(current_allocation)}\n\n"
        f"**Target Allocation**:\n{_format_dict(target_allocation)}\n\n"
        f"**Total Equity**: ${total_equity:,.2f}\n\n"
    )
    if constraints:
        user += f"**Constraints**:\n{_format_dict(constraints)}\n\n"

    user += (
        "Provide:\n"
        "1. **Required Trades** — Exact buy/sell orders with quantities\n"
        "2. **Estimated Transaction Costs** — Commission + slippage\n"
        "3. **Drift Analysis** — How far from target allocation\n"
        "4. **Rebalancing Priority** — Which trades to execute first\n"
        "5. **Tax Impact** — Short-term vs long-term capital gains\n"
        "6. **Risk Impact** — Change in portfolio risk metrics"
    )
    return FINANCIAL_ANALYST_SYSTEM, user


# ---------------------------------------------------------------------------
# Sentiment Analysis
# ---------------------------------------------------------------------------

def sentiment_analysis_prompt(
    text: str,
    context: Optional[str] = None,
    assets: Optional[List[str]] = None,
) -> tuple[str, str]:
    """Generate a sentiment analysis prompt.

    Args:
        text: News article, social media post, or report text.
        context: Additional context (earnings date, sector, etc.).
        assets: Relevant ticker symbols.

    Returns:
        (system_prompt, user_prompt) tuple.
    """
    user = "Analyze the sentiment of the following financial text.\n\n"
    user += f"**Text**:\n{text}\n\n"
    if context:
        user += f"**Context**: {context}\n\n"
    if assets:
        user += f"**Related Assets**: {', '.join(assets)}\n\n"

    user += (
        "Output in JSON format:\n"
        "```json\n"
        "{\n"
        '  "overall_sentiment": "bullish|neutral|bearish",\n'
        '  "confidence_score": -1.0 to 1.0,\n'
        '  "key_topics": ["topic1", "topic2"],\n'
        '  "affected_assets": {\n'
        '    "SYMBOL": {"direction": "bullish|bearish|neutral", "impact": "high|medium|low"}\n'
        "  },\n"
        '  "time_horizon": "immediate|short_term|medium_term|long_term",\n'
        '  "reasoning": "Brief explanation"\n'
        "}\n"
        "```"
    )
    return SENTIMENT_ANALYST_SYSTEM, user


# ---------------------------------------------------------------------------
# Trade Execution Decision
# ---------------------------------------------------------------------------

def trade_execution_prompt(
    signal: Dict[str, Any],
    current_position: Optional[Dict[str, Any]] = None,
    market_state: Optional[Dict[str, Any]] = None,
    risk_budget: Optional[Dict[str, Any]] = None,
) -> tuple[str, str]:
    """Generate a trade execution decision prompt.

    Args:
        signal: Trading signal (symbol, direction, strength, etc.).
        current_position: Current position in the symbol.
        market_state: Current market state (regime, volatility, etc.).
        risk_budget: Available risk budget (remaining daily/weekly loss).

    Returns:
        (system_prompt, user_prompt) tuple.
    """
    user = (
        f"Decide whether to execute this trade signal.\n\n"
        f"**Signal**:\n{_format_dict(signal)}\n\n"
    )
    if current_position:
        user += f"**Current Position**:\n{_format_dict(current_position)}\n\n"
    if market_state:
        user += f"**Market State**:\n{_format_dict(market_state)}\n\n"
    if risk_budget:
        user += f"**Risk Budget**:\n{_format_dict(risk_budget)}\n\n"

    user += (
        "Decide:\n"
        "1. **EXECUTE / SKIP / DEFER** — Clear recommendation\n"
        "2. **Position Size** — Recommended number of shares/contracts\n"
        "3. **Entry Price** — Limit price or market order recommendation\n"
        "4. **Stop Loss** — Exact stop-loss price and percentage\n"
        "5. **Take Profit** — Target exit price(s)\n"
        "6. **Risk/Reward Ratio** — Quantified asymmetric opportunity\n"
        "7. **Confidence** — 0-100% confidence in this trade\n"
        "8. **Conditions** — Any conditions that would invalidate this trade"
    )
    return RISK_ANALYST_SYSTEM, user


# ---------------------------------------------------------------------------
# Backtest Result Interpretation
# ---------------------------------------------------------------------------

def backtest_interpretation_prompt(
    strategy_name: str,
    metrics: Dict[str, Any],
    equity_curve_summary: str,
    trade_statistics: Optional[Dict[str, Any]] = None,
    comparison: Optional[Dict[str, Any]] = None,
) -> tuple[str, str]:
    """Generate a backtest result interpretation prompt.

    Args:
        strategy_name: Name of the strategy tested.
        metrics: Backtest metrics (Sharpe, max DD, CAGR, etc.).
        equity_curve_summary: Summary of the equity curve behaviour.
        trade_statistics: Win rate, avg win/loss, etc.
        comparison: Benchmark comparison metrics.

    Returns:
        (system_prompt, user_prompt) tuple.
    """
    user = (
        f"Interpret these backtest results for strategy '{strategy_name}'.\n\n"
        f"**Key Metrics**:\n{_format_dict(metrics)}\n\n"
        f"**Equity Curve Summary**: {equity_curve_summary}\n\n"
    )
    if trade_statistics:
        user += f"**Trade Statistics**:\n{_format_dict(trade_statistics)}\n\n"
    if comparison:
        user += f"**Benchmark Comparison**:\n{_format_dict(comparison)}\n\n"

    user += (
        "Provide:\n"
        "1. **Overall Assessment** — Is this strategy viable for live trading?\n"
        "2. **Strengths** — What works well\n"
        "3. **Weaknesses** — Areas of concern\n"
        "4. **Regime Dependency** — Does performance vary by market regime?\n"
        "5. **Risk Adjusted Quality** — Sharpe, Sortino, Calmar assessment\n"
        "6. **Overfitting Risk** — Signs of curve-fitting or data mining bias\n"
        "7. **Recommended Improvements** — Specific, actionable changes\n"
        "8. **Go/No-Go Recommendation** — With confidence level"
    )
    return STRATEGIST_SYSTEM, user


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _format_dict(d: Dict[str, Any], indent: int = 0) -> str:
    """Format a dictionary as a readable string for prompts."""
    lines: list[str] = []
    prefix = "  " * indent
    for k, v in d.items():
        if isinstance(v, dict):
            lines.append(f"{prefix}- {k}:")
            lines.append(_format_dict(v, indent + 1))
        elif isinstance(v, list):
            lines.append(f"{prefix}- {k}: [{', '.join(str(i) for i in v)}]")
        else:
            lines.append(f"{prefix}- {k}: {v}")
    return "\n".join(lines)


__all__ = [
    "FINANCIAL_ANALYST_SYSTEM",
    "STRATEGIST_SYSTEM",
    "RISK_ANALYST_SYSTEM",
    "SENTIMENT_ANALYST_SYSTEM",
    "CODE_GENERATOR_SYSTEM",
    "market_analysis_prompt",
    "strategy_generation_prompt",
    "risk_assessment_prompt",
    "portfolio_rebalancing_prompt",
    "sentiment_analysis_prompt",
    "trade_execution_prompt",
    "backtest_interpretation_prompt",
]
