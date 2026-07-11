"""
Chinese Wall — Agent Isolation Layer for Quant Nanggroe AI Trading Framework.

Implements an information barrier between agent compartments to prevent
conflicts of interest and unauthorized data flow between agents.
Each agent belongs to a compartment. Agents can only read/write data
within their compartment unless explicitly bridged.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ChineseWallError(Exception):
    """Raised when a Chinese Wall violation is detected."""

    def __init__(self, message: str, source: str = "", target: str = "",
                 access_type: str = "") -> None:
        self.source = source
        self.target = target
        self.access_type = access_type
        super().__init__(message)


class ChineseWall:
    """Information barrier between agent compartments.

    Each agent belongs to a compartment. Agents can only read/write
    data within their compartment unless explicitly bridged.
    """

    COMPARTMENTS: Dict[str, List[str]] = {
        "RESEARCH": ["ResearcherAgent", "MacroAgent"],
        "SIGNAL": ["StrategistAgent", "CryptoAgent", "ForexAgent"],
        "RISK": ["RiskAgent", "PortfolioAgent"],
        "EXECUTION": ["ExecutionAgent", "TraderAgent"],
    }

    BRIDGES: Dict[str, List[str]] = {
        "SIGNAL": ["RISK"],
        "RISK": ["EXECUTION"],
    }

    def __init__(self) -> None:
        self._access_log: List[Dict[str, Any]] = []

    def get_compartment_for(self, agent_class_name: str) -> str:
        """Return the compartment name for a given agent class name.

        Args:
            agent_class_name: Class name of the agent (e.g. 'ResearcherAgent')

        Returns:
            Compartment name (e.g. 'RESEARCH')

        Raises:
            ValueError: If the agent class name is not registered in any compartment
        """
        for compartment, agents in self.COMPARTMENTS.items():
            if agent_class_name in agents:
                return compartment
        raise ValueError(
            f"Agent '{agent_class_name}' is not assigned to any compartment. "
            f"Known agents: {self._all_agents()}"
        )

    def _all_agents(self) -> List[str]:
        """Return all agent class names across all compartments."""
        return [
            agent
            for agents in self.COMPARTMENTS.values()
            for agent in agents
        ]

    def check_read(self, source_agent: str, target_data_compartment: str) -> bool:
        """Check if source_agent can read data from target_data_compartment.

        Allowed if:
        1. Both are in the same compartment, OR
        2. The source agent's compartment has a bridge FROM the
           target_data_compartment

        Args:
            source_agent: Class name of the requesting agent
            target_data_compartment: Compartment name of the data being read

        Returns:
            True if read is permitted, False otherwise
        """
        try:
            source_comp = self.get_compartment_for(source_agent)
        except ValueError:
            return False

        if source_comp == target_data_compartment:
            return True

        return (
            target_data_compartment in self.BRIDGES
            and source_comp in self.BRIDGES[target_data_compartment]
        )

    def check_write(self, source_agent: str, target_data_compartment: str) -> bool:
        """Check if source_agent can write data to target_data_compartment.

        An agent can write only to its own compartment.

        Args:
            source_agent: Class name of the producing agent
            target_data_compartment: Compartment name where data will be stored

        Returns:
            True if write is permitted, False otherwise
        """
        try:
            source_comp = self.get_compartment_for(source_agent)
        except ValueError:
            return False

        return source_comp == target_data_compartment

    def can_communicate(self, source_agent: str, target_agent: str) -> bool:
        """Check if source_agent can communicate directly with target_agent.

        Communication is allowed if:
        1. Both agents are in the same compartment, OR
        2. There is a bridge from source's compartment to target's compartment

        Args:
            source_agent: Class name of the sending agent
            target_agent: Class name of the receiving agent

        Returns:
            True if communication is permitted, False otherwise
        """
        try:
            source_comp = self.get_compartment_for(source_agent)
            target_comp = self.get_compartment_for(target_agent)
        except ValueError:
            return False

        if source_comp == target_comp:
            return True

        return (
            source_comp in self.BRIDGES
            and target_comp in self.BRIDGES[source_comp]
        )

    def audit_access(
        self,
        source_agent: str,
        target: str,
        access_type: str,
        audit_logger: Optional[Any] = None,
    ) -> None:
        """Log an access event. Optionally forward to an external AuditLogger.

        Args:
            source_agent: Class name of the requesting agent
            target: Target compartment or agent name
            access_type: 'read', 'write', or 'communicate'
            audit_logger: Optional AuditLogger instance from engine.audit
        """
        entry = {
            "source": source_agent,
            "target": target,
            "access_type": access_type,
            "wall_action": "allowed",
        }

        try:
            source_comp = self.get_compartment_for(source_agent)
            entry["source_compartment"] = source_comp
        except ValueError:
            entry["source_compartment"] = "UNKNOWN"

        self._access_log.append(entry)

        if audit_logger is not None:
            audit_logger.log(
                layer="SYSTEM",
                severity="INFO",
                message=f"ChineseWall: {access_type.upper()} | {source_agent} -> {target}",
                details=entry,
            )

    def isolation_report(self) -> Dict[str, Any]:
        """Return a structured report of current walls and bridges.

        Returns:
            Dict with compartments, bridges, and access log summary
        """
        return {
            "compartments": {
                comp: {"agents": agents, "wall_active": True}
                for comp, agents in self.COMPARTMENTS.items()
            },
            "bridges": [
                {"from": src, "to": dst}
                for src, targets in self.BRIDGES.items()
                for dst in targets
            ],
            "isolation_zones": self._compute_isolation_zones(),
            "access_log_count": len(self._access_log),
        }

    def _compute_isolation_zones(self) -> List[Dict[str, Any]]:
        """Compute isolation zones — groups of compartments that cannot
        communicate with each other."""
        all_comps = list(self.COMPARTMENTS.keys())
        zones: List[Dict[str, Any]] = []
        seen: set = set()

        for i, comp_a in enumerate(all_comps):
            if comp_a in seen:
                continue
            zone_comps = [comp_a]
            for comp_b in all_comps[i + 1:]:
                if self._can_comp_communicate(comp_a, comp_b):
                    zone_comps.append(comp_b)
                    seen.add(comp_b)
            seen.add(comp_a)
            if len(zone_comps) > 1:
                zones.append({
                    "zone_compartments": zone_comps,
                    "isolated_from": [
                        c for c in all_comps
                        if c not in zone_comps and not any(
                            self._can_comp_communicate(zc, c) for zc in zone_comps
                        )
                    ],
                })

        return zones

    def _can_comp_communicate(self, comp_a: str, comp_b: str) -> bool:
        """Check if two compartments can communicate (either direction)."""
        if comp_a == comp_b:
            return True
        if comp_a in self.BRIDGES and comp_b in self.BRIDGES[comp_a]:
            return True
        if comp_b in self.BRIDGES and comp_a in self.BRIDGES[comp_b]:
            return True
        return False
