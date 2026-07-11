"""
Matrix Profile Pattern Detection
Uses the Matrix Profile algorithm (via STUMPY) for motif and discords discovery.
Identifies repeated patterns (motifs) and anomalies (discords) in time series.

Reference: Yeh et al. (2016), "Matrix Profile I: All-Pairs Similarity Joins for
Time Series" — used by Renaissance Technologies for pattern discovery.
"""
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class Motif:
    """A repeated pattern discovered in the time series"""
    start_idx: int
    end_idx: int
    matched_start: int
    matched_end: int
    distance: float
    length: int
    strength: float


@dataclass
class Discord:
    """An anomalous pattern in the time series"""
    start_idx: int
    end_idx: int
    distance: float
    score: float
    length: int


@dataclass
class MatrixProfileResult:
    matrix_profile: np.ndarray
    profile_index: np.ndarray
    motifs: List[Motif]
    discords: List[Discord]
    window_size: int
    mean: float
    std: float


class MatrixProfileDetector:
    """
    Matrix Profile-based pattern detection.

    Falls back to numpy-only implementation if STUMPY is not available,
    so it works in constrained environments.
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.use_stumpy = self.config.get("use_stumpy", self._check_stumpy())

    def _check_stumpy(self) -> bool:
        try:
            import stumpy
            return True
        except ImportError:
            logger.warning("STUMPY not available, using numpy fallback")
            return False

    def compute(self, series: pd.Series, window_size: int = 20) -> MatrixProfileResult:
        """Compute Matrix Profile and find motifs/discords"""
        values = series.dropna().values
        n = len(values)

        if n < window_size * 2:
            raise ValueError(f"Series too short: {n} < {window_size * 2}")

        if self.use_stumpy:
            import stumpy
            mp = stumpy.stump(values, m=window_size)
            matrix_profile = mp[:, 0]
            profile_index = mp[:, 1]
        else:
            matrix_profile, profile_index = self._numpy_mp(values, window_size)

        sq = self._squared_distance(values, matrix_profile, profile_index, window_size)

        motifs = self._find_motifs(values, matrix_profile, profile_index, window_size, n_motifs=5)
        discords = self._find_discords(matrix_profile, n_discords=5)

        valid_mp = matrix_profile[~np.isnan(matrix_profile)]

        return MatrixProfileResult(
            matrix_profile=matrix_profile,
            profile_index=profile_index,
            motifs=motifs,
            discords=discords,
            window_size=window_size,
            mean=float(np.mean(valid_mp)) if len(valid_mp) > 0 else 0.0,
            std=float(np.std(valid_mp)) if len(valid_mp) > 0 else 0.0,
        )

    def _numpy_mp(self, values: np.ndarray, m: int) -> Tuple[np.ndarray, np.ndarray]:
        """Numpy-only Matrix Profile computation (MASS algorithm)"""
        n = len(values)
        k = n - m + 1

        mp = np.full(k, np.inf)
        idx = np.full(k, -1)

        first_window = values[:m]
        first_mean = np.mean(first_window)
        first_std = np.std(first_window)

        for i in range(k):
            if i == 0:
                continue
            query = values[i:i+m]
            q_mean = np.mean(query)
            q_std = np.std(query)

            if q_std < 1e-8 or first_std < 1e-8:
                continue

            distances = self._compute_distances(values[:k], query, q_mean, q_std, m)

            exclusion_zone = m // 2
            min_idx = np.argmin(distances)
            min_val = distances[min_idx]

            if abs(min_idx - i) <= exclusion_zone:
                distances_sorted = np.argsort(distances)
                for j in distances_sorted:
                    if abs(j - i) > exclusion_zone:
                        min_idx = j
                        min_val = distances[j]
                        break

            mp[i] = min_val
            idx[i] = min_idx

            if i + m < n:
                first_mean = first_mean + (values[i+m] - values[i]) / m
                first_std = np.std(values[i+1:i+1+m])

        return mp, idx

    def _compute_distances(self, values: np.ndarray, query: np.ndarray,
                            q_mean: float, q_std: float, m: int) -> np.ndarray:
        """Compute sliding dot product (MASS algorithm)"""
        n = len(values)
        distances = np.full(n, np.inf)
        q_norm = (query - q_mean) / q_std

        for i in range(n - m + 1):
            window = values[i:i+m]
            w_mean = np.mean(window)
            w_std = np.std(window)
            if w_std < 1e-8:
                continue
            w_norm = (window - w_mean) / w_std
            dist = np.sqrt(np.sum((w_norm - q_norm) ** 2))
            distances[i] = dist

        return distances

    def _squared_distance(self, values: np.ndarray, mp: np.ndarray,
                           pi: np.ndarray, m: int) -> float:
        """Compute average squared distance of matched motifs"""
        valid = (mp < np.inf) & (mp >= 0)
        if not np.any(valid):
            return 0.0
        return float(np.mean(mp[valid] ** 2))

    def _find_motifs(self, values: np.ndarray, mp: np.ndarray,
                      pi: np.ndarray, m: int, n_motifs: int = 5) -> List[Motif]:
        """Find top motifs (repeated patterns)"""
        k = len(mp)
        valid_mask = (mp < np.inf) & (mp >= 0) & (pi >= 0)
        valid_indices = np.where(valid_mask)[0]

        if len(valid_indices) == 0:
            return []

        sorted_indices = valid_indices[np.argsort(mp[valid_indices])]

        result = []
        exclusion_zone = m
        used_indices = set()

        for idx in sorted_indices:
            if len(result) >= n_motifs:
                break

            if idx in used_indices:
                continue

            match_idx = int(pi[idx])
            if match_idx in used_indices:
                continue

            motif = Motif(
                start_idx=idx,
                end_idx=idx + m,
                matched_start=match_idx,
                matched_end=match_idx + m,
                distance=float(mp[idx]),
                length=m,
                strength=float(1.0 / (1.0 + mp[idx])),
            )
            result.append(motif)

            for i in range(max(0, idx - exclusion_zone), min(k, idx + exclusion_zone)):
                used_indices.add(i)
            for i in range(max(0, match_idx - exclusion_zone), min(k, match_idx + exclusion_zone)):
                used_indices.add(i)

        return result

    def _find_discords(self, mp: np.ndarray, n_discords: int = 5) -> List[Discord]:
        """Find top discords (anomalies)"""
        k = len(mp)
        valid_mask = (mp < np.inf) & (mp >= 0)
        valid_indices = np.where(valid_mask)[0]

        if len(valid_indices) == 0:
            return []

        sorted_indices = valid_indices[np.argsort(-mp[valid_indices])]

        result = []
        exclusion_zone = k // 4
        used_indices = set()

        max_mp = mp[sorted_indices[0]] if len(sorted_indices) > 0 else 1.0

        for idx in sorted_indices:
            if len(result) >= n_discords:
                break

            if idx in used_indices:
                continue

            discord = Discord(
                start_idx=idx,
                end_idx=idx + 1,
                distance=float(mp[idx]),
                score=float(mp[idx] / max_mp),
                length=1,
            )
            result.append(discord)

            for i in range(max(0, idx - exclusion_zone), min(k, idx + exclusion_zone)):
                used_indices.add(i)

        return result

    def find_motifs_of_length(self, series: pd.Series, window_sizes: List[int]) -> Dict[int, List[Motif]]:
        """Find motifs at multiple window sizes"""
        results = {}
        for w in window_sizes:
            try:
                mp_result = self.compute(series, window_size=w)
                if mp_result.motifs:
                    results[w] = mp_result.motifs
            except Exception as e:
                logger.warning(f"Window size {w} failed: {e}")
        return results
