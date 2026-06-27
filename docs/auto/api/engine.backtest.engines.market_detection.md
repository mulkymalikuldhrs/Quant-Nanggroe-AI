# engine.backtest.engines.market_detection

## Function: 

Infer market type from symbol format.

Args:
    code: Ticker / symbol string.

Returns:
    Market type (``a_share``, ``us_equity``, ``hk_equity``,
    ``crypto``, ``futures``, ``forex``).
    Unknown symbols default to ``us_equity``.

*Line: 51*

---

## Function: 

Check whether a futures code belongs to a Chinese exchange.

Recognises two forms:
  1. ``<product><delivery>.<exchange>`` where exchange is one of
     CFFEX/SHFE/DCE/ZCE/INE/GFEX.
  2. Bare ``<product><delivery>`` with no exchange suffix, matched
     against ``_CN_FUTURES_PRODUCTS``.

Args:
    code: Symbol string.

Returns:
    True if it looks like a Chinese futures contract.

*Line: 68*

---

## Function: 

Detect US vs HK vs China-A from symbol suffixes.

Args:
    codes: Instrument codes.

Returns:
    ``"hk"`` if any code ends with ``.HK``, ``"china_a"`` if A-share
    patterns are found, else ``"us"``.

*Line: 94*

---

