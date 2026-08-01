from __future__ import annotations

"""KMeans-based asset clustering for pairs-trading candidate generation.

This module clusters a universe of *assets* (each asset is one sample whose
feature vector is typically a normalized return series) into groups of
behaviourally similar instruments, then selects candidate **pairs** *within*
each cluster for statistical-arbitrage / pairs-trading.

Two building blocks are provided:

1. **Elbow method** (:func:`elbow_method` / :func:`optimal_k`) -- fit KMeans for a
   sweep of ``k`` values, record the inertia (within-cluster sum of squared
   distances) for each, and pick the ``k`` at the "elbow" -- the point of
   maximum curvature of the inertia curve -- as the number of clusters.

2. **Pairs candidate selection** (:func:`select_pairs_candidates`) -- for every
   cluster that contains at least two members, rank the intra-cluster pairs by
   their (inverse) distance and return the tightest pairs as trading candidates.

The KMeans core is implemented in pure NumPy so the module always runs even
where scikit-learn is unavailable. If scikit-learn *is* present it is used for
the fit (more numerically robust k-means++ seeding) via an optional fast path.

This mirrors the lazy-import / graceful-degradation pattern used by
:mod:`quant_nanggroe.engine.portfolio.hrp_allocator`.
"""

from dataclasses import dataclass, field
from typing import Any

import numpy as np

logger = __import__("logging").getLogger(__name__)

# Optional scikit-learn KMeans. Falls back to a pure-NumPy implementation when
# sklearn is not installed, so the module always imports and runs.
try:  # pragma: no cover - import guard
    from sklearn.cluster import KMeans as _SklearnKMeans  # type: ignore

    _HAS_SKLEARN = True
except Exception:  # pragma: no cover
    _SklearnKMeans = None  # type: ignore[assignment]
    _HAS_SKLEARN = False


# --------------------------------------------------------------------------- #
# Result containers
# --------------------------------------------------------------------------- #
@dataclass
class PairCandidate:
    """A candidate pairs-trading pair discovered inside one cluster."""

    a: str
    b: str
    cluster: int
    distance: float | None = None
    score: float | None = None

    def as_tuple(self) -> tuple[str, str, int, float | None, float | None]:
        return (self.a, self.b, self.cluster, self.distance, self.score)


@dataclass
class ClusterResult:
    """Outcome of a full KMeans clustering + pairs-selection pass."""

    k: int
    symbols: list[str]
    labels: dict[str, int]
    inertia: float
    pairs: list[PairCandidate] = field(default_factory=list)
    inertia_curve: list[tuple[int, float]] = field(default_factory=list)
    method: str = "kmeans"


# --------------------------------------------------------------------------- #
# NumPy KMeans core (sklearn-free)
# --------------------------------------------------------------------------- #
def _pairwise_sq_dists(X: np.ndarray, centroids: np.ndarray) -> np.ndarray:
    """Squared Euclidean distance from every row of ``X`` to each centroid."""
    # X: (n, d), centroids: (k, d) -> (n, k)
    return (
        np.sum(X**2, axis=1)[:, None]
        + np.sum(centroids**2, axis=1)[None, :]
        - 2.0 * (X @ centroids.T)
    )


def _kmeans_plusplus_init(X: np.ndarray, k: int, rng: np.random.Generator) -> np.ndarray:
    """k-means++ seeding: spread initial centroids to avoid poor local minima."""
    n = X.shape[0]
    idx0 = int(rng.integers(0, n))
    centers = [X[idx0].copy()]
    closest_sq = np.sum((X - centers[0]) ** 2, axis=1)
    for _ in range(1, k):
        # sample next centre proportionally to squared distance
        total = float(closest_sq.sum())
        if total <= 0.0:
            # degenerate: all points identical, just pick random
            nxt = int(rng.integers(0, n))
        else:
            probs = closest_sq / total
            nxt = int(rng.choice(n, p=probs))
        centers.append(X[nxt].copy())
        new_sq = np.sum((X - X[nxt]) ** 2, axis=1)
        closest_sq = np.minimum(closest_sq, new_sq)
    return np.asarray(centers, dtype=float)


