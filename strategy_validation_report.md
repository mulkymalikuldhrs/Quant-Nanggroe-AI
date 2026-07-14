# Strategy Implant Validation Report

**Profile:** traderbot
**Repo:** `/d/repositories/Quant-Nanggroe-AI-worktree` (worktree)
**Date:** 2026-07-15
**Method:** For every name in `list_strategies()`, run `create_strategy(name)`; failures
categorized by exception type. Both registries exercised (API `_NAME_MAP` + decorator
`StrategyRegistry`). Script: `scripts/validate_strategies.py`.

## Summary

| System | Source | Total | OK | Gagal |
|--------|--------|------:|---:|------:|
| **API strategies** (`engine/strategy/strategies`) | `_NAME_MAP` + `list_strategies()` | 106 | **106** | **0** |
| **Decorator registry** (`engine/strategies`) | `@StrategyRegistry.register` | 7 | **7** | **0** |
| **`NAME_MAP` integrity** (every mapped class exists) | — | 106 | **106** | **0** |

**Validation time:** < 2 s (well under the 30 s budget).

## What was validated

1. **API path (the one the REST API actually uses).** `api/routes/strategies.py` imports
   `list_strategies` / `create_strategy` from `engine.strategy.strategies`. All 106 names
   instantiate cleanly → 0 failures out of the box.
2. **Decorator registry path.** Consumed by `engine_production_bridge.py`,
   `engine/strategy/loader.py`, `engine/strategy/strategy_selector.py`,
   `engine/live/adaptive_integration.py`. After fixes, all 7 registered names create
   successfully.

## Defects found & fixed

The API `_NAME_MAP` path was already healthy. The real defects were in the parallel
decorator `StrategyRegistry` in `engine/strategies/`, where 2 valid `Strategy` subclasses
were silently invisible — the "decorator registry kosong" symptom. Root causes:

### Fix 1 — missing decorator + `name` as `@property` (class-name mismatch)
Files: `market_profile.py`, `volume_delta.py`

Both define a proper `Strategy` subclass (`MarketProfileStrategy`, `VolumeDeltaStrategy`)
but were **never decorated with `@StrategyRegistry.register`**, so they were absent from
the registry. Secondary break: they defined `name` as a `@property`. The `register`
decorator keys the registry by `strategy_class.name`; on a class, a property yields the
*descriptor object*, not the string, so even if decorated they would register under a
broken key (unlike the other 5 strategies that use `name = "..."` as a class attribute).

- Added `from quant_nanggroe.engine.strategies.registry import StrategyRegistry`.
- Added `@StrategyRegistry.register` above each class.
- Converted `name` from a `@property` to a class attribute (`name = "market_profile"` / `"volume_delta"`).

### Fix 2 — missing `__init__` arg
Files: `market_profile.py`, `volume_delta.py`

`StrategyRegistry.create()` calls `strategy_class(parameters=...)`. The two classes used
`__init__(self, params=...)` and rejected the `parameters=` keyword (`TypeError: ... got an
unexpected keyword argument 'parameters'`). Renamed the parameter to `parameters` to match
the other 5 decorated strategies and the base `Strategy.__init__`.

### Result
Decorator registry grew from **5 → 7** entries and is now 7/7 createable. API path unchanged
at 106/106.

## Per-file status (flagged / modified)

| File | Status | Note |
|------|--------|------|
| `engine/strategies/market_profile.py` | **FIXED** | added `@StrategyRegistry.register`, `name` class attribute, `parameters=` arg |
| `engine/strategies/volume_delta.py` | **FIXED** | same as above |
| `engine/strategies/hermes_smc.py` | NOT A STRATEGY | contains `SMCAgentEnhanced` (standalone agent, not a `Strategy` subclass) — correctly excluded from the registry |
| `engine/strategies/{fibonacci,ict,smc_strategy,unified_retail,wyckoff}.py` | OK | already decorated + working |
| `engine/strategy/strategies/*.py` (106 modules) | OK | `_NAME_MAP` resolvable, 0 instantiation failures |

No `INIT_ARG_ERROR`, no `CLASS_NOT_FOUND`, no `UNKNOWN` failures remain in either registry.

## On the "109" target

The repo contains **113** Python files that define a `Strategy` subclass. The surface that
actually registers strategies splits into two systems:

- **106** live in `engine/strategy/strategies/` and feed the API via `_NAME_MAP` (all OK).
- **7** live in `engine/strategies/` and feed `engine_production_bridge`/`loader` via the
  decorator registry (now all OK; 2 added by this fix).

The figure 109 appears to assume `106 + 3` extra files in `engine/strategies/`
(`hermes_smc`, `market_profile`, `volume_delta`). `hermes_smc` is **not** a `Strategy`
subclass (standalone SMC agent), so the realistic registrable maximum is **108**, not 109.
`market_profile` and `volume_delta` are now registered (the 2 fixed here), bringing the
decorator registry to 7 and the combined registrable count to 108. If `hermes_smc` must be
surfaceable, it needs to be wrapped as a `Strategy` subclass first — out of scope for a
validation/fix pass; flag for the parent.

## Verification

```text
$ .venv/Scripts/python.exe scripts/validate_strategies.py
API_TOTAL=106 API_OK=106 API_GAGAL=0
NAME_MAP_INTEGRITY: OK
DECORATOR_TOTAL=7 DECORATOR_OK=7 DECORATOR_GAGAL=0
```

Both edited files compile (`py_compile`) and the API router imports cleanly.
