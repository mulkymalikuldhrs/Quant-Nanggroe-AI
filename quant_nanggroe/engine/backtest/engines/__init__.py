"""Multi-market backtest engines.

Provides specialised engines for different asset classes, all inheriting
from BaseEngine. Use the factory function ``create_engine`` to auto-select
the correct engine based on market type or symbol patterns.

Engines:
  - BaseEngine: Abstract base with bar-by-bar execution loop
  - EquityEngine: US/HK equity (T+0, short allowed)
  - CryptoEngine: Crypto perpetuals (funding fees, liquidation)
  - ForexEngine: FX spot/CFD (spread, swap, high leverage)
  - FuturesEngine: Futures (contract multiplier, margin)
  - CompositeEngine: Cross-market (shared capital pool)

Ported from Vibe-Trading's backtest engine architecture.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from quant_nanggroe.engine.backtest.engines.base_engine import BaseEngine
from quant_nanggroe.engine.backtest.engines.composite_engine import CompositeEngine
from quant_nanggroe.engine.backtest.engines.crypto_engine import CryptoEngine
from quant_nanggroe.engine.backtest.engines.equity_engine import EquityEngine
from quant_nanggroe.engine.backtest.engines.forex_engine import ForexEngine
from quant_nanggroe.engine.backtest.engines.futures_engine import FuturesEngine
from quant_nanggroe.engine.backtest.engines.market_detection import (
    detect_market,
    detect_submarket,
    is_china_futures,
)

__all__ = [
    "BaseEngine",
    "EquityEngine",
    "CryptoEngine",
    "ForexEngine",
    "FuturesEngine",
    "CompositeEngine",
    "create_engine",
    "detect_market",
    "detect_submarket",
    "is_china_futures",
]


def create_engine(
    config: Dict[str, Any],
    codes: Optional[List[str]] = None,
) -> BaseEngine:
    """Factory: create the appropriate market engine.

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
    """
    explicit_market = config.get("market")

    if explicit_market:
        return _engine_from_market_name(explicit_market, config)

    if not codes:
        # Default to US equity if no codes provided
        return EquityEngine(config, market="us")

    market_types = {detect_market(c) for c in codes}

    # Cross-market -> CompositeEngine
    if len(market_types) > 1:
        return CompositeEngine(config, codes)

    market = market_types.pop()
    return _engine_from_market_name(market, config, codes)


def _engine_from_market_name(
    market: str,
    config: Dict[str, Any],
    codes: Optional[List[str]] = None,
) -> BaseEngine:
    """Map market name to engine instance.

    Args:
        market: Market type string.
        config: Backtest configuration.
        codes: Optional symbol list for sub-market detection.

    Returns:
        Engine instance.
    """
    if market in ("equity_us", "us_equity"):
        return EquityEngine(config, market="us")
    if market in ("equity_hk", "hk_equity"):
        return EquityEngine(config, market="hk")
    if market in ("equity",):
        sub = detect_submarket(codes) if codes else "us"
        return EquityEngine(config, market=sub)
    if market == "crypto":
        return CryptoEngine(config)
    if market == "forex":
        return ForexEngine(config)
    if market == "futures":
        return FuturesEngine(config)
    if market == "a_share":
        # Use equity engine with restricted rules (no short, T+1)
        return EquityEngine(config, market="china_a")

    # Default: US equity
    return EquityEngine(config, market="us")
