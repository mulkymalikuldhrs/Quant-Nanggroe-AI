"""Risk Config API — editable risk limits via UI, followed by entire QNA system.

Persistence: config/risk_config.json (gitignored, like mt5_accounts.yaml).
Every field is validated and hot-reloaded by RiskManager on next check_trade.

Fields:
- maxRiskPerTrade (0.001-0.02 = 0.1%-2%)
- maxDailyLoss (0.005-0.05 = 0.5%-5%)
- maxWeeklyLoss (0.01-0.10 = 1%-10%)
- maxDrawdown (0.05-0.30 = 5%-30%)
- maxLeverage (1-10)
- maxPositionSize (0.05-0.5 = 5%-50%)
- maxDailyTrades (1-20)
- minRiskReward (1.0-5.0)
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/risk-config", tags=["Risk Config"])

_CONFIG_PATH = Path(__file__).resolve().parents[3] / "config" / "risk_config.json"

_DEFAULTS: dict[str, Any] = {
    "maxRiskPerTrade": 0.005,  # 0.5%
    "maxPositionSize": 0.10,  # 10%
    "maxLeverage": 3.0,
    "maxDailyLoss": 0.01,  # 1%
    "maxDailyTrades": 5,
    "maxWeeklyLoss": 0.03,  # 3%
    "maxDrawdown": 0.10,  # 10%
    "minRiskReward": 2.0,
    "maxCorrelatedPositions": 3,
    "perSymbol": {},  # e.g. {"EURUSD": {"maxRiskPerTrade": 0.003}}
    "perStrategy": {},  # e.g. {"kaufman_ama": {"maxRiskPerTrade": 0.004}}
    "perRegime": {},  # e.g. {"trending": {"maxRiskPerTrade": 0.006}, "ranging": {"maxRiskPerTrade": 0.003}}
}

_LIMITS: dict[str, tuple[float, float]] = {
    "maxRiskPerTrade": (0.001, 0.02),
    "maxPositionSize": (0.05, 0.50),
    "maxLeverage": (1.0, 10.0),
    "maxDailyLoss": (0.005, 0.05),
    "maxDailyTrades": (1, 20),
    "maxWeeklyLoss": (0.01, 0.10),
    "maxDrawdown": (0.05, 0.30),
    "minRiskReward": (1.0, 5.0),
    "maxCorrelatedPositions": (1, 10),
}


def _load() -> dict[str, Any]:
    if not _CONFIG_PATH.exists():
        return dict(_DEFAULTS)
    try:
        data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
        out = dict(_DEFAULTS)
        # global keys
        for k in _DEFAULTS:
            if k in data and k not in ("perSymbol", "perStrategy", "perRegime"):
                out[k] = data[k]
        # per-* overrides (dicts)
        for pk in ("perSymbol", "perStrategy", "perRegime"):
            if pk in data and isinstance(data[pk], dict):
                out[pk] = data[pk]
            else:
                out[pk] = {}
        return out
    except Exception as e:
        logger.warning("risk_config load failed: %s", e)
        return dict(_DEFAULTS)


def _save(data: dict[str, Any]) -> None:
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _CONFIG_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def load_risk_config() -> dict[str, Any]:
    """Load risk config for engine use (hot-reload each check)."""
    return _load()


def get_effective_config(symbol: str | None = None, strategy: str | None = None, regime: str | None = None) -> dict[str, Any]:
    """Effective config for a specific symbol/strategy/regime (global + overrides)."""
    base = _load()
    out = {k: v for k, v in base.items() if k not in ("perSymbol", "perStrategy", "perRegime")}
    # perSymbol
    if symbol and isinstance(base.get("perSymbol"), dict):
        # normalize symbol like EURUSD.vx → EURUSD
        norm = symbol.upper().replace(".VX", "").replace(".VXC", "").replace("/", "")
        for k, overrides in base["perSymbol"].items():
            if k.upper().replace(".VX", "").replace("/", "") == norm and isinstance(overrides, dict):
                for rk, rv in overrides.items():
                    if rk in _LIMITS:
                        out[rk] = float(rv)
    # perStrategy
    if strategy and isinstance(base.get("perStrategy"), dict) and strategy in base["perStrategy"]:
        for rk, rv in base["perStrategy"][strategy].items():
            if rk in _LIMITS:
                out[rk] = float(rv)
    # perRegime
    if regime and isinstance(base.get("perRegime"), dict) and regime in base["perRegime"]:
        for rk, rv in base["perRegime"][regime].items():
            if rk in _LIMITS:
                out[rk] = float(rv)
    return out


@router.get("")
def get_risk_config() -> dict[str, Any]:
    return _load()


@router.put("")
def update_risk_config(body: dict[str, Any]) -> dict[str, Any]:
    current = _load()
    for k, v in body.items():
        if k in ("perSymbol", "perStrategy", "perRegime"):
            if not isinstance(v, dict):
                raise HTTPException(status_code=400, detail=f"{k} must be dict")
            # validate each override's numeric fields
            for sym, overrides in v.items():
                if not isinstance(overrides, dict):
                    raise HTTPException(status_code=400, detail=f"{k}[{sym}] must be dict")
                for rk, rv in overrides.items():
                    if rk not in _LIMITS:
                        raise HTTPException(status_code=400, detail=f"Unknown risk key: {rk} in {k}")
                    try:
                        fv = float(rv)
                    except Exception:
                        raise HTTPException(status_code=400, detail=f"{k}[{sym}].{rk} must be numeric")
                    lo, hi = _LIMITS[rk]
                    if not (lo <= fv <= hi):
                        raise HTTPException(status_code=400, detail=f"{k}[{sym}].{rk} must be {lo}..{hi}, got {fv}")
            current[k] = v
            continue
        if k not in _DEFAULTS:
            raise HTTPException(status_code=400, detail=f"Unknown risk key: {k}")
        lo, hi = _LIMITS[k]
        try:
            fv = float(v)
        except Exception:
            raise HTTPException(status_code=400, detail=f"{k} must be numeric")
        if not (lo <= fv <= hi):
            raise HTTPException(status_code=400, detail=f"{k} must be {lo}..{hi}, got {fv}")
        current[k] = fv
    _save(current)
    logger.info("risk_config updated: %s", list(body.keys()))
    return {"status": "saved", "config": current}


@router.get("/effective")
def get_effective_risk_config(symbol: str | None = None, strategy: str | None = None, regime: str | None = None) -> dict[str, Any]:
    return get_effective_config(symbol, strategy, regime)


@router.post("/reset")
def reset_risk_config() -> dict[str, Any]:
    _save(dict(_DEFAULTS))
    return {"status": "reset", "config": dict(_DEFAULTS)}