def _kmeans_numpy(
    X: np.ndarray,
    k: int,
    n_init: int = 10,
    max_iter: int = 300,
    seed: int = 0,
    tol: float = 1e-4,
) -> tuple[np.ndarray, np.ndarray, float]:
    """Pure-NumPy Lloyd's KMeans. Returns ``(labels, centroids, inertia)``."""
    rng = np.random.default_rng(seed)
    n = X.shape[0]
    best_labels = np.zeros(n, dtype=int)
    best_centroids = np.zeros((k, X.shape[1]), dtype=float)
    best_inertia = np.inf

    k_eff = min(k, n)
    for _ in range(max(1, n_init)):
        # handle the degenerate case where k > n: assign each point its own cluster
        if k_eff < k:
            centroids = X.copy()
        else:
            centroids = _kmeans_plusplus_init(X, k_eff, rng)
        labels = np.zeros(n, dtype=int)
        for _it in range(max_iter):
            d2 = _pairwise_sq_dists(X, centroids)
            new_labels = np.argmin(d2, axis=1)
            if np.array_equal(new_labels, labels):
                labels = new_labels
                break
            labels = new_labels
            new_centroids = centroids.copy()
            for c in range(k_eff):
                mask = labels == c
                if np.any(mask):
                    new_centroids[c] = X[mask].mean(axis=0)
            if np.allclose(new_centroids, centroids, atol=tol):
                centroids = new_centroids
                break
            centroids = new_centroids
        inertia = float(np.sum(_pairwise_sq_dists(X, centroids)[np.arange(n), labels]))
        if inertia < best_inertia:
            best_inertia = inertia
            best_labels = labels.copy()
            best_centroids = centroids.copy()
    return best_labels, best_centroids, best_inertia


def _fit_kmeans(
    X: np.ndarray,
    k: int,
    n_init: int = 10,
    max_iter: int = 300,
    seed: int = 0,
    use_sklearn: bool = True,
) -> tuple[np.ndarray, np.ndarray, float]:
    """Fit KMeans for a fixed ``k`` using sklearn if available else NumPy.

    Sklearn's ``n_init``/``max_iter`` signatures differ across versions, so any
    sklearn failure silently falls back to the NumPy implementation.
    """
    if use_sklearn and _HAS_SKLEARN and _SklearnKMeans is not None:
        try:
            km = _SklearnKMeans(
                n_clusters=int(k), n_init=n_init, max_iter=max_iter, random_state=seed
            )
            km.fit(X)
            labels = km.labels_
            centroids = km.cluster_centers_
            # inertia may be None on very new sklearn; recompute if needed
            if getattr(km, "inertia_", None) is None:
                inertia = float(
                    np.sum(_pairwise_sq_dists(X, centroids)[np.arange(X.shape[0]), labels])
                )
            else:
                inertia = float(km.inertia_)
            return np.asarray(labels), np.asarray(centroids), inertia
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.warning("sklearn KMeans failed (%s); using NumPy KMeans", exc)
    return _kmeans_numpy(X, k, n_init=n_init, max_iter=max_iter, seed=seed)


# --------------------------------------------------------------------------- #
# Elbow method
# --------------------------------------------------------------------------- #
def elbow_method(
    features: np.ndarray,
    k_min: int = 2,
    k_max: int = 10,
    n_init: int = 10,
    max_iter: int = 300,
    seed: int = 0,
    use_sklearn: bool = True,
) -> list[tuple[int, float]]:
    """Fit KMeans across ``k in [k_min, k_max]`` and return ``[(k, inertia)]``.

    The inertia is the within-cluster sum of squared distances and decreases
    monotonically with ``k``; the "elbow" of the resulting curve marks the point
    where adding another cluster stops buying much explanatory power.
    """
    X = np.asarray(features, dtype=float)
    n = X.shape[0]
    if n == 0:
        return []
    # clamp the sweep to what the data can support
    k_max = min(k_max, max(k_min, n - 1))
    curve: list[tuple[int, float]] = []
    for k in range(k_min, k_max + 1):
        _, _, inertia = _fit_kmeans(
            X, k, n_init=n_init, max_iter=max_iter, seed=seed, use_sklearn=use_sklearn
        )
        curve.append((k, float(inertia)))
    return curve


