# agents.debate.graph

## Class: 

Final result from the trading debate.

**Methods:** __init__, to_dict

*Line: 28*

---

## Class: 

Full trading debate graph combining research and risk debates.

Orchestrates the full debate flow:
1. Bull/Bear research debate (configurable rounds)
2. Risk debate (Conservative/Neutral/Aggressive)
3. Final decision synthesis

Usage::

    graph = TradingDebateGraph(max_research_rounds=3)
    result = await graph.run(symbol="AAPL", market_data={...})

**Methods:** __init__

*Line: 64*

---

## Function: 

*Line: 31*

---

## Function: 

*Line: 51*

---

## Function: 

*Line: 78*

---

