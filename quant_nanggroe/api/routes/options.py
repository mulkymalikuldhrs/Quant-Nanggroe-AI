"""Options trading & analysis API routes.

Enhanced with vol surface, SABR model, and multi-leg strategy analysis.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/options", tags=["options"])


def _exchange_manager(request: Request):
    """Lazily reuse the app-wide ExchangeManager (mirrors market.py)."""
    from quant_nanggroe.exchange.manager import ExchangeManager

    svc = getattr(request.app.state, "_services", {})
    if "exchange_manager" not in svc:
        svc["exchange_manager"] = ExchangeManager()
    return svc["exchange_manager"]


class AnalyzeRequest(BaseModel):
    symbol: str
    type: str  # call | put
    strike: float
    expiry: str  # YYYY-MM-DD
    spot: float | None = None  # omit to fetch live ticker
    volatility: float | None = 0.3
    rate: float = 0.05


class VolSurfaceRequest(BaseModel):
    spot: float = 100.0
    strikes: list[float] | None = None
    expiry: float = 1.0
    beta: float = 0.5
    alpha: float = 0.04
    rho: float = -0.3
    nu: float = 0.4


class StrategyRequest(BaseModel):
    name: str = "custom"
    spot: float = 100.0
    legs: list[dict]
    rate: float = 0.05
    sigma: float = 0.3


# DEPRECATED (v8.1.0 triage): no dashboard callers — see docs/DEAD_API.md
@router.get("/chain/{symbol}")
async def get_options_chain(symbol: str) -> dict[str, Any]:
    # ponytail: no real options feed wired — return honest empty state, never synthetic.
    return {
        "symbol": symbol.upper(),
        "items": [],
        "count": 0,
        "module": "options",
        "status": "unavailable",
        "detail": "Real options chain unavailable; no synthetic data returned.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# DEPRECATED (v8.1.0 triage): no dashboard callers — see docs/DEAD_API.md
@router.get("/positions")
async def get_options_positions() -> dict[str, Any]:
    # ponytail: no real options feed wired — return honest empty state, never synthetic.
    return {
        "positions": [],
        "count": 0,
        "module": "options",
        "status": "unavailable",
        "detail": "Real options positions unavailable; no synthetic data returned.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# DEPRECATED (v8.1.0 triage): no dashboard callers — see docs/DEAD_API.md
@router.post("/analyze")
async def analyze_option_strategy(req: AnalyzeRequest, request: Request) -> dict[str, Any]:
    # ponytail: real pricing via Black-Scholes (engine.options.analyzer).
    # spot defaults to a live ticker fetch; if no feed, caller must pass spot.
    from quant_nanggroe.engine.options.analyzer import OptionsAnalyzer

    otype = req.type.lower()
    if otype not in ("call", "put"):
        raise HTTPException(status_code=400, detail="type must be 'call' or 'put'")

    spot = req.spot
    if spot is None:
        try:
            em = _exchange_manager(request)
            ticker = await em.get_ticker(req.symbol)
            spot = ticker.last_price
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"spot price unavailable for {req.symbol}; pass 'spot' explicitly. ({exc})",
            )
    if not spot or spot <= 0:
        raise HTTPException(status_code=400, detail="spot price must be positive")

    try:
        expiry = datetime.strptime(req.expiry, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except ValueError:
        raise HTTPException(status_code=400, detail="expiry must be YYYY-MM-DD")
    T = (expiry - datetime.now(timezone.utc)).days / 365.0
    if T <= 0:
        raise HTTPException(status_code=400, detail="expiry must be in the future")

    sigma = req.volatility if req.volatility and req.volatility > 0 else 0.3
    analyzer = OptionsAnalyzer()
    bs = analyzer.analyze(S=spot, K=req.strike, T=T, r=req.rate, sigma=sigma)
    greeks = bs["greeks"]

    price = bs["call_price"] if otype == "call" else bs["put_price"]
    breakeven = (
        req.strike + price if otype == "call" else req.strike - price
    )

    return {
        "symbol": req.symbol,
        "type": otype,
        "spot": spot,
        "strike": req.strike,
        "expiry": req.expiry,
        "analysis": {
            "theoretical_price": round(price, 4),
            "intrinsic_value": round(max(0, spot - req.strike) if otype == "call"
                                     else max(0, req.strike - spot), 2),
            "time_value": round(max(0, price - (max(0, spot - req.strike)
                               if otype == "call" else max(0, req.strike - spot))), 2),
            "breakeven": round(breakeven, 2),
            "greeks": {
                "delta": round(greeks.delta, 4),
                "gamma": round(greeks.gamma, 4),
                "theta": round(greeks.theta, 4),
                "vega": round(greeks.vega, 4),
                "rho": round(greeks.rho, 4),
            },
        },
        "module": "options",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ── Vol Surface ──────────────────────────────────────────────────────────


# DEPRECATED (v8.1.0 triage): no dashboard callers — see docs/DEAD_API.md
@router.post("/vol-surface")
async def sabr_vol_surface(req: VolSurfaceRequest) -> dict[str, Any]:
    """Construct volatility smile using SABR model."""
    try:
        from quant_nanggroe.engine.options.vol_surface import SABRModel

        strikes = req.strikes or [round(req.spot * (0.8 + 0.4 * i / 10), 1) for i in range(11)]
        sabr = SABRModel(alpha=req.alpha, beta=req.beta, rho=req.rho, nu=req.nu)
        vols = [round(sabr.implied_vol(req.spot, k, req.expiry), 4) for k in strikes]

        return {
            "status": "success",
            "spot": req.spot,
            "model": "SABR",
            "parameters": {"alpha": req.alpha, "beta": req.beta, "rho": req.rho, "nu": req.nu},
            "expiry_years": req.expiry,
            "vol_surface": [
                {"strike": k, "forward": req.spot, "moneyness": round(k / req.spot, 4), "iv": v}
                for k, v in zip(strikes, vols)
            ],
            "module": "options_extra",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except ImportError:
        raise HTTPException(status_code=501, detail="Vol surface module requires scipy")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Multi-leg Strategy ───────────────────────────────────────────────────


# DEPRECATED (v8.1.0 triage): no dashboard callers — see docs/DEAD_API.md
@router.post("/strategy")
async def analyze_multi_leg_strategy(req: StrategyRequest) -> dict[str, Any]:
    """Analyze a multi-leg option strategy (straddle, strangle, butterfly, etc.)."""
    try:
        from quant_nanggroe.engine.options.strategies import analyze_strategy

        result = analyze_strategy(
            name=req.name,
            spot=req.spot,
            legs=req.legs,
            rate=req.rate,
            sigma=req.sigma,
        )

        return {
            "status": "success",
            "strategy": result.summary(),
            "net_premium": round(result.net_premium, 4),
            "max_profit": round(result.max_profit, 4),
            "max_loss": round(result.max_loss, 4),
            "break_even": [round(b, 4) for b in result.break_even],
            "greeks": {
                "delta": round(result.total_delta, 4),
                "gamma": round(result.total_gamma, 4),
                "theta": round(result.total_theta, 4),
                "vega": round(result.total_vega, 4),
            },
            "payoff": result.payoff_at_expiry[:10] if result.payoff_at_expiry else None,
            "legs": [
                {
                    "side": lg.side.value,
                    "position": lg.position.value,
                    "strike": lg.strike,
                    "premium": round(lg.premium, 4),
                    "delta": round(lg.delta, 4),
                }
                for lg in result.legs
            ],
            "module": "options_extra",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except ImportError as e:
        raise HTTPException(status_code=501, detail=f"Strategy module error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Named strategy shortcuts ─────────────────────────────────────────────


class NamedStrategyRequest(BaseModel):
    name: str  # straddle, strangle, bull_call_spread, bear_put_spread, butterfly, iron_condor, covered_call
    spot: float = 100.0
    strike: float | None = None
    strike_lower: float | None = None
    strike_upper: float | None = None
    expiry_years: float = 1.0


# DEPRECATED (v8.1.0 triage): no dashboard callers — see docs/DEAD_API.md
@router.post("/strategy/named")
async def named_strategy(req: NamedStrategyRequest) -> dict[str, Any]:
    """Quick named strategy analysis."""
    try:
        from quant_nanggroe.engine.options.strategies import OptionStrategy

        builder = OptionStrategy(spot=req.spot, T=req.expiry_years)
        result = None

        if req.name == "straddle" and req.strike:
            result = builder.straddle(req.strike, req.expiry_years)
        elif req.name == "strangle" and req.strike_lower and req.strike_upper:
            result = builder.strangle(req.strike_upper, req.strike_lower, req.expiry_years)
        elif req.name == "bull_call_spread" and req.strike_lower and req.strike_upper:
            result = builder.bull_call_spread(req.strike_lower, req.strike_upper, req.expiry_years)
        elif req.name == "bear_put_spread" and req.strike_lower and req.strike_upper:
            result = builder.bear_put_spread(req.strike_lower, req.strike_upper, req.expiry_years)
        elif req.name == "butterfly" and req.strike and req.strike_lower and req.strike_upper:
            result = builder.butterfly(req.strike_lower, req.strike, req.strike_upper, req.expiry_years)
        elif req.name == "iron_condor" and req.strike_lower and req.strike_upper:
            # For iron condor, user provides 4 strikes as list or defaults
            result = builder.iron_condor(
                req.strike_lower - 10, req.strike_lower,
                req.strike_upper, req.strike_upper + 10,
                req.expiry_years,
            )
        elif req.name == "covered_call" and req.strike:
            result = builder.covered_call(req.strike, req.expiry_years)
        else:
            raise HTTPException(status_code=400, detail=f"Invalid or incomplete parameters for {req.name}")

        return {
            "status": "success",
            "strategy": result.summary(),
            "net_premium": round(result.net_premium, 4),
            "max_profit": round(result.max_profit, 4),
            "max_loss": round(result.max_loss, 4),
            "break_even": [round(b, 4) for b in result.break_even],
            "greeks": {
                "delta": round(result.total_delta, 4),
                "gamma": round(result.total_gamma, 4),
                "theta": round(result.total_theta, 4),
                "vega": round(result.total_vega, 4),
            },
            "module": "options_extra",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
