# engine.shadow.extractor

## Class: 

A rule extracted from a text description.

*Line: 23*

---

## Class: 

A strategy extracted from text description.

*Line: 36*

---

## Class: 

Strategy Extractor.

Extracts trading strategies from natural language text descriptions.
Identifies entry/exit conditions, risk parameters, and market preferences.

Ported from Vibe-Trading/agent/src/shadow_account/extractor.py

**Methods:** extract, validate_strategy, _extract_rules, _extract_markets, _extract_timeframe, _extract_risk_tolerance, _generate_profile

*Line: 50*

---

## Function: 

Extract a strategy from a text description.

Args:
    text: Natural language description of a trading strategy.

Returns:
    ExtractedStrategy with parsed rules and parameters.

*Line: 112*

---

## Function: 

Validate an extracted strategy.

Args:
    strategy: ExtractedStrategy to validate.

Returns:
    Tuple of (is_valid, list_of_errors).

*Line: 150*

---

## Function: 

Extract trading rules from text.

*Line: 172*

---

## Function: 

Extract target markets from text.

*Line: 226*

---

## Function: 

Extract trading timeframe from text.

*Line: 237*

---

## Function: 

Extract risk tolerance from text.

*Line: 247*

---

## Function: 

Generate a profile summary from extracted data.

*Line: 258*

---

