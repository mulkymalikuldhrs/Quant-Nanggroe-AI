"""AI-Trader inspired agent marketplace for signal trading."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Any


@dataclass
class AgentListing:
    agent_id: str
    name: str
    strategy: str
    asset_class: str
    signal_history: List[Dict] = field(default_factory=list)
    rating: float = 0.0


class AgentMarketplace:
    def __init__(self):
        self.agents: Dict[str, AgentListing] = {}

    def register(self, listing: AgentListing):
        self.agents[listing.agent_id] = listing

    def find_by_asset(self, asset_class: str) -> List[AgentListing]:
        return [a for a in self.agents.values() if a.asset_class == asset_class]

    def find_top_rated(self, n: int = 5) -> List[AgentListing]:
        return sorted(self.agents.values(), key=lambda a: a.rating, reverse=True)[:n]
