# agents.geopolitics.base

## Function: 

Check sanctions status for an entity or country.

Args:
    entity: Company, individual, or sector to check
    country: Optional country filter

Returns:
    JSON string with sanctions status

*Line: 42*

---

## Function: 

Analyze trade flows between countries/regions.

Args:
    origin: Exporting country/region
    destination: Importing country/region
    commodity: Optional commodity filter

Returns:
    JSON string with trade flow data

*Line: 66*

---

## Function: 

Analyze currency impact from geopolitical events.

Args:
    base_currency: Base currency code (e.g., USD)
    quote_currency: Quote currency code (e.g., CNY)
    scenario: Scenario type (current, escalation, deescalation)

Returns:
    JSON string with currency impact analysis

*Line: 96*

---

## Function: 

Analyze commodity exposure from geopolitical perspective.

Args:
    commodity: Commodity name (e.g., oil, gold, rare_earth)
    region: Geographic region

Returns:
    JSON string with commodity exposure analysis

*Line: 125*

---

## Class: 

Base class for geopolitics-perspective agents.

Provides shared infrastructure for all geopolitics agents including
common tools (sanctions_checker, trade_flow_analyzer, currency_impact,
commodity_exposure) and a standard analysis workflow.

**Methods:** __init__, run, _build_analysis_task, _assess_confidence

*Line: 160*

---

## Function: 

Initialize geopolitics agent.

Args:
    name: Agent name
    llm: Language model instance
    system_prompt: Geopolitics-specific system prompt
    tools: Optional additional tools

*Line: 169*

---

## Function: 

Execute geopolitical analysis.

Args:
    state: Current agent state

Returns:
    State updates with geopolitics analysis

*Line: 200*

---

## Function: 

Build the analysis task prompt.

*Line: 252*

---

## Function: 

Assess confidence of analysis output.

*Line: 267*

---

## Function: 

No-op fallback when langchain_core is not installed.

*Line: 23*

---

## Function: 

*Line: 27*

---

