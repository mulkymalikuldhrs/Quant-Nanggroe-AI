"""
Agent Registry and Factory for Quant Nanggroe AI Trading Framework.

Provides a centralized registry for agent types and a factory for creating
agent instances with proper LLM configuration and tool binding.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional, Type

from langchain_core.language_models import BaseChatModel

from quant_nanggroe.agents.base import BaseAgent, create_llm
from quant_nanggroe.agents.state import AgentRole


logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Centralized registry for trading agent types.

    Maintains a mapping of agent names/roles to their factory functions,
    enabling dynamic agent creation and lookup. Supports registration
    of custom agent types at runtime.
    """

    _registry: Dict[str, Callable[..., BaseAgent]] = {}
    _role_mapping: Dict[AgentRole, str] = {}

    @classmethod
    def register(cls, name: str, role: AgentRole) -> Callable:
        """
        Decorator to register an agent class in the registry.

        Args:
            name: Unique agent name for registration
            role: Agent role type

        Returns:
            Decorator function
        """
        def decorator(agent_class: Type[BaseAgent]) -> Type[BaseAgent]:
            cls._registry[name] = agent_class
            cls._role_mapping[role] = name
            logger.debug(f"Registered agent: {name} (role={role.value})")
            return agent_class
        return decorator

    @classmethod
    def get(cls, name: str) -> Optional[Callable[..., BaseAgent]]:
        """
        Get an agent factory by name.

        Args:
            name: Agent name to look up

        Returns:
            Agent factory function, or None if not found
        """
        return cls._registry.get(name)

    @classmethod
    def get_by_role(cls, role: AgentRole) -> Optional[Callable[..., BaseAgent]]:
        """
        Get an agent factory by role.

        Args:
            role: Agent role to look up

        Returns:
            Agent factory function, or None if not found
        """
        name = cls._role_mapping.get(role)
        if name:
            return cls._registry.get(name)
        return None

    @classmethod
    def list_agents(cls) -> List[str]:
        """
        List all registered agent names.

        Returns:
            List of registered agent names
        """
        return list(cls._registry.keys())

    @classmethod
    def list_roles(cls) -> Dict[AgentRole, str]:
        """
        List all registered agent roles.

        Returns:
            Dictionary mapping roles to agent names
        """
        return dict(cls._role_mapping)

    @classmethod
    def clear(cls) -> None:
        """Clear the registry (useful for testing)."""
        cls._registry.clear()
        cls._role_mapping.clear()


class AgentFactory:
    """
    Factory for creating configured agent instances.

    Handles LLM initialization, tool binding, and agent instantiation
    based on configuration parameters.
    """

    def __init__(
        self,
        llm_provider: str = "openai",
        deep_think_model: str = "gpt-4o",
        quick_think_model: str = "gpt-4o-mini",
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        temperature: float = 0.0,
    ) -> None:
        """
        Initialize the agent factory.

        Args:
            llm_provider: LLM provider name
            deep_think_model: Model for deep thinking tasks
            quick_think_model: Model for quick response tasks
            base_url: Optional API base URL
            api_key: Optional API key
            temperature: Default sampling temperature
        """
        self.llm_provider = llm_provider
        self.deep_think_model = deep_think_model
        self.quick_think_model = quick_think_model
        self.base_url = base_url
        self.api_key = api_key
        self.temperature = temperature

        # Lazy-initialized LLM instances
        self._deep_llm: Optional[BaseChatModel] = None
        self._quick_llm: Optional[BaseChatModel] = None

    def get_deep_llm(self) -> BaseChatModel:
        """
        Get or create the deep-thinking LLM instance.

        Returns:
            Configured LLM for deep analysis tasks
        """
        if self._deep_llm is None:
            self._deep_llm = create_llm(
                provider=self.llm_provider,
                model=self.deep_think_model,
                base_url=self.base_url,
                api_key=self.api_key,
                temperature=self.temperature,
            )
        return self._deep_llm

    def get_quick_llm(self) -> BaseChatModel:
        """
        Get or create the quick-thinking LLM instance.

        Returns:
            Configured LLM for fast response tasks
        """
        if self._quick_llm is None:
            self._quick_llm = create_llm(
                provider=self.llm_provider,
                model=self.quick_think_model,
                base_url=self.base_url,
                api_key=self.api_key,
                temperature=self.temperature,
            )
        return self._quick_llm

    def create_agent(
        self,
        name: str,
        use_deep_llm: bool = False,
        **kwargs: Any,
    ) -> BaseAgent:
        """
        Create an agent instance by name.

        Args:
            name: Registered agent name
            use_deep_llm: Whether to use the deep-thinking LLM
            **kwargs: Additional arguments passed to the agent constructor

        Returns:
            Configured agent instance

        Raises:
            ValueError: If the agent name is not registered
        """
        agent_factory = AgentRegistry.get(name)
        if agent_factory is None:
            raise ValueError(
                f"Agent '{name}' not registered. "
                f"Available agents: {AgentRegistry.list_agents()}"
            )

        llm = self.get_deep_llm() if use_deep_llm else self.get_quick_llm()
        return agent_factory(llm=llm, **kwargs)

    def create_all_agents(self, **kwargs: Any) -> Dict[str, BaseAgent]:
        """
        Create instances of all registered agents.

        Args:
            **kwargs: Additional arguments passed to agent constructors

        Returns:
            Dictionary mapping agent names to agent instances
        """
        agents: Dict[str, BaseAgent] = {}

        # Define which agents use deep thinking
        deep_agents = {"strategist", "risk", "council"}

        for name in AgentRegistry.list_agents():
            use_deep = name in deep_agents
            try:
                agents[name] = self.create_agent(name, use_deep_llm=use_deep, **kwargs)
                logger.info(f"Created agent: {name} (deep_llm={use_deep})")
            except Exception as e:
                logger.error(f"Failed to create agent {name}: {e}")

        return agents

    def create_analysis_agents(self, **kwargs: Any) -> Dict[str, BaseAgent]:
        """
        Create only the analysis-phase agents (researcher, macro, crypto, forex).

        Args:
            **kwargs: Additional arguments passed to agent constructors

        Returns:
            Dictionary of analysis agent instances
        """
        analysis_names = ["researcher", "macro", "crypto", "forex"]
        agents: Dict[str, BaseAgent] = {}

        for name in analysis_names:
            try:
                agents[name] = self.create_agent(name, use_deep_llm=False, **kwargs)
                logger.info(f"Created analysis agent: {name}")
            except Exception as e:
                logger.error(f"Failed to create analysis agent {name}: {e}")

        return agents

    def create_decision_agents(self, **kwargs: Any) -> Dict[str, BaseAgent]:
        """
        Create only the decision-phase agents (strategist, risk, trader, portfolio, execution).

        Args:
            **kwargs: Additional arguments passed to agent constructors

        Returns:
            Dictionary of decision agent instances
        """
        decision_names = ["strategist", "risk", "trader", "portfolio", "execution"]
        agents: Dict[str, BaseAgent] = {}

        for name in decision_names:
            use_deep = name in ("strategist", "risk")
            try:
                agents[name] = self.create_agent(name, use_deep_llm=use_deep, **kwargs)
                logger.info(f"Created decision agent: {name}")
            except Exception as e:
                logger.error(f"Failed to create decision agent {name}: {e}")

        return agents
