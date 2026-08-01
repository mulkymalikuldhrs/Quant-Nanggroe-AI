from __future__ import annotations

"""Hierarchical Risk Parity (HRP) allocator.

Implements the HRP algorithm of Lopez de Prado (2016), "Building Diversified
Portfolios that Outperform Out-of-Sample". HRP does not require the inversion of
the covariance matrix (unlike classical mean-variance / risk parity), so it is
far more robust once the asset count grows and the covariance estimate becomes
ill-conditioned.

This module is a drop-in companion to
:class:`quant_nanggroe.engine.portfolio.risk_parity_bridgewater.RiskParityAllocator`:

* :class:`HRPAllocator` exposes the same ``compute_risk_parity_weights``
  signature and returns a dict ``{symbol: weight}`` of long-only weights that sum
  to 1.0.
* :func:`allocate` is a dispatcher that uses HRP whenever the universe has more
  than ``HRP_ASSET_THRESHOLD`` (5) assets and otherwise falls back to the
  Bridgewater-style :class:`RiskParityAllocator`. This is the intended behaviour
  for "replace RiskParityAllocator for >5 assets".

The clustering step relies on ``scipy.cluster.hierarchy.linkage`` and
``scipy.spatial.distance.squareform``. These are imported lazily so the module
always imports cleanly even where SciPy is unavailable; in that (rare) case HRP
degrades gracefully to an inverse-volatility ordering.
"""

from typing import Any

import numpy as np

logger = __import__("logging").getLogger(__name__)

# Above this many assets the allocator switches from classical risk parity to
# Hierarchical Risk Parity. 5 is the conventional cutoff where the covariance
# estimate starts to become unstable / noisy for a naive risk-parity solver.
HRP_ASSET_THRESHOLD = 5

# Lazily-bound reference to the Bridgewater allocator used for the <=5 fallback.
try:  # pragma: no cover - import guard
    from quant_nanggroe.engine.portfolio.risk_parity_bridgewater import (
        RiskParityAllocator,
    )

    _HAS_RISK_PARITY = True
except Exception:  # pragma: no cover
    RiskParityAllocator = None  # type: ignore[assignment]
    _HAS_RISK_PARITY = False


# --------------------------------------------------------------------------- #
# Internal helpers
# --------------------------------------------------------------------------- #
def _build_cov(
    volatilities: dict[str, float],
    correlations: dict[tuple[str, str], float] | None,
):
    """Return ``(symbols, vols, cov)`` built from per-asset vols + correlations."""
    symbols = list(volatilities.keys())
    n = len(symbols)
    vols = np.array([max(float(volatilities[s]), 1e-6) for s in symbols])
    cov = np.diag(vols**2)
    if correlations:
        for (a, b), corr in correlations.items():
            if a == b:
                continue
            if a in symbols and b in symbols:
                i, j = symbols.index(a), symbols.index(b)
                c = float(np.clip(corr, -0.999, 0.999))
                cov[i, j] = c * vols[i] * vols[j]
                cov[j, i] = cov[i, j]
    return symbols, vols, cov


def _cluster_variance(cov: np.ndarray, idx: list[int]) -> float:
    """Variance of an equal-weighted cluster ``idx`` under covariance ``cov``."""
    if len(idx) == 1:
        return float(cov[idx[0], idx[0]])
    sub = cov[np.ix_(idx, idx)]
    w = np.ones(len(idx)) / len(idx)
    return float(w @ sub @ w)


def _leaves_from_linkage(Z: np.ndarray, n: int) -> list[int]:
    """Reconstruct the leaf ordering of the final merged cluster from ``Z``.

    ``Z`` is a SciPy linkage matrix of shape ``(n-1, 4)``. Each row ``i`` merges
    clusters ``Z[i,0]`` and ``Z[i,1]`` into the new cluster ``n + i``. Traversing
    the root cluster ``(2*n - 2)`` recursively yields the dendrogram leaf order.
    """
    children: dict[int, list[int]] = {i: [i] for i in range(n)}
    for i in range(n - 1):
        a = int(Z[i, 0])
        b = int(Z[i, 1])
        children[n + i] = children[a] + children[b]
    return children[2 * n - 2]


