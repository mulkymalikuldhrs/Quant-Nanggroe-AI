# engine.factors.academic

## Function: 

Per-row z-score: (x - row_mean) / row_std; zero/NaN std rows -> NaN.

*Line: 46*

---

## Function: 

Per-row z-score: (x - row_mean) / row_std; zero/NaN std rows -> NaN.

*Line: 55*

---

## Function: 

Return 252-day minus 21-day return z-score (Carhart UMD).

Uses canonical (252, 21) windows without silent shrink on short panels.
Short panels produce all-NaN; the registry surfaces this as >95% NaN
(RegistryError) rather than returning a misleading shrunk-window value.

*Line: 85*

---

## Function: 

Return inverse 60-day log-volume change z-score per stock.

Uses the canonical 60-bar rolling mean + 60-bar delta windows without
silent shrink on short panels. Short panels produce all-NaN; the
registry surfaces this as >95% NaN (RegistryError) so the user sees
"insufficient history" rather than a misleading shrunk-window value.

*Line: 119*

---

## Function: 

Return inverse 252-day return cross-sectional z-score per stock.

Uses the canonical 252-day window without silent shrink on short panels.
Short panels produce an all-NaN result, which the registry surfaces as a
>95% NaN error (RegistryError) so the user sees "insufficient history"
instead of a misleading shrunk-window value.

*Line: 154*

---

## Function: 

Return 21-day return cross-sectional z-score per stock.

*Line: 186*

---

## Function: 

Return inverse 60-day return-volatility z-score per stock.

*Line: 213*

---

## Function: 

Return inverse log 60-day dollar-volume z-score per stock.

*Line: 241*

---

## Function: 

Return list of (meta_dict, compute_fn) tuples for all Academic Alpha Factors (Fama-French, Carhart) factors.

*Line: 250*

---

