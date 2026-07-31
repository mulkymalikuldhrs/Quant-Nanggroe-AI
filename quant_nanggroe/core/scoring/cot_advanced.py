"""COT Advanced z-score engine.

Matches test contract: score() returns object with .score, .confidence, .metadata,
plus module-level helpers _compute_rolling_z, _delta_acceleration, _staleness_penalty, _z_to_score.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Sequence

import numpy as np


@dataclass(frozen=True)
class COTAdvancedScore:
    score: float
    confidence: float
    staleness_penalty: bool
    z_commercial: float = 0.0
    z_noncommercial: float = 0.0
    delta_commercial: float = 0.0
    delta_noncommercial: float = 0.0
    metadata: dict = field(default_factory=dict)


class COTAdvancedScorer:
    def __init__(self, lookback_weeks: int = 156, max_staleness_days: int = 14, acceleration_weeks: int = 1) -> None:
        self.lookback_weeks = int(lookback_weeks)
        self.max_staleness_days = int(max_staleness_days)
        self.acceleration_weeks = int(acceleration_weeks)

    def score(
        self,
        commercial_net: Sequence[float] | None = None,
        noncommercial_net: Sequence[float] | None = None,
        timestamps: Sequence[float] | None = None,
        history: list[dict] | None = None,
        latest: dict | None = None,
    ) -> COTAdvancedScore:
        # Parse history-dict format
        if history is not None or latest is not None:
            hist = list(history or [])
            if latest:
                hist = [h for h in hist if h is not latest] + [latest]
            if not hist:
                return COTAdvancedScore(score=50.0, confidence=0.0, staleness_penalty=True, metadata={"status": "NO_DATA"})
            if len(hist) == 1:
                row = hist[0]
                return COTAdvancedScore(score=50.0, confidence=0.2, staleness_penalty=True, metadata={"status": "SINGLE_POINT"})
            com_list, non_list, ts_list = [], [], []
            for h in hist:
                com_list.append(float(h.get("commercial_long", 0) - h.get("commercial_short", 0)))
                non_list.append(float(h.get("non_commercial_long", 0) - h.get("non_commercial_short", 0)))
                ts_list.append(self._parse_ts(h.get("report_date")))
            commercial_net = com_list
            noncommercial_net = non_list
            timestamps = ts_list

        com = np.asarray(commercial_net or [], dtype=float)
        non = np.asarray(noncommercial_net or [], dtype=float)
        if com.size < 10 or non.size < 10:
            meta = {"status": "NO_DATA" if com.size == 0 else "SINGLE_POINT"}
            return COTAdvancedScore(score=50.0, confidence=0.2 if com.size == 1 else 0.0, staleness_penalty=True, metadata=meta)

        z_com = self._rolling_zscore(com)
        z_non = self._rolling_zscore(non)

        delta_com = float(com[-1] - com[-2])
        delta_non = float(non[-1] - non[-2])

        z_com_clamped = float(np.clip(z_com[-1] if np.isfinite(z_com[-1]) else 0.0, -3.0, 3.0))
        z_non_clamped = float(np.clip(z_non[-1] if np.isfinite(z_non[-1]) else 0.0, -3.0, 3.0))
        base = ((z_com_clamped + 3.0) / 6.0) * 50.0 + ((z_non_clamped + 3.0) / 6.0) * 50.0
        base = float(np.clip(base, 0.0, 100.0))

        staleness = False
        staleness_mult = 1.0
        if timestamps is not None and len(timestamps) >= 2:
            age_days = (float(timestamps[-1]) - float(timestamps[-2])) / 86400.0
            staleness = age_days > self.max_staleness_days
            staleness_mult = 0.5 if staleness else 1.0

        confidence = 80.0 if not staleness else 40.0
        if abs(delta_com) > 0 or abs(delta_non) > 0:
            confidence = min(100.0, confidence + 5.0)

        metadata = {
            "status": "OK",
            "commercial_net_z": round(z_com_clamped, 2),
            "non_commercial_net_z": round(z_non_clamped, 2),
            "staleness_multiplier": staleness_mult,
        }
        return COTAdvancedScore(
            score=base,
            confidence=confidence,
            staleness_penalty=staleness,
            z_commercial=round(z_com_clamped, 2),
            z_noncommercial=round(z_non_clamped, 2),
            delta_commercial=round(delta_com, 2),
            delta_noncommercial=round(delta_non, 2),
            metadata=metadata,
        )

    def _rolling_zscore(self, values: np.ndarray) -> np.ndarray:
        window = min(self.lookback_weeks, values.shape[0])
        out = np.zeros_like(values, dtype=float)
        for i in range(values.shape[0]):
            if i < window - 1:
                out[i] = 0.0
                continue
            window_vals = values[i - window + 1 : i + 1]
            mu = float(np.mean(window_vals))
            sigma = float(np.std(window_vals, ddof=0))
            out[i] = (values[i] - mu) / sigma if sigma > 1e-9 else 0.0
        return out

    @staticmethod
    def _parse_ts(value):
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        from datetime import datetime
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S%z"):
            try:
                return datetime.strptime(str(value), fmt).timestamp()
            except ValueError:
                pass
        return 0.0


# Module-level helpers expected by tests

def _compute_rolling_z(values, window=10.0):
    s = COTAdvancedScorer()
    arr = np.asarray(values, dtype=float)
    s.lookback_weeks = int(window) if window > 1 else 10
    out = s._rolling_zscore(arr)
    if out.shape[0] > 0:
        return float(out[-1]), float(arr.mean()), float(arr.std(ddof=0))
    return 0.0, 0.0, 1.0


def _delta_acceleration(current: float, previous: float) -> float:
    return float(current - previous)


def _staleness_penalty(age_days, max_staleness_days=14):
    if isinstance(age_days, str):
        try:
            from datetime import datetime
            dt = datetime.strptime(age_days, "%Y-%m-%d").replace(tzinfo=__import__("datetime").timezone.utc)
            now = datetime.now(__import__("datetime").timezone.utc)
            age_days = (now - dt).days
        except Exception:
            age_days = 999
    if age_days > max_staleness_days:
        return 1.0
    return 0.0


def _z_to_score(z: float, max_z: float = 3.0) -> float:
    z = max(-max_z, min(max_z, z))
    return ((z + max_z) / (2.0 * max_z)) * 100.0
