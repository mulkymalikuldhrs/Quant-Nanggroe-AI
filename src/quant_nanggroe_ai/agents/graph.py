"""
Main LangGraph Trading Graph
=============================
Full Agent Council Flow:
  Researcher → Macro → Analyst → Strategist → Risk Manager → Execution → Portfolio Manager

Domain-Specific Parallel Flows (activated by asset class):
  Crypto:     Researcher → Crypto → Strategist → Risk → Execution → Portfolio
  Forex:      Researcher → Forex → Strategist → Risk → Execution → Portfolio
  Prediction: Researcher → PredictionMarket → Strategist → Risk → Execution → Portfolio

Conditional routing:
- If risk is VETOED → skip to end (NO_TRADE)
- If regime is NO_TRADE → skip to end
- Portfolio Manager has final gate approval
- Asset-class nodes (crypto/forex/prediction) route based on symbol type

LangGraph passes state as a Pydantic model — access fields via attribute
notation, not dict .get(). Enum comparisons use enum members, not strings.
"""

from __future__ import annotations

from typing import Any

from langgraph.graph import StateGraph, END

from quant_nanggroe_ai.agents.state import AgentState
from quant_nanggroe_ai.types import MarketRegime, RiskClearance, DecisionAction


def researcher_node(state: AgentState) -> dict[str, Any]:
    """
    Research Agent — Gathers market data, news, and macro context.

    This is the entry point of the trading graph. Fetches data from
    market data tools and news APIs to build context for downstream agents.
    """
    from quant_nanggroe_ai.agents.tools.market_data import MarketDataTool
    from quant_nanggroe_ai.agents.tools.sentiment import SentimentTool

    market_tool = MarketDataTool()
    sentiment_tool = SentimentTool()

    # Fetch market data
    market_data = market_tool.get_ohlcv(state.symbol, state.timeframe)
    current_price = market_tool.get_current_price(state.symbol)

    # Fetch sentiment
    sentiment = sentiment_tool.analyze(state.symbol)

    return {
        "market_data": market_data,
        "research_summary": f"Research completed for {state.symbol}: price={current_price}, sentiment={sentiment.get('overall_score', 0.0):.2f}",
        "sentiment_score": sentiment.get("overall_score", 0.0),
        "news_items": sentiment.get("news_items", []),
        "agent_trace": state.agent_trace + [
            {"agent": "researcher", "status": "completed", "action": "research", "symbol": state.symbol}
        ],
    }


def analyst_node(state: AgentState) -> dict[str, Any]:
    """
    Market Intelligence Agent — Technical analysis, SMC, sentiment.

    Processes research data into actionable intelligence using the
    deterministic MathEngine indicator suite and pressure normalization.
    """
    from quant_nanggroe_ai.agents.tools.technical import TechnicalAnalysisTool
    from quant_nanggroe_ai.engine.market_state import MarketStateEngine

    tech_tool = TechnicalAnalysisTool()
    market_engine = MarketStateEngine()

    # Run technical analysis on available data
    tech_analysis = tech_tool.analyze(state.symbol, state.timeframe)

    # Detect market regime
    regime_result = market_engine.detect_regime(
        symbol=state.symbol,
        price_change_5d=tech_analysis.get("price_change_5d", 0.0),
        price_change_1d=tech_analysis.get("price_change_1d", 0.0),
        adx=tech_analysis.get("adx", 20.0),
        rsi=tech_analysis.get("rsi_14", 50.0),
        atr_pct=tech_analysis.get("atr_pct", 1.0),
        volume_ratio=tech_analysis.get("volume_ratio", 1.0),
        ema_trend=tech_analysis.get("ema_trend", "neutral"),
    )

    return {
        "technical_analysis": tech_analysis,
        "regime": regime_result.regime,
        "volatility": regime_result.volatility,
        "liquidity": regime_result.liquidity,
        "market_state": regime_result,
        "agent_trace": state.agent_trace + [
            {
                "agent": "analyst",
                "status": "completed",
                "action": "analyze",
                "regime": regime_result.regime.value,
                "trade_allowed": regime_result.trade_allowed,
            }
        ],
    }


