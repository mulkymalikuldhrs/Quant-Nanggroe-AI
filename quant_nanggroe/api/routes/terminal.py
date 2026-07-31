from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/terminal", tags=["Terminal"])


def _record_success(provider: str, data: Any = None) -> None:
    """Record provider success for data quality monitoring (C8 gap)."""
    try:
        from quant_nanggroe.engine.data_quality import get_monitor
        get_monitor().record_success(provider, data)
    except Exception:
        pass  # fail-closed: never break API on monitor failure


def _record_failure(provider: str, error: str = "") -> None:
    """Record provider failure for data quality monitoring (C8 gap)."""
    try:
        from quant_nanggroe.engine.data_quality import get_monitor
        get_monitor().record_failure(provider, error)
    except Exception:
        pass


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
    from quant_nanggroe.providers.tradebobby.news_scanner_provider import TradeBobbyNewsScanner
    return TradeBobbyNewsScanner()


def _get_derivatives_provider():
    from quant_nanggroe.providers.tradebobby.derivatives_provider import DerivativesProvider
    return DerivativesProvider()


def _get_econ_calendar_provider():
    from quant_nanggroe.providers.tradebobby.econ_calendar_provider import EconCalendarProvider
    return EconCalendarProvider()


def _compute_risk_index(vix_data: dict[str, Any], regime: dict[str, Any]) -> dict[str, Any]:
    """Heuristic 0-100 risk index from VIX level + regime signals."""
    vix = vix_data.get("vix", 20.0)
    # VIX maps: <12=low risk, 12-20=normal, 20-30=elevated, >30=high
    if vix < 12:
        vix_score = 10
    elif vix < 20:
        vix_score = 10 + (vix - 12) * 5  # 10-50
    elif vix < 30:
        vix_score = 50 + (vix - 20) * 4  # 50-90
    else:
        vix_score = min(100, 90 + (vix - 30))
    # Regime penalty
    regime_state = regime.get("vix_regime", "NORMAL")
    regime_adj = {"LOW_VOL": -10, "NORMAL": 0, "ELEVATED": 15, "HIGH_VOL": 30}.get(regime_state, 0)
    risk_index = max(0, min(100, round(vix_score + regime_adj)))
    return {
        "risk_index": risk_index,
        "vix_level": vix,
        "regime": regime_state,
    }


@router.get("/macro-pulse")
async def get_macro_pulse() -> dict[str, Any]:
    result: dict[str, Any]
    try:
        p = _get_macro_pulse_provider()
        data = p.fetch_all()
        vix = p.get_vix_term()
        yield_curve = p.get_yield_curve()
        regime = p.get_macro_regime()
        commodities = p.get_commodities()
        sector_rotation = p.get_sector_rotation()
        risk = _compute_risk_index(vix, regime)
        result = {
            "timestamp": datetime.now().isoformat(),
            "tickers": data.get("data", {}),
            "vix": vix,
            "yield_curve": yield_curve,
            "regime": regime,
            "commodities": commodities,
            "risk_index": risk["risk_index"],
            "vix_level": risk["vix_level"],
            "sector_rotation": sector_rotation,
        }
        _record_success("macro_pulse", result)
        return result
    except Exception as exc:
        logger.warning("macro-pulse failed: %s", exc)
        _record_failure("macro_pulse", str(exc))
        return {"timestamp": datetime.now().isoformat(), "error": str(exc)}


@router.get("/crypto-pulse")
async def get_crypto_pulse() -> dict[str, Any]:
    result: dict[str, Any]
    try:
        p = _get_crypto_pulse_provider()
        fng = p.get_fear_greed()
        dom = p.get_dominance()
        fund = p.get_funding_rates()
        result = {
            "timestamp": datetime.now().isoformat(),
            "fear_greed": fng,
            "dominance": dom,
            "funding_rates": fund,
        }
        _record_success("crypto_pulse", result)
        return result
    except Exception as exc:
        logger.warning("crypto-pulse failed: %s", exc)
        _record_failure("crypto_pulse", str(exc))
        return {"timestamp": datetime.now().isoformat(), "error": str(exc)}


@router.get("/cot")
async def get_cot() -> dict[str, Any]:
    from quant_nanggroe.providers.cot_provider import fetch_cot
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
    out = {
        "timestamp": datetime.now().isoformat(),
        "markets": results,
    }
    _record_success("cot", out)
    return out


