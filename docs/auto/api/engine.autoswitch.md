# engine.autoswitch

## Class: 

Available trading strategy types.

*Line: 34*

---

## Class: 

Reason for a strategy switch.

*Line: 46*

---

## Class: 

Profile for a trading strategy.

*Line: 59*

---

## Class: 

Record of a strategy switch.

*Line: 75*

---

## Class: 

Configuration for auto strategy switching.

*Line: 89*

---

## Class: 

Automatically switches strategies based on market conditions.

Integrates with the regime detector to select optimal strategies
for the current market environment.

Usage::

    switcher = AutoSwitcher()
    # Detect regime and switch
    strategy = switcher.evaluate_and_switch(
        regime=MarketRegime.TRENDING_UP,
        confidence=0.8,
    )

**Methods:** __init__, evaluate_and_switch, switch_manual, detect_and_switch, current_strategy, current_profile, switches, config, get_strategy_for_regime, get_profile, stats

*Line: 198*

---

## Function: 

*Line: 214*

---

## Function: 

Evaluate market regime and switch strategy if appropriate.

Parameters
----------
regime:
    Detected market regime.
confidence:
    Confidence of regime detection.
force:
    Force switch regardless of cooldown.

Returns
-------
StrategyType
    The current (possibly switched) strategy.

*Line: 226*

---

## Function: 

Manually switch to a specific strategy.

Parameters
----------
target:
    Target strategy type.
reason:
    Reason for the switch.

Returns
-------
StrategySwitch
    Record of the switch.

*Line: 303*

---

## Function: 

Detect market regime from price data and switch strategy.

Parameters
----------
closes:
    List of closing prices.
volumes:
    Optional volume data.
symbol:
    Symbol being analyzed.

Returns
-------
StrategyType
    The current strategy after potential switch.

*Line: 334*

---

## Function: 

*Line: 362*

---

## Function: 

*Line: 366*

---

## Function: 

*Line: 370*

---

## Function: 

*Line: 374*

---

## Function: 

Get the optimal strategy for a given regime.

*Line: 377*

---

## Function: 

Get the profile for a specific strategy.

*Line: 381*

---

## Function: 

Switcher statistics.

*Line: 386*

---

