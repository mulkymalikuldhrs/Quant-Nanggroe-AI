# types.decisions

## Class: 

Final decision classification.

*Line: 16*

---

## Class: 

Confluence scoring across multiple agents.

Measures agreement between agents before making a decision.
Higher confluence = more confidence in the decision.

**Methods:** compute_consensus

*Line: 27*

---

## Class: 

Decision table mapping conditions to actions.

Based on Quant-Nanggroe-AI's 5-layer deterministic decision pipeline.
Each entry maps a set of conditions to a trading action.

*Line: 60*

---

## Class: 

Final trading decision from the Trading Graph.

This is the output of the decision pipeline after all agents
have contributed their analysis and the risk engine has approved.

*Line: 80*

---

## Function: 

Determine consensus from agent distribution.

*Line: 44*

---