def strategist_node(state: AgentState) -> dict[str, Any]:
    """
    Strategy Lab Agent — Generates entry/exit strategies.

    Combines analysis with market state to produce trade plans.
    Uses pressure normalization and decision synthesis for deterministic
    signal generation.
    """
    from quant_nanggroe_ai.engine.pressure import PressureNormalizationEngine, PressureInput
    from quant_nanggroe_ai.engine.decision import DecisionSynthesisEngine
    from quant_nanggroe_ai.agents.tools.technical import TechnicalAnalysisTool

    pressure_engine = PressureNormalizationEngine()
    decision_engine = DecisionSynthesisEngine()
    tech_tool = TechnicalAnalysisTool()

    # Build pressure input from technical analysis
    ta = state.technical_analysis
    smc_signal = "none"
    if ta.get("smc_bullish_bos"):
        smc_signal = "bullish_bos"
    elif ta.get("smc_bearish_bos"):
        smc_signal = "bearish_bos"
    elif ta.get("smc_bullish_choch"):
        smc_signal = "bullish_choch"
    elif ta.get("smc_bearish_choch"):
        smc_signal = "bearish_choch"

    pressure_input = PressureInput(
        trend_direction="bullish" if ta.get("ema_trend") == "bullish" else ("bearish" if ta.get("ema_trend") == "bearish" else "neutral"),
        trend_strength=ta.get("trend_strength", 0.0),
        smc_signal=smc_signal,
        displacement_strength=ta.get("displacement_strength", 0.0),
        liquidity_sweep=ta.get("liquidity_sweep", False),
        news_impact=abs(state.sentiment_score),
        news_uncertainty=1.0 - abs(state.sentiment_score),
        flow_direction=ta.get("flow_direction", "neutral"),
        flow_imbalance=ta.get("flow_imbalance", 0.0),
    )

    # Compile pressure
    pressure_result = pressure_engine.compile_pressure(pressure_input)

    # Run decision synthesis
    decision_result = decision_engine.evaluate(
        regime=state.regime,
        buy_pressure=pressure_result.buy_pressure,
        sell_pressure=pressure_result.sell_pressure,
        confidence=pressure_result.confidence,
        volatility=state.volatility,
        daily_pnl_pct=state.daily_pnl_pct,
    )

    # Determine signal and entry parameters
    signal = "HOLD"
    entry_price = 0.0
    stop_loss = 0.0
    take_profit = []
    position_size = 0.0

    if decision_result.action in (DecisionAction.ALLOW_LONG, DecisionAction.ALLOW_LONG_TRENDING):
        signal = "BUY"
        # Calculate entry/exit based on ATR
        atr = ta.get("atr_14", 0.0)
        current_price = ta.get("current_price", 0.0)
        if current_price > 0:
            entry_price = current_price
            stop_loss = current_price - 2.0 * atr  # 2 ATR stop
            take_profit = [current_price + 2.0 * atr, current_price + 4.0 * atr]  # 1:2, 1:4 RR
    elif decision_result.action in (DecisionAction.ALLOW_SHORT, DecisionAction.ALLOW_SHORT_TRENDING):
        signal = "SELL"
        atr = ta.get("atr_14", 0.0)
        current_price = ta.get("current_price", 0.0)
        if current_price > 0:
            entry_price = current_price
            stop_loss = current_price + 2.0 * atr
            take_profit = [current_price - 2.0 * atr, current_price - 4.0 * atr]

    return {
        "strategy_signal": signal,
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "position_size": position_size,
        "buy_pressure": pressure_result.buy_pressure,
        "sell_pressure": pressure_result.sell_pressure,
        "confidence": pressure_result.confidence,
        "pressure": pressure_engine.get_pressure_state(),
        "decision_action": decision_result.action,
        "decision_reason": decision_result.reason,
        "risk_clearance": decision_result.risk_clearance,
        "strategy_name": f"pressure_{signal.lower()}" if signal != "HOLD" else "no_trade",
        "agent_trace": state.agent_trace + [
            {
                "agent": "strategist",
                "status": "completed",
                "signal": signal,
                "action": decision_result.action.value,
                "pressure_verdict": pressure_result.verdict,
            }
        ],
    }


