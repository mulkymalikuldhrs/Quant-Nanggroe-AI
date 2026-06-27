# engine.screener.orchestrator

## Class: 

Screener Orchestrator.

Combines all screener engines, runs them in sequence,
and produces a composite screening result.

Features:
- Runs all engines and aggregates results
- Configurable weights per engine
- Overall direction and score
- Detailed breakdown per engine

**Methods:** __init__, screen, configure_engine, list_engines, get_engine

*Line: 37*

---

## Function: 

Initialize orchestrator.

Args:
    weights: Custom weights per engine. Defaults to DEFAULT_WEIGHTS.
    enabled_engines: List of engine names to enable. None = all.

*Line: 50*

---

## Function: 

Run all screener engines and produce composite result.

Args:
    data: Dict with market data for all engines.

Returns:
    Dict with composite score, direction, and per-engine results.

*Line: 79*

---

## Function: 

Configure a specific engine.

Args:
    name: Engine name.
    **kwargs: Configuration parameters.

Returns:
    True if engine was found and configured.

*Line: 156*

---

## Function: 

List all available engine names.

*Line: 172*

---

## Function: 

Get a specific engine by name.

*Line: 176*

---

