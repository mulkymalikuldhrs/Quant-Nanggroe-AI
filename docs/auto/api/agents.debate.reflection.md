# agents.debate.reflection

## Class: 

Handles reflection on debate quality and identifies gaps.

Analyzes the output of research and risk debates to determine
what information is missing, what arguments need strengthening,
and whether the debate has reached sufficient depth.

**Methods:** __init__, reflect_on_research_debate, reflect_on_risk_debate, _estimate_quality

*Line: 42*

---

## Class: 

Handles state propagation and insight passing between debate rounds.

Manages the flow of information from one round to the next,
ensuring that key insights are preserved and debated arguments
build upon previous rounds.

**Methods:** __init__, propagate_research_insights, propagate_risk_insights, should_continue_debate, propagation_history

*Line: 186*

---

## Class: 

Processes debate output to extract actionable trading signals.

Takes the raw debate output (judge decisions, summaries) and
extracts clear BUY/SELL/HOLD signals with confidence levels.

**Methods:** __init__, process_investment_signal, process_risk_signal, _extract_conditions

*Line: 298*

---

## Function: 

*Line: 51*

---

## Function: 

Reflect on the research debate quality.

Args:
    bull_history: Bull arguments
    bear_history: Bear arguments
    judge_decision: Judge's decision

Returns:
    Reflection analysis dictionary

*Line: 54*

---

## Function: 

Reflect on the risk debate quality.

Args:
    conservative_history: Conservative arguments
    neutral_history: Neutral arguments
    aggressive_history: Aggressive arguments
    judge_decision: Risk judge's decision

Returns:
    Reflection analysis dictionary

*Line: 101*

---

## Function: 

Estimate debate quality based on argument length and presence.

Args:
    side_a: One side's arguments
    side_b: Other side's arguments

Returns:
    Quality score between 0 and 1

*Line: 156*

---

## Function: 

*Line: 195*

---

## Function: 

Propagate research debate insights to the next round.

Args:
    debate_state: Current debate state
    reflection: Reflection analysis

Returns:
    Updated state with propagated insights

*Line: 199*

---

## Function: 

Propagate risk debate insights to the next round.

Args:
    debate_state: Current debate state
    reflection: Reflection analysis

Returns:
    Updated state with propagated insights

*Line: 228*

---

## Function: 

Determine if debate should continue based on quality and rounds.

Args:
    current_round: Current debate round
    max_rounds: Maximum allowed rounds
    quality_score: Current debate quality score
    quality_threshold: Minimum quality threshold

Returns:
    True if debate should continue, False if consensus reached

*Line: 257*

---

## Function: 

Get the history of propagations.

*Line: 283*

---

## Function: 

*Line: 306*

---

## Function: 

Process a research debate judge decision into a core signal.

Args:
    judge_decision: Judge's decision text

Returns:
    BUY, SELL, or HOLD

*Line: 309*

---

## Function: 

Process a risk debate judge decision into a structured signal.

Args:
    judge_decision: Risk judge's decision text

Returns:
    Dictionary with risk verdict and conditions

*Line: 333*

---

## Function: 

Extract conditions from a risk decision.

Args:
    decision: Risk judge decision text

Returns:
    List of condition strings

*Line: 358*

---

