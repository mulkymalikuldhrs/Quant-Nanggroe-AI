"""Vector Manifold API — live status for dashboard vector page.

Observability-only: mispricing triggers here NEVER reach the trade path.
P0 is the rolling mean over the last HISTORY_N manifold snapshots so
/status is actually capable of triggering (previously p0 == manifold,
zero distance, endpoint could never fire).
"""
from __future__ import annotations

from collections import deque
from typing import Dict, Any

from fastapi import APIRouter

router = APIRouter(prefix="/vector", tags=["vector"])

# Rolling history of manifold snapshots (label -> np.ndarray), module-level
# so it survives across requests in-process. Bounded to avoid memory growth.
HISTORY_N = 20
_history: deque[Dict[str, Any]] = deque(maxlen=HISTORY_N)


def reset_history() -> None:
    """Test hook — clear the rolling buffer."""
    _history.clear()


@router.get("/status")
async def vector_status() -> Dict[str, Any]:
    try:
        from quant_nanggroe.engine.currency_graph import build_graph_from_mt5
        from quant_nanggroe.engine.vector_manifold import build_manifold
        from quant_nanggroe.engine.euclidean_mispricing import build_p0, scan_all
        # fallback static rates if MT5 offline
        g = build_graph_from_mt5(all_pairs=False)
        rates = g.rates or {"EURUSD.vx": 1.08, "USDJPY.vx": 137.01, "EURJPY.vx": 147.5, "USDCHF.vx": 0.90, "EURCHF.vx": 0.97, "USDCAD.vx": 1.36, "EURCAD.vx": 1.47}
        # ensure required keys for manifold
        if "EURUSD.vx" not in rates:
            rates["EURUSD.vx"] = 1.08
        manifold = build_manifold(rates)
        # P0 = rolling mean over history buffer (observability only).
        snapshot = {k: v.to_array() for k, v in manifold.items()}
        _history.append(snapshot)
        if len(_history) < 2:
            # Warming up: not enough history for a real mean — report
            # zero distance and force is_trigger False.
            p0 = dict(snapshot)
            mis = scan_all(manifold, p0, sigma=0.05)
            for m in mis.values():
                m.is_trigger = False
            warming_up, reason, p0_source = True, "warming up", "current"
        else:
            history = {k: [s[k] for s in _history if k in s] for k in snapshot}
            p0 = build_p0(history)
            mis = scan_all(manifold, p0, sigma=0.05)
            warming_up, reason, p0_source = False, "ok", "rolling_mean"
        return {
            "manifold": {k: v.to_array().tolist() for k, v in manifold.items()},
            "mispricing": {k: {"d": m.d, "threshold": m.threshold, "is_trigger": m.is_trigger, "reason": reason} for k, m in mis.items()},
            "rates": rates,
            "warming_up": warming_up,
            "p0_source": p0_source,
            "history_len": len(_history),
        }
    except Exception as e:
        return {"manifold": {}, "mispricing": {}, "error": str(e)}
