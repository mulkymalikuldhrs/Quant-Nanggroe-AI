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
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_REGISTRY_PATH = Path("data/cpcv_registry.json")

# Minimum share of profitable CPCV combinations required on a symbol's
# asset class before the strategy may trade it.
# Lowered from 0.50 to 0.35 — only 10 of 102 strategies have CPCV data;
# the old threshold was silently blocking all unvalidated strategies.
MIN_COMBO_PROFIT_SHARE = 0.35

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
    """Full view: asset class -> proven-good strategies (share >= threshold)."""
    reg = load_registry()
    out: Dict[str, List[str]] = {}
    for strat, per_symbol in reg.items():
        for cpcv_symbol, entry in per_symbol.items():
            share = float(entry.get("combo_profit_share", 0.0))
            n = int(entry.get("n_combinations", 0))
            if n >= 10 and share >= MIN_COMBO_PROFIT_SHARE:
                live_name = strat.removeprefix("archive_")
                out.setdefault(cpcv_symbol, []).append(live_name)
    for k in out:
        out[k].sort()
    return out


def admitted_for_symbol(symbol: str, all_strategies: Optional[List[str]] = None) -> Optional[List[str]]:
    """Strategies allowed to trade ``symbol`` per CPCV evidence.

    Returns None only when the registry FILE does not exist (no CPCV
    validation has ever run — caller keeps default behavior).  Returns
    an empty list when the registry exists but nothing qualifies for
    this symbol (caller must NOT trade unproven strategies).

    Logic: strategies WITHOUT CPCV data are admitted (fail-open for
    unvalidated). Strategies WITH CPCV data showing share < threshold
    are blocked (fail-closed for proven-bad).
    """
    reg = load_registry()
    if not reg:
        if _REGISTRY_PATH.exists():
            return []
        return None
    asset = _lookup_asset(symbol)
    if asset is None:
        logger.debug("no asset-class mapping for %s — no CPCV admission", symbol)
        return []

    # Classify: proven-good (CPCV share >= threshold) vs proven-bad (share < threshold)
    proven_bad = set()
    proven_good = set()
    for strat, per_symbol in reg.items():
        if asset in per_symbol:
            entry = per_symbol[asset]
            n = int(entry.get("n_combinations", 0))
            share = float(entry.get("combo_profit_share", 0.0))
            live_name = strat.removeprefix("archive_")
            if n >= 10 and share >= MIN_COMBO_PROFIT_SHARE:
                proven_good.add(live_name)
            elif n >= 10:
                proven_bad.add(live_name)

    logger.info(
        "CPCV allocation for %s (%s): %d proven-good, %d proven-bad",
        symbol, asset, len(proven_good), len(proven_bad))

    # If caller provides full strategy list — FAIL-CLOSED when CPCV data exists for this asset
    if all_strategies is not None:
        has_data = any(asset in per_symbol for per_symbol in reg.values())
        if has_data:
            if proven_good:
                # only proven-good may trade; allow override for research
                if os.environ.get("QNA_ALLOW_UNVALIDATED") == "1":
                    return [s for s in all_strategies if s not in proven_bad]
                return [s for s in all_strategies if s in proven_good]
            # data exists but no proven-good for this asset → block all (no edge)
            return []
        # no CPCV data at all for this asset → fallback to old permissive
        return [s for s in all_strategies if s not in proven_bad]

    # Legacy path: return only proven-good (for callers that don't pass all_strategies)
    return sorted(proven_good)


_TUNING_PATH = Path("data/tuning_results.json")
_RETRAIN_REPORT_PATH = Path("data/retrain_report.json")


def _stale_strategies() -> set:
    """Strategies flagged by the AutoRetrainer decay ledger.

    A key appears here when baseline score was negative on >= 3 consecutive
    retrain runs — the edge has decayed and its tuned params are no longer
    trustworthy. Fail-closed: fall back to strategy defaults.
    """
    try:
        report = json.loads(_RETRAIN_REPORT_PATH.read_text(encoding="utf-8"))
        return set(report.get("stale_strategies") or [])
    except Exception:
        return set()


def best_params_for(strategy: str, symbol: str) -> Optional[Dict[str, Any]]:
    """Tuned params for a strategy on a symbol's asset class.

    Reads ``data/tuning_results.json`` (written by
    ``scripts/run_param_tuning.py`` or engine/auto_retrain.py).
    Returns None when no tuning data exists — caller uses strategy defaults.
    Decay guard: if the retrain ledger flags ``strategy:symbol`` as stale
    (>= 3 consecutive negative baselines), tuned params are WITHHELD —
    trading falls back to un-tuned defaults until fresh evidence arrives.
    """
    if f"{strategy}:{_normalize(symbol)}" in _stale_strategies() or \
       f"{strategy}:{symbol}" in _stale_strategies():
        logger.info(
            "Decay guard: %s on %s flagged stale by retrain ledger — "
            "withholding tuned params", strategy, symbol)
        return None
    try:
        data = json.loads(_TUNING_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None
    per_symbol = data.get(strategy, {})
    asset = _lookup_asset(symbol)
    entry = per_symbol.get(asset) if asset else None
    if entry and entry.get("improved"):
        return dict(entry.get("best_params", {}))
    # even non-improved entries may have valid best params (equal to baseline)
    if entry and entry.get("best_params"):
        return dict(entry["best_params"])
    return None
