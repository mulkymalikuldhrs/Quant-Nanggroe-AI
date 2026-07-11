"""
Recurrence Plot Analysis for Regime Change Detection
Identifies changes in market dynamics by analyzing recurrence patterns.
A recurrence plot visualizes when a dynamical system revisits similar states.
"""
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class RecurrenceQuantification:
    recurrence_rate: float
    determinism: float
    laminarity: float
    trapping_time: float
    entropy: float
    longest_diagonal: int
    longest_vertical: int


class RecurrencePlotAnalyzer:
    """
    Recurrence Plot Analysis for detecting regime changes.

    Key insight from Simons/Medallion: recurrence quantification analysis (RQA)
    can detect when markets transition between regimes by measuring changes in
    the dynamical structure of price movements.
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.threshold = self.config.get("threshold", 0.1)
        self.dimension = self.config.get("dimension", 3)
        self.delay = self.config.get("delay", 1)

    def compute(self, series: np.ndarray) -> Tuple[np.ndarray, RecurrenceQuantification]:
        """Compute recurrence plot and RQA measures"""
        embedded = self._embed(series, self.dimension, self.delay)

        n = len(embedded)
        if n < 10:
            return np.zeros((n, n)), RecurrenceQuantification(0, 0, 0, 0, 0, 0, 0)

        dist_matrix = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                dist_matrix[i, j] = np.linalg.norm(embedded[i] - embedded[j])

        threshold = self.threshold * np.std(dist_matrix)
        recurrence = (dist_matrix < threshold).astype(float)

        rqa = self._compute_rqa(recurrence)

        return recurrence, rqa

    def _embed(self, series: np.ndarray, dim: int, delay: int) -> np.ndarray:
        """Time-delay embedding of a time series"""
        n = len(series)
        if n < dim + (dim - 1) * delay:
            return series.reshape(-1, 1)

        embedded = np.zeros((n - (dim - 1) * delay, dim))
        for i in range(dim):
            embedded[:, i] = series[i * delay:i * delay + len(embedded)]

        return embedded

    def _compute_rqa(self, recurrence: np.ndarray) -> RecurrenceQuantification:
        """Compute Recurrence Quantification Analysis measures"""
        n = len(recurrence)

        total_points = n * n - n
        if total_points <= 0:
            return RecurrenceQuantification(0, 0, 0, 0, 0, 0, 0)

        rr = float((np.sum(recurrence) - n) / total_points)

        diag_lengths = []
        for offset in range(-n + 1, n):
            if offset == 0:
                continue
            diag = recurrence.diagonal(offset=offset)
            lengths = self._count_consecutive(diag)
            diag_lengths.extend(lengths)

        vert_lengths = []
        for col in range(n):
            lengths = self._count_consecutive(recurrence[:, col])
            vert_lengths.extend(lengths)

        diag_array = np.array(diag_lengths) if diag_lengths else np.array([0])
        min_diag = 2
        det = float(np.sum(diag_array[diag_array >= min_diag]) / max(np.sum(diag_array), 1))

        vert_array = np.array(vert_lengths) if vert_lengths else np.array([0])
        min_vert = 2
        lam = float(np.sum(vert_array[vert_array >= min_vert]) / max(np.sum(vert_array), 1))

        tt = float(np.mean(vert_array[vert_array >= min_vert])) if np.any(vert_array >= min_vert) else 0.0

        if len(diag_array) > 1:
            hist, _ = np.histogram(diag_array, bins=max(2, len(np.unique(diag_array))))
            probs = hist / max(np.sum(hist), 1)
            entropy = float(-np.sum(probs * np.log(probs + 1e-10)))
        else:
            entropy = 0.0

        lmax = int(np.max(diag_array)) if len(diag_array) > 0 else 0
        vmax = int(np.max(vert_array)) if len(vert_array) > 0 else 0

        return RecurrenceQuantification(
            recurrence_rate=rr,
            determinism=det,
            laminarity=lam,
            trapping_time=tt,
            entropy=entropy,
            longest_diagonal=lmax,
            longest_vertical=vmax,
        )

    def _count_consecutive(self, arr: np.ndarray) -> List[int]:
        """Count consecutive 1s in binary array"""
        padded = np.concatenate([[0], arr, [0]])
        diffs = np.diff(padded)
        starts = np.where(diffs == 1)[0]
        ends = np.where(diffs == -1)[0]
        return [int(end - start) for start, end in zip(starts, ends)]

    def detect_regime_change(self, series: np.ndarray,
                               window: int = 100, step: int = 10) -> List[Dict]:
        """Detect regime changes by tracking RQA measures over time"""
        n = len(series)
        if n < window * 2:
            return []

        changes = []
        prev_rqa = None

        for start in range(0, n - window, step):
            chunk = series[start:start + window]
            _, rqa = self.compute(chunk)

            if prev_rqa is not None:
                det_change = abs(rqa.determinism - prev_rqa.determinism)
                rr_change = abs(rqa.recurrence_rate - prev_rqa.recurrence_rate)

                if det_change > 0.2 or rr_change > 0.1:
                    changes.append({
                        "position": start + window // 2,
                        "determinism_change": float(det_change),
                        "rr_change": float(rr_change),
                        "new_determinism": rqa.determinism,
                        "new_rr": rqa.recurrence_rate,
                    })

            prev_rqa = rqa

        return changes
