# engine.strategy.schema

## Class: 

Supported production strategy types for the strategy engine.

*Line: 45*

---

## Class: 

Supported technical indicators for strategy rules.

*Line: 59*

---

## Class: 

Comparison operators for rule evaluation.

*Line: 78*

---

## Class: 

Supported timeframe strings for strategy rules.

*Line: 91*

---

## Class: 

A single entry condition for a trading strategy.

Each entry rule specifies an indicator, comparison operator,
threshold value, and optional timeframe for multi-timeframe strategies.
All entry rules are evaluated with AND logic (all must be true).

**Methods:** indicator_must_be_valid

*Line: 105*

---

## Class: 

A single exit condition for a trading strategy.

Exit rules can be indicator-based (same as entry rules) or
percentage-based (trailing stop, take profit).

**Methods:** must_have_exit_condition

*Line: 150*

---

## Class: 

Risk management rules for a trading strategy.

These rules are enforced as hard limits during backtesting and
live trading. They cannot be overridden by agent decisions.

*Line: 205*

---

## Class: 

Defines the trading universe for a strategy.

A universe can be specified as:
- Explicit symbol list
- Exchange-based filtering
- Market cap range filtering
- Sector/industry filtering

Multiple filters are combined with AND logic.

**Methods:** symbols_must_be_uppercase, exchanges_must_be_uppercase, sectors_must_be_title_case, must_have_at_least_one_filter

*Line: 256*

---

## Class: 

Complete strategy configuration loaded from YAML.

This is the top-level model that validates an entire strategy definition.
It includes entry rules, exit rules, risk rules, and universe definition.

**Methods:** name_must_be_valid, tags_must_be_lowercase, must_have_strategy_or_rules

*Line: 339*

---

## Function: 

Validate indicator name is non-empty and lowercase.

*Line: 143*

---

## Function: 

Validate that at least one exit condition is specified.

*Line: 192*

---

## Function: 

Normalize symbols to uppercase.

*Line: 306*

---

## Function: 

Normalize exchange names to uppercase.

*Line: 312*

---

## Function: 

Normalize sector names to title case.

*Line: 318*

---

## Function: 

Validate that at least one universe filter is specified.

*Line: 323*

---

## Function: 

Validate strategy name.

*Line: 412*

---

## Function: 

Normalize tags to lowercase.

*Line: 423*

---

## Function: 

Validate that either strategy_type or entry/exit rules are provided.

*Line: 428*

---

