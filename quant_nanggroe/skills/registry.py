"""Vibe-Trading-inspired skill taxonomy for QNA trading strategies."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SkillCategory(Enum):
    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    SENTIMENT = "sentiment"
    RISK = "risk"
    EXECUTION = "execution"
    ANALYSIS = "analysis"


@dataclass
class SkillDef:
    name: str
    category: SkillCategory
    description: str
    params: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)


class SkillRegistry:
    """Registry of composable trading skills."""

    def __init__(self):
        self.skills: Dict[str, SkillDef] = {}

    def register(self, skill: SkillDef):
        self.skills[skill.name] = skill
        logger.info(f"Registered skill: {skill.name} ({skill.category.value})")

    def get_by_category(self, category: SkillCategory) -> List[SkillDef]:
        return [s for s in self.skills.values() if s.category == category]

    def get_dependency_chain(self, skill_name: str) -> List[str]:
        """Get ordered list of skills needed before this one."""
        chain = []
        visited = set()

        def resolve(name):
            if name in visited:
                return
            visited.add(name)
            skill = self.skills.get(name)
            if skill:
                for dep in skill.dependencies:
                    resolve(dep)
                chain.append(name)

        resolve(skill_name)
        return chain

    def compose(self, skill_names: List[str]) -> Optional[List[SkillDef]]:
        """Compose multiple skills into a pipeline, resolving dependencies."""
        ordered = []
        for name in skill_names:
            chain = self.get_dependency_chain(name)
            for s in chain:
                if s not in ordered:
                    ordered.append(s)
        return [self.skills[name] for name in ordered if name in self.skills]
