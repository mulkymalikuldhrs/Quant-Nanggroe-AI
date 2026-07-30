from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any

from fastapi import APIRouter
from quant_nanggroe.core.cache import TTLCache

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/terminal", tags=["Terminal"])

_CACHE = TTLCache(default_ttl=120)


def _get_macro_pulse_provider():
    from quant_nanggroe.providers.tradebobby.macro_pulse_provider import MacroPulseProvider
    return MacroPulseProvider()


def _get_crypto_pulse_provider():
    from quant_nanggroe.providers.tradebobby.crypto_pulse_provider import CryptoPulseProvider
    return CryptoPulseProvider()


def _get_cvd_provider():
    from quant_nanggroe.providers.tradebobby.cvd_provider import CVDProvider
    return CVDProvider()


def _get_liquidity_provider():
    from quant_nanggroe.providers.tradebobby.liquidity_wall_provider import LiquidityWallProvider
    return LiquidityWallProvider()


def _get_currency_provider():
    from quant_nanggroe.providers.tradebobby.currency_strength_provider import CurrencyStrengthProvider
    return CurrencyStrengthProvider()


def _get_etf_provider():
    from quant_nanggroe.providers.tradebobby.etf_flows_provider import ETFFlowProvider
    return ETFFlowProvider()


def _get_sentiment_provider():
    from quant_nanggroe.providers.tradebobby.news_scanner_provider import NewsScannerProvider
    return NewsScannerProvider()


@router.get("/macro-pulse")
async def get_macro_pulse() -> dict[str, Any]:
    try:
        p = _get_macro_pulse_provider()
        data = p.fetch_all()
        vix = p.get_vix_term()
        yield_curve = p.get_yield_curve()
        regime = p.get_macro_regime()
        commodities = p.get_commodities()
        return {
            "timestamp": datetime.now().isoformat(),
            "tickers": data.get("data", {}),
            "vix": vix,
            "yield_curve": yield_curve,
            "regime": regime,
            "commodities": commodities,
        }
    except Exception as exc:
        logger.warning("macro-pulse failed: %s", exc)
        return {"timestamp": datetime.now().isoformat(), "error": str(exc)}


@router.get("/crypto-pulse")
async def get_crypto_pulse() -> dict[str, Any]:
    try:
        p = _get_crypto_pulse_provider()
        fng = p.get_fear_greed()
        dom = p.get_dominance()
        fund = p.get_funding_rates()
        return {
            "timestamp": datetime.now().isoformat(),
            "fear_greed": fng,
            "dominance": dom,
            "funding_rates": fund,
        }
    except Exception as exc:
        logger.warning("crypto-pulse failed: %s", exc)
        return {"timestamp": datetime.now().isoformat(), "error": str(exc)}


@router.get("/cot")
async def get_cot() -> dict[str, Any]:
    from quant_nanggroe.providers.cot_provider import fetch_cot, COT_SYMBOL_MAP
    symbols = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD",
               "XAUUSD", "XAGUSD", "USOIL", "NATGAS",
               "ES", "NQ", "BTCUSD",
               "CORN", "WHEAT", "SOYBEAN",
               "COPPER", "ZN", "ZB"]
    results = []
    for sym in symbols:
        try:
            d = fetch_cot(sym, weeks=8)
            if d is not None:
                results.append(d)
        except Exception as exc:
            logger.debug("COT fetch failed %s: %s", sym, exc)
    return {
        "timestamp": datetime.now().isoformat(),
        "markets": results,
    }


@router.get("/cvd")
async def get_cvd() -> dict[str, Any]:
    try:
        p = _get_cvd_provider()
        return p.get_cvd_snapshot()
    except Exception as exc:
        logger.warning("cvd failed: %s", exc)
        return {"timestamp": datetime.now().isoformat(), "error": str(exc), "symbols": []}


@router.get("/liquidity-walls")
async def get_liquidity_walls() -> dict[str, Any]:
    try:
        p = _get_liquidity_provider()
        symbols = ["XAUUSD", "BTCUSD", "ETHUSD", "EURUSD", "GBPUSD", "USDJPY"]
        walls: dict[str, Any] = {}
        for sym in symbols:
            w = p.get_walls(sym)
            if w:
                walls[sym] = w
        return {
            "timestamp": datetime.now().isoformat(),
            "walls": walls,
        }
    except Exception as exc:
        logger.warning("liquidity-walls failed: %s", exc)
        return {"timestamp": datetime.now().isoformat(), "error": str(exc), "walls": {}}


@router.get("/currency-strength")
async def get_currency_strength() -> dict[str, Any]:
    try:
        p = _get_currency_provider()
        return p.get_currency_strength()
    except Exception as exc:
        logger.warning("currency-strength failed: %s", exc)
        return {"timestamp": datetime.now().isoformat(), "error": str(exc)}


@router.get("/etf-flows")
async def get_etf_flows() -> dict[str, Any]:
    try:
        p = _get_etf_provider()
        return p.get_etf_flows()
    except Exception as exc:
        logger.warning("etf-flows failed: %s", exc)
        return {"timestamp": datetime.now().isoformat(), "error": str(exc)}


@router.get("/sentiment")
async def get_sentiment() -> dict[str, Any]:
    try:
        p = _get_sentiment_provider()
        result = p.get_all_sentiment()
        return {
            "timestamp": datetime.now().isoformat(),
            "sentiment": result,
        }
    except Exception as exc:
        logger.warning("sentiment failed: %s", exc)
        return {"timestamp": datetime.now().isoformat(), "error": str(exc)}


@router.get("/health")
async def get_terminal_health() -> dict[str, Any]:
    providers = {
        "macro_pulse": False,
        "crypto_pulse": False,
        "cot": False,
        "cvd": False,
        "liquidity_walls": False,
        "currency_strength": False,
        "etf_flows": False,
        "sentiment": False,
    }
    for name in providers:
        try:
            ep = _get_endpoint(name)
            if ep is not None:
                providers[name] = True
        except Exception:
            providers[name] = False

    overall = "healthy" if all(providers.values()) else "degraded" if any(providers.values()) else "offline"
    return {
        "timestamp": datetime.now().isoformat(),
        "status": overall,
        "providers": providers,
        "version": "1.0.0",
    }


def _get_endpoint(name: str) -> Any:
    m = {
        "macro_pulse": _get_macro_pulse_provider,
        "crypto_pulse": _get_crypto_pulse_provider,
        "cot": lambda: True,
        "cvd": _get_cvd_provider,
        "liquidity_walls": _get_liquidity_provider,
        "currency_strength": _get_currency_provider,
        "etf_flows": _get_etf_provider,
        "sentiment": _get_sentiment_provider,
    }
    f = m.get(name)
    if f is not None:
        return f()
    return None
