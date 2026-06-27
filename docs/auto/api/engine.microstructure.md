# engine.microstructure

## Class: 

*Line: 25*

---

## Class: 

Volume-synchronized Probability of Informed Trading.

VPIN = 1 - |2 * V_buy - V_sell| / V_total over N volume buckets.

Higher VPIN (>0.6) indicates higher probability of informed trading
and toxic order flow.

**Methods:** __init__, calculate

*Line: 36*

---

## Class: 

Kyle's Lambda — price impact per unit of order flow.

Regresses ``Δprice`` on ``signed_volume``. Higher lambda = less liquid.

**Methods:** calculate

*Line: 69*

---

## Class: 

Amihud Illiquidity Ratio — daily price response per unit volume.

``Amihud = mean(|r| / V_daily)`` where ``r`` is return and ``V`` is volume.

Higher values indicate greater illiquidity (price moves more per $ traded).

**Methods:** calculate

*Line: 99*

---

## Class: 

Aggregate microstructure analysis combining VPIN, Kyle, Amihud.

Usage::
    analyzer = MicrostructureAnalyzer()
    metrics = analyzer.analyze(trade_dataframe)

**Methods:** __init__, analyze, _estimate_realized_spread, _estimate_effective_spread

*Line: 122*

---

## Function: 

*Line: 45*

---

## Function: 

*Line: 49*

---

## Function: 

*Line: 75*

---

## Function: 

*Line: 107*

---

## Function: 

*Line: 130*

---

## Function: 

*Line: 135*

---

## Function: 

*Line: 148*

---

## Function: 

*Line: 157*

---

