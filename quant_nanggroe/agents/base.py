"""
Base Agent for Quant Nanggroe AI Trading Framework.

Provides the abstract base class that all specialized agents inherit from.
Integrates with LangGraph via ToolNode and supports multiple LLM providers.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Sequence, Type

try:
    from langchain_core.language_models import BaseChatModel
except ImportError:
    BaseChatModel = None

try:
    from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
except ImportError:
    AIMessage = BaseMessage = HumanMessage = SystemMessage = None

try:
    from langchain_core.tools import BaseTool
except ImportError:
    BaseTool = None

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    ChatOpenAI = None

try:
    from langchain_anthropic import ChatAnthropic
except ImportError:
    ChatAnthropic = None

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:
    ChatGoogleGenerativeAI = None

try:
    from langgraph.prebuilt import ToolNode
except ImportError:
    ToolNode = None

from quant_nanggroe.agents.state import AgentOutput, AgentRole, AgentState


logger = logging.getLogger(__name__)


def create_llm(
    provider: str,
    model: str,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    temperature: float = 0.0,
    **kwargs: Any,
) -> BaseChatModel:
    """
    Create an LLM instance based on the specified provider.

    Args:
        provider: LLM provider name (openai, anthropic, google, ollama, openrouter)
        model: Model name to use
        base_url: Optional base URL for the API
        api_key: Optional API key
        temperature: Sampling temperature
        **kwargs: Additional provider-specific arguments

    Returns:
        A configured BaseChatModel instance

    Raises:
        ImportError: If the required langchain package is not installed
        ValueError: If the provider is not supported
    """
    provider_lower = provider.lower()

    if provider_lower in ("openai", "ollama", "openrouter"):
        if ChatOpenAI is None:
            raise ImportError(
                "langchain_openai is required for the openai/ollama/openrouter provider. "
                "Install with: pip install langchain-openai"
            )
        return ChatOpenAI(
            model=model,
            base_url=base_url,
            api_key=api_key,
            temperature=temperature,
            **kwargs,
        )
    elif provider_lower == "anthropic":
        if ChatAnthropic is None:
            raise ImportError(
                "langchain_anthropic is required for the anthropic provider. "
                "Install with: pip install langchain-anthropic"
            )
        return ChatAnthropic(
            model=model,
            base_url=base_url,
            api_key=api_key,
            temperature=temperature,
            **kwargs,
        )
    elif provider_lower == "google":
        if ChatGoogleGenerativeAI is None:
            raise ImportError(
                "langchain_google_genai is required for the google provider. "
                "Install with: pip install langchain-google-genai"
            )
        return ChatGoogleGenerativeAI(
            model=model,
            api_key=api_key,
            temperature=temperature,
            **kwargs,
        )
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}. "
                         f"Supported: openai, anthropic, google, ollama, openrouter")


class BaseAgent(ABC):
    """
    Abstract base class for all trading agents.

    Provides a common interface for agent execution, tool binding,
    LLM integration, and structured output. All specialized agents
    must inherit from this class and implement the `run` method.

    Attributes:
        name: Unique agent name
        role: Agent role type
        description: Human-readable description
        llm: Language model instance
        tools: List of available tools
        tool_node: LangGraph ToolNode for tool execution
    """

    def __init__(
        self,
        name: str,
        role: AgentRole,
        description: str,
        llm: BaseChatModel = None,
        tools: Optional[List[BaseTool]] = None,
        system_prompt: Optional[str] = None,
    ) -> None:
        """
        Initialize the base agent.

        Args:
            name: Unique agent name
            role: Agent role type
            description: Human-readable description
            llm: Language model instance (None if langchain not installed)
            tools: Optional list of LangChain tools
            system_prompt: Optional system prompt for the agent
        """
        self._name = name
        self._role = role
        self._description = description
        self._llm = llm
        self._tools = tools or []
        self._system_prompt = system_prompt or self.default_system_prompt()
        self._tool_node = ToolNode(self._tools) if self._tools and ToolNode is not None else None

        # Bind tools to LLM if tools exist and LLM supports it
        if self._tools and self._llm is not None and hasattr(self._llm, "bind_tools"):
            self._llm_with_tools = self._llm.bind_tools(self._tools)
        else:
            self._llm_with_tools = self._llm

        logger.info(f"Initialized agent: {self._name} (role={self._role.value})")

    @property
    def name(self) -> str:
        """Get the agent's name."""
        return self._name

    @property
    def role(self) -> AgentRole:
        """Get the agent's role."""
        return self._role

    @property
    def description(self) -> str:
        """Get the agent's description."""
        return self._description

    @property
    def llm(self) -> BaseChatModel:
        """Get the agent's LLM instance."""
        return self._llm

    @property
    def tools(self) -> List[BaseTool]:
        """Get the agent's tools."""
        return self._tools

    @property
    def tool_node(self) -> Optional[ToolNode]:
        """Get the agent's ToolNode."""
        return self._tool_node

    def default_system_prompt(self) -> str:
        """
        Return the default system prompt for this agent.

        Override in subclasses to customize the system prompt.

        Returns:
            Default system prompt string
        """
        return (
            f"You are {self._name}, a {self._role.value} agent in the "
            f"Quant Nanggroe AI Trading Framework. "
            f"{self._description} "
            f"Always provide structured, data-driven analysis. "
            f"Include confidence levels in your assessments. "
            f"Be thorough but concise."
        )

    def format_state_for_prompt(self, state: AgentState) -> str:
        """
        Format the current agent state into a human-readable prompt section.

        Args:
            state: Current agent state

        Returns:
            Formatted state string for inclusion in prompts
        """
        parts = [
            f"Trading Date: {state.get('trade_date', 'N/A')}",
            f"Symbols: {', '.join(state.get('symbols', []))}",
        ]

        # Add market data summary
        market_data = state.get("market_data", {})
        if market_data:
            parts.append("\nMarket Data:")
            for symbol, data in market_data.items():
                if isinstance(data, dict):
                    price = data.get("price", data.get("close", "N/A"))
                    change = data.get("change_pct", "N/A")
                    parts.append(f"  {symbol}: Price={price}, Change={change}%")

        # Add previous agent outputs
        agent_outputs = state.get("agent_outputs", {})
        if agent_outputs:
            parts.append("\nPrevious Agent Outputs:")
            for agent_name, output in agent_outputs.items():
                if isinstance(output, dict):
                    content = output.get("content", str(output))[:500]
                else:
                    content = str(output)[:500]
                parts.append(f"  [{agent_name}]: {content}")

        return "\n".join(parts)

    def invoke_llm(
        self,
        messages: List[BaseMessage],
        use_tools: bool = False,
    ) -> BaseMessage:
        """
        Invoke the LLM with the given messages.

        Args:
            messages: List of message objects
            use_tools: Whether to use tool-binding

        Returns:
            LLM response message
        """
        llm = self._llm_with_tools if use_tools and self._tools else self._llm
        response = llm.invoke(messages)
        return response

    def build_messages(
        self,
        state: AgentState,
        user_content: Optional[str] = None,
    ) -> List[BaseMessage]:
        """
        Build the message list for LLM invocation.

        Args:
            state: Current agent state
            user_content: Optional user message content

        Returns:
            List of messages for LLM invocation
        """
        messages = [SystemMessage(content=self._system_prompt)]

        # Add state context
        state_context = self.format_state_for_prompt(state)
        if state_context:
            messages.append(HumanMessage(content=f"Current Context:\n{state_context}"))

        # Add user content
        if user_content:
            messages.append(HumanMessage(content=user_content))

        return messages

    def create_output(
        self,
        content: str,
        data: Optional[Dict[str, Any]] = None,
        confidence: float = 0.0,
        success: bool = True,
        error: Optional[str] = None,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
    ) -> AgentOutput:
        """
        Create a structured AgentOutput from this agent's execution.

        Args:
            content: Agent's text output
            data: Structured output data
            confidence: Agent's confidence level
            success: Whether execution succeeded
            error: Error message if failed
            tool_calls: Tool calls made during execution

        Returns:
            Structured AgentOutput instance
        """
        return AgentOutput(
            agent_name=self._name,
            agent_role=self._role,
            content=content,
            data=data or {},
            confidence=confidence,
            success=success,
            error=error,
            timestamp=datetime.now(),
            tool_calls=tool_calls or [],
        )

    @abstractmethod
    def run(self, state: AgentState) -> Dict[str, Any]:
        """
        Execute the agent's main logic and return state updates.

        This is the primary method that each agent must implement.
        It receives the current state and returns a dictionary of
        state updates to merge back into the graph state.

        Args:
            state: Current agent state from the LangGraph graph

        Returns:
            Dictionary of state updates to merge into the graph state
        """
        ...

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """
        Make the agent callable for LangGraph node integration.

        Args:
            state: Current agent state

        Returns:
            State updates from running the agent
        """
        try:
            result = self.run(state)
            logger.info(f"Agent {self._name} completed successfully")
            return result
        except Exception as e:
            logger.error(f"Agent {self._name} failed: {e}")
            error_output = self.create_output(
                content=f"Agent execution failed: {str(e)}",
                success=False,
                error=str(e),
            )
            return {
                "agent_outputs": {
                    **state.get("agent_outputs", {}),
                    self._name: error_output.model_dump(),
                },
                "sender": self._name,
            }

    def __repr__(self) -> str:
        """Return string representation of the agent."""
        return f"{self.__class__.__name__}(name={self._name}, role={self._role.value})"
