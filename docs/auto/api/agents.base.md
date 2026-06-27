# agents.base

## Function: 

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

*Line: 56*

---

## Class: 

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

**Methods:** __init__, name, role, description, llm, tools, tool_node, default_system_prompt, format_state_for_prompt, invoke_llm, build_messages, create_output, run, __call__, __repr__

*Line: 127*

---

## Function: 

Initialize the base agent.

Args:
    name: Unique agent name
    role: Agent role type
    description: Human-readable description
    llm: Language model instance (None if langchain not installed)
    tools: Optional list of LangChain tools
    system_prompt: Optional system prompt for the agent

*Line: 144*

---

## Function: 

Get the agent's name.

*Line: 181*

---

## Function: 

Get the agent's role.

*Line: 186*

---

## Function: 

Get the agent's description.

*Line: 191*

---

## Function: 

Get the agent's LLM instance.

*Line: 196*

---

## Function: 

Get the agent's tools.

*Line: 201*

---

## Function: 

Get the agent's ToolNode.

*Line: 206*

---

## Function: 

Return the default system prompt for this agent.

Override in subclasses to customize the system prompt.

Returns:
    Default system prompt string

*Line: 210*

---

## Function: 

Format the current agent state into a human-readable prompt section.

Args:
    state: Current agent state

Returns:
    Formatted state string for inclusion in prompts

*Line: 228*

---

## Function: 

Invoke the LLM with the given messages.

Args:
    messages: List of message objects
    use_tools: Whether to use tool-binding

Returns:
    LLM response message

*Line: 266*

---

## Function: 

Build the message list for LLM invocation.

Args:
    state: Current agent state
    user_content: Optional user message content

Returns:
    List of messages for LLM invocation

*Line: 285*

---

## Function: 

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

*Line: 313*

---

## Function: 

Execute the agent's main logic and return state updates.

This is the primary method that each agent must implement.
It receives the current state and returns a dictionary of
state updates to merge back into the graph state.

Args:
    state: Current agent state from the LangGraph graph

Returns:
    Dictionary of state updates to merge into the graph state

*Line: 349*

---

## Function: 

Make the agent callable for LangGraph node integration.

Args:
    state: Current agent state

Returns:
    State updates from running the agent

*Line: 365*

---

## Function: 

Return string representation of the agent.

*Line: 394*

---

