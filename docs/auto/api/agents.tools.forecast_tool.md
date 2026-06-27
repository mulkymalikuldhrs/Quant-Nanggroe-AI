# agents.tools.forecast_tool

## Class: 

Forecast timeframe.

*Line: 48*

---

## Class: 

Forecast price direction.

*Line: 56*

---

## Class: 

Confidence level classification.

*Line: 67*

---

## Class: 

Technical analysis forecast component.

*Line: 80*

---

## Class: 

Fundamental analysis forecast component.

*Line: 91*

---

## Class: 

News and sentiment forecast component.

*Line: 101*

---

## Class: 

COT positioning forecast component.

*Line: 111*

---

## Class: 

Forecast for a specific timeframe.

*Line: 121*

---

## Class: 

Complete forecast result.

*Line: 135*

---

## Class: 

Forecast accuracy tracking record.

*Line: 149*

---

## Class: 

AI Forecast Engine for agent consumption.

Provides multi-day market forecast synthesis combining technical,
fundamental, news, and COT sentiment analysis with confidence
scoring per timeframe and forecast accuracy tracking.

Usage::

    tool = ForecastTool()
    forecast = await tool.forecast("AAPL")
    accuracy = await tool.get_accuracy_stats()

**Methods:** __init__, _synthesize_timeframe_forecasts, _calculate_composite, _direction_to_score, _score_to_direction, _confidence_from_value, _get_cache, _set_cache

*Line: 166*

---

## Function: 

*Line: 600*

---

## Function: 

*Line: 180*

---

## Function: 

Synthesize component forecasts into timeframe forecasts.

*Line: 439*

---

## Function: 

Calculate composite direction and confidence.

*Line: 520*

---

## Function: 

Convert direction string to numeric score.

*Line: 538*

---

## Function: 

Convert numeric score to direction.

*Line: 548*

---

## Function: 

Convert confidence value to label.

*Line: 565*

---

## Function: 

*Line: 579*

---

## Function: 

*Line: 589*

---

## Function: 

*Line: 34*

---

## Function: 

*Line: 37*

---

