"""
Main Trading Graph for Quant Nanggroe AI Trading Framework.

Implements the LangGraph StateGraph that orchestrates the full trading
pipeline from market analysis through execution and reflection.

Graph Flow:
1. market_analysis → Researcher + Macro + Crypto + Forex agents
2. signal_generation → Strategist agent
3. risk_assessment → Risk agent (9-checkpoint gate)
4. portfolio_optimization → Portfolio agent
5. execution_decision → Trader agent
6. order_execution → Execution agent
7. reflection → Council debate (post-trade analysis)

Conditional edges:
- If risk_assessment fails → halt (no trade)
- If confidence < threshold → council debate
- If kill_switch active → emergency exit
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain_core.language_models import BaseChatModel
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from quant_nanggroe.agents.base import create_llm
from quant_nanggroe.agents.council.debate import CouncilDebate
from quant_nanggroe.agents.council.voting import CouncilVoting
from quant_nanggroe.agents.registry import AgentFactory
from quant_nanggroe.agents.state import (
    AgentState,
    CONFIDENCE_THRESHOLD,
    RiskVerdict,
    TradeAction,
    create_initial_state,
)


logger = logging.getLogger(__name__)


class TradingGraph:
    """
    Main trading graph orchestrating the full trading pipeline.

    Uses LangGraph StateGraph to define the agent workflow with
    conditional edges for risk gates, council debates, and
    emergency exits.
    """

    def __init__(
        self,
        llm_provider: str = "openai",
        deep_think_model: str = "gpt-4o",
        quick_think_model: str = "gpt-4o-mini",
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        max_debate_rounds: int = 2,
        max_risk_rounds: int = 2,
        confidence_threshold: float = CONFIDENCE_THRESHOLD,
    ) -> None:
        """
        Initialize the trading graph.

        Args:
            llm_provider: LLM provider name
            deep_think_model: Model for deep analysis tasks
            quick_think_model: Model for quick response tasks
            base_url: Optional API base URL
            api_key: Optional API key
            max_debate_rounds: Maximum debate rounds
            max_risk_rounds: Maximum risk debate rounds
            confidence_threshold: Confidence threshold for council debate
        """
        self._llm_provider = llm_provider
        self._deep_think_model = deep_think_model
        self._quick_think_model = quick_think_model
        self._base_url = base_url
        self._api_key = api_key
        self._max_debate_rounds = max_debate_rounds
        self._max_risk_rounds = max_risk_rounds
        self._confidence_threshold = confidence_threshold

        # Create LLMs
        self._deep_llm = create_llm(
            provider=llm_provider,
            model=deep_think_model,
            base_url=base_url,
            api_key=api_key,
            temperature=0.0,
        )
        self._quick_llm = create_llm(
            provider=llm_provider,
            model=quick_think_model,
            base_url=base_url,
            api_key=api_key,
            temperature=0.0,
        )

        # Create agent factory
        self._factory = AgentFactory(
            llm_provider=llm_provider,
            deep_think_model=deep_think_model,
            quick_think_model=quick_think_model,
            base_url=base_url,
            api_key=api_key,
        )

        # Create council components
        self._council_debate = CouncilDebate(
            llm=self._deep_llm,
            max_debate_rounds=max_debate_rounds,
            max_risk_rounds=max_risk_rounds,
        )
        self._council_voting = CouncilVoting(
            llm=self._deep_llm,
            consensus_threshold=confidence_threshold,
        )

        # Build and compile the graph
        self._graph = self._build_graph()

    @property
    def graph(self) -> StateGraph:
        """Get the compiled LangGraph graph."""
        return self._graph

    def _build_graph(self) -> StateGraph:
        """
        Build the LangGraph trading graph.

        Returns:
            Compiled StateGraph
        """
        # Create the workflow
        workflow = StateGraph(AgentState)

        # Add agent nodes
        workflow.add_node("market_analysis", self._market_analysis_node)
        workflow.add_node("signal_generation", self._signal_generation_node)
        workflow.add_node("risk_assessment", self._risk_assessment_node)
        workflow.add_node("portfolio_optimization", self._portfolio_optimization_node)
        workflow.add_node("execution_decision", self._execution_decision_node)
        workflow.add_node("order_execution", self._order_execution_node)
        workflow.add_node("reflection", self._reflection_node)
        workflow.add_node("council_debate", self._council_debate_node)
        workflow.add_node("emergency_exit", self._emergency_exit_node)

        # Define the main flow
        workflow.add_edge(START, "market_analysis")
        workflow.add_edge("market_analysis", "signal_generation")
        workflow.add_edge("signal_generation", "risk_assessment")

        # Conditional edge after risk assessment
        workflow.add_conditional_edges(
            "risk_assessment",
            self._risk_conditional,
            {
                "continue": "portfolio_optimization",
                "halt": END,
                "council_debate": "council_debate",
                "emergency_exit": "emergency_exit",
            },
        )

        workflow.add_edge("portfolio_optimization", "execution_decision")
        workflow.add_edge("execution_decision", "order_execution")
        workflow.add_edge("order_execution", "reflection")
        workflow.add_edge("reflection", END)
        workflow.add_edge("council_debate", "execution_decision")
        workflow.add_edge("emergency_exit", END)

        # Compile
        return workflow.compile()

    def _risk_conditional(self, state: AgentState) -> str:
        """
        Determine the next step after risk assessment.

        Args:
            state: Current agent state

        Returns:
            Next node name
        """
        # Kill switch active → emergency exit
        if state.get("kill_switch_active", False):
            logger.warning("Kill switch active - routing to emergency exit")
            return "emergency_exit"

        # Risk vetoed → halt
        risk_verdict = state.get("risk_verdict", "VETOED")
        if risk_verdict == RiskVerdict.VETOED.value:
            logger.info("Risk assessment vetoed - halting pipeline")
            return "halt"

        if risk_verdict == RiskVerdict.KILL_SWITCH.value:
            logger.critical("Risk assessment triggered kill switch - emergency exit")
            return "emergency_exit"

        # Low confidence → council debate
        confidence = state.get("confidence", 0.0)
        if confidence < self._confidence_threshold:
            logger.info(
                f"Low confidence ({confidence:.2f} < {self._confidence_threshold}) "
                f"- routing to council debate"
            )
            return "council_debate"

        # Continue to portfolio optimization
        return "continue"

    def _market_analysis_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Market analysis node: runs researcher, macro, crypto, and forex agents.

        Args:
            state: Current agent state

        Returns:
            State updates with analysis outputs
        """
        logger.info("=== Market Analysis Phase ===")

        updates: Dict[str, Any] = {
            "iteration": state.get("iteration", 0) + 1,
        }

        # Run researcher agent
        try:
            researcher = self._factory.create_agent("researcher")
            result = researcher(state)
            updates["research_output"] = result.get("research_output", "")
            updates["agent_outputs"] = {
                **state.get("agent_outputs", {}),
                **result.get("agent_outputs", {}),
            }
        except Exception as e:
            logger.error(f"Researcher agent failed: {e}")
            updates["research_output"] = f"Research failed: {e}"

        # Run macro agent
        try:
            macro = self._factory.create_agent("macro")
            result = macro(state)
            updates["macro_output"] = result.get("macro_output", "")
            updates["agent_outputs"] = {
                **updates.get("agent_outputs", state.get("agent_outputs", {})),
                **result.get("agent_outputs", {}),
            }
        except Exception as e:
            logger.error(f"Macro agent failed: {e}")
            updates["macro_output"] = f"Macro analysis failed: {e}"

        # Run crypto agent
        try:
            crypto = self._factory.create_agent("crypto")
            result = crypto(state)
            updates["crypto_output"] = result.get("crypto_output", "")
            updates["agent_outputs"] = {
                **updates.get("agent_outputs", state.get("agent_outputs", {})),
                **result.get("agent_outputs", {}),
            }
        except Exception as e:
            logger.error(f"Crypto agent failed: {e}")
            updates["crypto_output"] = f"Crypto analysis failed: {e}"

        # Run forex agent
        try:
            forex = self._factory.create_agent("forex")
            result = forex(state)
            updates["forex_output"] = result.get("forex_output", "")
            updates["agent_outputs"] = {
                **updates.get("agent_outputs", state.get("agent_outputs", {})),
                **result.get("agent_outputs", {}),
            }
        except Exception as e:
            logger.error(f"Forex agent failed: {e}")
            updates["forex_output"] = f"Forex analysis failed: {e}"

        updates["sender"] = "market_analysis"
        return updates

    def _signal_generation_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Signal generation node: runs the strategist agent.

        Args:
            state: Current agent state

        Returns:
            State updates with generated signals
        """
        logger.info("=== Signal Generation Phase ===")

        try:
            strategist = self._factory.create_agent("strategist", use_deep_llm=True)
            result = strategist(state)
            return {
                "signals": result.get("signals", []),
                "strategist_output": result.get("strategist_output", ""),
                "confidence": result.get("confidence", 0.0),
                "agent_outputs": {
                    **state.get("agent_outputs", {}),
                    **result.get("agent_outputs", {}),
                },
                "sender": "signal_generation",
            }
        except Exception as e:
            logger.error(f"Strategist agent failed: {e}")
            return {
                "signals": [],
                "strategist_output": f"Strategy generation failed: {e}",
                "confidence": 0.0,
                "sender": "signal_generation",
            }

    def _risk_assessment_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Risk assessment node: runs the 9-checkpoint risk gate.

        Args:
            state: Current agent state

        Returns:
            State updates with risk assessment
        """
        logger.info("=== Risk Assessment Phase ===")

        try:
            risk = self._factory.create_agent("risk", use_deep_llm=True)
            result = risk(state)
            return {
                "risk_assessment": result.get("risk_assessment", {}),
                "risk_verdict": result.get("risk_verdict", RiskVerdict.VETOED.value),
                "kill_switch_active": result.get("kill_switch_active", False),
                "should_halt": result.get("should_halt", True),
                "agent_outputs": {
                    **state.get("agent_outputs", {}),
                    **result.get("agent_outputs", {}),
                },
                "sender": "risk_assessment",
            }
        except Exception as e:
            logger.error(f"Risk agent failed: {e}")
            return {
                "risk_assessment": {"error": str(e)},
                "risk_verdict": RiskVerdict.VETOED.value,
                "kill_switch_active": False,
                "should_halt": True,
                "sender": "risk_assessment",
            }

    def _portfolio_optimization_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Portfolio optimization node.

        Args:
            state: Current agent state

        Returns:
            State updates with portfolio optimization
        """
        logger.info("=== Portfolio Optimization Phase ===")

        try:
            portfolio = self._factory.create_agent("portfolio")
            result = portfolio(state)
            return {
                "portfolio_output": result.get("portfolio_output", ""),
                "agent_outputs": {
                    **state.get("agent_outputs", {}),
                    **result.get("agent_outputs", {}),
                },
                "sender": "portfolio_optimization",
            }
        except Exception as e:
            logger.error(f"Portfolio agent failed: {e}")
            return {
                "portfolio_output": f"Portfolio optimization failed: {e}",
                "sender": "portfolio_optimization",
            }

    def _execution_decision_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Execution decision node: runs the trader agent.

        Args:
            state: Current agent state

        Returns:
            State updates with trading decisions
        """
        logger.info("=== Execution Decision Phase ===")

        try:
            trader = self._factory.create_agent("trader")
            result = trader(state)
            return {
                "decisions": result.get("decisions", []),
                "trader_output": result.get("trader_output", ""),
                "confidence": result.get("confidence", state.get("confidence", 0.0)),
                "agent_outputs": {
                    **state.get("agent_outputs", {}),
                    **result.get("agent_outputs", {}),
                },
                "sender": "execution_decision",
            }
        except Exception as e:
            logger.error(f"Trader agent failed: {e}")
            return {
                "decisions": [],
                "trader_output": f"Trade decision failed: {e}",
                "sender": "execution_decision",
            }

    def _order_execution_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Order execution node: runs the execution agent.

        Args:
            state: Current agent state

        Returns:
            State updates with executed orders
        """
        logger.info("=== Order Execution Phase ===")

        try:
            execution = self._factory.create_agent("execution")
            result = execution(state)
            return {
                "execution_output": result.get("execution_output", ""),
                "orders_placed": result.get("orders_placed", []),
                "agent_outputs": {
                    **state.get("agent_outputs", {}),
                    **result.get("agent_outputs", {}),
                },
                "sender": "order_execution",
            }
        except Exception as e:
            logger.error(f"Execution agent failed: {e}")
            return {
                "execution_output": f"Order execution failed: {e}",
                "orders_placed": [],
                "sender": "order_execution",
            }

    def _reflection_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Reflection node: post-trade analysis and learning.

        Args:
            state: Current agent state

        Returns:
            State updates with reflection results
        """
        logger.info("=== Reflection Phase ===")

        # Run a brief council debate for reflection
        try:
            debate_results = self._council_debate.run_full_debate(state)
            return {
                "debate_state": debate_results.get("debate_state", {}),
                "sender": "reflection",
            }
        except Exception as e:
            logger.error(f"Reflection failed: {e}")
            return {
                "debate_state": {"error": str(e)},
                "sender": "reflection",
            }

    def _council_debate_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Council debate node: runs when confidence is below threshold.

        Args:
            state: Current agent state

        Returns:
            State updates with council debate results
        """
        logger.info("=== Council Debate Phase ===")

        try:
            # Run the council debate
            debate_results = self._council_debate.run_full_debate(state)

            # Run the council vote
            council_result = self._council_voting.run_council_vote(state)

            # Override the trader decision with council result if needed
            if council_result.final_decision in (TradeAction.BUY, TradeAction.SELL):
                # Update decisions based on council vote
                symbols = state.get("symbols", [])
                updated_decisions = []
                for symbol in symbols:
                    updated_decisions.append({
                        "symbol": symbol,
                        "action": council_result.final_decision.value,
                        "confidence": council_result.consensus_level,
                        "reasoning": "Council debate decision with weighted voting",
                    })

                return {
                    "debate_state": debate_results.get("debate_state", {}),
                    "council_result": council_result.model_dump(),
                    "decisions": updated_decisions,
                    "confidence": council_result.consensus_level,
                    "agent_outputs": {
                        **state.get("agent_outputs", {}),
                        "council": council_result.model_dump(),
                    },
                    "sender": "council_debate",
                }

            return {
                "debate_state": debate_results.get("debate_state", {}),
                "council_result": council_result.model_dump(),
                "sender": "council_debate",
            }
        except Exception as e:
            logger.error(f"Council debate failed: {e}")
            return {
                "debate_state": {"error": str(e)},
                "sender": "council_debate",
            }

    def _emergency_exit_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Emergency exit node: closes all positions immediately.

        Args:
            state: Current agent state

        Returns:
            State updates with emergency exit actions
        """
        logger.critical("=== EMERGENCY EXIT ACTIVATED ===")

        symbols = state.get("symbols", [])
        decisions = []
        for symbol in symbols:
            decisions.append({
                "symbol": symbol,
                "action": TradeAction.EMERGENCY_EXIT.value,
                "quantity": 0,
                "reasoning": "Kill switch activated - emergency exit",
                "confidence": 1.0,
            })

        return {
            "decisions": decisions,
            "should_halt": True,
            "kill_switch_active": True,
            "sender": "emergency_exit",
        }

    def run(
        self,
        symbols: List[str],
        trade_date: Optional[str] = None,
        market_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Run the complete trading pipeline.

        Args:
            symbols: List of trading symbols to analyze
            trade_date: Trading date string (YYYY-MM-DD)
            market_data: Optional pre-loaded market data
            metadata: Optional additional metadata

        Returns:
            Final agent state after pipeline completion
        """
        trade_date = trade_date or datetime.now().strftime("%Y-%m-%d")

        # Create initial state
        initial_state = create_initial_state(symbols, trade_date)

        # Add optional data
        if market_data:
            initial_state["market_data"] = market_data
        if metadata:
            initial_state["metadata"].update(metadata)

        logger.info(f"Starting trading pipeline for {symbols} on {trade_date}")

        # Run the graph
        try:
            final_state = self._graph.invoke(initial_state)
            logger.info("Trading pipeline completed successfully")
            return final_state
        except Exception as e:
            logger.error(f"Trading pipeline failed: {e}")
            return {
                **initial_state,
                "error": str(e),
                "should_halt": True,
            }

    def run_stream(self, symbols: List[str], trade_date: Optional[str] = None, **kwargs: Any):
        """
        Run the trading pipeline with streaming output.

        Args:
            symbols: List of trading symbols
            trade_date: Trading date string
            **kwargs: Additional arguments passed to run()

        Yields:
            State updates as they occur
        """
        trade_date = trade_date or datetime.now().strftime("%Y-%m-%d")
        initial_state = create_initial_state(symbols, trade_date)

        for chunk in self._graph.stream(initial_state):
            yield chunk
