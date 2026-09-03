"""Risk Config API — editable risk limits via UI, followed by entire QNA system.

Persistence: config/risk_config.json (gitignored, like mt5_accounts.yaml).
Every field is validated and hot-reloaded by RiskManager on next check_trade.

Schema (v8.0.23 — A2 fail-closed):
- version: 1 (REQUIRED on write; missing on read = default-fill, fail-closed warning)
- maxRiskPerTrade (0.001-0.02 = 0.1%-2%)
- maxDailyLoss (0.005-0.05 = 0.5%-5%)
- maxWeeklyLoss (0.01-0.10 = 1%-10%)
- maxDrawdown (0.05-0.30 = 5%-30%)
- maxLeverage (1-10)
- maxPositionSize (0.05-0.5 = 5%-50%)
- maxDailyTrades (1-20)
- minRiskReward (1.0-5.0)
- maxCorrelatedPositions (1-10)
- perSymbol, perStrategy, perRegime — same fields nested per key (fail-closed: unknown keys rejected)
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
SCHEMA_VERSION = 1

_DEFAULTS: dict[str, Any] = {
    "version": SCHEMA_VERSION,
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

# Per-override key allowlist — same numeric fields as global
_OVERRIDE_KEYS: frozenset[str] = frozenset(_LIMITS.keys())

# A2: known top-level keys (so we can reject unknown ones instead of silently dropping)
_KNOWN_TOP_KEYS: frozenset[str] = frozenset(_DEFAULTS.keys())

# A-G10: known regime vocabulary — market regimes (check_trade docstring) +
# vol regimes (VolRegime enum). A perRegime key outside this set warns as
# "unknown" so typos (e.g. "trendin") cannot silently disable an override.
_KNOWN_REGIMES: frozenset[str] = frozenset({
    "trending", "ranging", "crisis", "bullish", "bearish", "neutral",
    "low", "normal", "elevated", "high", "extreme",
})

# A-G10: normalized keys observed by get_effective_config, per axis.
# A configured override key that never matches any evaluation warns once.
_SEEN_KEYS: dict[str, set[str]] = {"perSymbol": set(), "perStrategy": set(), "perRegime": set()}
_WARNED_UNUSED_KEYS: set[tuple[str, str]] = set()


def _warn_unused_override_keys(base: dict[str, Any]) -> None:
    """Warn once per configured override key that never matched any evaluation."""
    for axis in ("perSymbol", "perStrategy", "perRegime"):
        section = base.get(axis)
        if not isinstance(section, dict):
            continue
        for key in section:
            norm = _normalize_symbol(str(key)) if axis == "perSymbol" else str(key).lower()
            if norm not in _SEEN_KEYS[axis] and (axis, norm) not in _WARNED_UNUSED_KEYS:
                _WARNED_UNUSED_KEYS.add((axis, norm))
                logger.warning(
                    "risk_config[%s][%s] never matched any evaluated symbol/strategy/regime — "
                    "check for typos or stale keys", axis, key,
                )
            if axis == "perRegime" and str(key).lower() not in _KNOWN_REGIMES \
                    and ("perRegime:unknown", str(key).lower()) not in _WARNED_UNUSED_KEYS:
                _WARNED_UNUSED_KEYS.add(("perRegime:unknown", str(key).lower()))
                logger.warning("risk_config[perRegime][%s] is not a known regime name — override may never apply", key)


def _coerce_override_value(rk: str, rv: Any) -> float:
    """Validate a per-* override's numeric value. Fail-closed: raises ValueError on any error."""
    if rk not in _OVERRIDE_KEYS:
        raise ValueError(f"Unknown risk key: {rk}")
    try:
        fv = float(rv)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{rk} must be numeric, got {rv!r}") from exc
    lo, hi = _LIMITS[rk]
    if not (lo <= fv <= hi):
        raise ValueError(f"{rk} must be {lo}..{hi}, got {fv}")
    return fv


def _load() -> dict[str, Any]:
    """Load + validate + default-fill risk config. Fail-closed: corrupt file → defaults."""
    if not _CONFIG_PATH.exists():
        return dict(_DEFAULTS)
    try:
        data = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        logger.warning("risk_config parse failed: %s — falling back to defaults", e)
        return dict(_DEFAULTS)
    if not isinstance(data, dict):
        logger.warning("risk_config root is not a dict — falling back to defaults")
        return dict(_DEFAULTS)
    out = dict(_DEFAULTS)
    # Reject unknown top-level keys (A2 fail-closed)
    unknown = set(data.keys()) - _KNOWN_TOP_KEYS
    if unknown:
        logger.warning("risk_config has unknown top-level keys %s — ignoring", unknown)
    # Global keys (numeric, validated)
    for k in _LIMITS:
        if k in data:
            try:
                out[k] = _coerce_override_value(k, data[k])
            except ValueError as e:
                logger.warning("risk_config[%s] invalid: %s — using default", k, e)
                # keep default
    # Per-* overrides (dicts of dicts)
    for pk in ("perSymbol", "perStrategy", "perRegime"):
        src = data.get(pk)
        if isinstance(src, dict):
            cleaned: dict[str, dict[str, float]] = {}
            for key, overrides in src.items():
                if not isinstance(overrides, dict):
                    logger.warning("risk_config[%s][%s] not a dict — skipping", pk, key)
                    continue
                inner: dict[str, float] = {}
                for rk, rv in overrides.items():
                    try:
                        inner[rk] = _coerce_override_value(rk, rv)
                    except ValueError as e:
                        logger.warning("risk_config[%s][%s].%s invalid: %s — skipping", pk, key, rk, e)
                if inner:
                    cleaned[str(key)] = inner
            out[pk] = cleaned
        else:
            out[pk] = {}
    # Stamp schema version on read
    out["version"] = SCHEMA_VERSION
    return out


