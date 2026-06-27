# engine.risk.kelly

## Class: 

Legacy Kelly method names mapped to new engine/kelly/ package.

**Methods:** to_new

*Line: 39*

---

## Class: 

Legacy Kelly parameters — delegates to engine/kelly/ backend.

**Methods:** to_new

*Line: 60*

---

## Class: 

Legacy Kelly result — wraps engine/kelly/ result.

**Methods:** from_new, _recommendation

*Line: 83*

---

## Class: 

Legacy Kelly Criterion — delegates to engine/kelly/ package.

Maintains full backward compatibility while routing computation
to the new ``engine/kelly/`` implementations.

Config parameters:
    max_position: Maximum position size (default: 0.20).
    min_position: Minimum position size (default: 0.01).

**Methods:** __init__, calculate_kelly, _get_implementation, calculate_continuous_kelly, calculate_multi_asset_kelly, get_optimal_position_size, get_summary_statistics

*Line: 122*

---

## Function: 

*Line: 48*

---

## Function: 

*Line: 70*

---

## Function: 

*Line: 95*

---

## Function: 

*Line: 107*

---

## Function: 

*Line: 133*

---

## Function: 

Calculate Kelly Criterion via delegation to engine/kelly/.

Args:
    params: Legacy Kelly parameters.
    method: Legacy Kelly method enum.

Returns:
    Legacy KellyResult wrapping the new engine result.

*Line: 148*

---

## Function: 

*Line: 182*

---

## Function: 

Continuous-time Kelly: f* = (mu - r) / sigma^2.

*Line: 193*

---

## Function: 

Multi-asset Kelly via engine/kelly/ delegation.

*Line: 204*

---

## Function: 

Get position size in monetary terms.

*Line: 225*

---

## Function: 

*Line: 235*

---

