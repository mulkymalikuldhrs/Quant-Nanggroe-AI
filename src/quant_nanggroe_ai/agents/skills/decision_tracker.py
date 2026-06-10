"""
Decision Tracker Skill — Track and recall investment decisions via MCP
======================================================================

Ported from mnemosyne MCP server's mnemosyne_add_decision and
mnemosyne_detect_patterns tools. Provides structured decision
tracking for investment and trading decisions with reasoning
preservation and pattern analysis.

Adapted from:
  - mnemosyne/mcp-server/index.ts (mnemosyne_add_decision tool)
  - mnemosyne/src/lib/agent/index.ts (decision_track tool)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from quant_nanggroe_ai.agents.mcp_protocol import MCPTool

logger = logging.getLogger(__name__)


class InvestmentDecision(BaseModel):
    """Structured investment decision record."""
    id: str
    title: str
    context: str
    decision: str
    reasoning: str
    symbol: str | None = None
    direction: str | None = None  # BUY, SELL, HOLD
    outcome: str | None = None    # profit, loss, pending
    tags: list[str] = Field(default_factory=list)
    created_at: str = ""


class DecisionTrackerSkill(MCPTool):
    """
    MCP skill for tracking investment decisions.

    Records decisions with full context and reasoning, enabling
    future reference and pattern analysis. Inspired by mnemosyne's
    decision tracking but adapted for trading/investment workflows.
    """

    def __init__(self) -> None:
        self._decisions: dict[str, dict[str, Any]] = {}
        self._counter: int = 0

    @property
    def name(self) -> str:
        return "decision_tracker"

    @property
    def description(self) -> str:
        return (
            "Track investment decisions with context, reasoning, and outcomes. "
            "Retrieve past decisions, analyze decision patterns, and review "
            "decision outcomes for learning and improvement."
        )

    @property
    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": [
                        "add_decision",
                        "get_decision",
                        "list_decisions",
                        "update_outcome",
                        "analyze_patterns",
                        "search_decisions",
                    ],
                    "description": "The decision tracking action to perform.",
                },
                "title": {
                    "type": "string",
                    "description": "Title/summary of the decision.",
                },
                "context": {
                    "type": "string",
                    "description": "The situation that led to the decision.",
                },
                "decision": {
                    "type": "string",
                    "description": "The actual decision that was made.",
                },
                "reasoning": {
                    "type": "string",
                    "description": "The reasoning behind the decision.",
                },
                "symbol": {
                    "type": "string",
                    "description": "Related ticker symbol.",
                },
                "direction": {
                    "type": "string",
                    "enum": ["BUY", "SELL", "HOLD"],
                    "description": "Trade direction.",
                },
                "decision_id": {
                    "type": "string",
                    "description": "Decision ID for retrieval/update.",
                },
                "outcome": {
                    "type": "string",
                    "enum": ["profit", "loss", "pending", "breakeven"],
                    "description": "Outcome of the decision.",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Tags for categorization.",
                },
                "query": {
                    "type": "string",
                    "description": "Search query for decisions.",
                },
                "limit": {
                    "type": "integer",
                    "default": 20,
                    "description": "Max results to return.",
                },
            },
            "required": ["action"],
            "additionalProperties": False,
        }

    @property
    def tags(self) -> list[str]:
        return ["decisions", "investment", "tracking", "reasoning"]

    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        """Execute a decision tracking action."""
        action = kwargs.get("action")
        if not action:
            from quant_nanggroe_ai.exceptions import AgentError
            raise AgentError("'action' is required for decision_tracker skill")

        if action == "add_decision":
            return self._add_decision(kwargs)
        elif action == "get_decision":
            return self._get_decision(kwargs)
        elif action == "list_decisions":
            return self._list_decisions(kwargs)
        elif action == "update_outcome":
            return self._update_outcome(kwargs)
        elif action == "analyze_patterns":
            return self._analyze_patterns()
        elif action == "search_decisions":
            return self._search_decisions(kwargs)
        else:
            from quant_nanggroe_ai.exceptions import AgentError
            raise AgentError(f"Unknown decision_tracker action: '{action}'")

    def _add_decision(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Record a new investment decision."""
        title = kwargs.get("title", "")
        context = kwargs.get("context", "")
        decision = kwargs.get("decision", "")
        reasoning = kwargs.get("reasoning", "")

        if not title or not decision:
            return {"error": "'title' and 'decision' are required"}

        self._counter += 1
        decision_id = f"dec_{self._counter:06d}"

        entry = {
            "id": decision_id,
            "title": title,
            "context": context,
            "decision": decision,
            "reasoning": reasoning,
            "symbol": kwargs.get("symbol"),
            "direction": kwargs.get("direction"),
            "outcome": kwargs.get("outcome", "pending"),
            "tags": kwargs.get("tags", []),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._decisions[decision_id] = entry

        return {
            "status": "recorded",
            "decision_id": decision_id,
            "message": f'Decision "{title}" recorded successfully',
        }

    def _get_decision(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Retrieve a decision by ID."""
        decision_id = kwargs.get("decision_id", "")
        entry = self._decisions.get(str(decision_id))
        if not entry:
            return {"status": "not_found", "decision_id": str(decision_id)}
        return {"status": "found", **entry}

    def _list_decisions(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        """List all decisions with optional filtering."""
        limit = kwargs.get("limit", 20)
        symbol = kwargs.get("symbol")

        entries = list(self._decisions.values())
        if symbol:
            entries = [e for e in entries if e.get("symbol") == symbol]

        entries.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        entries = entries[:limit]

        return {"decisions": entries, "count": len(entries), "total": len(self._decisions)}

    def _update_outcome(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Update the outcome of a decision."""
        decision_id = kwargs.get("decision_id", "")
        outcome = kwargs.get("outcome")
        if not decision_id or not outcome:
            return {"error": "'decision_id' and 'outcome' are required"}

        entry = self._decisions.get(str(decision_id))
        if not entry:
            return {"status": "not_found", "decision_id": str(decision_id)}

        entry["outcome"] = outcome
        return {"status": "updated", "decision_id": str(decision_id), "outcome": outcome}

    def _analyze_patterns(self) -> dict[str, Any]:
        """Analyze patterns in past decisions."""
        patterns: list[str] = []

        if not self._decisions:
            return {"patterns": ["No decisions recorded yet."]}

        # Outcome distribution
        outcomes: dict[str, int] = {}
        for entry in self._decisions.values():
            outcome = entry.get("outcome", "pending")
            outcomes[outcome] = outcomes.get(outcome, 0) + 1

        patterns.append(
            "Outcome distribution: "
            + ", ".join(f"{k}: {v}" for k, v in sorted(outcomes.items()))
        )

        # Symbol frequency
        symbol_freq: dict[str, int] = {}
        for entry in self._decisions.values():
            sym = entry.get("symbol")
            if sym:
                symbol_freq[sym] = symbol_freq.get(sym, 0) + 1

        if symbol_freq:
            top = sorted(symbol_freq.items(), key=lambda x: x[1], reverse=True)[:5]
            patterns.append("Most-decided symbols: " + ", ".join(f"{s} ({c})" for s, c in top))

        # Direction distribution
        directions: dict[str, int] = {}
        for entry in self._decisions.values():
            d = entry.get("direction")
            if d:
                directions[d] = directions.get(d, 0) + 1

        if directions:
            patterns.append("Direction bias: " + ", ".join(f"{k}: {v}" for k, v in sorted(directions.items())))

        # Win rate for decided outcomes
        decided = [e for e in self._decisions.values() if e.get("outcome") in ("profit", "loss")]
        if decided:
            wins = sum(1 for e in decided if e.get("outcome") == "profit")
            win_rate = wins / len(decided) * 100
            patterns.append(f"Win rate: {win_rate:.1f}% ({wins}/{len(decided)})")

        patterns.append(f"Total decisions recorded: {len(self._decisions)}")
        return {"patterns": patterns}

    def _search_decisions(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        """Search decisions by query."""
        query = kwargs.get("query", "").lower()
        limit = kwargs.get("limit", 20)

        if not query:
            return self._list_decisions(kwargs)

        results = []
        for entry in self._decisions.values():
            searchable = (
                f"{entry.get('title', '')} {entry.get('context', '')} "
                f"{entry.get('decision', '')} {entry.get('reasoning', '')} "
                f"{entry.get('symbol', '')} {' '.join(entry.get('tags', []))}"
            ).lower()
            if query in searchable:
                results.append(entry)

        results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return {"results": results[:limit], "count": len(results), "query": query}