def optimal_k(curve: list[tuple[int, float]]) -> int:
    """Pick the ``k`` at the elbow of the inertia curve.

    The elbow is the point of maximum perpendicular distance from the straight
    line joining the first and last ``(k, inertia)`` points. This is the classic
    "kneedle"-style heuristic and is robust for the typical monotone inertia drop.
    """
    if not curve:
        return 1
    if len(curve) == 1:
        return curve[0][0]
    ks = np.array([c[0] for c in curve], dtype=float)
    ys = np.array([c[1] for c in curve], dtype=float)
    x0, x1 = ks[0], ks[-1]
    y0, y1 = ys[0], ys[-1]
    # perpendicular distance from (xi, yi) to the line (x0,y0)-(x1,y1)
    num = np.abs((y1 - y0) * ks - (x1 - x0) * ys + x1 * y0 - y1 * x0)
    den = np.hypot(y1 - y0, x1 - x0)
    dist = num / den if den > 0 else np.zeros_like(ks)
    idx = int(np.argmax(dist))
    return int(curve[idx][0])


# --------------------------------------------------------------------------- #
# Pairs candidate selection
# --------------------------------------------------------------------------- #
def select_pairs_candidates(
    symbols: list[str],
    labels: dict[str, int] | np.ndarray,
    distance_matrix: np.ndarray | None = None,
    top_n: int = 5,
    max_per_cluster: int | None = None,
) -> list[PairCandidate]:
    """Select the tightest intra-cluster pairs as pairs-trading candidates.

    Parameters
    ----------
    symbols:
        Asset identifiers, in the same order as ``labels`` / ``distance_matrix``.
    labels:
        Cluster assignment -- either a ``{symbol: cluster_id}`` dict or an array
        aligned with ``symbols``.
    distance_matrix:
        Optional symmetric ``(n, n)`` distance matrix (e.g. ``sqrt(0.5*(1-C))``).
        When given, pairs are ranked by ascending distance (closest = best pair).
        When omitted, *all* intra-cluster pairs are returned (still rankable by
        the downstream caller using its own similarity measure).
    top_n:
        Maximum number of candidate pairs to return overall.
    max_per_cluster:
        Optional cap on pairs taken from a single cluster.
    """
    if len(symbols) == 0:
        return []

    if isinstance(labels, dict):
        idx_of = {s: i for i, s in enumerate(symbols)}
        label_arr = np.array([labels[s] for s in symbols], dtype=int)
    else:
        label_arr = np.asarray(labels, dtype=int)

    dist = None
    if distance_matrix is not None:
        dist = np.asarray(distance_matrix, dtype=float)

    # group symbol indices by cluster
    clusters: dict[int, list[int]] = {}
    for i, lbl in enumerate(label_arr):
        clusters.setdefault(int(lbl), []).append(i)

    candidates: list[PairCandidate] = []
    for lbl, members in clusters.items():
        if len(members) < 2:
            continue
        scored: list[PairCandidate] = []
        for ii in range(len(members)):
            a = symbols[members[ii]]
            for jj in range(ii + 1, len(members)):
                b = symbols[members[jj]]
                d = None
                if dist is not None:
                    d = float(dist[members[ii], members[jj]])
                scored.append(PairCandidate(a=a, b=b, cluster=lbl, distance=d))

        # rank: closest distance first; if no distance, by symbol name
        if dist is not None:
            scored.sort(key=lambda p: (p.distance if p.distance is not None else np.inf))
        else:
            scored.sort(key=lambda p: (p.a, p.b))

        if max_per_cluster is not None:
            scored = scored[: max_per_cluster]

        # score in [0,1]: 1 - normalized distance (higher = tighter pair)
        if dist is not None and scored:
            ds = [p.distance for p in scored if p.distance is not None]
            if ds:
                lo, hi = min(ds), max(ds)
                span = hi - lo
                for p in scored:
                    if p.distance is not None and span > 0:
                        p.score = 1.0 - (p.distance - lo) / span
                    elif p.distance is not None:
                        p.score = 1.0
        candidates.extend(scored)

    # global ranking: best (highest score) pairs first, ties broken by closeness
    candidates.sort(
        key=lambda p: (
            p.score if p.score is not None else -1.0,
            -(p.distance if p.distance is not None else np.inf),
        ),
        reverse=True,
    )
    return candidates[:top_n]