@router.get("/cvd")
async def get_cvd() -> dict[str, Any]:
    try:
        p = _get_cvd_provider()
        snap = p.get_cvd_snapshot()
        # Surface classification + divergence at top level for quick scan.
        symbols = snap.get("symbols", [])
        classifications = {s["symbol"]: s.get("regime", "NO_DATA") for s in symbols}
        divergences = [
            {"symbol": s["symbol"], "divergence": s["divergence"]}
            for s in symbols if s.get("divergence")
        ]
        snap["classifications"] = classifications
        snap["active_divergences"] = divergences
        _record_success("cvd", snap)
        return snap
    except Exception as exc:
        logger.warning("cvd failed: %s", exc)
        _record_failure("cvd", str(exc))
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
        result = {"timestamp": datetime.now().isoformat(), "walls": walls}
        _record_success("liquidity_wall", result)
        return result
    except Exception as exc:
        logger.warning("liquidity-walls failed: %s", exc)
        _record_failure("liquidity_wall", str(exc))
        return {"timestamp": datetime.now().isoformat(), "error": str(exc), "walls": {}}


@router.get("/currency-strength")
async def get_currency_strength() -> dict[str, Any]:
    try:
        p = _get_currency_provider()
        result = p.get_currency_strength()
        _record_success("currency_strength", result)
        return result
    except Exception as exc:
        logger.warning("currency-strength failed: %s", exc)
        _record_failure("currency_strength", str(exc))
        return {"timestamp": datetime.now().isoformat(), "error": str(exc)}


@router.get("/etf-flows")
async def get_etf_flows() -> dict[str, Any]:
    try:
        p = _get_etf_provider()
        result = p.get_etf_flows()
        _record_success("etf_flows", result)
        return result
    except Exception as exc:
        logger.warning("etf-flows failed: %s", exc)
        _record_failure("etf_flows", str(exc))
        return {"timestamp": datetime.now().isoformat(), "error": str(exc)}


@router.get("/sentiment")
async def get_sentiment() -> dict[str, Any]:
    try:
        p = _get_sentiment_provider()
        result = p.get_news_pulse()
        triggers = p.get_critical_triggers()
        risk_off = p.get_risk_off_score()
        out = {
            "timestamp": datetime.now().isoformat(),
            "news_pulse": result,
            "critical_triggers": triggers,
            "risk_off_score": risk_off,
        }
        _record_success("news_scanner", out)
        return out
    except Exception as exc:
        logger.warning("sentiment failed: %s", exc)
        _record_failure("news_scanner", str(exc))
        return {"timestamp": datetime.now().isoformat(), "error": str(exc)}


@router.get("/derivatives")
async def get_derivatives(symbol: str = Query("BTCUSDT")) -> dict[str, Any]:
    try:
        p = _get_derivatives_provider()
        data = p.get_derivatives(symbol.upper())
        result = {"timestamp": datetime.now().isoformat(), **data}
        _record_success("derivatives", result)
        return result
    except Exception as exc:
        logger.warning("derivatives failed for %s: %s", symbol, exc)
        _record_failure("derivatives", str(exc))
        return {"timestamp": datetime.now().isoformat(), "error": str(exc), "symbol": symbol}


@router.get("/econ-calendar")
async def get_econ_calendar(hours: int = Query(48)) -> dict[str, Any]:
    try:
        p = _get_econ_calendar_provider()
        events = p.get_upcoming(hours=hours)
        result = {"timestamp": datetime.now().isoformat(), "hours": hours, "events": events}
        _record_success("econ_calendar", result)
        return result
    except Exception as exc:
        logger.warning("econ-calendar failed: %s", exc)
        _record_failure("econ_calendar", str(exc))
        return {"timestamp": datetime.now().isoformat(), "error": str(exc), "events": []}


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
        "derivatives": False,
        "econ_calendar": False,
    }
    for name in providers:
        try:
            ep = _get_endpoint(name)
            if ep is not None:
                providers[name] = True
        except Exception:
            providers[name] = False

    overall = "healthy" if all(providers.values()) else "degraded" if any(providers.values()) else "offline"
    result = {
        "timestamp": datetime.now().isoformat(),
        "status": overall,
        "providers": providers,
        "version": "1.0.0",
    }
    # Cross-reference data quality monitor — staleness detection (C8)
    try:
        from quant_nanggroe.engine.data_quality import get_monitor
        dq_health = get_monitor().get_health()
        result["data_quality"] = {
            "overall_status": dq_health["overall_status"],
            "healthy": dq_health["healthy_count"],
            "stale": dq_health["stale_count"],
            "degraded": dq_health["degraded_count"],
            "failed": dq_health["failed_count"],
        }
    except Exception:
        pass  # never break health endpoint on monitor failure
    return result


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
        "derivatives": _get_derivatives_provider,
        "econ_calendar": _get_econ_calendar_provider,
    }
    f = m.get(name)
    if f is not None:
        return f()
    return None
