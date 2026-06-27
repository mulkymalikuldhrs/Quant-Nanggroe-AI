# agents.researcher.agent

## Class: 

Research Agent that conducts deep financial research.

Uses web search, SEC filings, news analysis, and financial data
to produce comprehensive research reports on requested symbols.
These reports feed into the Strategist agent for signal generation.

**Methods:** __init__, run, _execute_tool, _build_additional_context, _assess_confidence

*Line: 37*

---

## Function: 

Initialize the Researcher Agent.

Args:
    llm: Language model instance
    tools: Optional list of tools (defaults to research tools)
    system_prompt: Optional custom system prompt

*Line: 46*

---

## Function: 

Execute research on the requested symbols.

Gathers information from multiple sources using available tools,
then synthesizes findings into a structured research report.

Args:
    state: Current agent state

Returns:
    Dictionary with research_output and updated agent_outputs

*Line: 73*

---

## Function: 

Execute a single tool call.

Args:
    tool_call: Tool call dictionary with 'name' and 'args'

Returns:
    Tool execution result as string

*Line: 150*

---

## Function: 

Build additional context string from existing state.

Args:
    state: Current agent state

Returns:
    Additional context string

*Line: 170*

---

## Function: 

Assess the confidence level of the research output.

Args:
    content: Research output content
    symbols: Symbols that were researched

Returns:
    Confidence level between 0.0 and 1.0

*Line: 196*

---

