# agents.tools.screener_tool

## Class: 

Final screening verdict.

*Line: 49*

---

## Class: 

Screening component names.

*Line: 61*

---

## Class: 

Individual component screening score.

*Line: 81*

---

## Class: 

Filter criteria for screening.

*Line: 92*

---

## Class: 

Execution plan from screening.

*Line: 105*

---

## Class: 

Complete screening result for a symbol.

*Line: 119*

---

## Class: 

12-component screening engine for agent consumption.

Provides comprehensive screening with technical, fundamental, sentiment,
macro, DEX, liquidity, order book, positioning, quant scoring, market
structure, execution plan, and final verdict components.

Each component is scored independently (0-100) and combined into a
composite score with configurable weights.

Usage::

    tool = ScreenerTool()
    result = await tool.screen("AAPL")
    batch = await tool.screen_batch(["AAPL", "GOOGL", "MSFT"])

**Methods:** __init__, _score_to_verdict, _generate_execution_plan, _apply_filters, _get_cache, _set_cache

*Line: 153*

---

## Function: 

*Line: 533*

---

## Function: 

*Line: 170*

---

## Function: 

Convert composite score to verdict.

*Line: 366*

---

## Function: 

Generate an execution plan based on screening results.

*Line: 386*

---

## Function: 

Apply filter criteria to screening results.

*Line: 427*

---

## Function: 

*Line: 512*

---

## Function: 

*Line: 522*

---

## Function: 

*Line: 35*

---

## Function: 

*Line: 38*

---