def _save(data: dict[str, Any]) -> None:
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    out = dict(data)
    out["version"] = SCHEMA_VERSION  # always stamp current schema on write
    _CONFIG_PATH.write_text(json.dumps(out, indent=2, sort_keys=True), encoding="utf-8")


def load_risk_config() -> dict[str, Any]:
    """Load risk config for engine use (hot-reload each check)."""
    return _load()


def _normalize_symbol(s: str) -> str:
    """Normalize a trading symbol for override matching.

    Strips broker suffixes and slashes consistently:
    - EURUSD.vxc / EURUSD.vx / EURUSD.VX / EURUSD.VXC → EURUSD
    - EURUSD/C → EURUSD
    - eurUSD   → EURUSD
    """
    import re
    s = s.upper()
    # strip broker suffixes (any of .vx, .vxc, .VX, .VXC, etc.) — only if 3+ trailing chars
    s = re.sub(r"\.(VX|VXC)$", "", s)
    # strip slash and anything after (e.g. EURUSD/C → EURUSD)
    s = s.split("/", 1)[0]
    return s


def get_effective_config(symbol: str | None = None, strategy: str | None = None, regime: str | None = None) -> dict[str, Any]:
    """Effective config for a specific symbol/strategy/regime (global + overrides).

    Matching is case-insensitive for perStrategy/perRegime keys (A-G10);
    perSymbol matching goes through _normalize_symbol (already case-insensitive).
    Layering (last wins): global → perSymbol → perStrategy → perRegime.
    """
    base = _load()
    out = {k: v for k, v in base.items() if k not in ("perSymbol", "perStrategy", "perRegime", "version")}
    # A-G10: track which override keys actually match an evaluation, so
    # typos / stale keys (e.g. perRegime "trendin") surface as warnings
    # instead of silently never applying.
    if symbol:
        _SEEN_KEYS["perSymbol"].add(_normalize_symbol(symbol))
    if strategy:
        _SEEN_KEYS["perStrategy"].add(strategy.lower())
    if regime:
        _SEEN_KEYS["perRegime"].add(regime.lower())
        if regime.lower() not in _KNOWN_REGIMES:
            logger.warning("risk_config: unknown regime name %r — no perRegime override can match it", regime)
    # perSymbol
    if symbol and isinstance(base.get("perSymbol"), dict):
        norm = _normalize_symbol(symbol)
        for k, overrides in base["perSymbol"].items():
            if _normalize_symbol(k) == norm and isinstance(overrides, dict):
                for rk, rv in overrides.items():
                    if rk in _LIMITS:
                        out[rk] = float(rv)
    # perStrategy (A-G10: case-insensitive)
    if strategy and isinstance(base.get("perStrategy"), dict):
        lowered = {str(k).lower(): v for k, v in base["perStrategy"].items()}
        hit = lowered.get(strategy.lower())
        if isinstance(hit, dict):
            for rk, rv in hit.items():
                if rk in _LIMITS:
                    out[rk] = float(rv)
    # perRegime (A-G10: case-insensitive)
    if regime and isinstance(base.get("perRegime"), dict):
        lowered = {str(k).lower(): v for k, v in base["perRegime"].items()}
        hit = lowered.get(regime.lower())
        if isinstance(hit, dict):
            for rk, rv in hit.items():
                if rk in _LIMITS:
                    out[rk] = float(rv)
    _warn_unused_override_keys(base)
    return out


@router.get("")
def get_risk_config() -> dict[str, Any]:
    return _load()


@router.put("")
def update_risk_config(body: dict[str, Any]) -> dict[str, Any]:
    """PUT /risk-config — strict schema validation. Unknown keys → 400 (A2 fail-closed)."""
    current = _load()
    for k, v in body.items():
        if k == "version":
            # version is auto-stamped on save; reject explicit version writes
            raise HTTPException(status_code=400, detail="version is auto-managed; do not write it")
        if k in ("perSymbol", "perStrategy", "perRegime"):
            if not isinstance(v, dict):
                raise HTTPException(status_code=400, detail=f"{k} must be dict")
            cleaned: dict[str, dict[str, float]] = {}
            for key, overrides in v.items():
                if not isinstance(overrides, dict):
                    raise HTTPException(status_code=400, detail=f"{k}[{key}] must be dict")
                inner: dict[str, float] = {}
                for rk, rv in overrides.items():
                    if rk not in _OVERRIDE_KEYS:
                        raise HTTPException(status_code=400, detail=f"Unknown risk key: {rk} in {k}[{key}]")
                    try:
                        inner[rk] = _coerce_override_value(rk, rv)
                    except ValueError as e:
                        raise HTTPException(status_code=400, detail=str(e))
                cleaned[str(key)] = inner
            current[k] = cleaned
            continue
        if k not in _DEFAULTS:
            raise HTTPException(status_code=400, detail=f"Unknown risk key: {k}")
        try:
            current[k] = _coerce_override_value(k, v)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    _save(current)
    logger.info("risk_config updated: %s", [k for k in body.keys() if k != "version"])
    return {"status": "saved", "config": current}


@router.get("/effective")
def get_effective_risk_config(symbol: str | None = None, strategy: str | None = None, regime: str | None = None) -> dict[str, Any]:
    return get_effective_config(symbol, strategy, regime)


@router.post("/reset")
def reset_risk_config() -> dict[str, Any]:
    _save(dict(_DEFAULTS))
    return {"status": "reset", "config": dict(_DEFAULTS)}
