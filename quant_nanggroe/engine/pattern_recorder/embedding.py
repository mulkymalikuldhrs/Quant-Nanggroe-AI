"""
Embedding Similarity for Pattern Matching
Converts time series windows into embedding vectors and compares them
using cosine similarity. Enables fast nearest-neighbor search.
"""
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingResult:
    embedding: np.ndarray
    window_start: int
    window_end: int
    timestamp: Any = None


@dataclass
class SimilarityMatch:
    query_idx: int
    match_idx: int
    similarity: float
    embedding: Optional[np.ndarray] = None


class EmbeddingSimilarity:
    """
    Embedding-based time series similarity.

    Converts time series windows into feature vectors using:
    1. Statistical features (mean, std, skew, kurtosis, etc.)
    2. Spectral features (FFT coefficients)
    3. Shape features (auto-correlation)

    Then compares using cosine similarity for fast matching.
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.embedding_dim = self.config.get("embedding_dim", 32)

    def compute_embedding(self, window: np.ndarray) -> np.ndarray:
        """Convert a time series window to embedding vector"""
        if len(window) < 2:
            return np.zeros(self.embedding_dim)

        features = []

        features.append(float(np.mean(window)))
        features.append(float(np.std(window)))
        features.append(float(self._skewness(window)))
        features.append(float(self._kurtosis(window)))

        for p in [5, 25, 50, 75, 95]:
            features.append(float(np.percentile(window, p)))

        features.append(float(np.max(window) - np.min(window)))
        features.append(float(np.max(window) / max(abs(np.min(window)), 1e-10)))
        features.append(float(np.sum(np.abs(np.diff(window)))))

        ac = self._auto_correlation(window, max_lag=5)
        features.extend(ac)

        fft_features = self._spectral_features(window, n_coeffs=8)
        features.extend(fft_features)

        features.append(float(self._linear_trend(window)))
        features.append(float(np.mean(np.diff(window))))
        features.append(float(np.std(np.diff(window))))

        feature_array = np.array(features, dtype=float)
        if len(feature_array) < self.embedding_dim:
            feature_array = np.pad(feature_array, (0, self.embedding_dim - len(feature_array)))
        else:
            feature_array = feature_array[:self.embedding_dim]

        norm = np.linalg.norm(feature_array)
        if norm > 0:
            feature_array = feature_array / norm

        return feature_array

    def _skewness(self, x: np.ndarray) -> float:
        """Compute sample skewness"""
        n = len(x)
        if n < 3:
            return 0.0
        std = np.std(x)
        if std < 1e-10:
            return 0.0
        return float(np.mean(((x - np.mean(x)) / std) ** 3))

    def _kurtosis(self, x: np.ndarray) -> float:
        """Compute excess kurtosis"""
        n = len(x)
        if n < 4:
            return 0.0
        std = np.std(x)
        if std < 1e-10:
            return 0.0
        return float(np.mean(((x - np.mean(x)) / std) ** 4) - 3)

    def _auto_correlation(self, x: np.ndarray, max_lag: int = 5) -> List[float]:
        """Compute auto-correlation at specified lags"""
        n = len(x)
        x_mean = np.mean(x)
        x_var = np.var(x)

        if x_var < 1e-10:
            return [0.0] * max_lag

        results = []
        for lag in range(1, max_lag + 1):
            if lag >= n:
                results.append(0.0)
            else:
                ac = np.mean((x[:n-lag] - x_mean) * (x[lag:] - x_mean)) / x_var
                results.append(float(ac))

        return results

    def _spectral_features(self, x: np.ndarray, n_coeffs: int = 8) -> List[float]:
        """Compute FFT-based spectral features"""
        n = len(x)
        if n < 2:
            return [0.0] * n_coeffs

        fft = np.fft.fft(x - np.mean(x))
        magnitudes = np.abs(fft[:n_coeffs])

        max_mag = np.max(magnitudes) if len(magnitudes) > 0 else 1.0
        if max_mag > 0:
            magnitudes = magnitudes / max_mag

        if len(magnitudes) < n_coeffs:
            magnitudes = np.pad(magnitudes, (0, n_coeffs - len(magnitudes)))

        return magnitudes.tolist()[:n_coeffs]

    def _linear_trend(self, x: np.ndarray) -> float:
        """Compute linear trend coefficient"""
        n = len(x)
        if n < 2:
            return 0.0
        t = np.arange(n, dtype=float)
        slope = np.polyfit(t, x, 1)[0]
        return float(slope)

    def cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Compute cosine similarity between two embeddings"""
        dot = np.dot(a, b)
        norm = np.linalg.norm(a) * np.linalg.norm(b)
        if norm < 1e-10:
            return 0.0
        return float(dot / norm)

    def search(self, query_window: np.ndarray,
                database_windows: List[np.ndarray],
                top_k: int = 5) -> List[SimilarityMatch]:
        """Search for similar windows in database"""
        query_emb = self.compute_embedding(query_window)

        similarities = []
        for idx, db_window in enumerate(database_windows):
            db_emb = self.compute_embedding(db_window)
            sim = self.cosine_similarity(query_emb, db_emb)
            similarities.append(SimilarityMatch(
                query_idx=0,
                match_idx=idx,
                similarity=sim,
            ))

        similarities.sort(key=lambda x: x.similarity, reverse=True)
        return similarities[:top_k]
