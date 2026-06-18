"""
Dynamic Time Warping (DTW) for Pattern Matching
Measures similarity between time series that may vary in speed/timing.
Useful for finding patterns regardless of market rhythm changes.
"""
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import numpy as np
import logging

logger = logging.getLogger(__name__)


@dataclass
class DTWAlignment:
    distance: float
    normalized_distance: float
    path: List[Tuple[int, int]]
    path_length: int
    similarity: float


class DTWMatcher:
    """
    Dynamic Time Warping for pattern matching in financial time series.

    Supports:
    - Custom window constraints (Sakoe-Chiba band)
    - Multi-dimensional DTW
    - Derivative DTW (DDTW) for shape-based matching
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.window_ratio = self.config.get("window_ratio", 0.2)

    def compute(self, reference: np.ndarray, query: np.ndarray) -> DTWAlignment:
        """Compute DTW distance between reference and query"""
        ref = np.asarray(reference, dtype=float)
        qry = np.asarray(query, dtype=float)

        if ref.ndim == 1:
            ref = ref.reshape(-1, 1)
            qry = qry.reshape(-1, 1)

        n, m = len(ref), len(qry)
        window = max(int(n * self.window_ratio), 1)

        cost = np.full((n + 1, m + 1), np.inf)
        cost[0, 0] = 0.0

        for i in range(1, n + 1):
            j_start = max(1, i - window)
            j_end = min(m + 1, i + window)

            for j in range(j_start, j_end):
                d = float(np.sqrt(np.sum((ref[i-1] - qry[j-1]) ** 2)))
                cost[i, j] = d + min(cost[i-1, j], cost[i, j-1], cost[i-1, j-1])

        dtw_distance = float(cost[n, m])
        path = self._backtrack(cost, n, m, window)

        norm_dist = dtw_distance / max(len(path), 1)

        similarity = 1.0 / (1.0 + norm_dist)

        return DTWAlignment(
            distance=dtw_distance,
            normalized_distance=norm_dist,
            path=path,
            path_length=len(path),
            similarity=similarity,
        )

    def _backtrack(self, cost: np.ndarray, i: int, j: int,
                    window: int) -> List[Tuple[int, int]]:
        """Backtrack through cost matrix to find warping path"""
        path = [(i - 1, j - 1)]

        while i > 1 or j > 1:
            candidates = []

            if i > 1 and j > 1:
                candidates.append((cost[i-1, j-1], i-1, j-1))
            if i > 1 and abs((i-1) - j) <= window:
                candidates.append((cost[i-1, j], i-1, j))
            if j > 1 and abs(i - (j-1)) <= window:
                candidates.append((cost[i, j-1], i, j-1))

            if not candidates:
                break

            _, i, j = min(candidates, key=lambda x: x[0])
            path.append((i - 1, j - 1))

        return list(reversed(path))

    def derivative_dtw(self, reference: np.ndarray, query: np.ndarray) -> DTWAlignment:
        """Derivative DTW — matches shape rather than absolute values"""
        ref_deriv = self._compute_derivative(reference)
        qry_deriv = self._compute_derivative(query)
        return self.compute(ref_deriv, qry_deriv)

    def _compute_derivative(self, series: np.ndarray) -> np.ndarray:
        """Compute local derivative of a series"""
        x = np.asarray(series, dtype=float)
        deriv = np.zeros_like(x)
        for i in range(1, len(x) - 1):
            deriv[i] = ((x[i] - x[i-1]) + (x[i+1] - x[i-1]) / 2) / 2
        return deriv

    def batch_match(self, reference: np.ndarray,
                     database: List[np.ndarray]) -> List[Tuple[int, DTWAlignment]]:
        """Match reference against a database of patterns"""
        results = []
        for idx, pattern in enumerate(database):
            alignment = self.compute(reference, pattern)
            results.append((idx, alignment))

        results.sort(key=lambda x: x[1].similarity, reverse=True)
        return results
