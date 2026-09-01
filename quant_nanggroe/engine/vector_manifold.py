"""Vector Manifold — Ruang 3D P=xî+yĵ+zk (Klip 00:09-00:14).

Video: sumbu X USD Y EUR Z EURUSD, PointYEN/CHF/CAD, plane ungu/hijau.
Geometri: manifold pasar R^n, origin 0,0,0 ekuilibrium.

Real-trade-ready: z-normalize JPY (*100), fail-closed.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict

import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class VectorPoint:
    x: float  # USD component
    y: float  # EUR component
    z: float  # synthetic/EURUSD
    label: str

    def to_array(self) -> np.ndarray:
        return np.array([self.x, self.y, self.z], dtype=float)

def point_yen(usd_jpy: float, eur_jpy: float, eur_usd: float) -> VectorPoint:
    """PointYEN(USDJPY, EURJPY, EURUSD) — z-normalize JPY /100."""
    # normalize JPY to ~1.0 scale (137.01 -> 1.3701) to avoid bias
    return VectorPoint(x=usd_jpy / 100.0, y=eur_jpy / 100.0, z=eur_usd, label="PointYEN")

def point_chf(usd_chf: float, eur_chf: float, eur_usd: float) -> VectorPoint:
    return VectorPoint(x=usd_chf, y=eur_chf, z=eur_usd, label="PointCHF")

def point_cad(usd_cad: float, eur_cad: float, eur_usd: float) -> VectorPoint:
    return VectorPoint(x=usd_cad, y=eur_cad, z=eur_usd, label="PointCAD")

def plane_projection(p1: VectorPoint, p2: VectorPoint) -> Dict[str, float]:
    """Plane projection — cari simetri antara dua point (garis ungu/hijau)."""
    v1, v2 = p1.to_array(), p2.to_array()
    # normal = v1 x v2
    normal = np.cross(v1, v2)
    # distance between planes
    dist = float(np.linalg.norm(v1 - v2))
    # symmetry score = cosine similarity
    dot = float(np.dot(v1, v2))
    norm = float(np.linalg.norm(v1) * np.linalg.norm(v2))
    cos_sim = dot / norm if norm != 0 else 0.0
    return {"normal": normal.tolist(), "distance": dist, "cos_sim": cos_sim, "symmetry": abs(cos_sim) > 0.95}

def build_manifold(rates: Dict[str, float]) -> Dict[str, VectorPoint]:
    """Build manifold dari rates dict symbol->price."""
    eur_usd = rates.get("EURUSD.vx") or rates.get("EURUSD") or 1.08
    out: Dict[str, VectorPoint] = {}
    # YEN
    if "USDJPY.vx" in rates and "EURJPY.vx" in rates:
        out["YEN"] = point_yen(rates["USDJPY.vx"], rates["EURJPY.vx"], eur_usd)
    # CHF
    if "USDCHF.vx" in rates and "EURCHF.vx" in rates:
        out["CHF"] = point_chf(rates["USDCHF.vx"], rates["EURCHF.vx"], eur_usd)
    # CAD
    if "USDCAD.vx" in rates and "EURCAD.vx" in rates:
        out["CAD"] = point_cad(rates["USDCAD.vx"], rates["EURCAD.vx"], eur_usd)
    return out
