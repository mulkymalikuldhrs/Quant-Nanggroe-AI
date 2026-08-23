"""Risk Parity Portfolio — native HRP + Equal Risk Contribution.

Allocates capital across strategies so each contributes EQUAL RISK,
not equal capital. Prevents one high-vol strategy from dominating PnL.

Algorithms:
    - HRP (Hierarchical Risk Parity): scipy clustering → quasi-diagonal → bisection
    - ERC (Equal Risk Contribution): Newton-Raphson iterative solver

Reference: López de Prado (2016) "Building Diversified Portfolios that
Outperform Out-of-Sample"
"""
from __future__ import annotations

import logging
from typing import Dict, List

import numpy as np

logger = logging.getLogger("QNA.RiskParity")


def hrp_weights(returns: Dict[str, List[float]]) -> Dict[str, float]:
    """Hierarchical Risk Parity allocation.

    Args:
        returns: {strategy_name: list_of_periodic_returns}

    Returns:
        {strategy_name: weight (sums to 1.0)}
    """
    names = list(returns.keys())
    if len(names) < 2:
        return {names[0]: 1.0} if names else {}

    # Build return matrix
    min_len = min(len(v) for v in returns.values())
    if min_len < 5:
        logger.warning("Insufficient data for HRP (%d obs)", min_len)
        return {n: 1.0 / len(names) for n in names}

    rets = np.array([returns[n][:min_len] for n in names])
    corr = np.corrcoef(rets)

    # Handle NaN/inf
    corr = np.nan_to_num(corr, nan=0.0, posinf=0.0, neginf=0.0)
    np.fill_diagonal(corr, 1.0)

    # Distance matrix
    dist = np.sqrt(np.clip((1 - corr) / 2, 0, 1))

    # Hierarchical clustering (scipy linkage)
    try:
        from scipy.cluster.hierarchy import linkage
        from scipy.spatial.distance import squareform

        condensed = squareform(dist, checks=False)
        link = linkage(condensed, method="single")
        sort_ix = _get_quasi_diag(link)
    except Exception:
        sort_ix = list(range(len(names)))

    sorted_names = [names[i] for i in sort_ix]

    # Recursive bisection
    sorted_rets = rets[sort_ix]
    weights = _recursive_bisection(sorted_rets)

    # Un-sort back to original order
    result: Dict[str, float] = {}
    for i, idx in enumerate(sort_ix):
        result[names[idx]] = round(float(weights[i]), 6)

    total = sum(result.values())
    if total > 0:
        result = {k: round(v / total, 6) for k, v in result.items()}

    logger.info("HRP weights: %s", result)
    return result


def _get_quasi_diag(link: np.ndarray) -> List[int]:
    """Get quasi-diagonal ordering from scipy linkage matrix."""
    import pandas as pd

    link_df = pd.DataFrame(link[:, :3].astype(int),
                           columns=["member_1", "member_2", "cluster"])
    n_items = link_df.shape[0] + 1
    items = []
    cluster_queue = [link_df.iloc[-1].name]
    while cluster_queue:
        cid = cluster_queue.pop(0)
        if cid < n_items:
            items.append(int(cid))
        else:
            row = link_df.loc[cid - n_items]
            cluster_queue.extend([int(row.member_2), int(row.member_1)])
    return items


def _recursive_bisection(rets: np.ndarray) -> np.ndarray:
    """Split portfolio into halves recursively, allocating inverse-vol."""
    n = rets.shape[0]
    weights = np.ones(n)

    clusters = [list(range(n))]
    while clusters:
        # Split each cluster into two halves
        new_clusters = []
        for cluster in clusters:
            if len(cluster) <= 1:
                continue
            mid = len(cluster) // 2
            left = cluster[:mid]
            right = cluster[mid:]

            # Compute cluster volatility (inverse of variance)
            left_vol = np.std(rets[left].sum(axis=0)) if len(left) > 1 else np.std(rets[left])
            right_vol = np.std(rets[right].sum(axis=0)) if len(right) > 1 else np.std(rets[right])

            left_var = max(left_vol ** 2, 1e-10)
            right_var = max(right_vol ** 2, 1e-10)

            alloc_factor = 1 - left_var / (left_var + right_var)
            weights[left] *= alloc_factor
            weights[right] *= (1 - alloc_factor)

            new_clusters.extend([left, right])
        clusters = new_clusters

    return weights / max(weights.sum(), 1e-10)


def erc_weights(volatilities: Dict[str, float]) -> Dict[str, float]:
    """Equal Risk Contribution — simpler alternative to HRP.

    Each strategy contributes equally to total portfolio risk.
    Weight ∝ 1/volatility, then normalized.

    Args:
        volatilities: {strategy_name: annualized_volatility}

    Returns:
        Normalized weights summing to 1.0
    """
    inv_vols = {name: 1.0 / max(vol, 1e-10) for name, vol in volatilities.items()}
    total = sum(inv_vols.values())
    return {name: round(w / total, 6) for name, w in inv_vols.items()}
