"""
Risk Agent for Quant Nanggroe AI Trading Framework.

Implements the 9-checkpoint risk gate with HARD-CODED constitutional
limits that CANNOT be overridden. Has full veto authority over all
trading decisions and manages the kill switch.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from langchain_core.language_models import BaseChatModel

from quant_nanggroe.agents.base import BaseAgent
from quant_nanggroe.agents.risk.prompts import (
    RISK_SYSTEM_PROMPT,
    RISK_TASK_TEMPLATE,
)
from quant_nanggroe.agents.risk.tools import RISK_TOOLS, _is_correlated
from quant_nanggroe.agents.registry import AgentRegistry
from quant_nanggroe.agents.state import (
    AgentOutput,
    RiskAssessment,
    AgentRole,
    AgentState,
    RiskCheckpoint,
    RiskVerdict,
    MAX_CORRELATED_POSITIONS,
    MAX_DAILY_LOSS,
    MAX_DRAWDOWN_PCT,
    MAX_LEVERAGE,
    MAX_POSITION_SIZE_PCT,
    MAX_RISK_PER_TRADE,
    MAX_TRADES_PER_DAY,
    MAX_WEEKLY_LOSS,
    MIN_RISK_REWARD,
)


logger = logging.getLogger(__name__)


@AgentRegistry.register("risk", AgentRole.RISK)
class RiskAgent(BaseAgent):
    """
    Risk Agent with 9-checkpoint gate and FULL VETO AUTHORITY.

    Constitutional risk limits are HARDCODED and CANNOT be overridden.
    Any checkpoint failure results in trade VETO. Breach of daily/weekly
    limits activates the kill switch automatically.
    """

    def __init__(
        self,
        llm: BaseChatModel,
        tools: Optional[List] = None,
        system_prompt: Optional[str] = None,
    ) -> None:
        super().__init__(
            name="risk",
            role=AgentRole.RISK,
            description=(
                "9-checkpoint risk gate with FULL VETO AUTHORITY. "
                "Constitutional risk limits are HARDCODED and cannot be overridden. "
                "Manages kill switch for emergency halts."
            ),
            llm=llm,
            tools=tools or RISK_TOOLS,
            system_prompt=system_prompt or RISK_SYSTEM_PROMPT,
        )

    def run(self, state: AgentState) -> Dict[str, Any]:
        """
        Execute the 9-checkpoint risk validation.

        Every proposed trade must pass ALL 9 constitutional checkpoints.
        Any failure results in VETO. No exceptions possible.

        Args:
            state: Current agent state

        Returns:
            State updates with risk assessment and verdict
        """
        # Check kill switch first
        if state.get("kill_switch_active", False):
            return self._kill_switch_active(state)

        # Get current risk parameters from state
        portfolio_state = state.get("portfolio_state", {})
        signals = state.get("signals", [])
        daily_pnl = state.get("metadata", {}).get("daily_pnl_pct", 0.0)
        weekly_pnl = state.get("metadata", {}).get("weekly_pnl_pct", 0.0)
        trades_today = state.get("metadata", {}).get("trades_today", 0)

        # Run the 9-checkpoint validation
        checkpoints = self._run_checkpoints(
            signals=signals,
            portfolio_state=portfolio_state,
            daily_pnl_pct=daily_pnl,
            weekly_pnl_pct=weekly_pnl,
            trades_today=trades_today,
        )

        all_passed = all(cp.passed for cp in checkpoints)
        kill_switch_triggered = any(cp.name == "8_drawdown" and not cp.passed for cp in checkpoints)

        # Determine verdict
        if kill_switch_triggered or abs(min(0, daily_pnl)) >= MAX_DAILY_LOSS or abs(min(0, weekly_pnl)) >= MAX_WEEKLY_LOSS:
            verdict = RiskVerdict.KILL_SWITCH
        elif not all_passed:
            verdict = RiskVerdict.VETOED
        else:
            verdict = RiskVerdict.APPROVED

        # Build risk assessment
        assessment = RiskAssessment(
            verdict=verdict,
            checkpoints=checkpoints,
            daily_pnl_pct=daily_pnl,
            weekly_pnl_pct=weekly_pnl,
            trade_count_today=trades_today,
            kill_switch_active=verdict == RiskVerdict.KILL_SWITCH,
            position_sizing_approved=all_passed,
            override_possible=False,
        )

        # Also get LLM analysis
        task = RISK_TASK_TEMPLATE.format(
            signals=str(signals)[:2000],
            portfolio_state=str(portfolio_state)[:1000],
            market_data_summary=self._summarize_market_data(state),
            daily_pnl=daily_pnl,
            weekly_pnl=weekly_pnl,
            trades_today=trades_today,
            kill_switch_active=state.get("kill_switch_active", False),
        )

        messages = self.build_messages(state, user_content=task)
        response = self.invoke_llm(messages, use_tools=True)
        content = response.content

        output = self.create_output(
            content=content,
            data=assessment.model_dump(),
            confidence=1.0 if verdict == RiskVerdict.APPROVED else 0.0,
        )

        return {
            "risk_assessment": assessment.model_dump(),
            "risk_verdict": verdict.value,
            "kill_switch_active": assessment.kill_switch_active,
            "should_halt": verdict in (RiskVerdict.VETOED, RiskVerdict.KILL_SWITCH),
            "agent_outputs": {
                **state.get("agent_outputs", {}),
                self.name: output.model_dump(),
            },
            "sender": self.name,
        }

    def _run_checkpoints(
        self,
        signals: List[Dict[str, Any]],
        portfolio_state: Dict[str, Any],
        daily_pnl_pct: float,
        weekly_pnl_pct: float,
        trades_today: int,
    ) -> List[RiskCheckpoint]:
        """
        Run all 9 constitutional risk checkpoints.

        Args:
            signals: Proposed trading signals
            portfolio_state: Current portfolio state
            daily_pnl_pct: Daily PnL percentage
            weekly_pnl_pct: Weekly PnL percentage
            trades_today: Number of trades executed today

        Returns:
            List of RiskCheckpoint results
        """
        checkpoints: List[RiskCheckpoint] = []
        portfolio_value = portfolio_state.get("total_value", 100000.0)
        positions = portfolio_state.get("positions", {})

        # Checkpoint 1: Risk per trade <= 0.5%
        max_signal_risk = 0.0
        for signal in signals:
            if isinstance(signal, dict):
                entry = signal.get("entry_price", 0)
                sl = signal.get("stop_loss", 0)
                if entry and sl and portfolio_value > 0:
                    risk_pct = abs(entry - sl) / portfolio_value
                    max_signal_risk = max(max_signal_risk, risk_pct)

        checkpoints.append(RiskCheckpoint(
            name="1_risk_per_trade",
            value=f"{max_signal_risk:.4f}",
            limit=f"{MAX_RISK_PER_TRADE:.4f}",
            passed=max_signal_risk <= MAX_RISK_PER_TRADE,
            details="Max risk per individual trade",
        ))

        # Checkpoint 2: Daily loss < 1%
        daily_loss = abs(min(0, daily_pnl_pct / 100)) if daily_pnl_pct < 0 else 0
        checkpoints.append(RiskCheckpoint(
            name="2_daily_loss",
            value=f"{daily_loss:.4f}",
            limit=f"{MAX_DAILY_LOSS:.4f}",
            passed=daily_loss < MAX_DAILY_LOSS,
            details="Current daily loss as percentage",
        ))

        # Checkpoint 3: Weekly loss < 3%
        weekly_loss = abs(min(0, weekly_pnl_pct / 100)) if weekly_pnl_pct < 0 else 0
        checkpoints.append(RiskCheckpoint(
            name="3_weekly_loss",
            value=f"{weekly_loss:.4f}",
            limit=f"{MAX_WEEKLY_LOSS:.4f}",
            passed=weekly_loss < MAX_WEEKLY_LOSS,
            details="Current weekly loss as percentage",
        ))

        # Checkpoint 4: Risk:Reward >= 1:2
        min_rr = float('inf')
        for signal in signals:
            if isinstance(signal, dict):
                rr = signal.get("risk_reward_ratio")
                if rr is not None:
                    min_rr = min(min_rr, rr)

        if min_rr == float('inf'):
            min_rr = 0.0  # No R:R calculated = fail

        checkpoints.append(RiskCheckpoint(
            name="4_risk_reward",
            value=f"1:{min_rr:.1f}" if min_rr > 0 else "N/A",
            limit=f"1:{MIN_RISK_REWARD:.1f}",
            passed=min_rr >= MIN_RISK_REWARD,
            details="Minimum risk:reward ratio across signals",
        ))

        # Checkpoint 5: Stop loss exists
        all_have_sl = True
        for signal in signals:
            if isinstance(signal, dict) and signal.get("action") in ("BUY", "SELL"):
                if not signal.get("stop_loss"):
                    all_have_sl = False
                    break

        checkpoints.append(RiskCheckpoint(
            name="5_stop_loss_exists",
            value=str(all_have_sl),
            limit="True",
            passed=all_have_sl,
            details="All BUY/SELL signals have stop losses",
        ))

        # Checkpoint 6: Position size <= 10%
        max_position_pct = 0.0
        for signal in signals:
            if isinstance(signal, dict):
                pos_pct = signal.get("position_size_pct", 0)
                max_position_pct = max(max_position_pct, pos_pct)

        checkpoints.append(RiskCheckpoint(
            name="6_position_size",
            value=f"{max_position_pct:.2f}%",
            limit=f"{MAX_POSITION_SIZE_PCT * 100:.0f}%",
            passed=max_position_pct <= MAX_POSITION_SIZE_PCT * 100,
            details="Maximum position size as percentage of portfolio",
        ))

        # Checkpoint 7: Leverage <= 3x
        current_leverage = portfolio_state.get("leverage", 1.0)
        checkpoints.append(RiskCheckpoint(
            name="7_leverage",
            value=f"{current_leverage:.1f}x",
            limit=f"{MAX_LEVERAGE:.1f}x",
            passed=current_leverage <= MAX_LEVERAGE,
            details="Current portfolio leverage",
        ))

        # Checkpoint 8: Drawdown < 15%
        current_dd = portfolio_state.get("max_drawdown_pct", 0.0)
        checkpoints.append(RiskCheckpoint(
            name="8_drawdown",
            value=f"{current_dd:.2f}%",
            limit=f"{MAX_DRAWDOWN_PCT * 100:.0f}%",
            passed=current_dd < MAX_DRAWDOWN_PCT * 100,
            details="Current maximum drawdown percentage",
        ))

        # Checkpoint 9: Correlated positions < 3
        max_correlated = 0
        new_symbols = [s.get("symbol", "") for s in signals if isinstance(s, dict)]
        existing_symbols = list(positions.keys()) if isinstance(positions, dict) else []
        all_symbols = existing_symbols + new_symbols

        for sym in all_symbols:
            correlated_count = sum(1 for other in all_symbols if other != sym and _is_correlated(sym, other))
            max_correlated = max(max_correlated, correlated_count)

        checkpoints.append(RiskCheckpoint(
            name="9_correlation_check",
            value=str(max_correlated),
            limit=str(MAX_CORRELATED_POSITIONS),
            passed=max_correlated < MAX_CORRELATED_POSITIONS,
            details="Maximum correlated positions",
        ))

        return checkpoints

    def _kill_switch_active(self, state: AgentState) -> Dict[str, Any]:
        """Handle already-active kill switch."""
        assessment = RiskAssessment(
            verdict=RiskVerdict.KILL_SWITCH,
            kill_switch_active=True,
            override_possible=False,
        )

        content = "KILL SWITCH ACTIVE - All trading halted. Manual reset required after review."

        output = self.create_output(
            content=content,
            data=assessment.model_dump(),
            confidence=1.0,
        )

        return {
            "risk_assessment": assessment.model_dump(),
            "risk_verdict": RiskVerdict.KILL_SWITCH.value,
            "kill_switch_active": True,
            "should_halt": True,
            "agent_outputs": {
                **state.get("agent_outputs", {}),
                self.name: output.model_dump(),
            },
            "sender": self.name,
        }

    def _summarize_market_data(self, state: AgentState) -> str:
        """Summarize market data for the risk prompt."""
        market_data = state.get("market_data", {})
        if not market_data:
            return "No market data available"
        parts = []
        for symbol, data in market_data.items():
            if isinstance(data, dict):
                parts.append(f"  {symbol}: {data}")
        return "\n".join(parts) if parts else "No detailed data"
