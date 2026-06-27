# engine.strategies.wyckoff

## Class: 

Wyckoff Method Strategy.

Detects accumulation and distribution phases using:
- Price/volume analysis (effort vs result)
- Support/resistance levels
- Springs and upthrusts
- Sign of strength / sign of weakness
- Cause and effect (range projection)

Phases:
- Accumulation: A (selling climax) -> B (auto rally) -> C (spring) -> D (sign of strength) -> E (markup)
- Distribution: A (buying climax) -> B (auto decline) -> C (upthrust) -> D (sign of weakness) -> E (markdown)

**Methods:** __init__, generate_signal, _hold_signal

*Line: 21*

---

## Function: 

*Line: 40*

---

## Function: 

Generate Wyckoff-based trading signal.

Analyzes price/volume relationships to detect:
- Springs (bullish): Price dips below support then reverses on high volume
- Upthrusts (bearish): Price spikes above resistance then reverses
- Signs of Strength (bullish): Price rises on high volume with wide spread
- Signs of Weakness (bearish): Price falls on high volume with wide spread

*Line: 50*

---

## Function: 

*Line: 173*

---