# --------------------------------------------------------------------------- #
# High-level orchestrator
# --------------------------------------------------------------------------- #
class KMeansClusterSelector:
    """Cluster a universe of assets with KMeans, then mine pairs candidates.

    Typical usage::

        sel = KMeansClusterSelector(k_min=2, k_max=10, top_pairs=5)
        result = sel.fit(symbols, returns_matrix, distance_matrix=dist)
        result.labels        # {symbol: cluster_id}
        result.pairs         # [PairCandidate(...), ...]
    """

    def __init__(
        self,
        k_min: int = 2,
        k_max: int = 10,
        n_init: int = 10,
        max_iter: int = 300,
        seed: int = 0,
        top_pairs: int = 5,
        max_per_cluster: int | None = None,
        use_sklearn: bool = True,
    ):
        self.k_min = k_min
        self.k_max = k_max
        self.n_init = n_init
        self.max_iter = max_iter
        self.seed = seed
        self.top_pairs = top_pairs
        self.max_per_cluster = max_per_cluster
        self.use_sklearn = use_sklearn

    # -- public API --------------------------------------------------------- #
    def fit(
        self,
        symbols: list[str],
        features: np.ndarray,
        distance_matrix: np.ndarray | None = None,
    ) -> ClusterResult:
        """Run elbow selection + KMeans fit + pairs candidate selection."""
        X = np.asarray(features, dtype=float)
        n = X.shape[0]
        if n == 0:
            return ClusterResult(k=0, symbols=[], labels={}, inertia=0.0, pairs=[])

        if n == 1:
            return ClusterResult(
                k=1,
                symbols=list(symbols),
                labels={symbols[0]: 0},
                inertia=0.0,
                pairs=[],
                method="kmeans",
            )

        curve = elbow_method(
            X,
            k_min=self.k_min,
            k_max=min(self.k_max, n - 1),
            n_init=self.n_init,
            max_iter=self.max_iter,
            seed=self.seed,
            use_sklearn=self.use_sklearn,
        )
        k = optimal_k(curve)
        labels_arr, _, inertia = _fit_kmeans(
            X,
            k,
            n_init=self.n_init,
            max_iter=self.max_iter,
            seed=self.seed,
            use_sklearn=self.use_sklearn,
        )
        labels = {symbols[i]: int(labels_arr[i]) for i in range(n)}
        pairs = select_pairs_candidates(
            symbols,
            labels,
            distance_matrix=distance_matrix,
            top_n=self.top_pairs,
            max_per_cluster=self.max_per_cluster,
        )
        return ClusterResult(
            k=k,
            symbols=list(symbols),
            labels=labels,
            inertia=float(inertia),
            pairs=pairs,
            inertia_curve=curve,
            method="kmeans",
        )


# --------------------------------------------------------------------------- #
# Module smoke test (run: python -m quant_nanggroe.engine.portfolio.clustering)
# --------------------------------------------------------------------------- #
if __name__ == "__main__":  # pragma: no cover
    rng = np.random.default_rng(42)
    # 3 latent clusters of synthetic return series
    base = rng.normal(0, 0.01, size=(60,))
    groups = []
    for _ in range(3):
        c = base + rng.normal(0, 0.005, size=60)
        for _ in range(8):
            groups.append(c + rng.normal(0, 0.003, size=60))
    feats = np.asarray(groups, dtype=float)
    syms = [f"A{i:02d}" for i in range(feats.shape[0])]
    sel = KMeansClusterSelector(k_min=2, k_max=8, top_pairs=6)
    res = sel.fit(syms, feats)
    print(f"optimal k = {res.k}, inertia = {res.inertia:.6g}")
    print(f"inertia curve = {res.inertia_curve}")
    print(f"selected pairs ({len(res.pairs)}):")
    for p in res.pairs:
        print(f"  {p.a} ~ {p.b}  cluster={p.cluster}  dist={p.distance}  score={p.score}")


__all__ = [
    "KMeansClusterSelector",
    "ClusterResult",
    "PairCandidate",
    "elbow_method",
    "optimal_k",
    "select_pairs_candidates",
]