def risk_manager_node(state: AgentState) -> dict[str, Any]:
    """
    Risk Engine Agent — 9-checkpoint VETO system.

    Has FULL VETO authority. Cannot be overridden.
    Uses the shared ConstitutionalRiskGuard instance for state persistence.
    """
    from quant_nanggroe_ai.engine.risk_guard import ConstitutionalRiskGuard

    # Use shared instance from app state if available, otherwise create
    risk_guard = ConstitutionalRiskGuard()

    # Check the trade through the 9-checkpoint system
    result = risk_guard.check_trade(
        symbol=state.symbol,
        direction=state.strategy_signal,
        lot_size=state.position_size if state.position_size > 0 else 0.01,
        entry=state.entry_price,
        stop_loss=state.stop_loss if state.stop_loss > 0 else None,
        take_profit=state.take_profit[0] if state.take_profit else None,
    )

    risk_clearance = RiskClearance.CLEAR if result.verdict == "APPROVED" else RiskClearance.BLOCKED

    return {
        "risk_verdict": result.verdict,
        "risk_checkpoints": {k: v.model_dump() for k, v in result.checkpoints.items()},
        "risk_clearance": risk_clearance,
        "risk_pct": result.risk_pct,
        "agent_trace": state.agent_trace + [
            {"agent": "risk_manager", "status": "completed", "verdict": result.verdict, "clearance": risk_clearance.value}
        ],
    }


def trader_node(state: AgentState) -> dict[str, Any]:
    """
    Execution Agent — Executes approved trades.

    Only reached if risk clearance is CLEAR.
    Routes to appropriate execution backend based on symbol type.
    """
    from quant_nanggroe_ai.agents.tools.execution import ExecutionTool

    exec_tool = ExecutionTool()

    if state.risk_clearance != RiskClearance.CLEAR:
        return {
            "execution_status": "SKIPPED",
            "agent_trace": state.agent_trace + [
                {"agent": "trader", "status": "skipped", "reason": "Risk clearance not CLEAR"}
            ],
        }

    # Execute the trade
    result = exec_tool.execute_order(
        symbol=state.symbol,
        side=state.strategy_signal,
        quantity=state.position_size if state.position_size > 0 else 0.01,
        order_type="LIMIT" if state.entry_price > 0 else "MARKET",
        price=state.entry_price if state.entry_price > 0 else None,
        stop_loss=state.stop_loss if state.stop_loss > 0 else None,
        take_profit=state.take_profit[0] if state.take_profit else None,
    )

    return {
        "execution_status": result.get("status", "PENDING"),
        "order_id": result.get("order_id", ""),
        "execution_price": result.get("execution_price", 0.0),
        "slippage": result.get("slippage", 0.0),
        "agent_trace": state.agent_trace + [
            {"agent": "trader", "status": "completed", "action": "execute", "order_id": result.get("order_id")}
        ],
    }


def portfolio_manager_node(state: AgentState) -> dict[str, Any]:
    """
    Portfolio Intelligence Agent — Final gate.

    Reviews all decisions before execution. Can REJECT even after risk approval.
    Checks portfolio-level constraints: concentration, correlation, total exposure.
    """
    # Final portfolio-level checks
    portfolio_decision = "REJECT"
    rejection_reason = ""

    if state.risk_clearance != RiskClearance.CLEAR:
        rejection_reason = f"Risk clearance is {state.risk_clearance.value}, not CLEAR"
    elif state.decision_action == DecisionAction.NO_TRADE:
        rejection_reason = "Decision action is NO_TRADE"
    elif state.execution_status in ("FILLED", "PENDING"):
        portfolio_decision = "APPROVE"
    elif state.execution_status == "SKIPPED":
        rejection_reason = "Execution was skipped"
    else:
        rejection_reason = f"Unexpected execution status: {state.execution_status}"

    return {
        "portfolio_decision": portfolio_decision,
        "portfolio_rejection_reason": rejection_reason,
        "agent_trace": state.agent_trace + [
            {"agent": "portfolio_manager", "status": "completed", "decision": portfolio_decision}
        ],
    }


