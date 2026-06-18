"""Crypto Agent Tools for Quant Nanggroe AI Trading Framework.

PRODUCTION: Wired to real crypto data:
- fetch_onchain: Uses DexIntelligenceEngine for real on-chain metrics
- analyze_dex: Uses MarketDataTool + DexIntelligenceEngine for real DEX data
- check_contract_risk: Uses DexIntelligenceEngine for real contract risk
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional

try:
    from langchain_core.tools import tool
except ImportError:
    def tool(func=None, *args, **kwargs):
        """No-op fallback when langchain_core is not installed."""
        if func is not None:
            return func
        def decorator(f):
            return f
        return decorator


logger = logging.getLogger(__name__)

# ── Mock mode flag ─────────────────────────────────────────────────────
_MOCK_MODE = False


# ── Lazy imports for real engine components ─────────────────────────────
def _get_dex_intelligence():
    """Lazy-load DexIntelligenceEngine from engine.screener."""
    try:
        from quant_nanggroe.engine.screener.dex_intelligence import DexIntelligenceEngine
        return DexIntelligenceEngine()
    except Exception as exc:
        logger.warning("Failed to load DexIntelligenceEngine: %s", exc)
        return None


def _get_market_data_tool():
    """Lazy-load MarketDataTool for real price data."""
    try:
        from quant_nanggroe.agents.tools.market_data import MarketDataTool
        return MarketDataTool()
    except Exception as exc:
        logger.warning("Failed to load MarketDataTool: %s", exc)
        return None


# ── Mock data fallbacks ─────────────────────────────────────────────────

def _mock_onchain(symbol, metrics, network) -> dict:
    logger.warning("MOCK MODE: Returning hardcoded on-chain data for %s", symbol)
    default_metrics = ["active_addresses", "transaction_count", "exchange_flow", "whale_activity", "hash_rate"]
    selected = metrics or default_metrics
    return {
        "symbol": symbol.upper(),
        "network": network,
        "metrics": {
            "active_addresses_24h": 850000,
            "transaction_count_24h": 1250000,
            "exchange_inflow_24h": 15000,
            "exchange_outflow_24h": 18000,
            "net_exchange_flow": -3000,
            "whale_transactions_24h": 245,
            "hash_rate": "580 EH/s" if symbol.upper() == "BTC" else "1.2 PH/s",
            "nvt_ratio": 45.2,
            "mvrv_zscore": 1.35,
            "supply_on_exchanges_pct": 11.8,
            "stablecoin_supply_ratio": 4.2,
        },
        "selected": selected,
        "timestamp": datetime.now().isoformat(),
        "_mock": True,
    }


def _mock_dex(symbol, chain, dex_name) -> dict:
    logger.warning("MOCK MODE: Returning hardcoded DEX data for %s", symbol)
    return {
        "symbol": symbol.upper(),
        "chain": chain,
        "dex_name": dex_name or "all",
        "analysis": {
            "total_volume_24h_usd": 150000000,
            "liquidity_usd": 500000000,
            "price_impact_1pct": 0.05,
            "price_impact_5pct": 0.25,
            "avg_slippage_bps": 12,
            "top_pool": f"{symbol.upper()}/USDC" if symbol.upper() != "USDC" else f"{symbol.upper()}/ETH",
            "pool_count": 45,
            "unique_traders_24h": 3200,
        },
        "timestamp": datetime.now().isoformat(),
        "_mock": True,
    }


def _mock_contract_risk(address, chain) -> dict:
    logger.warning("MOCK MODE: Returning hardcoded contract risk for %s", address)
    return {
        "address": address,
        "chain": chain,
        "risk_assessment": {
            "audit_status": "audited",
            "audit_firms": ["CertiK", "OpenZeppelin"],
            "overall_risk": "LOW",
            "risk_score": 25,
            "issues_found": 0,
            "critical_issues": 0,
            "is_verified": True,
            "is_proxy": False,
            "owner_is_multisig": True,
            "time_lock_active": True,
            "can_mint": False,
            "can_pause": True,
            "can_blacklist": False,
        },
        "recommendation": "Contract appears safe based on audit history and permissions.",
        "timestamp": datetime.now().isoformat(),
        "_mock": True,
    }


# ═══════════════════════════════════════════════════════════════════════
# LangChain @tool functions — PRODUCTION wired
# ═══════════════════════════════════════════════════════════════════════

@tool
def fetch_onchain(
    symbol: str,
    metrics: Optional[list] = None,
    network: str = "ethereum",
) -> str:
    """
    Fetch on-chain data for a cryptocurrency.

    PRODUCTION: Uses DexIntelligenceEngine for real on-chain metrics
    and MarketDataTool for real price/volume data.
    Falls back to mock data only in _MOCK_MODE.

    Args:
        symbol: Crypto symbol (BTC, ETH, SOL, etc.)
        metrics: Specific on-chain metrics to fetch
        network: Blockchain network

    Returns:
        JSON string with on-chain data
    """
    default_metrics = ["active_addresses", "transaction_count", "exchange_flow", "whale_activity", "hash_rate"]
    selected = metrics or default_metrics

    if not _MOCK_MODE:
        # PRODUCTION: Wired to real engine — try DexIntelligenceEngine
        dex = _get_dex_intelligence()
        mdt = _get_market_data_tool()

        result = {
            "symbol": symbol.upper(),
            "network": network,
            "metrics": {},
            "selected": selected,
            "timestamp": datetime.now().isoformat(),
        }

        # Try to get real price data from MarketDataTool
        if mdt is not None:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if not loop.is_running():
                    # Normalize symbol for crypto
                    crypto_symbol = symbol.upper()
                    if "/" not in crypto_symbol and not crypto_symbol.endswith("USDT"):
                        crypto_symbol = f"{crypto_symbol}/USDT"
                    price_data = loop.run_until_complete(
                        mdt.get_current_price(crypto_symbol)
                    )
                    result["metrics"]["current_price"] = price_data.get("price", 0.0)
                    result["metrics"]["volume_24h"] = price_data.get("volume_24h", 0.0)
                    result["_source"] = "MarketDataTool"  # PRODUCTION: Wired to real engine
            except Exception as exc:
                logger.debug("MarketDataTool price fetch failed for %s: %s", symbol, exc)

        # Try DexIntelligenceEngine
        if dex is not None:
            try:
                dex_data = dex.screen({"symbol": symbol, "network": network})
                if dex_data:
                    result["metrics"].update(dex_data.get("details", {}))
                    result["dex_intelligence_available"] = True  # PRODUCTION: Wired to real engine
            except Exception as exc:
                logger.debug("DexIntelligenceEngine failed for %s: %s", symbol, exc)

        if result["metrics"]:
            return json.dumps(result, indent=2, default=str)

    # Mock fallback
    if _MOCK_MODE:
        return json.dumps(_mock_onchain(symbol, metrics, network), indent=2)

    raise RuntimeError(
        f"Cannot fetch on-chain data for {symbol}: real engine unavailable and _MOCK_MODE=False. "
        "Install required dependencies or set _MOCK_MODE=True."
    )


@tool
def analyze_dex(
    symbol: str,
    chain: str = "ethereum",
    dex_name: Optional[str] = None,
) -> str:
    """
    Analyze DEX trading activity for a cryptocurrency.

    PRODUCTION: Uses DexIntelligenceEngine for real DEX analysis.
    Falls back to mock data only in _MOCK_MODE.

    Args:
        symbol: Crypto symbol
        chain: Blockchain chain
        dex_name: Specific DEX to analyze (uniswap, sushiswap, curve, etc.)

    Returns:
        JSON string with DEX analysis
    """
    if not _MOCK_MODE:
        # PRODUCTION: Wired to real engine — try DexIntelligenceEngine
        dex = _get_dex_intelligence()

        if dex is not None:
            try:
                dex_data = dex.screen({
                    "symbol": symbol,
                    "chain": chain,
                    "dex_name": dex_name,
                })
                if dex_data:
                    result = {
                        "symbol": symbol.upper(),
                        "chain": chain,
                        "dex_name": dex_name or "all",
                        "analysis": dex_data.get("details", {}),
                        "timestamp": datetime.now().isoformat(),
                        "_source": "DexIntelligenceEngine",  # PRODUCTION: Wired to real engine
                    }
                    return json.dumps(result, indent=2, default=str)
            except Exception as exc:
                logger.error("DexIntelligenceEngine failed for %s: %s", symbol, exc)
                raise RuntimeError(
                    f"Failed to analyze DEX for {symbol}: {exc}. "
                    "Set _MOCK_MODE=True for mock fallback."
                ) from exc

    # Mock fallback
    if _MOCK_MODE:
        return json.dumps(_mock_dex(symbol, chain, dex_name), indent=2)

    raise RuntimeError(
        f"Cannot analyze DEX for {symbol}: real engine unavailable and _MOCK_MODE=False. "
        "Install required dependencies or set _MOCK_MODE=True."
    )


@tool
def check_contract_risk(
    address: str,
    chain: str = "ethereum",
) -> str:
    """
    Check smart contract risk for a given address.

    PRODUCTION: Attempts real contract verification via block explorer APIs.
    Falls back to mock data only in _MOCK_MODE.

    Args:
        address: Contract address to check
        chain: Blockchain chain

    Returns:
        JSON string with contract risk assessment
    """
    if not _MOCK_MODE:
        # PRODUCTION: Wired to real engine — try DexIntelligenceEngine
        dex = _get_dex_intelligence()

        if dex is not None:
            try:
                risk_data = dex.screen({
                    "address": address,
                    "chain": chain,
                    "check_risk": True,
                })
                if risk_data:
                    result = {
                        "address": address,
                        "chain": chain,
                        "risk_assessment": risk_data.get("details", {}),
                        "timestamp": datetime.now().isoformat(),
                        "_source": "DexIntelligenceEngine",  # PRODUCTION: Wired to real engine
                    }
                    return json.dumps(result, indent=2, default=str)
            except Exception as exc:
                logger.debug("DexIntelligenceEngine contract check failed: %s", exc)

        # Try direct block explorer API (Etherscan)
        try:
            import urllib.request
            import json as _json

            if chain.lower() == "ethereum":
                url = f"https://api.etherscan.io/api?module=contract&action=getabi&address={address}"
            elif chain.lower() == "bsc":
                url = f"https://api.bscscan.com/api?module=contract&action=getabi&address={address}"
            else:
                url = None

            if url:
                req = urllib.request.Request(url, headers={"User-Agent": "QuantNanggroeAI/2.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = _json.loads(resp.read().decode())

                is_verified = data.get("status") == "1"
                return json.dumps({  # PRODUCTION: Wired to real engine
                    "address": address,
                    "chain": chain,
                    "risk_assessment": {
                        "is_verified": is_verified,
                        "verified_via": "block_explorer_api",
                    },
                    "timestamp": datetime.now().isoformat(),
                    "_source": "BlockExplorerAPI",
                }, indent=2)
        except Exception as exc:
            logger.debug("Block explorer API failed for %s: %s", address, exc)
            raise RuntimeError(
                f"Cannot check contract risk for {address}: {exc}. "
                "Set _MOCK_MODE=True for mock fallback."
            ) from exc

    # Mock fallback
    if _MOCK_MODE:
        return json.dumps(_mock_contract_risk(address, chain), indent=2)

    raise RuntimeError(
        f"Cannot check contract risk for {address}: real engine unavailable and _MOCK_MODE=False. "
        "Install required dependencies or set _MOCK_MODE=True."
    )


CRYPTO_TOOLS = [fetch_onchain, analyze_dex, check_contract_risk]
