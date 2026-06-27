# engine.integration.bh_qna_bridge

## Class: 

Which side of the bridge a component belongs to.

*Line: 41*

---

## Class: 

Status of a bridge operation.

*Line: 47*

---

## Class: 

Result of a cross-module bridge operation.

**Methods:** to_dict

*Line: 56*

---

## Class: 

Configuration for the BH↔QNA bridge.

*Line: 81*

---

## Class: 

Bridge that routes data between BH and QNA engine modules.

Responsibilities:
- Fetch market data from BH backtest infrastructure and convert for QNA
- Run QNA analysis and package results for BH consumption
- Handle errors gracefully with configurable fallback logic
- Track latency and operation metrics

**Methods:** __init__, get_market_data_from_bh, _fetch_bh_market_data, _generate_synthetic_data, _align_columns, _fallback_market_data, run_qna_analysis, _execute_qna_analysis, _compute_risk_metrics, _compute_kelly_params, _compute_signal, _fallback_analysis, send_results_to_bh, _package_for_bh, run_full_pipeline, _record_success, _record_fallback, _record_failure, _update_avg_latency, get_metrics

*Line: 92*

---

## Function: 

*Line: 67*

---

## Function: 

*Line: 102*

---

## Function: 

Fetch market data from BH backtest infrastructure for QNA analysis.

Args:
    symbol: Ticker symbol (e.g. "SPY", "BTC-USD").
    start_date: Start date string (ISO format).
    end_date: End date string (ISO format).
    interval: Data interval (e.g. "1d", "1h", "5m").
    fields: Optional list of fields to include.

Returns:
    BridgeResult with market data DataFrame.

*Line: 115*

---

## Function: 

Internal method to fetch data from BH backtest infrastructure.

This is a bridge stub — in production this would call the BH
data loader or persistence layer. For now we generate synthetic data.

*Line: 185*

---

## Function: 

Generate synthetic OHLCV data for testing/fallback.

*Line: 206*

---

## Function: 

Ensure DataFrame has the requested columns.

*Line: 235*

---

## Function: 

Generate fallback data when primary source fails.

*Line: 243*

---

## Function: 

Run QNA analysis on market data.

Args:
    market_data: OHLCV DataFrame from BH.
    analysis_type: Type of analysis ("full", "risk", "kelly", "signal").
    params: Optional analysis parameters.

Returns:
    BridgeResult with analysis results dict.

*Line: 262*

---

## Function: 

Execute the actual QNA analysis logic.

*Line: 325*

---

## Function: 

Compute risk metrics from returns.

*Line: 361*

---

## Function: 

Compute Kelly parameters from returns.

*Line: 379*

---

## Function: 

Compute a basic trading signal.

*Line: 404*

---

## Function: 

Provide minimal fallback analysis when primary fails.

*Line: 434*

---

## Function: 

Send QNA analysis results back to BH for consumption.

Packages the QNA results in a format suitable for backtest
strategy consumption.

Args:
    analysis_result: BridgeResult from QNA analysis.
    metadata: Optional metadata to attach.

Returns:
    BridgeResult with packaged results for BH.

*Line: 454*

---

## Function: 

Package QNA analysis results for BH consumption.

*Line: 505*

---

## Function: 

Run the full BH→QNA→BH pipeline.

1. Fetch market data from BH
2. Run QNA analysis
3. Package results for BH

Args:
    symbol: Ticker symbol.
    start_date: Start date (ISO format).
    end_date: End date (ISO format).
    interval: Data interval.
    analysis_type: QNA analysis type.
    params: Optional parameters.

Returns:
    BridgeResult with full pipeline output.

*Line: 551*

---

## Function: 

*Line: 622*

---

## Function: 

*Line: 628*

---

## Function: 

*Line: 634*

---

## Function: 

*Line: 640*

---

## Function: 

Return bridge operation metrics.

*Line: 644*

---

