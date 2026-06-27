# agents.tools.intermarket_tool

## Class: 

Market sectors for rotation analysis.

*Line: 49*

---

## Class: 

Sector rotation signal.

*Line: 64*

---

## Class: 

Correlation strength classification.

*Line: 73*

---

## Class: 

Correlation between two market instruments.

*Line: 88*

---

## Class: 

Full correlation matrix across market classes.

*Line: 99*

---

## Class: 

Relative strength analysis result.

*Line: 112*

---

## Class: 

Sector rotation analysis result.

*Line: 123*

---

## Class: 

Commodity-currency pair analysis.

*Line: 134*

---

## Class: 

Intermarket analysis tool for agent consumption.

Provides cross-market correlation analysis, relative strength,
sector rotation signals, and commodity-currency pair analysis.

When market data APIs are unavailable, the tool uses heuristic
estimates based on well-known intermarket relationships.

Usage::

    tool = IntermarketTool()
    matrix = await tool.analyze_correlations()
    rotation = await tool.analyze_sector_rotation()

**Methods:** __init__

*Line: 163*

---

## Function: 

*Line: 413*

---

## Function: 

*Line: 179*

---

## Function: 

*Line: 35*

---

## Function: 

*Line: 38*

---

