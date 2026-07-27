"""
Causal Engine API — FastAPI Router
===================================
Provides endpoints for all causal macro engine data:
  - DCC-GARCH correlation matrix + volatilities
  - CME futures price data + returns cache
  - Causal bias evaluations
  - Macro weather status
  - COT positioning
  - Macro Surprise Index (MSI)
  - SMT divergence detection
  - Thesis drift guard status
  - Full pipeline evaluation

All data is sourced from the shared DCCState singleton and MasterQuantNanggroeEngine.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from quant_nanggroe.engine.causal import MasterQuantNanggroeEngine
from quant_nanggroe.engine.causal.cme_provider import CME_FUTURES_MAP, CMEPriceProvider
from quant_nanggroe.engine.risk.dcc_state import get_dcc_state

router = APIRouter(prefix="/api/causal", tags=["Causal Engine"])
logger = logging.getLogger("QNA-API-Causal")

# ── Shared engine instances (lazy, singletons for this module) ──────
_engine: Optional[MasterQuantNanggroeEngine] = None
_cme: Optional[CMEPriceProvider] = None


def _get_engine() -> MasterQuantNanggroeEngine:
    global _engine
    if _engine is None:
        _engine = MasterQuantNanggroeEngine(enable_fred=False, enable_cot=False)
    return _engine


def _get_cme() -> CMEPriceProvider:
    global _cme
    if _cme is None:
        _cme = CMEPriceProvider()
    return _cme


# ── Response Models ──────────────────────────────────────────────────

class CausalBiasResponse(BaseModel):
    event_type: str
    asset_biases: Dict[str, float]
    n_assets: int
    geopolitical_risk_delta: float = 0.0


class MacroWeatherResponse(BaseModel):
    classification: str
    dxy_change_pct: float = 0.0
    bond_change_pct: float = 0.0


class DCCStatusResponse(BaseModel):
    fitted: bool
    mean_corr: Optional[float] = None
    mean_vol_pct: Optional[float] = None
    n_assets: int = 0
    asset_names: List[str] = Field(default_factory=list)
    correlation_matrix: List[List[float]] = Field(default_factory=list)
    volatilities: List[float] = Field(default_factory=list)
    update_count: int = 0
    last_update: Optional[str] = None
    dcc_a: float = 0.05
    dcc_b: float = 0.90


class DCCTimeSeries(BaseModel):
    timestamps: List[str] = Field(default_factory=list)
    correlations: List[float] = Field(default_factory=list)
    asset_pair: str = ""
    n_observations: int = 0


class CMEPriceResponse(BaseModel):
    symbol: str
    price: Optional[float] = None
    spot_equivalent: Optional[str] = None
    futures_equivalent: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())


class CMEReturnsResponse(BaseModel):
    n_assets: int
    n_observations: int
    symbols: List[str]
    interval: str


class COTStatusResponse(BaseModel):
    signal: str = "UNAVAILABLE"
    n_extreme_long: int = 0
    n_extreme_short: int = 0
    n_balanced: int = 0
    extreme_assets: Dict[str, str] = Field(default_factory=dict)


class MSIResponse(BaseModel):
    connected: bool = False
    n_significant: int = 0
    n_series_total: int = 0
    events: Dict[str, Any] = Field(default_factory=dict)


class SMTDivergenceResponse(BaseModel):
    diverged: bool = False
    severity: str = "none"
    zscore: Optional[float] = None
    half_life: Optional[float] = None
    is_cointegrated: bool = False
    asset_a: str = ""
    asset_b: str = ""
    hedge_ratio: Optional[float] = None


class ThesisDriftResponse(BaseModel):
    stage: str = "STAGE_0_MONITOR"
    action: str = "hold"
    n_active_theses: int = 0
    theses: Dict[str, Any] = Field(default_factory=dict)


class PipelineEvalResponse(BaseModel):
    summary: str
    phase1_causal: Optional[CausalBiasResponse] = None
    phase2_weather: Optional[MacroWeatherResponse] = None
    phase2_cot: Optional[COTStatusResponse] = None
    phase2_dcc: Optional[DCCStatusResponse] = None
    phase2_smt: Optional[SMTDivergenceResponse] = None
    phase4_thesis: Optional[ThesisDriftResponse] = None


# ── Endpoints ────────────────────────────────────────────────────────

@router.get("/biases", response_model=CausalBiasResponse)
async def get_causal_biases(
    event: str = Query("GEOPOLITICAL_SUPPLY_SHOCK", description="Macro event type"),
    risk_delta: float = Query(0.0, description="Geopolitical risk delta (0-100)"),
):
    """Get directional biases for all tracked assets under a macro event."""
    engine = _get_engine()
    biases = engine.evaluate_causal_bias(
        event_type=event,
        geopolitical_risk_delta=risk_delta,
    )
    return CausalBiasResponse(
        event_type=event,
        asset_biases=biases,
        n_assets=len(biases),
        geopolitical_risk_delta=risk_delta,
    )


@router.get("/weather", response_model=MacroWeatherResponse)
async def get_macro_weather(
    dxy: float = Query(0.0, description="DXY change %"),
    bond: float = Query(0.0, description="ZB1 change %"),
):
    """Classify macro weather (Risk-On/Risk-Off/Neutral)."""
    engine = _get_engine()
    weather = engine.detect_macro_weather(
        dxy_change_pct=dxy, bond_zb_change_pct=bond
    )
    return MacroWeatherResponse(
        classification=weather,
        dxy_change_pct=dxy,
        bond_change_pct=bond,
    )


@router.get("/dcc/status", response_model=DCCStatusResponse)
async def get_dcc_status():
    """Get DCC-GARCH correlation matrix, volatilities, and fit status."""
    state = get_dcc_state()
    return DCCStatusResponse(
        fitted=state.fitted,
        mean_corr=state.get_status().get("mean_corr"),
        mean_vol_pct=state.get_status().get("mean_vol_pct"),
        n_assets=state.get_status().get("n_assets", 0),
        asset_names=state.asset_names,
        correlation_matrix=state.get_correlation_matrix(),
        volatilities=state.get_volatilities(),
        update_count=state.update_count,
        last_update=(
            state.last_update.isoformat() if state.last_update else None
        ),
        dcc_a=0.05,
        dcc_b=0.90,
    )


@router.get("/dcc/correlation")
async def get_dcc_correlation_matrix():
    """Get the full DCC correlation matrix as a 2D array."""
    state = get_dcc_state()
    return {
        "correlation_matrix": state.get_correlation_matrix(),
        "asset_names": state.asset_names,
        "fitted": state.fitted,
    }


@router.get("/dcc/pair")
async def get_pair_correlation(
    asset_i: str = Query(..., description="First asset name"),
    asset_j: str = Query(..., description="Second asset name"),
):
    """Get correlation between two specific assets."""
    state = get_dcc_state()
    corr = state.get_pair_correlation(asset_i, asset_j)
    if corr is None:
        raise HTTPException(
            status_code=404,
            detail=f"Pair {asset_i}/{asset_j} not found in DCC model",
        )
    return {"pair": f"{asset_i}/{asset_j}", "correlation": corr}


@router.post("/dcc/refresh")
async def refresh_dcc(
    interval: str = Query("1h", description="Candle interval"),
    lookback: int = Query(100, ge=30, le=500, description="Observations"),
):
    """Force-refresh DCC-GARCH with latest market data."""
    cme = _get_cme()
    returns = cme.get_returns(
        symbols=list(CME_FUTURES_MAP.keys())[:8],
        interval=interval,
        lookback=lookback,
        force_refresh=True,
    )
    if returns.empty:
        raise HTTPException(status_code=503, detail="Insufficient market data for DCC fit")

    state = get_dcc_state()
    success = state.update(returns)
    return {
        "status": "fitted" if success else "failed",
        "n_assets": len(returns.columns),
        "n_observations": len(returns),
        "interval": interval,
    }


@router.get("/cme/prices")
async def get_cme_prices():
    """Get latest prices for all tracked CME futures."""
    cme = _get_cme()
    prices = cme.get_all_prices()
    return {
        "prices": prices,
        "n_symbols": len(prices),
        "watchlist": cme.DEFAULT_WATCHLIST,
    }


@router.get("/cme/returns")
async def get_cme_returns(
    interval: str = Query("1h", description="Candle interval"),
    lookback: int = Query(100, ge=30, le=500, description="Observations"),
):
    """Get log returns data for DCC-GARCH."""
    cme = _get_cme()
    returns = cme.get_returns(interval=interval, lookback=lookback)
    return CMEReturnsResponse(
        n_assets=len(returns.columns) if not returns.empty else 0,
        n_observations=len(returns) if not returns.empty else 0,
        symbols=list(returns.columns) if not returns.empty else [],
        interval=interval,
    )


@router.get("/cot", response_model=COTStatusResponse)
async def get_cot_status():
    """Get COT institutional positioning signals."""
    engine = _get_engine()
    # Try engine's COT analyzer
    signal = "UNAVAILABLE"
    n_extreme_long = 0
    n_extreme_short = 0
    n_balanced = 0
    extremes: Dict[str, str] = {}

    if engine._cot_analyzer is not None:
        try:
            analysis = engine._cot_analyzer.analyze()
            signal = analysis.get("signal", "UNAVAILABLE")
            n_extreme_long = analysis.get("n_extreme_long", 0)
            n_extreme_short = analysis.get("n_extreme_short", 0)
            n_balanced = analysis.get("n_balanced", 0)
            extremes = analysis.get("extreme_assets", {})
        except Exception as e:
            logger.debug("COT analysis failed: %s", e)
    elif engine._cot is not None:
        try:
            extremes = engine._cot.detect_extreme_positioning()
            n_extreme_long = sum(
                1 for v in extremes.values() if v == "EXTREME_LONG_OVERBOUGHT"
            )
            n_extreme_short = sum(
                1 for v in extremes.values() if v == "EXTREME_SHORT_OVERSOLD"
            )
            n_balanced = sum(1 for v in extremes.values() if v == "BALANCED")
            signal = "ANALYZED"
        except Exception:
            pass

    return COTStatusResponse(
        signal=signal,
        n_extreme_long=n_extreme_long,
        n_extreme_short=n_extreme_short,
        n_balanced=n_balanced,
        extreme_assets=extremes,
    )


@router.get("/msi", response_model=MSIResponse)
async def get_macro_surprises():
    """Get Macro Surprise Index data from FRED."""
    engine = _get_engine()
    if engine._msi is not None and engine._msi.connected:
        try:
            surprises = engine._msi.get_recent_surprises()
            return MSIResponse(
                connected=True,
                n_significant=surprises.get("n_significant", 0),
                n_series_total=surprises.get("total_series", 0),
                events=surprises.get("events", {}),
            )
        except Exception as e:
            logger.debug("MSI fetch failed: %s", e)

    return MSIResponse(connected=False)


@router.get("/smt", response_model=SMTDivergenceResponse)
async def get_smt_divergence(
    asset_a: str = Query("GC1!", description="First asset symbol"),
    asset_b: str = Query("SI1!", description="Second asset symbol"),
    lookback: int = Query(100, ge=30, le=500, description="Price observations"),
):
    """Check SMT divergence between two correlated assets."""
    cme = _get_cme()
    engine = _get_engine()

    klines_a = cme.get_klines(asset_a, limit=lookback)
    klines_b = cme.get_klines(asset_b, limit=lookback)

    if not klines_a or not klines_b:
        raise HTTPException(status_code=503, detail="Insufficient price data")

    prices_a = [k["close"] for k in klines_a]
    prices_b = [k["close"] for k in klines_b]

    result = engine.check_smt_divergence(prices_a, prices_b, asset_a, asset_b)

    return SMTDivergenceResponse(
        diverged=result.get("diverged", False),
        severity=result.get("severity", "none"),
        zscore=result.get("zscore"),
        half_life=result.get("half_life"),
        is_cointegrated=result.get("is_cointegrated", False),
        asset_a=asset_a,
        asset_b=asset_b,
        hedge_ratio=result.get("hedge_ratio"),
    )


@router.get("/smt/pairs")
async def get_smt_pairs():
    """Get all tracked SMT pairs and their current status."""
    engine = _get_engine()
    if engine._smt is not None:
        summary = engine._smt.pair_summary()
    else:
        from quant_nanggroe.engine.causal.smt_divergence import SMTDivergenceDetector
        smt = SMTDivergenceDetector()
        summary = smt.pair_summary()
    return {"pairs": summary}


@router.get("/thesis", response_model=ThesisDriftResponse)
async def get_thesis_status():
    """Get thesis drift guard status for all active theses."""
    engine = _get_engine()
    if engine._thesis_guard is not None:
        theses = engine._thesis_guard.get_active_theses()
        stage = "STAGE_0_MONITOR"
        action = "hold"
        for tid, t in theses.items():
            if t.get("stage", "STAGE_0_MONITOR") == "STAGE_2_EXECUTE":
                stage = "STAGE_2_EXECUTE"
                action = "exit"
            elif t.get("stage") == "STAGE_1_ALERT" and stage == "STAGE_0_MONITOR":
                stage = "STAGE_1_ALERT"
                action = "reduce"
        return ThesisDriftResponse(
            stage=stage,
            action=action,
            n_active_theses=len(theses),
            theses=theses,
        )
    return ThesisDriftResponse()


@router.get("/pipeline")
async def evaluate_pipeline(
    event: str = Query("GEOPOLITICAL_SUPPLY_SHOCK", description="Macro event type"),
    dxy: float = Query(0.0, description="DXY change %"),
    bond: float = Query(0.0, description="ZB1 change %"),
):
    """Run the full 4-phase causal macro pipeline and return results."""
    engine = _get_engine()
    result = engine.evaluate_full_pipeline(
        event_type=event,
        dxy_change=dxy,
        bond_change=bond,
    )
    return result


@router.get("/status")
async def get_full_status():
    """Get aggregated causal engine status — all subsystems in one call."""
    dcc_state = get_dcc_state()
    engine = _get_engine()
    cme = _get_cme()

    return {
        "dcc": dcc_state.get_status(),
        "cme": cme.get_status(),
        "pairs_tracked": len(CME_FUTURES_MAP),
        "available_endpoints": [
            "/api/causal/biases",
            "/api/causal/weather",
            "/api/causal/dcc/status",
            "/api/causal/dcc/correlation",
            "/api/causal/dcc/pair",
            "/api/causal/dcc/refresh",
            "/api/causal/cme/prices",
            "/api/causal/cme/returns",
            "/api/causal/cot",
            "/api/causal/msi",
            "/api/causal/smt",
            "/api/causal/smt/pairs",
            "/api/causal/thesis",
            "/api/causal/pipeline",
        ],
    }


__all__ = ["router"]
