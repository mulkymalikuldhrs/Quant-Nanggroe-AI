# engine.backtest.engines.__init__

## Function: 

Factory: create the appropriate market engine.

Routing priority:
  1. If config has ``market`` set explicitly, use that.
  2. Detect market type from symbol patterns.
  3. Multiple market types -> CompositeEngine.

Args:
    config: Backtest configuration dict. Recognised keys:
        - ``market``: Explicit market type (``equity_us``, ``equity_hk``,
          ``crypto``, ``forex``, ``futures``).
        - ``leverage``: Default leverage (default 1.0).
        - ``initial_cash``: Starting capital (default 1_000_000).
    codes: List of instrument codes. Used for auto-detection when
        ``market`` is not set.

Returns:
    BaseEngine subclass instance.

Raises:
    ValueError: If market cannot be determined.

*Line: 48*

---

## Function: 

Map market name to engine instance.

Args:
    market: Market type string.
    config: Backtest configuration.
    codes: Optional symbol list for sub-market detection.

Returns:
    Engine instance.

*Line: 93*

---

