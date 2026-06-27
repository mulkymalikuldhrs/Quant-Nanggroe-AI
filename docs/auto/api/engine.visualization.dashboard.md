# engine.visualization.dashboard

## Class: 

*Line: 29*

---

## Class: 

Summary of a single portfolio position.

*Line: 47*

---

## Class: 

Aggregate portfolio summary.

*Line: 60*

---

## Class: 

Date range for dashboard filtering.

**Methods:** last_n_days, this_month, this_year, all

*Line: 72*

---

## Class: 

Optional WebSocket-based real-time updater.

Provides a simple pub/sub mechanism for pushing dashboard updates
to connected clients. Falls back to polling if WebSocket is unavailable.

**Methods:** __init__, _try_start_server, publish, subscribe, get_latest

*Line: 103*

---

## Class: 

Main dashboard aggregating all visualizations and metrics.

Features:
    - Refresh button: Call refresh() to reload all data
    - Date range selector: Use set_date_range() to filter time periods
    - Portfolio summary: Use build_portfolio_summary() for holdings view
    - Risk metrics panel: Use build_risk_panel() for detailed risk analysis
    - Real-time updates: Enable via config={'realtime': True}

**Methods:** __init__, register_refresh_callback, refresh, last_refresh, set_date_range, set_date_range_preset, date_range, _apply_date_filter_returns, _apply_date_filter_prices, compute_metrics, update_regime, update_kelly, build_overview, build_portfolio_summary, build_risk_panel, _compute_risk_score, build_kelly_view, export_html, to_dict

*Line: 171*

---

## Function: 

*Line: 79*

---

## Function: 

*Line: 85*

---

## Function: 

*Line: 92*

---

## Function: 

*Line: 99*

---

## Function: 

*Line: 110*

---

## Function: 

Attempt to start WebSocket server; fail silently.

*Line: 121*

---

## Function: 

Publish a dashboard update to all subscribers.

*Line: 150*

---

## Function: 

Register a callback for dashboard updates.

*Line: 161*

---

## Function: 

Return the latest published data.

*Line: 165*

---

## Function: 

*Line: 182*

---

## Function: 

Register a callback to be invoked on refresh.

*Line: 204*

---

## Function: 

Refresh all dashboard data.

Triggers registered callbacks and re-computes metrics.
Returns a status dict with refresh timestamp and affected panels.

*Line: 208*

---

## Function: 

*Line: 264*

---

## Function: 

Set the dashboard date range filter.

*Line: 269*

---

## Function: 

Set date range from a preset string.

Presets: '1d', '7d', '30d', '90d', 'ytd', '1y', 'all'

*Line: 277*

---

## Function: 

*Line: 298*

---

## Function: 

Filter returns series by date range.

*Line: 301*

---

## Function: 

Filter price DataFrame by date range.

*Line: 314*

---

## Function: 

Compute all portfolio metrics from returns.

*Line: 327*

---

## Function: 

*Line: 391*

---

## Function: 

*Line: 394*

---

## Function: 

Build overview page with key charts.

*Line: 399*

---

## Function: 

Build portfolio summary panel.

Args:
    positions: List of position dicts with keys: symbol, quantity,
               entry_price, current_price.
    cash: Current cash balance.

Returns:
    Portfolio summary dict with holdings table and aggregate stats.

*Line: 441*

---

## Function: 

Build detailed risk metrics panel.

Args:
    stress_results: Optional stress test scenario results.
    additional_var: Optional additional VaR calculations
                   (e.g. {"var_99": -0.05, "var_90": -0.02}).

Returns:
    Risk metrics panel dict.

*Line: 527*

---

## Function: 

Compute an overall risk score (low/medium/high/critical).

*Line: 577*

---

## Function: 

Build Kelly analysis view.

*Line: 607*

---

## Function: 

Export dashboard as HTML.

*Line: 637*

---

## Function: 

Export dashboard state as dict (for API responses).

*Line: 688*

---

