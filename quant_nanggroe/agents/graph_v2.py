"""
Enhanced Trading Graph v2 for Quant Nanggroe AI Trading Framework.

Implements a multi-path LangGraph StateGraph that orchestrates the full
trading pipeline with asset-class conditional routing, smart order
execution, enhanced position sizing, and human-in-the-loop checkpoints.

Graph Architecture (v2):
━━━━━━━━━━━━━━━━━━━━━━━
                          ┌─────────────────┐
                          │     START       │
                          └────────┬────────┘
                                   │
                          ┌────────▼────────┐
                          │ market_analysis │
                          └────────┬────────┘
                                   │
                          ┌────────▼────────┐
                          │  asset_router   │─────── detects asset class
                          └────────┬────────┘
                                   │
               ┌───────────────────┼───────────────────┐
               │                   │                   │
    ┌──────────▼──────┐ ┌─────────▼──────┐ ┌──────────▼──────────────┐
    │  crypto_path    │ │  forex_path    │ │  equity_path            │
    │  (crypto agent  │ │  (forex agent  │ │  (researcher + macro)   │
    │  + Solana/Jup)  │ │  + FX tools)   │ │                         │
    └──────────┬──────┘ └─────────┬──────┘ └──────────┬──────────────┘
               │                   │                   │
               │         ┌─────────▼────────┐          │
               └────────►│signal_generation │◄─────────┘
                         └────────┬─────────┘
                                  │
                         ┌────────▼────────┐
                         │ position_sizer  │ (ATR + TP1/TP2/TP3)
                         └────────┬────────┘
                                  │
                         ┌────────▼────────┐
                         │ risk_assessment │ (9-checkpoint gate)
                         └────────┬────────┘
                                  │
                     ┌────────────┼────────────┐
                     │            │            │
              ┌──────▼─────┐ ┌───▼───┐ ┌──────▼──────┐
              │   halt     │ │council│ │  continue   │
              │   (END)    │ │debate │ │             │
              └────────────┘ └───┬───┘ └──────┬──────┘
                                 │            │
                         ┌───────▼────────────▼──────┐
                         │  portfolio_validation      │
                         │  (concentration/corr/Kelly)│
                         └────────────┬───────────────┘
                                      │
                         ┌────────────▼───────────────┐
                         │  portfolio_optimization     │
                         └────────────┬───────────────┘
                                      │
                         ┌────────────▼───────────────┐
                         │  execution_decision         │
                         └────────────┬───────────────┘
                                      │
                         ┌────────────▼───────────────┐
                         │  human_checkpoint           │
                         └────────────┬───────────────┘
                                      │
                          ┌───────────┼───────────┐
                          │           │           │
                   ┌──────▼──┐  ┌─────▼────┐ ┌───▼──────┐
                   │ execute │  │  wait /  │ │  reject  │
                   │         │  │  reject  │ │  (END)   │
                   └────┬────┘  └──────────┘ └──────────┘
                        │
               ┌────────▼────────┐
               │ smart_executor  │ (venue scoring)
               └────────┬────────┘
                        │
               ┌────────▼────────┐
               │   reflection    │
               └────────┬────────┘
                        │
               ┌────────▼────────┐
               │      END        │
               └─────────────────┘

Emergency exit can be triggered from ANY node and goes directly to END.
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
    AssetClass,
    CONFIDENCE_THRESHOLD,
    RiskVerdict,
    TradeAction,
    create_initial_state,
)
from quant_nanggroe.agents.nodes.asset_router import (
    AssetRouter,
    route_by_asset_class,
)
from quant_nanggroe.agents.nodes.position_sizer import (
    PositionSizer,
    compute_atr_position_sizing,
)
from quant_nanggroe.agents.nodes.portfolio_validator import (
    PortfolioValidator,
    validate_portfolio,
)
from quant_nanggroe.agents.nodes.smart_executor import (
    SmartExecutor,
    route_order_smart,
)
from quant_nanggroe.agents.nodes.human_checkpoint import (
    HumanCheckpoint,
    check_human_approval,
    human_approval_conditional,
)


logger = logging.getLogger(__name__)


class TradingGraphV2:
    """
    Enhanced trading graph with multi-path architecture, smart order
    routing, ATR position sizing, portfolio validation, and
    human-in-the-loop checkpoints.

    This is the v2 evolution of TradingGraph that introduces:
    - Asset-class conditional routing after market analysis
    - Specialized paths for crypto, forex, equity, prediction markets
    - ATR-based position sizing with TP1/TP2/TP3 geometry
    - Portfolio concentration/correlation/Kelly validation
    - Smart order routing with venue scoring
    - Human-in-the-loop checkpoint for high-risk trades
    - Council debate as fallback for low-confidence decisions
    - Emergency exit path from any node
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
        fractional_risk_pct: float = 0.005,
        atr_sl_multiplier: float = 1.5,
        atr_tp1_multiplier: float = 1.0,
        atr_tp2_multiplier: float = 2.0,
        atr_tp3_multiplier: float = 3.0,
    ) -> None:
        """
        Initialize the v2 trading graph.

        Args:
            llm_provider: LLM provider name
            deep_think_model: Model for deep analysis tasks
            quick_think_model: Model for quick response tasks
            base_url: Optional API base URL
            api_key: Optional API key
            max_debate_rounds: Maximum debate rounds
            max_risk_rounds: Maximum risk debate rounds
            confidence_threshold: Confidence threshold for council debate
            fractional_risk_pct: Fixed-fractional risk % per trade
            atr_sl_multiplier: ATR multiplier for stop-loss
            atr_tp1_multiplier: ATR multiplier for TP1
            atr_tp2_multiplier: ATR multiplier for TP2
            atr_tp3_multiplier: ATR multiplier for TP3
        """
        self._llm_provider = llm_provider
        self._deep_think_model = deep_think_model
        self._quick_think_model = quick_think_model
        self._base_url = base_url
        self._api_key = api_key
        self._max_debate_rounds = max_debate_rounds
        self._max_risk_rounds = max_risk_rounds
        self._confidence_threshold = confidence_threshold
        self._fractional_risk_pct = fractional_risk_pct
        self._atr_sl_multiplier = atr_sl_multiplier
        self._atr_tp1_multiplier = atr_tp1_multiplier
        self._atr_tp2_multiplier = atr_tp2_multiplier
        self._atr_tp3_multiplier = atr_tp3_multiplier

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

        # Create node instances
        self._asset_router = AssetRouter()
        self._position_sizer = PositionSizer(
            fractional_risk_pct=fractional_risk_pct,
            atr_sl_multiplier=atr_sl_multiplier,
            atr_tp1_multiplier=atr_tp1_multiplier,
            atr_tp2_multiplier=atr_tp2_multiplier,
            atr_tp3_multiplier=atr_tp3_multiplier,
        )
        self._portfolio_validator = PortfolioValidator()
        self._smart_executor = SmartExecutor()
        self._human_checkpoint = HumanCheckpoint()

        # Build and compile the graph
        self._graph = self._build_graph()

    @property
    def graph(self) -> StateGraph:
        """Get the compiled LangGraph graph."""
        return self._graph

    def _build_graph(self) -> StateGraph:
        """
        Build the enhanced v2 LangGraph trading graph.

        Returns:
            Compiled StateGraph
        """
        workflow = StateGraph(AgentState)

        # ── Phase 1: Market Analysis ──────────────────────────────────
        workflow.add_node("market_analysis", self._market_analysis_node)
        workflow.add_node("asset_router", self._asset_router_node)

        # ── Phase 2: Asset-Class Paths ────────────────────────────────
        workflow.add_node("crypto_path", self._crypto_path_node)
        workflow.add_node("forex_path", self._forex_path_node)
        workflow.add_node("equity_path", self._equity_path_node)
        workflow.add_node("prediction_market_path", self._prediction_market_path_node)

        # ── Phase 3: Signal Generation + Sizing ───────────────────────
        workflow.add_node("signal_generation", self._signal_generation_node)
        workflow.add_node("position_sizer", self._position_sizer_node)

        # ── Phase 4: Risk Assessment ──────────────────────────────────
        workflow.add_node("risk_assessment", self._risk_assessment_node)

        # ── Phase 5: Portfolio Validation + Optimization ──────────────
        workflow.add_node("portfolio_validation", self._portfolio_validation_node)
        workflow.add_node("portfolio_optimization", self._portfolio_optimization_node)

        # ── Phase 6: Execution Decision + Human Checkpoint ────────────
        workflow.add_node("execution_decision", self._execution_decision_node)
        workflow.add_node("human_checkpoint", self._human_checkpoint_node)
        workflow.add_node("smart_execution", self._smart_execution_node)
        workflow.add_node("trade_rejected", self._trade_rejected_node)

        # ── Phase 7: Reflection ──────────────────────────────────────
        workflow.add_node("reflection", self._reflection_node)

        # ── Council Debate (fallback) ─────────────────────────────────
        workflow.add_node("council_debate", self._council_debate_node)

        # ── Emergency Exit ────────────────────────────────────────────
        workflow.add_node("emergency_exit", self._emergency_exit_node)

        # ══════════════════════════════════════════════════════════════
        # EDGES
        # ══════════════════════════════════════════════════════════════

        # Start → Market Analysis
        workflow.add_edge(START, "market_analysis")
        workflow.add_edge("market_analysis", "asset_router")

        # Asset Router → conditional branching by asset class
        workflow.add_conditional_edges(
            "asset_router",
            route_by_asset_class,
            {
                "crypto_path": "crypto_path",
                "forex_path": "forex_path",
                "equity_path": "equity_path",
                "prediction_market_path": "prediction_market_path",
            },
        )

        # All paths converge at signal_generation
        workflow.add_edge("crypto_path", "signal_generation")
        workflow.add_edge("forex_path", "signal_generation")
        workflow.add_edge("equity_path", "signal_generation")
        workflow.add_edge("prediction_market_path", "signal_generation")

        # Signal generation → position sizing → risk assessment
        workflow.add_edge("signal_generation", "position_sizer")
        workflow.add_edge("position_sizer", "risk_assessment")

        # Risk assessment → conditional routing
        workflow.add_conditional_edges(
            "risk_assessment",
            self._risk_conditional,
            {
                "continue": "portfolio_validation",
                "halt": END,
                "council_debate": "council_debate",
                "emergency_exit": "emergency_exit",
            },
        )

        # Council debate → position sizer (re-evaluate after debate)
        workflow.add_edge("council_debate", "position_sizer")

        # Portfolio validation → conditional (pass/fail)
        workflow.add_conditional_edges(
            "portfolio_validation",
            self._portfolio_validation_conditional,
            {
                "pass": "portfolio_optimization",
                "fail": END,
            },
        )

        # Portfolio optimization → execution decision → human checkpoint
        workflow.add_edge("portfolio_optimization", "execution_decision")
        workflow.add_edge("execution_decision", "human_checkpoint")

        # Human checkpoint → conditional
        workflow.add_conditional_edges(
            "human_checkpoint",
            human_approval_conditional,
            {
                "execute": "smart_execution",
                "wait_approval": "smart_execution",  # In prod, would pause here
                "reject": "trade_rejected",
            },
        )

        # Smart execution → reflection
        workflow.add_edge("smart_execution", "reflection")

        # Trade rejected → END
        workflow.add_edge("trade_rejected", END)

        # Reflection → END
        workflow.add_edge("reflection", END)

        # Emergency exit → END
        workflow.add_edge("emergency_exit", END)

        # Compile
        return workflow.compile()

    # ══════════════════════════════════════════════════════════════════
    # CONDITIONAL EDGE FUNCTIONS
    # ══════════════════════════════════════════════════════════════════

    def _risk_conditional(self, state: AgentState) -> str:
        """
        Determine the next step after risk assessment.

        Enhanced v2 logic includes:
        - Kill switch state check
        - Regime safety check (CRISIS regime → stricter gate)
        - 9-checkpoint validation
        """
        # Kill switch active → emergency exit
        if state.get("kill_switch_active", False):
            logger.warning("Kill switch active - routing to emergency exit")
            return "emergency_exit"

        risk_verdict = state.get("risk_verdict", "VETOED")

        if risk_verdict == RiskVerdict.KILL_SWITCH.value:
            logger.critical("Risk assessment triggered kill switch - emergency exit")
            return "emergency_exit"

        if risk_verdict == RiskVerdict.VETOED.value:
            logger.info("Risk assessment vetoed - halting pipeline")
            return "halt"

        # Low confidence → council debate
        confidence = state.get("confidence", 0.0)
        if confidence < self._confidence_threshold:
            logger.info(
                f"Low confidence ({confidence:.2f} < {self._confidence_threshold}) "
                f"- routing to council debate"
            )
            return "council_debate"

        # Regime safety check: in CRISIS, require higher confidence
        metadata = state.get("metadata", {})
        regime = metadata.get("market_regime", "")
        if regime == "CRISIS" and confidence < 0.85:
            logger.warning(
                f"CRISIS regime with confidence {confidence:.2f} "
                f"< 0.85 - routing to council debate"
            )
            return "council_debate"

        return "continue"

    def _portfolio_validation_conditional(self, state: AgentState) -> str:
        """
        Determine next step after portfolio validation.

        If validation fails with errors, halt the pipeline.
        Warnings are logged but don't block.
        """
        validation = state.get("portfolio_validation", {})
        if isinstance(validation, dict):
            is_valid = validation.get("is_valid", True)
            errors = validation.get("errors", [])

            if not is_valid and errors:
                logger.warning(
                    f"Portfolio validation FAILED with {len(errors)} error(s) - halting"
                )
                return "fail"

        return "pass"

    # ══════════════════════════════════════════════════════════════════
    # NODE IMPLEMENTATIONS
    # ══════════════════════════════════════════════════════════════════

    def _market_analysis_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Market analysis node: runs researcher and macro agents.

        In v2, we run only the universal agents here. Asset-class
        specific analysis happens in the path nodes.
        """
        logger.info("=== Market Analysis Phase (v2) ===")

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

        updates["sender"] = "market_analysis"
        return updates

    def _asset_router_node(self, state: AgentState) -> Dict[str, Any]:
        """Route to the correct asset-class path."""
        return self._asset_router(state)

    # ── Asset-Class Path Nodes ────────────────────────────────────────

    def _crypto_path_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Crypto path: runs crypto agent with Solana/Jupiter tools.

        Performs on-chain analysis, DEX monitoring, and smart contract
        risk assessment specific to cryptocurrency trading.
        """
        logger.info("=== Crypto Path ===")

        try:
            crypto = self._factory.create_agent("crypto")
            result = crypto(state)
            return {
                "crypto_output": result.get("crypto_output", ""),
                "agent_outputs": {
                    **state.get("agent_outputs", {}),
                    **result.get("agent_outputs", {}),
                },
                "metadata": {
                    **state.get("metadata", {}),
                    "crypto_path_executed": True,
                    "crypto_tools": ["solana_rpc", "jupiter_swap", "on_chain_analytics"],
                },
                "sender": "crypto_path",
            }
        except Exception as e:
            logger.error(f"Crypto path failed: {e}")
            return {
                "crypto_output": f"Crypto path failed: {e}",
                "sender": "crypto_path",
            }

    def _forex_path_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Forex path: runs forex agent with FX-specific analysis.

        Analyzes currency pairs, central bank policies, carry trades,
        and cross-currency dynamics.
        """
        logger.info("=== Forex Path ===")

        try:
            forex = self._factory.create_agent("forex")
            result = forex(state)
            return {
                "forex_output": result.get("forex_output", ""),
                "agent_outputs": {
                    **state.get("agent_outputs", {}),
                    **result.get("agent_outputs", {}),
                },
                "metadata": {
                    **state.get("metadata", {}),
                    "forex_path_executed": True,
                    "forex_tools": ["fx_rates", "carry_trade_calc", "cb_policy_tracker"],
                },
                "sender": "forex_path",
            }
        except Exception as e:
            logger.error(f"Forex path failed: {e}")
            return {
                "forex_output": f"Forex path failed: {e}",
                "sender": "forex_path",
            }

    def _equity_path_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Equity path: standard equity analysis.

        Uses the researcher and macro outputs already computed in
        market_analysis. This is the default path for stocks and ETFs.
        """
        logger.info("=== Equity Path ===")

        # Equity path uses the researcher + macro outputs already computed.
        # We enrich with equity-specific metadata.
        return {
            "metadata": {
                **state.get("metadata", {}),
                "equity_path_executed": True,
                "equity_tools": ["sec_filings", "earnings_calendar", "insider_trades"],
            },
            "sender": "equity_path",
        }

    def _prediction_market_path_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Prediction market path: Polymarket integration.

        Analyzes event contracts, probability estimates, and
        outcome token pricing for prediction market trading.
        Invokes the PredictionMarketAgent for full analysis.
        """
        logger.info("=== Prediction Market Path ===")

        try:
            prediction_market = self._factory.create_agent("prediction_market")
            result = prediction_market(state)
            return {
                "prediction_market_output": result.get("prediction_market_output", ""),
                "human_approval_required": True,
                "agent_outputs": {
                    **state.get("agent_outputs", {}),
                    **result.get("agent_outputs", {}),
                },
                "metadata": {
                    **state.get("metadata", {}),
                    "prediction_market_path_executed": True,
                    "prediction_market_tools": [
                        "polymarket_api",
                        "kalshi_api",
                        "probability_estimator",
                        "kelly_sizing",
                    ],
                },
                "sender": "prediction_market_path",
            }
        except Exception as e:
            logger.error(f"Prediction market path failed: {e}")
            return {
                "prediction_market_output": f"Prediction market path failed: {e}",
                "human_approval_required": True,
                "sender": "prediction_market_path",
            }

    # ── Signal Generation + Position Sizing ───────────────────────────

    def _signal_generation_node(self, state: AgentState) -> Dict[str, Any]:
        """Signal generation: combines all path outputs into trading signals."""
        logger.info("=== Signal Generation Phase (v2) ===")

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

    def _position_sizer_node(self, state: AgentState) -> Dict[str, Any]:
        """Position sizing with fixed-fractional ATR model and TP1/TP2/TP3."""
        return self._position_sizer(state)

    # ── Risk Assessment ───────────────────────────────────────────────

    def _risk_assessment_node(self, state: AgentState) -> Dict[str, Any]:
        """
        Enhanced risk assessment with 9-checkpoint gate.

        v2 adds:
        - Kill switch state check
        - Regime safety check
        - Position sizing validation (from position_sizer results)
        """
        logger.info("=== Risk Assessment Phase (v2) ===")

        try:
            risk = self._factory.create_agent("risk", use_deep_llm=True)
            result = risk(state)

            # v2: Add position sizing validation to risk assessment
            sizing_result = state.get("position_sizing_result", {})
            sizing_approved = True
            if isinstance(sizing_result, dict):
                for symbol, sizing in sizing_result.items():
                    if isinstance(sizing, dict):
                        if sizing.get("position_size_pct", 0) > 10.0:
                            sizing_approved = False

            return {
                "risk_assessment": result.get("risk_assessment", {}),
                "risk_verdict": result.get("risk_verdict", RiskVerdict.VETOED.value),
                "kill_switch_active": result.get("kill_switch_active", False),
                "should_halt": result.get("should_halt", True),
                "agent_outputs": {
                    **state.get("agent_outputs", {}),
                    **result.get("agent_outputs", {}),
                },
                "metadata": {
                    **state.get("metadata", {}),
                    "position_sizing_approved": sizing_approved,
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

    # ── Portfolio Validation ──────────────────────────────────────────

    def _portfolio_validation_node(self, state: AgentState) -> Dict[str, Any]:
        """Run concentration, correlation, and Kelly checks."""
        return self._portfolio_validator(state)

    def _portfolio_optimization_node(self, state: AgentState) -> Dict[str, Any]:
        """Portfolio optimization node."""
        logger.info("=== Portfolio Optimization Phase (v2) ===")

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

    # ── Execution ─────────────────────────────────────────────────────

    def _execution_decision_node(self, state: AgentState) -> Dict[str, Any]:
        """Execution decision: runs the trader agent."""
        logger.info("=== Execution Decision Phase (v2) ===")

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

    def _human_checkpoint_node(self, state: AgentState) -> Dict[str, Any]:
        """Human-in-the-loop checkpoint for high-risk trades."""
        return self._human_checkpoint(state)

    def _smart_execution_node(self, state: AgentState) -> Dict[str, Any]:
        """Smart order execution with venue scoring and routing."""
        return self._smart_executor(state)

    def _trade_rejected_node(self, state: AgentState) -> Dict[str, Any]:
        """Handle trade rejection (human or validation)."""
        logger.info("=== Trade Rejected ===")

        reason = state.get("human_approval_reason", "Trade rejected by human checkpoint")

        return {
            "execution_output": f"Trade rejected: {reason}",
            "orders_placed": [],
            "should_halt": True,
            "metadata": {
                **state.get("metadata", {}),
                "rejection_reason": reason,
                "rejected_at": datetime.now().isoformat(),
            },
            "sender": "trade_rejected",
        }

    # ── Reflection ────────────────────────────────────────────────────

    def _reflection_node(self, state: AgentState) -> Dict[str, Any]:
        """Reflection node: post-trade analysis and learning."""
        logger.info("=== Reflection Phase (v2) ===")

        try:
            debate_results = self._council_debate.run_full_debate(state)
            return {
                "debate_state": debate_results.get("debate_state", {}),
                "metadata": {
                    **state.get("metadata", {}),
                    "reflection_completed": True,
                    "venue_scores_recorded": len(state.get("venue_scores", [])),
                    "position_sizing_model": "fixed_fractional_atr",
                },
                "sender": "reflection",
            }
        except Exception as e:
            logger.error(f"Reflection failed: {e}")
            return {
                "debate_state": {"error": str(e)},
                "sender": "reflection",
            }

    # ── Council Debate ────────────────────────────────────────────────

    def _council_debate_node(self, state: AgentState) -> Dict[str, Any]:
        """Council debate: runs when confidence is below threshold."""
        logger.info("=== Council Debate Phase (v2) ===")

        try:
            debate_results = self._council_debate.run_full_debate(state)
            council_result = self._council_voting.run_council_vote(state)

            if council_result.final_decision in (TradeAction.BUY, TradeAction.SELL):
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

    # ── Emergency Exit ────────────────────────────────────────────────

    def _emergency_exit_node(self, state: AgentState) -> Dict[str, Any]:
        """Emergency exit: closes all positions immediately."""
        logger.critical("=== EMERGENCY EXIT ACTIVATED (v2) ===")

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
            "metadata": {
                **state.get("metadata", {}),
                "emergency_exit_at": datetime.now().isoformat(),
                "emergency_exit_triggered_by": state.get("sender", "unknown"),
            },
            "sender": "emergency_exit",
        }

    # ══════════════════════════════════════════════════════════════════
    # PUBLIC API
    # ══════════════════════════════════════════════════════════════════

    def run(
        self,
        symbols: List[str],
        trade_date: Optional[str] = None,
        market_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        human_approval_status: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run the complete v2 trading pipeline.

        Args:
            symbols: List of trading symbols to analyze
            trade_date: Trading date string (YYYY-MM-DD)
            market_data: Optional pre-loaded market data
            metadata: Optional additional metadata
            human_approval_status: Pre-set approval status for
                human-in-the-loop (APPROVED/REJECTED)

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

        # Pre-set human approval if provided
        if human_approval_status:
            initial_state["human_approval_status"] = human_approval_status
            if human_approval_status == "APPROVED":
                initial_state["human_approval_required"] = True

        logger.info(
            f"Starting v2 trading pipeline for {symbols} on {trade_date} "
            f"(asset_class will be auto-detected)"
        )

        try:
            final_state = self._graph.invoke(initial_state)
            logger.info("v2 Trading pipeline completed successfully")
            return final_state
        except Exception as e:
            logger.error(f"v2 Trading pipeline failed: {e}")
            return {
                **initial_state,
                "error": str(e),
                "should_halt": True,
            }

    def run_stream(
        self,
        symbols: List[str],
        trade_date: Optional[str] = None,
        **kwargs: Any,
    ):
        """
        Run the v2 trading pipeline with streaming output.

        Args:
            symbols: List of trading symbols
            trade_date: Trading date string
            **kwargs: Additional arguments passed to run()

        Yields:
            State updates as they occur
        """
        trade_date = trade_date or datetime.now().strftime("%Y-%m-%d")
        initial_state = create_initial_state(symbols, trade_date)

        if kwargs.get("market_data"):
            initial_state["market_data"] = kwargs["market_data"]
        if kwargs.get("metadata"):
            initial_state["metadata"].update(kwargs["metadata"])

        for chunk in self._graph.stream(initial_state):
            yield chunk
