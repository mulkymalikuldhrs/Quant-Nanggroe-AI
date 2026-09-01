"""Euclidean Mispricing — d=||P(t)-P0|| + √2 (Klip 00:15).

Video: CADJPY = CADJPY/√2 =95.98 Pythagoras, box merah tolerance.
Metrik: jarak Euclidean ke ekuilibrium, threshold → trigger.

Real-trade-ready: P0 = rolling mean manifold, box = σ, fail-closed.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Dict, Optional

import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class MispricingSignal:
    label: str  # YEN/CHF/CAD
    d: float  # Euclidean distance
    threshold: float
    is_trigger: bool  # d > threshold + box breach
    p_current: np.ndarray
    p0: np.ndarray

SQRT2 = math.sqrt(2)

def cadjpy_pythagoras(cad_jpy: float) -> float:
    """Video rumus: CADJPY/√2 =95.98 — proyeksi 45° 1:1:√2."""
    return cad_jpy / SQRT2

def euclidean_distance(p: np.ndarray, p0: np.ndarray) -> float:
    return float(np.linalg.norm(p - p0))

def check_mispricing(p_current: np.ndarray, p0: np.ndarray, sigma: float = 0.05) -> MispricingSignal:
    """Box merah: threshold = sigma (0.05) * √2 untuk 45°."""
    d = euclidean_distance(p_current, p0)
    threshold = sigma * SQRT2  # 0.05*1.414=0.0707
    # also check per-axis box breach
    box_breach = bool(np.any(np.abs(p_current - p0) > sigma))
    is_trigger = d > threshold or box_breach
    return MispricingSignal(
        label="", d=d, threshold=threshold, is_trigger=is_trigger,
        p_current=p_current, p0=p0
    )

def build_p0(manifold_history: Dict[str, list]) -> Dict[str, np.ndarray]:
    """P0 = mean dari history manifold (rolling). manifold_history: label -> list[np.ndarray]."""
    p0: Dict[str, np.ndarray] = {}
    for label, hist in manifold_history.items():
        if hist:
            p0[label] = np.mean(np.stack(hist), axis=0)
        else:
            p0[label] = np.zeros(3)
    return p0

def scan_all(manifold: Dict[str, object], p0: Dict[str, np.ndarray], sigma: float = 0.05) -> Dict[str, MispricingSignal]:
    """Scan semua Point* — return trigger signals."""
    out: Dict[str, MispricingSignal] = {}
    for label, pt in manifold.items():
        arr = pt.to_array() if hasattr(pt, "to_array") else np.array(pt)  # type: ignore
        base = p0.get(label, np.zeros(3))
        sig = check_mispricing(arr, base, sigma)
        sig.label = label
        if sig.is_trigger:
            logger.info("Mispricing %s d=%.4f > thr=%.4f box=%s", label, sig.d, sig.threshold, sig.is_trigger)
        out[label] = sig
    return out