# --------------------------------------------------------------------------- #
# HRP allocator
# --------------------------------------------------------------------------- #
class HRPAllocator:
    """Hierarchical Risk Parity allocator (Lopez de Prado, 2016).

    Pipeline:
      1. Convert the correlation matrix to a distance matrix
         ``D = sqrt(0.5 * (1 - C))``.
      2. Hierarchically cluster the assets (single/ward linkage) and recover the
         quasi-diagonal ordering (seriation).
      3. Recursively bisect the tree, allocating capital inversely proportional to
         each sub-cluster's variance, so that risk is spread evenly across the
         hierarchy.
    """

    def __init__(self, method: str = "single"):
        self.method = method

    # --- Drop-in API mirroring RiskParityAllocator ------------------------- #
    def compute_risk_parity_weights(
        self,
        volatilities: dict[str, float],
        correlations: dict[tuple[str, str], float] | None = None,
    ) -> dict[str, float]:
        """Same signature as RiskParityAllocator; delegates to HRP."""
        return self.compute_hrp_weights(volatilities, correlations)

    # --- Core HRP ---------------------------------------------------------- #
    def compute_hrp_weights(
        self,
        volatilities: dict[str, float],
        correlations: dict[tuple[str, str], float] | None = None,
    ) -> dict[str, float]:
        symbols, vols, cov = _build_cov(volatilities, correlations)
        n = len(symbols)
        if n == 0:
            return {}
        if n == 1:
            return {symbols[0]: 1.0}

        # 1. Correlation -> distance matrix.
        denom = np.outer(vols, vols)
        corr = np.clip(cov / denom, -0.999999, 0.999999)
        dist = np.sqrt(np.clip(0.5 * (1.0 - corr), 0.0, None))

        # 2. Hierarchical clustering / seriation.
        try:
            sort_ix = self._seriate(dist)
        except Exception as exc:  # pragma: no cover - graceful degradation
            logger.warning("HRP clustering unavailable (%s); using vol order", exc)
            sort_ix = list(range(n))

        # 3. Recursive bisection on the quasi-diagonalized covariance.
        cov_sorted = cov[np.ix_(sort_ix, sort_ix)]
        w_sorted = self._recursive_bisection(cov_sorted)

        w = np.empty(n)
        for pos, orig in enumerate(sort_ix):
            w[orig] = w_sorted[pos]
        total = w.sum()
        if total <= 0 or not np.isfinite(total):
            w = np.ones(n) / n
            total = w.sum()
        w = w / total
        return {symbols[i]: float(w[i]) for i in range(n)}

    # --- Internal steps ---------------------------------------------------- #
    def _seriate(self, dist: np.ndarray) -> list[int]:
        from scipy.cluster.hierarchy import linkage
        from scipy.spatial.distance import squareform

        n = dist.shape[0]
        condensed = squareform(dist, checks=False)
        Z = linkage(condensed, method=self.method)
        return _leaves_from_linkage(Z, n)

    def _recursive_bisection(self, cov_sorted: np.ndarray) -> np.ndarray:
        n = cov_sorted.shape[0]
        w = np.ones(n)
        clusters: list[list[int]] = [list(range(n))]
        while clusters:
            next_level: list[list[int]] = []
            for cluster in clusters:
                if len(cluster) <= 1:
                    continue
                mid = len(cluster) // 2
                left = cluster[:mid]
                right = cluster[mid:]
                next_level.append(left)
                next_level.append(right)

                var_l = _cluster_variance(cov_sorted, left)
                var_r = _cluster_variance(cov_sorted, right)
                if var_l + var_r <= 0:
                    alpha = 0.5
                else:
                    # weight toward the lower-variance (lower-risk) branch
                    alpha = 1.0 - var_l / (var_l + var_r)
                w[left] *= alpha
                w[right] *= 1.0 - alpha
            clusters = next_level
        return w


# --------------------------------------------------------------------------- #
# Dispatcher: HRP for >5 assets, else classical risk parity
# --------------------------------------------------------------------------- #
def allocate(
    volatilities: dict[str, float],
    correlations: dict[tuple[str, str], float] | None = None,
    hrp_threshold: int = HRP_ASSET_THRESHOLD,
    **kwargs: Any,
) -> dict[str, float]:
    """Allocate weights, using HRP for large universes (``> hrp_threshold``).

    For ``len(volatilities) > hrp_threshold`` this returns
    :meth:`HRPAllocator.compute_hrp_weights`. Otherwise it defers to the
    Bridgewater-style :class:`RiskParityAllocator` (or HRP if that module is
    unavailable). This is the canonical entry point for "replace
    RiskParityAllocator for >5 assets".
    """
    n = len(volatilities)
    if n > hrp_threshold:
        logger.info("Using Hierarchical Risk Parity for %d assets (HRP)", n)
        return HRPAllocator().compute_hrp_weights(volatilities, correlations)
    if _HAS_RISK_PARITY:
        return RiskParityAllocator().compute_risk_parity_weights(
            volatilities, correlations
        )
    logger.info("RiskParityAllocator unavailable; falling back to HRP for %d assets", n)
    return HRPAllocator().compute_hrp_weights(volatilities, correlations)


__all__ = [
    "HRP_ASSET_THRESHOLD",
    "HRPAllocator",
    "allocate",
]
