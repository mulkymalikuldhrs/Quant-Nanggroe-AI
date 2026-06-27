# agents.personas.base_investor

## Function: 

Get valuation metrics for a symbol.

Args:
    symbol: Stock ticker symbol
    metric_type: Type of metrics (overview, dcf, relative, owner_earnings)

Returns:
    JSON string with valuation data

*Line: 41*

---

## Function: 

Assess financial health of a company.

Args:
    symbol: Stock ticker symbol

Returns:
    JSON string with financial health assessment

*Line: 67*

---

## Function: 

Analyze competitive moat strength.

Args:
    symbol: Stock ticker symbol

Returns:
    JSON string with moat analysis

*Line: 92*

---

## Function: 

Assess management quality and capital allocation.

Args:
    symbol: Stock ticker symbol

Returns:
    JSON string with management quality assessment

*Line: 117*

---

## Class: 

Base class for investor persona agents.

Each persona inherits from this class and provides:
- A unique system prompt embodying the investor's philosophy
- Investor-specific analysis tools
- A consistent analysis workflow

The base class handles the common analysis pipeline:
1. Gather financial data via shared tools
2. Apply investor-specific analytical framework
3. Generate signal (bullish/bearish/neutral) with confidence

**Methods:** __init__, investor_name, run, _extract_signal, _assess_confidence

*Line: 147*

---

## Function: 

Initialize investor persona agent.

Args:
    name: Agent registration name
    llm: Language model instance
    system_prompt: Investor-specific system prompt
    investor_name: Display name of the investor
    tools: Optional additional tools

*Line: 162*

---

## Function: 

Get the investor's display name.

*Line: 196*

---

## Function: 

Execute investor persona analysis.

Args:
    state: Current agent state

Returns:
    State updates with investor analysis

*Line: 200*

---

## Function: 

Extract investment signal from content.

*Line: 259*

---

## Function: 

Assess confidence of investor analysis output.

*Line: 268*

---

## Function: 

No-op fallback when langchain_core is not installed.

*Line: 22*

---

## Function: 

*Line: 26*

---