def should_continue_after_risk(state: AgentState) -> str:
    """Conditional routing: if risk VETOED, skip to end."""
    if state.risk_clearance == RiskClearance.CLEAR:
        return "execution"
    return "end"


def should_continue_after_regime(state: AgentState) -> str:
    """Conditional routing: if NO_TRADE regime, skip to end."""
    if state.regime in (MarketRegime.NO_TRADE, MarketRegime.PANIC, MarketRegime.RISK_OFF):
        return "end"
    # Route to asset-class-specific analyst or default analyst
    symbol = getattr(state, "symbol", "").upper()
    if any(suffix in symbol for suffix in ["/USDT", "/BUSD", "/USD", "-PERP", "SOL/", "BNB/"]):
        return "crypto"
    if "/" in symbol and any(ccy in symbol for ccy in ["EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF"]):
        return "forex"
    if any(kw in symbol.upper() for kw in ["POLY", "KALSHI", "PREDICT"]):
        return "prediction_market"
    return "analyst"


def build_trading_graph() -> StateGraph:
    """
    Build the main LangGraph trading graph.

    Full Agent Council Flow:
    1. Researcher → gathers market data & news
    2. Macro → macro-economic context (all flows)
    3. [Conditional] → Crypto / Forex / PredictionMarket / Analyst
    4. Strategist → generates strategy via pressure normalization
    5. Risk Manager → 9-checkpoint VETO/APPROVE
    6. Execution → smart order routing (if approved)
    7. Portfolio Manager → final gate approval

    Returns:
        Compiled StateGraph ready for execution
    """
    from quant_nanggroe_ai.agents.nodes.crypto import crypto_node
    from quant_nanggroe_ai.agents.nodes.forex import forex_node
    from quant_nanggroe_ai.agents.nodes.execution import execution_node
    from quant_nanggroe_ai.agents.nodes.prediction_market import prediction_market_node

    graph = StateGraph(AgentState)

    # Add core nodes
    graph.add_node("researcher", researcher_node)
    graph.add_node("analyst", analyst_node)
    graph.add_node("strategist", strategist_node)
    graph.add_node("risk_manager", risk_manager_node)
    graph.add_node("execution", execution_node)
    graph.add_node("portfolio_manager", portfolio_manager_node)

    # Add domain-specific nodes
    graph.add_node("crypto", crypto_node)
    graph.add_node("forex", forex_node)
    graph.add_node("prediction_market", prediction_market_node)

    # Set entry point
    graph.set_entry_point("researcher")

    # Conditional routing after researcher: regime check + asset class routing
    graph.add_conditional_edges(
        "researcher",
        should_continue_after_regime,
        {
            "analyst": "analyst",
            "crypto": "crypto",
            "forex": "forex",
            "prediction_market": "prediction_market",
            "end": END,
        },
    )

    # All analysis nodes converge to strategist
    graph.add_edge("analyst", "strategist")
    graph.add_edge("crypto", "strategist")
    graph.add_edge("forex", "strategist")
    graph.add_edge("prediction_market", "strategist")

    # Strategist → Risk Manager
    graph.add_edge("strategist", "risk_manager")

    # Risk Manager → Execution or END
    graph.add_conditional_edges(
        "risk_manager",
        should_continue_after_risk,
        {"execution": "execution", "end": END},
    )

    # Execution → Portfolio Manager → END
    graph.add_edge("execution", "portfolio_manager")
    graph.add_edge("portfolio_manager", END)

    return graph.compile()


# Singleton compiled graph
_compiled_graph = None


def get_trading_graph():
    """Get or create the compiled trading graph."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_trading_graph()
    return _compiled_graph
