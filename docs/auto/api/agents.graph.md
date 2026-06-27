# agents.graph

## Class: 

Main trading graph orchestrating the full trading pipeline.

Uses LangGraph StateGraph to define the agent workflow with
conditional edges for risk gates, council debates, and
emergency exits.

**Methods:** __init__, graph, _build_graph, _deterministic_risk_conditional, _market_analysis_node, _signal_generation_node, _risk_assessment_node, _deterministic_risk_gate_node, _kelly_sizing_node, _portfolio_optimization_node, _execution_decision_node, _order_execution_node, _reflection_node, _council_debate_node, _emergency_exit_node, run, run_stream

*Line: 71*

---

## Function: 

Initialize the trading graph.

Args:
    llm_provider: LLM provider name
    deep_think_model: Model for deep analysis tasks
    quick_think_model: Model for quick response tasks
    base_url: Optional API base URL
    api_key: Optional API key
    max_debate_rounds: Maximum debate rounds
    max_risk_rounds: Maximum risk debate rounds
    confidence_threshold: Confidence threshold for council debate

*Line: 80*

---

## Function: 

Get the compiled LangGraph graph.

*Line: 157*

---

## Function: 

Build the LangGraph trading graph.

Returns:
    Compiled StateGraph

*Line: 161*

---

## Function: 

Determine the next step after the DETERMINISTIC risk gate.

This is the FINAL routing decision — the deterministic gate's verdict
is the ultimate authority. The LLM risk agent's verdict was considered
earlier but is NOT the final word.

Args:
    state: Current agent state

Returns:
    Next node name

*Line: 217*

---

## Function: 

Market analysis node: runs researcher, macro, crypto, and forex agents.

Args:
    state: Current agent state

Returns:
    State updates with analysis outputs

*Line: 262*

---

## Function: 

Signal generation node: runs the strategist agent.

Args:
    state: Current agent state

Returns:
    State updates with generated signals

*Line: 333*

---

## Function: 

Risk assessment node: runs the LLM-based risk agent for QUALITATIVE analysis.

This provides qualitative risk analysis (sentiment, regime, narrative risk).
The DETERMINISTIC risk gate runs AFTER this node as the HARD GATE.

Args:
    state: Current agent state

Returns:
    State updates with LLM risk assessment

*Line: 367*

---

## Function: 

Deterministic risk gate node: runs the 9-checkpoint RiskCheckGate.

This is the HARD GATE — it runs AFTER the LLM risk agent and is the
FINAL authority on whether a trade can proceed. It CANNOT be bypassed.

The deterministic gate:
1. Takes trade decisions from the agent pipeline
2. Runs them through the deterministic RiskCheckGate (all 9 checkpoints)
3. Returns APPROVED, REJECTED, MODIFIED (with adjusted position size)
4. If REJECTED, provides the specific check that failed
5. If MODIFIED, provides the adjusted position size from Kelly

If both the LLM risk agent and deterministic gate disagree,
the deterministic gate WINS.

Args:
    state: Current agent state

Returns:
    State updates with deterministic risk gate results

*Line: 408*

---

## Function: 

Kelly sizing node: calculates optimal position sizes using Kelly Criterion.

Runs AFTER the deterministic risk gate approves a trade and BEFORE
portfolio optimization. Uses the deterministic Kelly Criterion engine
to calculate position sizes that respect constitutional limits.

Args:
    state: Current agent state

Returns:
    State updates with Kelly position sizing results

*Line: 471*

---

## Function: 

Portfolio optimization node.

Args:
    state: Current agent state

Returns:
    State updates with portfolio optimization

*Line: 504*

---

## Function: 

Execution decision node: runs the trader agent.

Args:
    state: Current agent state

Returns:
    State updates with trading decisions

*Line: 534*

---

## Function: 

Order execution node: runs the execution agent.

Args:
    state: Current agent state

Returns:
    State updates with executed orders

*Line: 567*

---

## Function: 

Reflection node: post-trade analysis and learning.

Args:
    state: Current agent state

Returns:
    State updates with reflection results

*Line: 599*

---

## Function: 

Council debate node: runs when confidence is below threshold.

Args:
    state: Current agent state

Returns:
    State updates with council debate results

*Line: 625*

---

## Function: 

Emergency exit node: closes all positions immediately.

Args:
    state: Current agent state

Returns:
    State updates with emergency exit actions

*Line: 681*

---

## Function: 

Run the complete trading pipeline.

Args:
    symbols: List of trading symbols to analyze
    trade_date: Trading date string (YYYY-MM-DD)
    market_data: Optional pre-loaded market data
    metadata: Optional additional metadata

Returns:
    Final agent state after pipeline completion

*Line: 711*

---

## Function: 

Run the trading pipeline with streaming output.

Args:
    symbols: List of trading symbols
    trade_date: Trading date string
    **kwargs: Additional arguments passed to run()

Yields:
    State updates as they occur

*Line: 756*

---

