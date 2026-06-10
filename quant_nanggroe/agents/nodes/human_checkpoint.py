"""
Human-in-the-Loop Checkpoint for Quant Nanggroe AI Trading Framework v2.

Implements a checkpoint node that pauses the trading pipeline when
human approval is required before executing high-risk trades.

Human approval is triggered when:
  - Risk verdict is CONDITIONAL (not fully approved)
  - Position size exceeds 50% of constitutional max (i.e., >5% of portfolio)
  - Council debate consensus is low (< 0.4)
  - Portfolio validation has errors
  - Asset class is PREDICTION_MARKET (novel/risky)
  - Leverage is being used
  - Kill switch was recently reset

In a production system, this would integrate with a notification system
(Slack, PagerDuty, etc.) and a manual approval UI. For now, the
checkpoint sets state flags that a UI layer can read and act upon.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from quant_nanggroe.agents.state import (
    AgentState,
    AssetClass,
    MAX_POSITION_SIZE_PCT,
    RiskVerdict,
)


logger = logging.getLogger(__name__)


# =============================================================================
# Configuration
# =============================================================================

# Position size threshold for human review (as fraction of constitutional max)
HUMAN_REVIEW_POSITION_THRESHOLD: float = 0.50  # 50% of max position size

# Consensus threshold below which human review is required
HUMAN_REVIEW_CONSENSUS_THRESHOLD: float = 0.40

# Whether prediction market trades always require human review
PREDICTION_MARKET_REQUIRES_HUMAN: bool = True

# Whether leveraged trades always require human review
LEVERAGE_REQUIRES_HUMAN: bool = True


# =============================================================================
# Human approval requirement detection
# =============================================================================

def should_require_human_approval(state: AgentState) -> tuple[bool, str]:
    """
    Determine whether human approval is required for the current trade.

    Evaluates multiple conditions and returns a decision with reason.

    Args:
        state: Current agent state

    Returns:
        Tuple of (requires_approval: bool, reason: str)
    """
    reasons: List[str] = []

    # 1. Risk verdict is CONDITIONAL
    risk_verdict = state.get("risk_verdict", RiskVerdict.VETOED.value)
    if risk_verdict == RiskVerdict.CONDITIONAL.value:
        reasons.append("Risk verdict is CONDITIONAL — requires manual review")

    # 2. Large position sizes
    signals = state.get("signals", [])
    position_threshold_pct = (
        MAX_POSITION_SIZE_PCT * HUMAN_REVIEW_POSITION_THRESHOLD * 100
    )
    for signal in signals:
        if isinstance(signal, dict):
            pos_pct = signal.get("position_size_pct", 0)
            if pos_pct > position_threshold_pct:
                reasons.append(
                    f"Position {signal.get('symbol', '')} at {pos_pct:.1f}% "
                    f"exceeds review threshold ({position_threshold_pct:.1f}%)"
                )

    # 3. Low council consensus
    council_result = state.get("council_result", {})
    if isinstance(council_result, dict):
        consensus = council_result.get("consensus_level", 1.0)
        if consensus < HUMAN_REVIEW_CONSENSUS_THRESHOLD:
            reasons.append(
                f"Council consensus ({consensus:.2f}) below threshold "
                f"({HUMAN_REVIEW_CONSENSUS_THRESHOLD:.2f})"
            )

    # 4. Portfolio validation errors
    portfolio_validation = state.get("portfolio_validation", {})
    if isinstance(portfolio_validation, dict):
        errors = portfolio_validation.get("errors", [])
        if errors:
            reasons.append(
                f"Portfolio validation has {len(errors)} error(s): "
                f"{errors[0][:100]}"
            )

    # 5. Prediction market trades
    asset_class = state.get("asset_class", "")
    if asset_class == AssetClass.PREDICTION_MARKET.value and PREDICTION_MARKET_REQUIRES_HUMAN:
        reasons.append("Prediction market trades require human review")

    # 6. Leveraged trades
    if LEVERAGE_REQUIRES_HUMAN:
        portfolio_state = state.get("portfolio_state", {})
        if isinstance(portfolio_state, dict):
            leverage = portfolio_state.get("leverage", 1.0)
            if leverage > 1.0:
                reasons.append(
                    f"Leveraged trade ({leverage:.1f}x) requires human review"
                )

    # 7. Kill switch was recently reset
    metadata = state.get("metadata", {})
    if isinstance(metadata, dict):
        if metadata.get("kill_switch_recently_reset", False):
            reasons.append("Kill switch was recently reset — requires manual review")

    requires_approval = len(reasons) > 0
    reason = "; ".join(reasons) if reasons else "No human review required"

    return requires_approval, reason


# =============================================================================
# LangGraph node
# =============================================================================

class HumanCheckpoint:
    """
    Human-in-the-loop checkpoint node for the v2 LangGraph trading graph.

    Evaluates whether human approval is needed and sets state flags
    accordingly. In a LangGraph deployment, this would typically be
    used with `interrupt_before` or a checkpoint-based human-in-the-loop
    pattern.

    The node sets:
      - human_approval_required: bool
      - human_approval_status: PENDING / NOT_REQUIRED / APPROVED / REJECTED / TIMEOUT
      - human_approval_reason: str

    When human_approval_required is True, the graph should pause and
    wait for external input to set human_approval_status to APPROVED
    or REJECTED before continuing.
    """

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """
        Execute the human checkpoint evaluation.

        Args:
            state: Current agent state

        Returns:
            State updates with human approval flags
        """
        logger.info("=== Human-in-the-Loop Checkpoint ===")

        requires_approval, reason = should_require_human_approval(state)

        if requires_approval:
            logger.warning(f"Human approval REQUIRED: {reason}")
            return {
                "human_approval_required": True,
                "human_approval_status": "PENDING",
                "human_approval_reason": reason,
                "metadata": {
                    **state.get("metadata", {}),
                    "human_checkpoint": {
                        "required": True,
                        "reason": reason,
                        "triggered_at": datetime.now().isoformat(),
                        "status": "PENDING",
                    },
                },
                "sender": "human_checkpoint",
            }
        else:
            logger.info("Human approval NOT required — proceeding to execution")
            return {
                "human_approval_required": False,
                "human_approval_status": "NOT_REQUIRED",
                "human_approval_reason": reason,
                "metadata": {
                    **state.get("metadata", {}),
                    "human_checkpoint": {
                        "required": False,
                        "reason": reason,
                        "triggered_at": datetime.now().isoformat(),
                        "status": "NOT_REQUIRED",
                    },
                },
                "sender": "human_checkpoint",
            }


def check_human_approval(state: AgentState) -> Dict[str, Any]:
    """
    Functional interface for the human checkpoint node.

    Args:
        state: Current agent state

    Returns:
        State updates with human approval status
    """
    checkpoint = HumanCheckpoint()
    return checkpoint(state)


def human_approval_conditional(state: AgentState) -> str:
    """
    Conditional-edge function: route based on human approval status.

    After the human_checkpoint node, this function determines whether
    to proceed to execution, wait for approval, or reject the trade.

    Args:
        state: Current agent state

    Returns:
        Next node name: 'execute' | 'wait_approval' | 'reject'
    """
    if not state.get("human_approval_required", False):
        return "execute"

    status = state.get("human_approval_status", "PENDING")

    if status == "APPROVED":
        return "execute"
    elif status == "REJECTED":
        return "reject"
    elif status == "TIMEOUT":
        return "reject"
    else:
        # PENDING or unknown — wait for approval
        return "wait_approval"
