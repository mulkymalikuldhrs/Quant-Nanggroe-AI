# Task 8-a: Enhanced LangGraph Orchestration (graph_v2)

**Date**: 2025-06-10
**Branch**: cl1-agent-3
**Task ID**: 8-a

## Summary

Implemented the enhanced LangGraph v2 orchestration layer for the Quant-Nanggroe-AI trading framework. This adds multi-path asset-class conditional routing, ATR-based position sizing with TP1/TP2/TP3 geometry, portfolio concentration/correlation/Kelly validation, smart order routing with venue scoring, and human-in-the-loop checkpoint for high-risk trades.

## Files Modified

1. **`quant_nanggroe/agents/state.py`** — Extended AgentState with v2 fields:
   - `AssetClass` enum (CRYPTO, FOREX, EQUITY, PREDICTION_MARKET, UNKNOWN)
   - `PositionSizingResult` model (ATR + TP1/TP2/TP3 + fractional risk)
   - `PortfolioValidation` model (concentration/correlation/Kelly checks)
   - `VenueScore` and `SmartOrderRouting` models
   - New AgentState fields: `asset_class`, `execution_path`, `position_sizing_result`, `portfolio_validation`, `venue_scores`, `smart_routing_result`, `human_approval_required`, `human_approval_status`, `human_approval_reason`, `prediction_market_output`
   - Updated `create_initial_state()` with v2 defaults
   - Added `PREDICTION_MARKET` to `AgentRole`

## Files Created

2. **`quant_nanggroe/agents/nodes/__init__.py`** — Package init with exports

3. **`quant_nanggroe/agents/nodes/asset_router.py`** — Asset class detection and routing:
   - `detect_asset_class()` — regex-based symbol classification
   - `detect_dominant_asset_class()` — multi-symbol dominant class detection
   - `AssetRouter` class — LangGraph node that detects class and writes state
   - `route_by_asset_class()` — conditional-edge function for LangGraph routing

4. **`quant_nanggroe/agents/nodes/position_sizer.py`** — ATR-based position sizing:
   - `estimate_atr_from_market_data()` — ATR estimation from market data
   - `compute_position_size()` — Fixed-fractional risk model with ATR TP1/TP2/TP3
   - `PositionSizer` class — LangGraph node for batch position sizing

5. **`quant_nanggroe/agents/nodes/portfolio_validator.py`** — Portfolio validation:
   - `check_concentration()` — Single-position concentration limits
   - `check_correlation()` — Correlation group analysis (9 groups)
   - `check_kelly()` — Kelly Criterion half-Kelly validation
   - `PortfolioValidator` class — LangGraph node

6. **`quant_nanggroe/agents/nodes/smart_executor.py`** — Smart order routing:
   - `VENUE_REGISTRY` — 15 venues across 4 asset classes
   - `score_venue()` — Weighted scoring (35% fill, 25% fee, 20% latency, 20% slippage)
   - `route_order()` — Venue selection with routing decision explanation
   - `SmartExecutor` class — LangGraph node

7. **`quant_nanggroe/agents/nodes/human_checkpoint.py`** — Human-in-the-loop:
   - `should_require_human_approval()` — 7 trigger conditions
   - `HumanCheckpoint` class — LangGraph node
   - `human_approval_conditional()` — Conditional-edge function

8. **`quant_nanggroe/agents/graph_v2.py`** — Enhanced trading graph:
   - `TradingGraphV2` class with full multi-path architecture
   - Graph: START → market_analysis → asset_router → {crypto|forex|equity|prediction}_path → signal_generation → position_sizer → risk_assessment → portfolio_validation → portfolio_optimization → execution_decision → human_checkpoint → smart_execution → reflection → END
   - Council debate fallback, emergency exit, regime safety check

9. **`quant_nanggroe/agents/__init__.py`** — Updated with all v2 exports

## Verification

- All Python files compile successfully
- All node modules tested with unit assertions
- Full v1/v2 package import compatibility verified
