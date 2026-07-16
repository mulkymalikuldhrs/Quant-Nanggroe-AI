"""
Main Trading Graph for Quant Nanggroe AI Trading Framework.

Implements the LangGraph StateGraph that orchestrates the full trading
pipeline from market analysis through execution and reflection.

Graph Flow:
1. market_analysis → Researcher + Macro + Crypto + Forex agents
2. signal_generation → Strategist agent
3. risk_assessment → Risk agent (LLM-based qualitative analysis)
4. deterministic_risk_gate → RiskGateBridge (HARD GATE — 9-checkpoint deterministic)
5. portfolio_optimization → Portfolio agent
6. execution_decision → Trader agent
7. order_execution → Execution agent
8. reflection → Council debate (post-trade analysis)

CRITICAL ARCHITECTURE:
- Step 3 (risk_assessment) provides LLM-based qualitative risk analysis
- Step 4 (deterministic_risk_gate) is the HARD GATE using the deterministic
  RiskCheckGate with all 9 checkpoints. This gate CANNOT be bypassed.
- If both the LLM risk agent and deterministic gate disagree, the
  deterministic gate WINS.

Conditional edges:
- If deterministic_risk_gate fails → halt (no trade)
- If confidence < threshold → council debate
- If kill_switch active → emergency exit
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from langchain_core.language_models import BaseChatModel
except ImportError:
    BaseChatModel = None

try:
    from langgraph.graph import END, START, StateGraph
except ImportError:
    END = "END"
    START = "START"
    StateGraph = None

try:
    from langgraph.prebuilt import ToolNode
except ImportError:
    ToolNode = None

from quant_nanggroe.agents.base import create_llm
from quant_nanggroe.agents.bridges.kelly_bridge import KellyBridge
from quant_nanggroe.agents.bridges.risk_gate_bridge import GateVerdict, RiskGateBridge
from quant_nanggroe.agents.chinese_wall import ChineseWall, ChineseWallError
from quant_nanggroe.agents.council.debate import CouncilDebate
from quant_nanggroe.agents.council.voting import CouncilVoting
from quant_nanggroe.agents.registry import AgentFactory
from quant_nanggroe.agents.state import (
    CONFIDENCE_THRESHOLD,
    AgentState,
    RiskVerdict,
    TradeAction,
    create_initial_state,
)

try:
    from quant_nanggroe.engine.audit import AuditLogger
except ImportError:
    AuditLogger = None


logger = logging.getLogger(__name__)


# Node name -> compartment mapping for Chinese Wall checks
_NODE_COMPARTMENTS: Dict[str, str] = {
    "market_analysis": "RESEARCH",
    "signal_generation": "SIGNAL",
    "risk_assessment": "RISK",
    "deterministic_risk_gate": "RISK",
    "kelly_sizing": "RISK",
    "portfolio_optimization": "RISK",
    "execution_decision": "EXECUTION",
    "order_execution": "EXECUTION",
    "reflection": "EXECUTION",
    "council_debate": "EXECUTION",
    "emergency_exit": "EXECUTION",
}


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
        audit_logger: Optional[Any] = None,
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
            audit_logger: Optional AuditLogger instance for Chinese Wall logging
        """
        self._llm_provider = llm_provider
        self._deep_think_model = deep_think_model
        self._quick_think_model = quick_think_model
        self._base_url = base_url
        self._api_key = api_key
        self._max_debate_rounds = max_debate_rounds
        self._max_risk_rounds = max_risk_rounds
        self._confidence_threshold = confidence_threshold
        self._audit_logger = audit_logger

        # Create Chinese Wall isolation layer
        self._wall = ChineseWall()

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

        # Create bridges to deterministic engine
        self._risk_gate_bridge = RiskGateBridge()
        self._kelly_bridge = KellyBridge()

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
        workflow.add_node("deterministic_risk_gate", self._deterministic_risk_gate_node)
        workflow.add_node("kelly_sizing", self._kelly_sizing_node)
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

        # LLM risk assessment → deterministic risk gate (HARD GATE)
        # The deterministic risk gate is MANDATORY and sits AFTER the LLM risk agent
        workflow.add_edge("risk_assessment", "deterministic_risk_gate")

        # Conditional edge after DETERMINISTIC risk gate (not LLM risk)
        workflow.add_conditional_edges(
            "deterministic_risk_gate",
            self._deterministic_risk_conditional,
            {
                "continue": "kelly_sizing",
                "halt": END,
                "council_debate": "council_debate",
                "emergency_exit": "emergency_exit",
            },
        )

        # Kelly sizing → portfolio optimization → execution
        workflow.add_edge("kelly_sizing", "portfolio_optimization")
        workflow.add_edge("portfolio_optimization", "execution_decision")
        workflow.add_edge("execution_decision", "order_execution")
        workflow.add_edge("order_execution", "reflection")
        workflow.add_edge("reflection", END)
        workflow.add_edge("council_debate", "execution_decision")
        workflow.add_edge("emergency_exit", END)

        # Compile
        return workflow.compile()

    def _check_wall(self, source_node: str, target_node: str) -> None:
        """Check Chinese Wall restrictions between two graph nodes.

        Args:
            source_node: Name of the source/origin node
            target_node: Name of the target/destination node

        Raises:
            ChineseWallError: If the transition violates wall restrictions
        """
        source_comp = _NODE_COMPARTMENTS.get(source_node)
        target_comp = _NODE_COMPARTMENTS.get(target_node)

        if not source_comp or not target_comp:
            return

        if source_comp == target_comp:
            return

        if source_comp in self._wall.BRIDGES and target_comp in self._wall.BRIDGES[source_comp]:
            return

        msg = (
            f"Chinese Wall violation: '{target_node}' ({target_comp} compartment) "
            f"cannot read data from '{source_node}' ({source_comp} compartment). "
            f"No bridge exists from {source_comp} to {target_comp}."
        )
        logger.critical(msg)
        if self._audit_logger is not None:
            self._audit_logger.log(
                layer="SYSTEM",
                severity="CRITICAL",
                message=f"ChineseWall BLOCKED: {source_node}({source_comp}) -> {target_node}({target_comp})",
                details={
                    "source": source_node,
                    "target": target_node,
                    "source_compartment": source_comp,
                    "target_compartment": target_comp,
                    "violation_type": "bridge_missing",
                },
            )
        raise ChineseWallError(
            message=msg,
            source=source_node,
            target=target_node,
            access_type="read",
        )

    def _deterministic_risk_conditional(self, state: AgentState) -> str:
        """
        Determine the next step after the DETERMINISTIC risk gate.

        This is the FINAL routing decision — the deterministic gate's verdict
        is the ultimate authority. The LLM risk agent's verdict was considered
        earlier but is NOT the final word.

        Args:
            state: Current agent state

        Returns:
            Next node name
        """
        # Check kill switch (set by either LLM or deterministic gate)
        if state.get("kill_switch_active", False):
            logger.warning("Kill switch active - routing to emergency exit")
            return "emergency_exit"

        # Check the DETERMINISTIC risk gate verdict (not LLM)
        det_verdict = state.get("deterministic_risk_verdict", "REJECTED")
        if det_verdict == GateVerdict.KILL_SWITCH.value:
            logger.critical("Deterministic risk gate triggered kill switch - emergency exit")
            return "emergency_exit"

        if det_verdict == GateVerdict.REJECTED.value:
            logger.info("Deterministic risk gate REJECTED trade - halting pipeline")
            return "halt"

        # Low confidence → council debate
        confidence = state.get("confidence", 0.0)
        if confidence < self._confidence_threshold:
            logger.info(
                f"Low confidence ({confidence:.2f} < {self._confidence_threshold}) "
                f"- routing to council debate"
            )
            return "council_debate"

        # Approved or Modified → continue to Kelly sizing
        logger.info(
            "Deterministic risk gate %s - proceeding to Kelly sizing",
            det_verdict,
        )
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
        self._check_wall("market_analysis", "signal_generation")

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
        Risk assessment node: runs the LLM-based risk agent for QUALITATIVE analysis.
        
        This provides qualitative risk analysis (sentiment, regime, narrative risk).
        The DETERMINISTIC risk gate runs AFTER this node as the HARD GATE.

        Args:
            state: Current agent state

        Returns:
            State updates with LLM risk assessment
        """
        logger.info("=== Risk Assessment Phase (LLM — Qualitative) ===")
        self._check_wall("signal_generation", "risk_assessment")

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
            # If LLM risk fails, we still have the deterministic gate as backup
            # Default to VETOED so the deterministic gate must explicitly approve
            return {
                "risk_assessment": {"error": str(e)},
                "risk_verdict": RiskVerdict.VETOED.value,
                "kill_switch_active": False,
                "should_halt": True,
                "sender": "risk_assessment",
            }

    def _deterministic_risk_gate_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Deterministic risk gate node: runs the 9-checkpoint RiskCheckGate.

        This is the HARD GATE — it runs AFTER the LLM risk agent and is the
        FINAL authority on whether a trade can proceed. It CANNOT be bypassed.

        The deterministic gate:
        1. Takes trade decisions from the agent pipeline
        2. Runs them through the deterministic RiskCheckGate (all 9 checkpoints)
        3. Returns APPROVED, REJECTED, MODIFIED (with adjusted position size)
        4. If REJECTED, provides the specific check that failed
        5. If MODIFIED, provides the adjusted position size from Kelly

        If both the LLM risk agent and deterministic gate disagree,
        the deterministic gate WINS.

        Args:
            state: Current agent state

        Returns:
            State updates with deterministic risk gate results
        """
        logger.info("=== Deterministic Risk Gate Phase (HARD GATE — 9 Checkpoints) ===")
        self._check_wall("risk_assessment", "deterministic_risk_gate")

        try:
            result = self._risk_gate_bridge.evaluate_from_state(state)

            # Log any disagreements with the LLM risk agent
            llm_verdict = state.get("risk_verdict", "UNKNOWN")
            det_verdict = result.get("deterministic_risk_verdict", "UNKNOWN")
            det_results = result.get("deterministic_risk_results", [])

            disagreements = [
                r for r in det_results
                if r.get("llm_disagreement", False)
            ]
            if disagreements:
                logger.warning(
                    "DETERMINISTIC GATE: %d disagreement(s) with LLM risk agent. "
                    "LLM=%s, Deterministic=%s. Deterministic WINS.",
                    len(disagreements), llm_verdict, det_verdict,
                )

            return {
                **result,
                "agent_outputs": {
                    **state.get("agent_outputs", {}),
                    "deterministic_risk_gate": result,
                },
            }
        except Exception as e:
            logger.critical("Deterministic risk gate FAILED: %s — BLOCKING ALL TRADES", e)
            # If the deterministic gate fails, we MUST block all trades
            # (fail-safe: default to rejected)
            return {
                "deterministic_risk_verdict": GateVerdict.REJECTED.value,
                "deterministic_risk_results": [],
                "should_halt": True,
                "sender": "deterministic_risk_gate",
                "error": str(e),
            }

    def _kelly_sizing_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Kelly sizing node: calculates optimal position sizes using Kelly Criterion.

        Runs AFTER the deterministic risk gate approves a trade and BEFORE
        portfolio optimization. Uses the deterministic Kelly Criterion engine
        to calculate position sizes that respect constitutional limits.

        Args:
            state: Current agent state

        Returns:
            State updates with Kelly position sizing results
        """
        logger.info("=== Kelly Sizing Phase (Deterministic Position Sizing) ===")
        self._check_wall("deterministic_risk_gate", "kelly_sizing")

        try:
            result = self._kelly_bridge.calculate_from_state(state)
            return {
                **result,
                "agent_outputs": {
                    **state.get("agent_outputs", {}),
                    "kelly_sizing": result.get("kelly_results", []),
                },
            }
        except Exception as e:
            logger.error("Kelly sizing failed: %s — using defaults", e)
            return {
                "kelly_results": [],
                "sender": "kelly_sizing",
                "error": str(e),
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
        self._check_wall("kelly_sizing", "portfolio_optimization")

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
        self._check_wall("portfolio_optimization", "execution_decision")

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
        self._check_wall("execution_decision", "order_execution")

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
        self._check_wall("order_execution", "reflection")

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
        self._check_wall("deterministic_risk_gate", "council_debate")

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


def get_trading_graph(
    llm_provider: str | None = None,
    deep_think_model: str | None = None,
    quick_think_model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
) -> StateGraph:
    """Factory: build a ready-to-invoke trading graph from env defaults.

    Falls back to environment variables for API keys so the worker can
    construct a graph without hardcoding credentials.

    Returns
    -------
    Compiled ``StateGraph`` — call ``.ainvoke(state_dict)`` on it.
    """
    import os

    return TradingGraph(
        llm_provider=llm_provider or os.getenv("QNA_LLM_PROVIDER", "openai"),
        deep_think_model=deep_think_model or os.getenv("QNA_DEEP_MODEL", "gpt-4o"),
        quick_think_model=quick_think_model or os.getenv("QNA_QUICK_MODEL", "gpt-4o-mini"),
        base_url=base_url or os.getenv("OPENAI_BASE_URL"),
        api_key=api_key or os.getenv("OPENAI_API_KEY"),
    ).graph
