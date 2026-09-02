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
        # merge defaults for missing keys
        out = dict(_DEFAULTS)
        out.update({k: v for k, v in data.items() if k in _DEFAULTS})
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


@router.get("")
def get_risk_config() -> dict[str, Any]:
    return _load()


@router.put("")
def update_risk_config(body: dict[str, Any]) -> dict[str, Any]:
    current = _load()
    for k, v in body.items():
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


@router.post("/reset")
def reset_risk_config() -> dict[str, Any]:
    _save(dict(_DEFAULTS))
    return {"status": "reset", "config": dict(_DEFAULTS)}
