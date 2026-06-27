# agents.trader.agent

## Class: 

Trader Agent that makes final trading decisions.

Synthesizes all agent outputs into a final BUY/SELL/HOLD decision
with precise entry, stop-loss, and take-profit levels. Respects
risk verdicts and kill switch status unconditionally.

**Methods:** __init__, run, _emergency_exit, _vetoed_decision, _parse_decisions, _extract_confidence

*Line: 34*

---

## Function: 

Initialize the Trader Agent.

Args:
    llm: Language model instance
    tools: Optional list of tools (defaults to trader tools)
    system_prompt: Optional custom system prompt

*Line: 43*

---

## Function: 

Execute the trading decision process.

Args:
    state: Current agent state

Returns:
    Dictionary with decisions, trader_output, and updated agent_outputs

*Line: 70*

---

## Function: 

Handle emergency exit when kill switch is active.

Args:
    state: Current agent state

Returns:
    State updates with emergency exit decision

*Line: 142*

---

## Function: 

Handle vetoed risk assessment.

Args:
    state: Current agent state
    risk_verdict: The risk verdict that caused the veto

Returns:
    State updates with HOLD decision

*Line: 183*

---

## Function: 

Parse trading decisions from the LLM output.

Args:
    content: LLM output content
    state: Current agent state

Returns:
    List of decision dictionaries

*Line: 226*

---

## Function: 

Extract confidence level from content.

Args:
    content: LLM output content

Returns:
    Confidence level between 0.0 and 1.0

*Line: 271*

---

