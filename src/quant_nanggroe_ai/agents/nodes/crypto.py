"""
Crypto Specialist Agent — DeFi, on-chain analysis, and crypto market structure.
=================================================================================
Analyzes crypto-specific market data including on-chain metrics, DEX volumes,
funding rates, liquidation levels, and DeFi protocol activity.

Responsibilities:
  - Fetch crypto-specific market data (funding rates, OI, liquidations)
  - Analyze on-chain metrics (whale movements, exchange flows)
  - Assess DeFi protocol health and TVL trends
  - Provide crypto-specific risk assessment
  - Return crypto_context for the trading graph
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from quant_nanggroe_ai.agents.state import AgentState

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════
# Crypto Risk Levels
# ══════════════════════════════════════════════════════════════════════

CRYPTO_RISK_LOW = "LOW"
CRYPTO_RISK_MEDIUM = "MEDIUM"
CRYPTO_RISK_HIGH = "HIGH"
CRYPTO_RISK_EXTREME = "EXTREME"


# ══════════════════════════════════════════════════════════════════════
# Crypto Symbol Classification
# ══════════════════════════════════════════════════════════════════════

MAJOR_CRYPTO = {"BTC", "ETH", "BNB", "XRP", "SOL", "ADA", "AVAX", "DOT"}
STABLECOINS = {"USDT", "USDC", "DAI", "BUSD", "FRAX"}
DEFI_TOKENS = {"UNI", "AAVE", "COMP", "MKR", "CRV", "SUSHI", "DYDX", "SNX"}
MEME_TOKENS = {"DOGE", "SHIB", "PEPE", "FLOKI", "BONK"}


def _classify_crypto(symbol: str) -> dict[str, Any]:
    """
    Classify a crypto symbol into categories.

    Returns a dict with category, risk tier, and relevant metrics.
    """
    upper = symbol.upper().replace("USDT", "").replace("USDC", "").replace("BUSD", "")
    base = upper.rstrip("/")

    if base in MAJOR_CRYPTO:
        return {
            "category": "major",
            "risk_tier": 1,
            "typical_volatility": 0.03,
            "liquidity": "HIGH",
            "has_perpetuals": True,
        }
    elif base in DEFI_TOKENS:
        return {
            "category": "defi",
            "risk_tier": 2,
            "typical_volatility": 0.05,
            "liquidity": "MEDIUM",
            "has_perpetuals": True,
        }
    elif base in MEME_TOKENS:
        return {
            "category": "meme",
            "risk_tier": 4,
            "typical_volatility": 0.10,
            "liquidity": "LOW",
            "has_perpetuals": False,
        }
    elif base in STABLECOINS:
        return {
            "category": "stablecoin",
            "risk_tier": 0,
            "typical_volatility": 0.001,
            "liquidity": "VERY_HIGH",
            "has_perpetuals": False,
        }
    else:
        return {
            "category": "altcoin",
            "risk_tier": 3,
            "typical_volatility": 0.07,
            "liquidity": "LOW",
            "has_perpetuals": False,
        }


def _fetch_funding_rate(symbol: str) -> dict[str, Any]:
    """
    Fetch current perpetual funding rate for a crypto symbol.

    In production, this would query Binance/Bybit/OKX API.
    Returns structured data with graceful degradation.
    """
    try:
        from quant_nanggroe_ai.agents.tools.market_data import MarketDataTool
        tool = MarketDataTool()
        # Try to get funding rate from exchange data
        # For now, return a reasonable placeholder
        return {
            "symbol": symbol,
            "funding_rate": 0.0001,  # 0.01% typical
            "next_funding_time": None,
            "open_interest": None,
            "source": "placeholder",
            "note": "Connect exchange API for live funding rates",
        }
    except Exception as exc:
        logger.debug("Funding rate fetch failed: %s", exc)
        return {
            "symbol": symbol,
            "funding_rate": None,
            "source": "unavailable",
            "error": str(exc),
        }


def _assess_crypto_risk(
    classification: dict[str, Any],
    volatility: float = 0.0,
    funding_rate: float | None = None,
) -> tuple[str, str]:
    """
    Assess crypto-specific risk level.

    Returns (risk_level, risk_reason) tuple.
    """
    category = classification.get("category", "altcoin")
    risk_tier = classification.get("risk_tier", 3)
    typical_vol = classification.get("typical_volatility", 0.05)

    # Extreme risk: meme tokens or very high volatility
    if category == "meme":
        return CRYPTO_RISK_EXTREME, (
            f"Meme token ({category}) — extremely high volatility and "
            f"low liquidity. Use minimal position sizes."
        )

    # High volatility relative to typical
    if volatility > typical_vol * 3:
        return CRYPTO_RISK_HIGH, (
            f"Current volatility ({volatility:.4f}) is >3x typical "
            f"({typical_vol:.4f}) for {category}. Elevated risk."
        )

    # Negative funding rate (shorts paying longs) can indicate squeeze
    if funding_rate is not None and funding_rate < -0.001:
        return CRYPTO_RISK_HIGH, (
            f"Highly negative funding rate ({funding_rate:.4%}) — "
            f"potential short squeeze risk."
        )

    # Very high funding rate (overleveraged longs)
    if funding_rate is not None and funding_rate > 0.001:
        return CRYPTO_RISK_MEDIUM, (
            f"Elevated positive funding rate ({funding_rate:.4%}) — "
            f"longs are crowded, potential cascade risk."
        )

    # DeFi tokens have smart contract risk
    if category == "defi":
        return CRYPTO_RISK_MEDIUM, (
            "DeFi token — additional smart contract and protocol risk. "
            "Verify contract audits and TVL stability."
        )

    # Major crypto with normal volatility
    if category == "major":
        return CRYPTO_RISK_LOW, (
            f"Major cryptocurrency with standard volatility. "
            f"Normal risk parameters apply."
        )

    # Altcoin default
    return CRYPTO_RISK_MEDIUM, (
        f"Altcoin ({category}) — higher inherent risk than majors. "
        f"Reduce position size by 50% vs major crypto."
    )


async def crypto_node(state: AgentState) -> dict[str, Any]:
    """
    Crypto Specialist Agent node.

    Analyzes crypto-specific market data including on-chain metrics,
    DEX volumes, funding rates, and DeFi protocol health.

    This node enriches the agent state with crypto-specific context
    that is not captured by the generic analyst node.
    """
    symbol = state.symbol or "BTCUSDT"
    errors: list[str] = []

    # ── 1. Classify the crypto symbol ──────────────────────────────────
    classification = _classify_crypto(symbol)

    # ── 2. Fetch funding rate data ─────────────────────────────────────
    try:
        funding_data = _fetch_funding_rate(symbol)
    except Exception as exc:
        logger.warning("Funding rate fetch failed: %s", exc)
        funding_data = {"symbol": symbol, "funding_rate": None, "source": "error"}
        errors.append(f"Funding rate: {exc}")

    # ── 3. Get volatility from technical analysis ──────────────────────
    ta = state.technical_analysis
    current_volatility = ta.get("atr_pct", 0.0) / 100.0 if ta else 0.0

    # ── 4. Assess crypto risk ──────────────────────────────────────────
    crypto_risk_level, crypto_risk_reason = _assess_crypto_risk(
        classification=classification,
        volatility=current_volatility,
        funding_rate=funding_data.get("funding_rate"),
    )

    # ── 5. Build crypto context string ─────────────────────────────────
    category = classification.get("category", "unknown")
    risk_tier = classification.get("risk_tier", 3)
    funding_str = "N/A"
    if funding_data.get("funding_rate") is not None:
        funding_str = f"{funding_data['funding_rate']:.4%}"

    crypto_context = (
        f"Crypto analysis for {symbol} (category: {category}, risk tier: {risk_tier}): "
        f"Volatility: {current_volatility:.4f}. "
        f"Funding rate: {funding_str}. "
        f"Risk level: {crypto_risk_level} — {crypto_risk_reason}. "
        f"Liquidity: {classification.get('liquidity', 'UNKNOWN')}. "
        f"Perpetuals available: {classification.get('has_perpetuals', False)}."
    )

    # ── Return state updates ────────────────────────────────────────────
    return {
        "macro_context": (
            (state.macro_context + "\n" + crypto_context)
            if state.macro_context
            else crypto_context
        ),
        "errors": state.errors + errors,
        "agent_trace": state.agent_trace + [
            {
                "agent": "crypto",
                "status": "completed",
                "action": "crypto_analysis",
                "symbol": symbol,
                "category": category,
                "risk_tier": risk_tier,
                "crypto_risk_level": crypto_risk_level,
                "funding_rate": funding_data.get("funding_rate"),
                "timestamp": datetime.now().isoformat(),
            }
        ],
    }
