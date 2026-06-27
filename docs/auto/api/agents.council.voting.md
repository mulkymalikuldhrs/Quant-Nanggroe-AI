# agents.council.voting

## Class: 

Weighted voting mechanism for the trading council.

Each agent casts a vote weighted by their historical accuracy.
The final decision is determined by the highest weighted score.

**Methods:** __init__, collect_votes, compute_weighted_scores, determine_decision, compute_consensus, run_council_vote, _extract_vote, _summarize_debate

*Line: 90*

---

## Function: 

Initialize the council voting system.

Args:
    llm: Language model for vote synthesis
    voter_weights: Custom voter weights (defaults to DEFAULT_VOTER_WEIGHTS)
    consensus_threshold: Minimum consensus level for automatic execution

*Line: 98*

---

## Function: 

Collect votes from all agents based on their outputs.

Args:
    state: Current agent state with all agent outputs

Returns:
    List of VoteResult instances

*Line: 116*

---

## Function: 

Compute weighted scores for each trade action.

Args:
    votes: List of vote results

Returns:
    Dictionary mapping action to weighted score

*Line: 153*

---

## Function: 

Determine the final council decision from weighted scores.

Args:
    scores: Weighted scores by action

Returns:
    Final TradeAction based on highest weighted score

*Line: 172*

---

## Function: 

Compute the consensus level of the council.

Args:
    votes: List of vote results
    scores: Weighted scores by action

Returns:
    Consensus level between 0.0 and 1.0

*Line: 191*

---

## Function: 

Run the full council voting process.

Args:
    state: Current agent state

Returns:
    CouncilResult with final decision and all vote details

*Line: 214*

---

## Function: 

Extract a vote from an agent's output.

Args:
    agent_name: Name of the voting agent
    output: Agent output dictionary
    state: Current agent state

Returns:
    Tuple of (vote_action, confidence, reasoning)

*Line: 261*

---

## Function: 

Create a summary of the debate for the council result.

Args:
    debate_state: Debate state dictionary

Returns:
    Debate summary string

*Line: 328*

---

