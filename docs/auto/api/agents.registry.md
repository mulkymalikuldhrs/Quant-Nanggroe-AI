# agents.registry

## Class: 

Centralized registry for trading agent types.

Maintains a mapping of agent names/roles to their factory functions,
enabling dynamic agent creation and lookup. Supports registration
of custom agent types at runtime.

**Methods:** register, get, get_by_role, list_agents, list_roles, clear

*Line: 25*

---

## Class: 

Factory for creating configured agent instances.

Handles LLM initialization, tool binding, and agent instantiation
based on configuration parameters.

**Methods:** __init__, get_deep_llm, get_quick_llm, create_agent, create_all_agents, create_analysis_agents, create_decision_agents

*Line: 112*

---

## Function: 

Decorator to register an agent class in the registry.

Args:
    name: Unique agent name for registration
    role: Agent role type

Returns:
    Decorator function

*Line: 38*

---

## Function: 

Get an agent factory by name.

Args:
    name: Agent name to look up

Returns:
    Agent factory function, or None if not found

*Line: 57*

---

## Function: 

Get an agent factory by role.

Args:
    role: Agent role to look up

Returns:
    Agent factory function, or None if not found

*Line: 70*

---

## Function: 

List all registered agent names.

Returns:
    List of registered agent names

*Line: 86*

---

## Function: 

List all registered agent roles.

Returns:
    Dictionary mapping roles to agent names

*Line: 96*

---

## Function: 

Clear the registry (useful for testing).

*Line: 106*

---

## Function: 

Initialize the agent factory.

Args:
    llm_provider: LLM provider name
    deep_think_model: Model for deep thinking tasks
    quick_think_model: Model for quick response tasks
    base_url: Optional API base URL
    api_key: Optional API key
    temperature: Default sampling temperature

*Line: 120*

---

## Function: 

Get or create the deep-thinking LLM instance.

Returns:
    Configured LLM for deep analysis tasks

*Line: 151*

---

## Function: 

Get or create the quick-thinking LLM instance.

Returns:
    Configured LLM for fast response tasks

*Line: 168*

---

## Function: 

Create an agent instance by name.

Args:
    name: Registered agent name
    use_deep_llm: Whether to use the deep-thinking LLM
    **kwargs: Additional arguments passed to the agent constructor

Returns:
    Configured agent instance

Raises:
    ValueError: If the agent name is not registered

*Line: 185*

---

## Function: 

Create instances of all registered agents.

Args:
    **kwargs: Additional arguments passed to agent constructors

Returns:
    Dictionary mapping agent names to agent instances

*Line: 234*

---

## Function: 

Create only the analysis-phase agents (researcher, macro, crypto, forex).

Args:
    **kwargs: Additional arguments passed to agent constructors

Returns:
    Dictionary of analysis agent instances

*Line: 259*

---

## Function: 

Create only the decision-phase agents (strategist, risk, trader, portfolio, execution).

Args:
    **kwargs: Additional arguments passed to agent constructors

Returns:
    Dictionary of decision agent instances

*Line: 281*

---

## Function: 

*Line: 49*

---

