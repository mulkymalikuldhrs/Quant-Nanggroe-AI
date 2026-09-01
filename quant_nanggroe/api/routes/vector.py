"""Vector Manifold API — live status for dashboard vector page."""
from __future__ import annotations

from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter(prefix="/vector", tags=["vector"])

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
        # p0 as manifold itself for demo (zero distance) + small sigma
        p0 = {k: v.to_array() for k, v in manifold.items()}
        mis = scan_all(manifold, p0, sigma=0.05)
        return {
            "manifold": {k: v.to_array().tolist() for k, v in manifold.items()},
            "mispricing": {k: {"d": m.d, "threshold": m.threshold, "is_trigger": m.is_trigger} for k, m in mis.items()},
            "rates": rates,
        }
    except Exception as e:
        return {"manifold": {}, "mispricing": {}, "error": str(e)}
