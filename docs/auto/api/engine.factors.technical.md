# engine.factors.technical

## Class: 

Price momentum factor (N-period return).

Formula: close / close.shift(n) - 1

**Methods:** name, meta, __init__, compute

*Line: 22*

---

## Class: 

Rate of Change (ROC) factor.

Formula: (close - close.shift(n)) / close.shift(n) * 100

**Methods:** name, meta, __init__, compute

*Line: 54*

---

## Class: 

Mean reversion factor — z-score of price vs moving average.

Formula: (close - SMA(close, n)) / STD(close, n)

**Methods:** name, meta, __init__, compute

*Line: 87*

---

## Class: 

Realized volatility factor.

Formula: STD(returns, n) * sqrt(252)

**Methods:** name, meta, __init__, compute

*Line: 122*

---

## Class: 

Average True Range (ATR) factor.

Formula: ATR(n) / close (normalized)

**Methods:** name, meta, __init__, compute

*Line: 154*

---

## Class: 

Bollinger Band Width factor.

Formula: 2 * STD(close, n) / SMA(close, n)

**Methods:** name, meta, __init__, compute

*Line: 197*

---

## Class: 

Volume ratio factor — current volume vs average volume.

Formula: volume / SMA(volume, n)

**Methods:** name, meta, __init__, compute

*Line: 231*

---

## Class: 

Relative Strength Index (RSI) factor.

Formula: 100 - 100 / (1 + avg_gain / avg_loss)

**Methods:** name, meta, __init__, compute

*Line: 264*

---

## Class: 

MACD Histogram factor.

Formula: MACD_line - Signal_line
Where MACD_line = EMA(12) - EMA(26), Signal_line = EMA(MACD, 9)

**Methods:** name, meta, compute

*Line: 304*

---

## Function: 

Return instances of all implemented technical factors.

*Line: 337*

---

## Function: 

*Line: 29*

---

## Function: 

*Line: 33*

---

## Function: 

*Line: 45*

---

## Function: 

*Line: 48*

---

## Function: 

*Line: 61*

---

## Function: 

*Line: 65*

---

## Function: 

*Line: 77*

---

## Function: 

*Line: 80*

---

## Function: 

*Line: 94*

---

## Function: 

*Line: 98*

---

## Function: 

*Line: 111*

---

## Function: 

*Line: 114*

---

## Function: 

*Line: 129*

---

## Function: 

*Line: 133*

---

## Function: 

*Line: 145*

---

## Function: 

*Line: 148*

---

## Function: 

*Line: 161*

---

## Function: 

*Line: 165*

---

## Function: 

*Line: 178*

---

## Function: 

*Line: 181*

---

## Function: 

*Line: 204*

---

## Function: 

*Line: 208*

---

## Function: 

*Line: 220*

---

## Function: 

*Line: 223*

---

## Function: 

*Line: 238*

---

## Function: 

*Line: 242*

---

## Function: 

*Line: 254*

---

## Function: 

*Line: 257*

---

## Function: 

*Line: 271*

---

## Function: 

*Line: 275*

---

## Function: 

*Line: 287*

---

## Function: 

*Line: 290*

---

## Function: 

*Line: 312*

---

## Function: 

*Line: 316*

---

## Function: 

*Line: 328*

---

