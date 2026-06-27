# engine.screener.base

## Class: 

Screener signal direction.

*Line: 22*

---

## Class: 

Result from a screener component analysis.

Attributes:
    component_name: Name of the screener component.
    direction: Bullish/bearish/neutral direction.
    score: Score from -1.0 (strong bearish) to 1.0 (strong bullish).
    confidence: Confidence in the analysis (0.0-1.0).
    details: Detailed analysis data.
    status: Status of the analysis (configured, not_configured, error).
    message: Human-readable message about the analysis.

*Line: 30*

---

## Class: 

Abstract base class for all screener components.

Every screener must implement:
- analyze(): Run analysis on market data and return a ScreenerResult

**Methods:** __init__, name, description, analyze, configure, is_configured, _not_configured_result

*Line: 54*

---

## Function: 

*Line: 61*

---

## Function: 

Component name identifier.

*Line: 66*

---

## Function: 

Component description.

*Line: 72*

---

## Function: 

Run analysis on market data.

Args:
    data: Dict with market data (prices, fundamentals, etc.)

Returns:
    ScreenerResult with analysis scores and details.

*Line: 77*

---

## Function: 

Configure the component with external data sources.

*Line: 88*

---

## Function: 

Whether the component is properly configured.

*Line: 93*

---

## Function: 

Return a not-configured result.

*Line: 97*

---

