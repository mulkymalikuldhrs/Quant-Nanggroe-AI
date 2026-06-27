# engine.backtest.report

## Class: 

Generates backtest reports.

Supports:
- JSON report for programmatic consumption
- HTML report with embedded charts (using inline SVG/JS)
- Text summary for console output
- Trade-by-trade analysis
- Performance attribution
- Monthly returns heatmap
- Drawdown analysis
- Parameter sensitivity (if provided)
- Benchmark comparison (if provided)

**Methods:** generate, generate_json, generate_html, _generate_json, _generate_html, _generate_text, _compute_equity_chart_data, _compute_drawdown_data, _compute_monthly_returns, _compute_trade_distribution, _html_metrics_section, _html_risk_section, _html_trade_section, _html_benchmark_section, _html_sensitivity_section, _html_monthly_returns_heatmap, _html_trade_distribution

*Line: 32*

---

## Function: 

Generate a backtest report.

Args:
    metrics: Performance metrics dict.
    equity_curve: Equity curve series.
    trades: List of trade records.
    config: Backtest configuration dict.
    format: Output format ('json', 'html', 'text').
    benchmark_comparison: Optional benchmark comparison dict.
    sensitivity_analysis: Optional sensitivity analysis results.
    strategy_name: Optional strategy name for the report.

Returns:
    Formatted report string.

*Line: 48*

---

## Function: 

Generate JSON report.

Args:
    metrics: Performance metrics dict.
    equity_curve: Equity curve series.
    trades: List of trade records.
    config: Backtest configuration dict.
    benchmark_comparison: Optional benchmark comparison.
    sensitivity_analysis: Optional sensitivity analysis.
    strategy_name: Strategy name.

Returns:
    JSON report string.

*Line: 92*

---

## Function: 

Generate HTML report.

Args:
    metrics: Performance metrics dict.
    equity_curve: Equity curve series.
    trades: List of trade records.
    config: Backtest configuration dict.
    benchmark_comparison: Optional benchmark comparison.
    sensitivity_analysis: Optional sensitivity analysis.
    strategy_name: Strategy name.

Returns:
    HTML report string.

*Line: 121*

---

## Function: 

Generate JSON report.

*Line: 150*

---

## Function: 

Generate HTML report with embedded chart data.

*Line: 220*

---

## Function: 

Generate text summary report.

*Line: 391*

---

## Function: 

Compute equity curve data for chart rendering.

Downsamples to a maximum of 500 points for performance.

*Line: 464*

---

## Function: 

Compute drawdown chart data.

Returns:
    List of dicts with 't' (timestamp) and 'd' (drawdown as decimal).

*Line: 482*

---

## Function: 

Compute monthly returns for heatmap visualization.

Returns:
    Dict with 'years', 'months', 'data' keys.
    'data' is a dict mapping "YYYY-MM" to return value.

*Line: 504*

---

## Function: 

Compute trade distribution statistics.

Returns:
    Dict with distribution data for visualization.

*Line: 541*

---

## Function: 

Generate HTML for performance summary section.

*Line: 582*

---

## Function: 

Generate HTML for risk metrics section.

*Line: 636*

---

## Function: 

Generate HTML for trade statistics section.

*Line: 680*

---

## Function: 

Generate HTML for benchmark comparison section.

*Line: 724*

---

## Function: 

Generate HTML for parameter sensitivity section.

*Line: 756*

---

## Function: 

Generate HTML for monthly returns heatmap.

*Line: 769*

---

## Function: 

Generate HTML for trade distribution.

*Line: 810*

---

