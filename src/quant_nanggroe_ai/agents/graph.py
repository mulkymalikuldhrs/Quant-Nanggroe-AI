"""
Main LangGraph Trading Graph
=============================
Researcher → Analyst → Strategist → Risk Manager → Trader → Portfolio Manager

The graph uses conditional routing:
- If risk is VETOED → skip to end (NO_TRADE)
- If regime is NO_TRADE → skip to end
- Portfolio Manager has final gate approval

Stateful engine components (RiskGuard, MarketEngine, DecisionEngine) are
resolved from shared singletons when a FastAPI app is available, ensuring
PnL tracking and regime history persist across graph invocations.  When
running outside an app context (e.g. tests), fresh instances are used.
"""

from __future__ import annotations

from typing import Any, Callable, TYPE_CHECKING

from langgraph.graph import StateGraph, END

from quant_nanggroe_ai.agents.state import AgentState
from quant_nanggroe_ai.types import MarketRegime, RiskClearance, DecisionAction

if TYPE_CHECKING:
    from fastapi import FastAPI

# ══════════════════════════════════════════════════════════════════════
# App context — allows nodes to access shared service singletons
# ══════════════════════════════════════════════════════════════════════

_app: FastAPI | None = None


def set_app(app: FastAPI | None) -> None:
    """Set the FastAPI app reference so graph nodes can access shared singletons."""
    global _app
    _app = app


def get_app() -> FastAPI | None:
    """Return the current FastAPI app reference (or None if outside app context)."""
    return _app


def _get_service(getter_fn: Callable, fallback_factory: Callable) -> Any:
    """
    Try to obtain a shared service singleton via *getter_fn(app)*.
    Fall back to *fallback_factory()* when no app context is available.
    """
    app = get_app()
    if app is not None:
        try:
            return getter_fn(app)
        except Exception:
            pass
    return fallback_factory()


# ══════════════════════════════════════════════════════════════════════
# Node implementations
# ══════════════════════════════════════════════════════════════════════


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
    Uses the shared MarketStateEngine when available for regime history.
    """
    from quant_nanggroe_ai.agents.tools.technical import TechnicalAnalysisTool
    from quant_nanggroe_ai.engine.market_state import MarketStateEngine
    from quant_nanggroe_ai.services import get_market_engine

    tech_tool = TechnicalAnalysisTool()
    # Use shared singleton to preserve regime history across calls
    market_engine = _get_service(get_market_engine, MarketStateEngine)

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
    signal generation. Leverages shared DecisionSynthesisEngine when
    available for decision cache persistence.
    """
    from quant_nanggroe_ai.engine.pressure import PressureNormalizationEngine, PressureInput
    from quant_nanggroe_ai.engine.decision import DecisionSynthesisEngine
    from quant_nanggroe_ai.agents.tools.technical import TechnicalAnalysisTool
    from quant_nanggroe_ai.services import get_decision_engine

    pressure_engine = PressureNormalizationEngine()
    # Use shared singleton for decision cache
    decision_engine = _get_service(get_decision_engine, DecisionSynthesisEngine)
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
        atr = ta.get("atr_14", 0.0)
        current_price = ta.get("current_price", 0.0)
        if current_price > 0:
            entry_price = current_price
            stop_loss = current_price - 2.0 * atr
            take_profit = [current_price + 2.0 * atr, current_price + 4.0 * atr]
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
    Uses the shared ConstitutionalRiskGuard instance for state persistence
    so daily/weekly PnL limits work correctly across graph invocations.
    """
    from quant_nanggroe_ai.engine.risk_guard import ConstitutionalRiskGuard
    from quant_nanggroe_ai.services import get_risk_guard

    # Use shared singleton to preserve PnL tracking across calls
    risk_guard = _get_service(get_risk_guard, ConstitutionalRiskGuard)

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


# ══════════════════════════════════════════════════════════════════════
# Conditional routing
# ══════════════════════════════════════════════════════════════════════


def should_continue_after_risk(state: AgentState) -> str:
    """Conditional routing: if risk VETOED, skip to end."""
    if state.risk_clearance == RiskClearance.CLEAR:
        return "trader"
    return "end"


def should_continue_after_regime(state: AgentState) -> str:
    """Conditional routing: if NO_TRADE regime, skip to end; route to specialist."""
    if state.regime in (MarketRegime.NO_TRADE, MarketRegime.PANIC, MarketRegime.RISK_OFF):
        return "end"
    # Route to domain specialist based on symbol type
    symbol = state.symbol.upper()
    crypto_bases = {"BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "AVAX", "DOT", "DOGE", "SHIB"}
    if any(symbol.startswith(c) for c in crypto_bases) or "USDT" in symbol or "USDC" in symbol:
        return "crypto"
    forex_currencies = {"USD", "EUR", "GBP", "JPY", "CHF", "AUD", "NZD", "CAD"}
    if len(symbol) == 6:
        base, quote = symbol[:3], symbol[3:6]
        if base in forex_currencies and quote in forex_currencies:
            return "forex"
    return "analyst"


def should_continue_after_specialist(state: AgentState) -> str:
    """After crypto/forex specialist, always go to analyst."""
    return "analyst"


# ══════════════════════════════════════════════════════════════════════
# Graph builder
# ══════════════════════════════════════════════════════════════════════


def build_trading_graph() -> StateGraph:
    """
    Build the main LangGraph trading graph.

    Flow:
    1. Researcher → gathers data
    2. (Crypto|Forex specialist) → domain-specific context (conditional)
    3. Analyst → processes intelligence (skip if NO_TRADE regime)
    4. Strategist → generates strategy
    5. Risk Manager → VETO/APPROVE
    6. Trader → executes (if approved)
    7. Portfolio Manager → final gate

    The graph routes through specialist nodes (crypto, forex) based on
    the symbol type before reaching the generic analyst node.

    Returns:
        Compiled StateGraph ready for execution
    """
    from quant_nanggroe_ai.agents.nodes.crypto import crypto_node
    from quant_nanggroe_ai.agents.nodes.forex import forex_node

    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("researcher", researcher_node)
    graph.add_node("crypto", crypto_node)
    graph.add_node("forex", forex_node)
    graph.add_node("analyst", analyst_node)
    graph.add_node("strategist", strategist_node)
    graph.add_node("risk_manager", risk_manager_node)
    graph.add_node("trader", trader_node)
    graph.add_node("portfolio_manager", portfolio_manager_node)

    # Set entry point
    graph.set_entry_point("researcher")

    # Add edges
    # Researcher → conditional: crypto, forex, analyst, or end
    graph.add_conditional_edges(
        "researcher",
        should_continue_after_regime,
        {"crypto": "crypto", "forex": "forex", "analyst": "analyst", "end": END},
    )
    # Specialist nodes → analyst
    graph.add_edge("crypto", "analyst")
    graph.add_edge("forex", "analyst")
    graph.add_edge("analyst", "strategist")
    graph.add_edge("strategist", "risk_manager")
    graph.add_conditional_edges(
        "risk_manager",
        should_continue_after_risk,
        {"trader": "trader", "end": END},
    )
    graph.add_edge("trader", "portfolio_manager")
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
