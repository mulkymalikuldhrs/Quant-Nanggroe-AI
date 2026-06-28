"""
Compliance Agent for Quant Nanggroe AI Trading Framework.

Enforces regulatory and policy compliance: position limits, concentration,
trade surveillance, Chinese Wall adherence, and audit trail completeness.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from langchain_core.language_models import BaseChatModel
except ImportError:
    BaseChatModel = None

from quant_nanggroe.agents.base import BaseAgent
from quant_nanggroe.agents.registry import AgentRegistry
from quant_nanggroe.agents.state import AgentRole


logger = logging.getLogger(__name__)

POSITION_LIMIT_PCT: float = 0.10
CONCENTRATION_LIMIT_PCT: float = 0.80
MAX_TRADES_PER_CYCLE: int = 10


class VerdictStatus:
    APPROVED = "APPROVED"
    FLAG = "FLAG"
    REJECT = "REJECT"


@dataclass
class ComplianceVerdict:
    status: str = VerdictStatus.APPROVED
    reason: str = ""
    severity: str = "INFO"
    check_name: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@AgentRegistry.register("compliance", AgentRole.COMPLIANCE)
class ComplianceAgent(BaseAgent):
    """Enforces regulatory and policy compliance.

    Checks: position limits, concentration, trade surveillance,
    Chinese Wall adherence, audit trail completeness.
    """

    def __init__(
        self,
        llm: Optional[BaseChatModel] = None,
        tools: Optional[List] = None,
        system_prompt: Optional[str] = None,
    ) -> None:
        super().__init__(
            name="compliance",
            role=AgentRole.COMPLIANCE,
            description=(
                "Enforces regulatory and policy compliance. "
                "Checks position limits, concentration, trade surveillance, "
                "Chinese Wall adherence, and audit trail completeness."
            ),
            llm=llm,
            tools=tools or [],
            system_prompt=system_prompt or "Compliance agent for Quant Nanggroe AI.",
        )
        self._wall_violations: List[Dict[str, Any]] = []
        self._audit_gaps: List[Dict[str, Any]] = []

    def run(self, state: dict) -> Dict[str, Any]:
        """Execute compliance checks on the agent state (LangGraph interface)."""
        verdicts = []
        signals = state.get("signals", [])
        portfolio = state.get("portfolio_state", {})
        equity = portfolio.get("total_value", 0.0)
        positions = portfolio.get("positions", {})

        for sig in signals:
            v = self.check_trade(
                symbol=sig.get("symbol", ""),
                side=sig.get("action", ""),
                qty=sig.get("quantity", 0.0),
                strategy=sig.get("source_agents", [None])[0] if sig.get("source_agents") else "",
                equity=equity,
                positions=positions,
            )
            verdicts.append(v)

        port_check = self.check_portfolio(positions, equity)

        return {
            "compliance_verdicts": [v.__dict__ for v in verdicts],
            "compliance_portfolio_check": port_check,
            "sender": self.name,
        }

    # ── Public checks ────────────────────────────────────────────────

    def check_trade(
        self,
        symbol: str,
        side: str,
        qty: float,
        strategy: str = "",
        equity: float = 0.0,
        price: float = 0.0,
        positions: Optional[Dict[str, Any]] = None,
    ) -> ComplianceVerdict:
        """Check a single proposed trade against compliance rules."""
        if positions is None:
            positions = {}

        price = price or equity  # Fallback to equity if price not passed (legacy callers)
        notional_value = abs(qty) * price if equity > 0 else 0

        if equity > 0 and qty > 0 and notional_value / equity > POSITION_LIMIT_PCT:
            return ComplianceVerdict(
                status=VerdictStatus.REJECT,
                reason=f"Position limit exceeded: {notional_value/equity:.2%} > {POSITION_LIMIT_PCT:.0%}",
                severity="ERROR",
                check_name="position_limit",
            )

        total_positions_value = sum(
            abs(p.get("quantity", 0)) * p.get("current_price", 0)
            if isinstance(p, dict) else (abs(p) * 1.0)
            for p in positions.values()
        )
        total_with_proposed = total_positions_value + notional_value
        if equity > 0 and total_with_proposed / equity > CONCENTRATION_LIMIT_PCT:
            return ComplianceVerdict(
                status=VerdictStatus.FLAG,
                reason=f"Concentration would reach {total_with_proposed/equity:.2%} > {CONCENTRATION_LIMIT_PCT:.0%}",
                severity="WARNING",
                check_name="concentration",
            )

        if strategy and "unknown" in strategy.lower():
            return ComplianceVerdict(
                status=VerdictStatus.FLAG,
                reason=f"Trade from unknown strategy: {strategy}",
                severity="WARNING",
                check_name="strategy_origin",
            )

        return ComplianceVerdict(
            status=VerdictStatus.APPROVED,
            reason="All compliance checks passed",
            check_name="trade_check",
        )

    def check_portfolio(
        self,
        positions: Dict[str, Any],
        equity: float,
    ) -> Dict[str, Any]:
        """Check portfolio-wide compliance."""
        total_exposure = 0.0
        largest_position = 0.0
        largest_symbol = ""
        symbol_exposures: Dict[str, float] = {}

        for sym, pos in positions.items():
            if isinstance(pos, dict):
                pos_qty = abs(pos.get("quantity", 0))
                pos_price = pos.get("current_price", 0)
                exposure = pos_qty * pos_price
            else:
                exposure = abs(pos)
            total_exposure += exposure
            symbol_exposures[sym] = exposure
            if exposure > largest_position:
                largest_position = exposure
                largest_symbol = sym

        concentration_ratio = total_exposure / equity if equity > 0 else 0
        largest_pct = largest_position / equity if equity > 0 else 0

        breaches = []
        if largest_pct > POSITION_LIMIT_PCT:
            breaches.append({
                "symbol": largest_symbol,
                "exposure_pct": round(largest_pct * 100, 2),
                "limit_pct": POSITION_LIMIT_PCT * 100,
                "type": "position_limit",
            })
        if concentration_ratio > CONCENTRATION_LIMIT_PCT:
            breaches.append({
                "exposure_pct": round(concentration_ratio * 100, 2),
                "limit_pct": CONCENTRATION_LIMIT_PCT * 100,
                "type": "concentration_limit",
            })

        return {
            "total_exposure": round(total_exposure, 2),
            "equity": round(equity, 2),
            "concentration_ratio": round(concentration_ratio, 4),
            "largest_position": {"symbol": largest_symbol, "pct": round(largest_pct * 100, 2)},
            "limit_breaches": breaches,
            "num_positions": len(positions),
        }

    def audit_log_check(self, audit_logger: Any) -> Dict[str, Any]:
        """Check audit log for completeness and gaps."""
        missing_entries = []
        gaps = []

        try:
            entries = getattr(audit_logger, "entries", [])
            entry_ids = {e.get("id") for e in entries}
            expected = set(range(1, len(entries) + 1))
            missing_ids = expected - entry_ids
            if missing_ids:
                missing_entries = [{"missing_id": i} for i in sorted(missing_ids)]

            layers_present = set(e.get("layer") for e in entries if "layer" in e)
            from quant_nanggroe.engine.audit import AuditLogger
            expected_layers = set(AuditLogger.LAYERS)
            missing_layers = expected_layers - layers_present
            if missing_layers:
                gaps = [{"layer": l, "issue": "no entries found"} for l in sorted(missing_layers)]

            self._audit_gaps = gaps + missing_entries
        except Exception as e:
            logger.warning("Audit log check error: %s", e)
            self._audit_gaps = [{"issue": f"check failed: {e}"}]

        return {
            "total_entries": len(getattr(audit_logger, "entries", [])),
            "missing_entries": missing_entries,
            "layer_gaps": gaps,
            "has_gaps": bool(missing_entries or gaps),
        }

    def check_wall_violations(self, chinese_wall: Any) -> Dict[str, Any]:
        """Check Chinese Wall for recent violations."""
        violations = []
        try:
            access_log = getattr(chinese_wall, "_access_log", [])
            recent = [e for e in access_log if e.get("violation", False)]
            for v in recent[-20:]:
                violations.append({
                    "source": v.get("source", "unknown"),
                    "target": v.get("target", "unknown"),
                    "timestamp": str(v.get("timestamp", "")),
                })
            self._wall_violations = violations
        except Exception as e:
            logger.warning("Chinese Wall check error: %s", e)
            violations = [{"error": str(e)}]

        return {
            "recent_violations": violations,
            "violation_count": len(violations),
        }

    def status(self) -> Dict[str, Any]:
        """Return summary of compliance state."""
        return {
            "agent": self.name,
            "role": self.role.value,
            "checks": ["position_limit", "concentration", "trade_surveillance", "chinese_wall", "audit_trail"],
            "recent_wall_violations": len(self._wall_violations),
            "audit_gaps": len(self._audit_gaps),
            "timestamp": datetime.now().isoformat(),
        }
