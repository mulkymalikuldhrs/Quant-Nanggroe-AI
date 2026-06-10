"""
Asset Class Detection and Routing for Quant Nanggroe AI Trading Framework v2.

Implements the conditional routing logic that dispatches the trading pipeline
down specialized paths based on the detected asset class of the symbols
under analysis. This is the key branching point after market_analysis in
the v2 graph architecture.

Routing paths:
  - crypto_path   → Solana/Jupiter DEX tools, on-chain analysis
  - forex_path    → FX-specific analysis, carry-trade evaluation
  - equity_path   → Standard equity flow (researcher + macro)
  - prediction_market_path → Polymarket / event-contract integration
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from quant_nanggroe.agents.state import (
    AgentState,
    AssetClass,
)


logger = logging.getLogger(__name__)


# =============================================================================
# Symbol pattern definitions for asset-class detection
# =============================================================================

# Crypto symbols typically end with USDT, BTC, ETH, SOL, BNB, etc. or are
# well-known crypto tickers.
_CRYPTO_PATTERNS: List[str] = [
    r".*USDT$", r".*BUSD$", r".*USDC$", r".*BTC$",
    r".*ETH$", r".*SOL$", r".*BNB$",
    r"^(BTC|ETH|SOL|BNB|XRP|ADA|DOGE|DOT|AVAX|MATIC|LINK|UNI|AAVE|ARB|OP|FIL|ATOM|NEAR|FTM|ALGO|XTZ|EOS|LTC|BCH|ETC|ICP|VET|HBAR|SAND|MANA|AXS|CRV|SUSHI|1INCH|COMP|MKR|SNX|YFI|BAL|RNDR|INJ|SUI|SEI|TIA|JUP|PYTH|WIF|BONK|PEPE|FLOKI|SHIB)$",
    r"^(WBTC|STETH|CBETH|RPL|LDO|FXS|PENDLE|STRK|IMX|GALAXY)$",
]

# Forex symbols are 6-letter pairs (EURUSD, GBPUSD) or common FX suffixes.
_FOREX_PATTERNS: List[str] = [
    r"^[A-Z]{3}[A-Z]{3}$",  # Standard 6-char currency pair
    r"^[A-Z]{3}\/[A-Z]{3}$",  # EUR/USD format
    r"^(EURUSD|GBPUSD|USDJPY|AUDUSD|USDCAD|USDCHF|NZDUSD)$",
    r"^(XAUUSD|XAGUSD|XPTUSD|XPDUSD)$",  # Precious metals via FX brokers
    r"^(EURGBP|EURJPY|GBPJPY|AUDJPY|NZDJPY|CADJPY|CHFJPY)$",
    r"^(EURAUD|EURNZD|EURNOK|EURSEK|GBPAUD|GBPCAD|GBPNZD)$",
    r"^(AUDCAD|AUDNZD|AUDSGD|NZDCAD|NZDSGD|CADCHF|AUDCHF|NZDCHF)$",
    r"^(USDMXN|USDBRL|USDZAR|USDTRY|USDCNH|USDINR|USDKRW|USDTWD)$",
    r"^(USDSGD|USDHKD|USDNOK|USDSEK|USDDKK|USDPLN|USDCZK|USDHUF)$",
]

# Prediction market symbols use specific prefixes or patterns.
_PREDICTION_MARKET_PATTERNS: List[str] = [
    r"^POLY:",  # Polymarket condition-id prefix
    r"^PM_",  # Internal prediction-market symbol prefix
    r"^EVENT:",  # Generic event contract prefix
    r"\.(YES|NO|TRUE|FALSE)$",  # Outcome tokens (e.g., "TRUMP_WIN.YES")
    r"\.(DEM|REP)$",  # Political outcome tokens
    r"^KALSHI:",  # Kalshi prefix
    r"^META:",  # Metaculus prefix
]

# Equity symbols are anything that doesn't match the above (default path).
# We do NOT maintain a full equity list; instead we rely on negative matching.


# =============================================================================
# Core detection logic
# =============================================================================

def detect_asset_class(symbol: str) -> AssetClass:
    """
    Detect the asset class of a single trading symbol.

    Uses regex pattern matching on the symbol string. If no pattern matches,
    defaults to EQUITY (the broadest category).

    Args:
        symbol: Trading symbol to classify

    Returns:
        AssetClass enum value
    """
    symbol_upper = symbol.upper().strip()

    # Check prediction market first (most specific patterns)
    for pattern in _PREDICTION_MARKET_PATTERNS:
        if re.search(pattern, symbol_upper):
            logger.debug(f"Symbol '{symbol}' classified as PREDICTION_MARKET (pattern: {pattern})")
            return AssetClass.PREDICTION_MARKET

    # Check crypto patterns
    for pattern in _CRYPTO_PATTERNS:
        if re.search(pattern, symbol_upper):
            logger.debug(f"Symbol '{symbol}' classified as CRYPTO (pattern: {pattern})")
            return AssetClass.CRYPTO

    # Check forex patterns
    for pattern in _FOREX_PATTERNS:
        if re.search(pattern, symbol_upper):
            logger.debug(f"Symbol '{symbol}' classified as FOREX (pattern: {pattern})")
            return AssetClass.FOREX

    # Default: equity
    logger.debug(f"Symbol '{symbol}' classified as EQUITY (default)")
    return AssetClass.EQUITY


def detect_dominant_asset_class(symbols: List[str]) -> AssetClass:
    """
    Determine the dominant asset class across a list of symbols.

    If all symbols belong to the same class, returns that class.
    For mixed lists, returns the class with the most symbols.
    In case of ties, prioritises: CRYPTO > FOREX > PREDICTION_MARKET > EQUITY.

    Args:
        symbols: List of trading symbols

    Returns:
        Dominant AssetClass
    """
    if not symbols:
        return AssetClass.UNKNOWN

    class_counts: Dict[AssetClass, int] = {}
    for symbol in symbols:
        ac = detect_asset_class(symbol)
        class_counts[ac] = class_counts.get(ac, 0) + 1

    # If all symbols share one class, return it directly
    if len(class_counts) == 1:
        return next(iter(class_counts.keys()))

    # Tie-breaking priority order
    priority = [
        AssetClass.PREDICTION_MARKET,
        AssetClass.CRYPTO,
        AssetClass.FOREX,
        AssetClass.EQUITY,
    ]

    max_count = max(class_counts.values())
    for ac in priority:
        if class_counts.get(ac, 0) == max_count:
            return ac

    return AssetClass.EQUITY


def asset_class_to_path(asset_class: AssetClass) -> str:
    """
    Map an AssetClass to its execution path name in the graph.

    Args:
        asset_class: Detected asset class

    Returns:
        Execution path string (e.g., 'crypto_path', 'forex_path')
    """
    mapping: Dict[AssetClass, str] = {
        AssetClass.CRYPTO: "crypto_path",
        AssetClass.FOREX: "forex_path",
        AssetClass.EQUITY: "equity_path",
        AssetClass.PREDICTION_MARKET: "prediction_market_path",
        AssetClass.UNKNOWN: "equity_path",  # Safe default
    }
    return mapping.get(asset_class, "equity_path")


# =============================================================================
# LangGraph node / conditional-edge functions
# =============================================================================

class AssetRouter:
    """
    Asset class router node for the v2 LangGraph trading graph.

    When used as a graph node, it detects the asset class of the symbols
    in the current state and writes the `asset_class` and `execution_path`
    fields.

    When used as a conditional-edge function, it returns the execution
    path string so that LangGraph can route to the correct branch.
    """

    def __call__(self, state: AgentState) -> Dict[str, Any]:
        """
        Execute the asset routing node: detect class and write state.

        Args:
            state: Current agent state

        Returns:
            State updates with asset_class and execution_path
        """
        symbols = state.get("symbols", [])
        logger.info(f"=== Asset Router: classifying {len(symbols)} symbol(s) ===")

        # Detect per-symbol classes for diagnostics
        per_symbol_classes: Dict[str, str] = {}
        for symbol in symbols:
            ac = detect_asset_class(symbol)
            per_symbol_classes[symbol] = ac.value

        # Determine dominant class for routing
        dominant_class = detect_dominant_asset_class(symbols)
        path = asset_class_to_path(dominant_class)

        logger.info(
            f"Asset classification: {per_symbol_classes} → "
            f"dominant={dominant_class.value}, path={path}"
        )

        return {
            "asset_class": dominant_class.value,
            "execution_path": path,
            "metadata": {
                **state.get("metadata", {}),
                "per_symbol_asset_classes": per_symbol_classes,
                "routing_decision": {
                    "dominant_class": dominant_class.value,
                    "execution_path": path,
                },
            },
            "sender": "asset_router",
        }


def route_by_asset_class(state: AgentState) -> str:
    """
    Conditional-edge function: route to the correct execution path.

    This function reads the `execution_path` field from state (populated
    by the asset_router node) and returns the path name so that
    LangGraph can follow the correct branch.

    Args:
        state: Current agent state

    Returns:
        Execution path name string
    """
    path = state.get("execution_path", "equity_path")

    # Validate the path is one we support
    valid_paths = {
        "crypto_path",
        "forex_path",
        "equity_path",
        "prediction_market_path",
    }

    if path not in valid_paths:
        logger.warning(
            f"Unknown execution path '{path}', defaulting to equity_path"
        )
        return "equity_path"

    logger.info(f"Routing to execution path: {path}")
    return path
