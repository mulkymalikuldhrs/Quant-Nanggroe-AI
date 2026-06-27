# agents.tools.flow_tool

## Class: 

Flow direction classification.

*Line: 49*

---

## Class: 

Positioning crowd signal.

*Line: 58*

---

## Class: 

CFTC Commitment of Traders report data.

*Line: 67*

---

## Class: 

Whale (large) transaction record.

*Line: 80*

---

## Class: 

Composite flow direction score.

*Line: 92*

---

## Class: 

Positioning crowd analysis result.

*Line: 104*

---

## Class: 

Whale flow and COT positioning analysis tool for agent consumption.

Provides institutional flow analysis, whale tracking, COT data parsing,
and positioning crowd analysis for contrarian signals.

When COT data or whale tracking APIs are unavailable, the tool gracefully
degrades and returns low-confidence estimates.

Usage::

    tool = FlowTool()
    flow = await tool.analyze_flow("EURUSD")
    positioning = await tool.analyze_positioning("GC")

**Methods:** __init__, _get_cache, _set_cache

*Line: 120*

---

## Function: 

*Line: 433*

---

## Function: 

*Line: 136*

---

## Function: 

*Line: 412*

---

## Function: 

*Line: 422*

---

## Function: 

Fallback no-op decorator when langchain is not installed.

*Line: 34*

---

## Function: 

*Line: 38*

---

