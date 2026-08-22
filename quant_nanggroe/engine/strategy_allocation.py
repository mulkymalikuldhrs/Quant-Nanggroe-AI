"""Per-symbol strategy allocation from CPCV evidence.

CANONICAL §15.6 finding: no single strategy survives CPCV across all assets —
specialists win. This module maps each trading symbol to its asset class,
then admits only strategies with proven combo-profit-share on that class.

Evidence source: ``data/cpcv_registry.json`` written by
``scripts/run_cpcv_validation.py``.

Fail-closed policy: if the registry is missing/unreadable, allocation returns
an empty admit-list and callers fall back to their existing behavior (lifecycle
gate only). We never fabricate evidence.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_REGISTRY_PATH = Path("data/cpcv_registry.json")

# Minimum share of profitable CPCV combinations required on a symbol's
# asset class before the strategy may trade it.
MIN_COMBO_PROFIT_SHARE = 0.50

# Trading symbol -> CPCV evidence symbol (asset-class proxy).
SYMBOL_ASSET_MAP: Dict[str, str] = {
    # crypto
    "BTCUSD": "BTC-USD", "BTCUSDT": "BTC-USD", "BTC-USD": "BTC-USD",
    "ETHUSD": "BTC-USD", "ETHUSDT": "BTC-USD",
    "SOLUSD": "BTC-USD", "SOLUSDT": "BTC-USD",
    "XRPUSD": "BTC-USD", "ADAUSD": "BTC-USD",
    # forex majors -> EURUSD evidence
    "EURUSD": "EURUSD=X", "GBPUSD": "EURUSD=X", "USDJPY": "EURUSD=X",
    "AUDUSD": "EURUSD=X", "NZDUSD": "EURUSD=X", "USDCAD": "EURUSD=X",
    "EURUSD.VX": "EURUSD=X", "GBPUSD.VX": "EURUSD=X",
    # gold/metals -> GC=F evidence; silver correlates closer to gold than FX
    "XAUUSD": "GC=F", "XAUUSD.VX": "GC=F",
    "XAGUSD": "GC=F", "XAGUSD.VX": "GC=F",
}


def _normalize(symbol: str) -> str:
    """Normalize any symbol variant to the bare uppercase base."""
    s = symbol.upper().strip()
    return s.replace("-", "").replace(".VX", "").replace(".", "")


def _lookup_asset(symbol: str) -> Optional[str]:
    """Map a trading symbol to its CPCV evidence key."""
    if symbol in SYMBOL_ASSET_MAP:
        return SYMBOL_ASSET_MAP[symbol]
    norm = _normalize(symbol)
    for raw, asset in SYMBOL_ASSET_MAP.items():
        if _normalize(raw) == norm:
            return asset
    # heuristic fallback by prefix
    if norm.startswith(("XAU", "XAG")):
        return "GC=F"
    if norm.startswith(("EUR", "GBP", "USD", "AUD", "NZD")):
        return "EURUSD=X"
    if norm.startswith(("BTC", "ETH", "SOL", "XRP", "ADA")):
        return "BTC-USD"
    return None


def load_registry() -> dict:
    try:
        return json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        logger.debug("cpcv registry unavailable: %s", e)
        return {}


def allocation_map() -> Dict[str, List[str]]:
    """Full view: asset class -> admitted strategies (share >= threshold)."""
    reg = load_registry()
    out: Dict[str, List[str]] = {}
    for strat, per_symbol in reg.items():
        for cpcv_symbol, entry in per_symbol.items():
            share = float(entry.get("combo_profit_share", 0.0))
            n = int(entry.get("n_combinations", 0))
            if n >= 10 and share >= MIN_COMBO_PROFIT_SHARE:
                out.setdefault(cpcv_symbol, []).append(strat)
    for k in out:
        out[k].sort()
    return out


def admitted_for_symbol(symbol: str) -> Optional[List[str]]:
    """Strategies allowed to trade ``symbol`` per CPCV evidence.

    Returns None when no evidence exists (caller keeps default behavior);
    returns a possibly-empty list when evidence exists but nothing qualifies
    (caller should NOT trade unproven strategies on this symbol).
    """
    reg = load_registry()
    if not reg:
        return None  # no evidence at all — caller decides
    asset = _lookup_asset(symbol)
    if asset is None:
        logger.debug("no asset-class mapping for %s — no CPCV admission", symbol)
        return []
    admitted = [
        strat for strat, per_symbol in reg.items()
        if asset in per_symbol
        and int(per_symbol[asset].get("n_combinations", 0)) >= 10
        and float(per_symbol[asset].get("combo_profit_share", 0.0))
        >= MIN_COMBO_PROFIT_SHARE
    ]
    admitted.sort()
    logger.info("CPCV allocation for %s (%s): %d admitted %s",
                symbol, asset, len(admitted), admitted)
    return admitted
