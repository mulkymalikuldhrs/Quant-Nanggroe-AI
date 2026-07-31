"""
Tests for QNA Cointegration & Pairs Framework (Fase 1.2).

Uses synthetic cointegrated price series and imports the module directly
from the repo path. No network and no NumPy/SciPy/scipy dependency.
"""

from __future__ import annotations

import math

from quant_nanggroe.core.intermarket.cointegration import (
    PairGroup,
    PairScores,
    DEFAULT_PAIR_GROUPS,
    compute_spread,
    engle_granger_test,
    generate_pair_signals,
    rolling_zscore,
    estimate_half_life,
    run_pairs,
)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _brownian_bridge(n: int = 500, seed: int = 0):
    rnd = __import__("random").Random(seed)
    w = [0.0]
    for _ in range(n - 1):
        w.append(w[-1] + rnd.gauss(0, 1))
    return [100 + x for x in w]


def _cointegrated_pair(n: int = 500, seed: int = 0, beta: float = 1.0, noise: float = 0.2):
    rnd = __import__("random").Random(seed)
    w = [0.0]
    for _ in range(n - 1):
        w.append(w[-1] + rnd.gauss(0, 1))
    a = [100 + w[i] + rnd.gauss(0, noise) for i in range(n)]
    b = [50 + w[i] * max(beta, 1e-12) for i in range(n)]
    return a, b


def _trending_noncointegrated(n: int = 500):
    rnd = __import__("random")
    a = [100 + 0.05 * i + rnd.gauss(0, 1) for i in range(n)]
    b = [80 + 0.02 * i + rnd.gauss(0, 1) for i in range(n)]
    return a, b


# ------------------------------------------------------------------
# Tests: core math helpers
# ------------------------------------------------------------------


def test_compute_spread_basic():
    a = [1.0, 2.0, 3.0]
    b = [1.0, 1.0, 1.0]
    out = compute_spread(a, b, 1.0)
    assert out == (0.0, 1.0, 2.0)


def test_compute_spread_beta_mismatch_length():
    a = [1.0, 2.0, 3.0, 4.0]
    b = [1.0, 2.0]
    out = compute_spread(a, b, 1.0)
    assert len(out) == min(len(a), len(b))


def test_rolling_zscore_constant():
    vals = [5.0] * 100
    out = rolling_zscore(vals, window=10)
    assert all(math.isfinite(z) for z in out)
    # all values same => every z-score should be 0.
    assert all(math.isclose(z, 0.0) for z in out)


def test_rolling_zscore_window_smaller_than_series():
    v = list(range(100))
    out = rolling_zscore(v, window=3)
    assert all(math.isfinite(z) for z in out)


def test_rolling_zscore_empty():
    out = rolling_zscore([], window=10)
    assert out == ()


# ------------------------------------------------------------------
# Tests: half-life
# ------------------------------------------------------------------


def test_half_life_positive_for_ou():
    rnd = __import__("random").Random(99)
    s = [1.0]
    for _ in range(999):
        s.append(s[-1] + 0.2 * (100.0 - s[-1]) + rnd.gauss(0, 1))
    hl = estimate_half_life(s)
    assert hl is not None and hl > 0


def test_half_life_none_for_linear_drift():
    s = [1.0 * i + __import__("random").gauss(0, 0.1) for i in range(200)]
    hl = estimate_half_life(s)
    assert hl is None


def test_half_life_short_input():
    assert estimate_half_life([]) is None
    assert estimate_half_life([1.0, 2.0, 3.0]) is None or (isinstance(hl := estimate_half_life([1.0, 2.0, 3.0]), float) and hl > 0)


# ------------------------------------------------------------------
# Tests: Engle-Granger
# ------------------------------------------------------------------


def test_cointegrated_pair_fields():
    a, b = _cointegrated_pair(n=500, seed=7, beta=1.0, noise=0.2)
    res = engle_granger_test(a, b)
    assert hasattr(res, "hedge_ratio")
    assert hasattr(res, "p_value")
    assert hasattr(res, "confidence")
    assert res.confidence in {"high", "medium", "low", "none"}


def test_noncointegrated_pair_not_cointegrated():
    a, b = _trending_noncointegrated(500)
    res = engle_granger_test(a, b)
    # With separate random trends we should not find cointegration at 5% sig.
    assert (res.cointegrated is False) or (res.confidence not in {"high", "medium"})


def test_short_input_returns_no_cointegration():
    res = engle_granger_test([1.0, 2.0], [1.0, 2.0])
    assert res.cointegrated is False
    assert res.spread == ()


def test_no_nan_in_spread():
    a, b = _cointegrated_pair(n=400, seed=3, beta=1.0, noise=0.2)
    res = engle_granger_test(a, b)
    if res.spread:
        assert all(math.isfinite(x) for x in res.spread)


# ------------------------------------------------------------------
# Tests: signals
# ------------------------------------------------------------------


def test_signals_include_trades():
    # Cointegrated pair with noise -> z-score crosses thresholds => long/short
    a, b = _cointegrated_pair(500, seed=2, beta=1.0, noise=0.3)
    sigs = generate_pair_signals(a, b, 1.0, entry_z=1.2, exit_z=0.2)
    assert any(s.signal in {"long", "short"} for s in sigs)


def test_signals_length_matches_min_len():
    a = list(range(200))
    b = list(range(200, 400))
    sigs = generate_pair_signals(a, b, 1.0)
    assert len(sigs) == min(len(a), len(b))


def test_signal_z_finite():
    a, b = _cointegrated_pair(500, seed=1, beta=1.1, noise=0.25)
    sigs = generate_pair_signals(a, b, 1.1)
    assert all(math.isfinite(s.z_score) for s in sigs)


def test_entry_z_triggers_long_then_exit():
    # Craft long sequence: near-constant then a long DROP (negative z-score
    # => spread below mean => "long" per module convention z < -entry_z).
    a = [100.0] * 120 + [100.0 - i * 5 for i in range(40)]
    b = [50.0] * 160
    sigs = generate_pair_signals(a, b, 1.0, entry_z=1.8, exit_z=0.2)
    assert any(s.signal == "long" for s in sigs)
    assert any(s.signal == "exit" for s in sigs)


# ------------------------------------------------------------------
# Tests: defaults
# ------------------------------------------------------------------


def test_default_pairs_contains_all_required():
    names = {p.name for p in DEFAULT_PAIR_GROUPS}
    expected = {"GC1!/SI1!", "6E1!/DXY", "NQ1!/ES1!", "BTC1!/ETH1!", "ZB1!/ZN1!"}
    assert expected == names


def test_pair_group_dataclass():
    p = PairGroup("A/B", "A", "B", default_beta=0.5)
    assert p.name == "A/B"
    assert p.default_beta == 0.5


def test_run_pairs_returns_scores():
    scores = run_pairs()
    assert len(scores) == 5
    assert all(isinstance(s, PairScores) for s in scores)
