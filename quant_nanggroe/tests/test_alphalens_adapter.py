"""
Tests for the Alphalens adapter tear sheets (IC, quantile spread, turnover).

The repo ships a local ``types/`` package that shadows the stdlib ``types``
module, which breaks ``import quant_nanggroe`` under the verify venv. We
therefore load the adapter module directly via importlib (mirroring the
production smoke test). This is an environment limitation, not a defect in the
module under test.
"""

import importlib.util
import sys

import numpy as np
import pandas as pd

MODULE_PATH = (
    "D:/repositories/Quant-Nanggroe-AI-worktree/quant_nanggroe/"
    "engine/factors/alphalens_adapter.py"
)


def _load_adapter():
    spec = importlib.util.spec_from_file_location("alphalens_adapter", MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["alphalens_adapter"] = mod
    spec.loader.exec_module(mod)
    return mod


def _make_panels(seed=0):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2024-01-01", periods=120, freq="D")
    assets = [f"A{i:02d}" for i in range(20)]
    base = pd.DataFrame(rng.standard_normal((len(dates), len(assets))), index=dates, columns=assets)
    factor = base * 0.5
    prices = (1 + factor.shift(-1) * 0.02 + base * 0.01).cumprod()
    return factor, prices


def test_to_alphalens_factor_data_shape():
    m = _load_adapter()
    factor, prices = _make_panels()
    fd = m.to_alphalens_factor_data(factor, prices, periods=(1, 5, 10), quantiles=5)
    assert fd.data.index.names == ["date", "asset"]
    assert {"factor", "1D", "5D", "10D", "factor_quantile"}.issubset(fd.data.columns)
    # 120 dates * 20 assets - dropped leading/trailing edge rows.
    assert 0 < len(fd.data) <= 120 * 20


def test_information_coefficient_columns():
    m = _load_adapter()
    factor, prices = _make_panels()
    fd = m.to_alphalens_factor_data(factor, prices, periods=(1, 5), quantiles=5)
    ic = m.factor_information_coefficient(fd)
    for p in (1, 5):
        for c in (f"{p}D_IC", f"{p}D_IC_p", f"{p}D_RankIC", f"{p}D_RankIC_p"):
            assert c in ic.columns
    # p-values must be in [0, 1].
    pvals = ic[[f"{p}D_RankIC_p" for p in (1, 5)]].dropna().to_numpy()
    assert bool((pvals >= 0).all() and (pvals <= 1).all())


def test_mean_information_coefficient_summary():
    m = _load_adapter()
    factor, prices = _make_panels()
    fd = m.to_alphalens_factor_data(factor, prices, periods=(1, 5), quantiles=5)
    summary = m.mean_information_coefficient(fd)
    assert set(summary.index) == {"1D", "5D"}
    # ICIR equals IC_mean / IC_std.
    assert np.allclose(
        summary["ICIR"], summary["IC_mean"] / summary["IC_std"], equal_nan=True
    )


def test_quantile_spread():
    m = _load_adapter()
    factor, prices = _make_panels()
    fd = m.to_alphalens_factor_data(factor, prices, periods=(1, 5), quantiles=5)
    mean_ret, spread_summary = m.quantile_spread(fd, quantiles=5)
    # One spread column per horizon plus 5 quantile-mean columns.
    assert "1D_spread" in mean_ret.columns
    assert "5D_spread" in mean_ret.columns
    assert spread_summary.loc["1D", "n_days"] > 0
    assert np.isfinite(spread_summary.loc["1D", "spread_mean"])


def test_turnover():
    m = _load_adapter()
    factor, prices = _make_panels()
    fd = m.to_alphalens_factor_data(factor, prices, periods=(1, 5), quantiles=5)
    daily, summary = m.factor_turnover(fd, quantiles=5)
    assert list(daily.columns) == ["turnover_1D", "turnover_5D"]
    # Turnover is a fraction in [0, 1].
    assert (daily.dropna() >= 0).all().all()
    assert (daily.dropna() <= 1).all().all()
    assert "autocorrelation" in summary.columns


def test_run_tear_sheets_one_call():
    m = _load_adapter()
    factor, prices = _make_panels()
    out = m.run_tear_sheets(factor, prices, quantiles=5, periods=(1, 5))
    assert set(out) == {
        "factor_data",
        "ic",
        "ic_summary",
        "spread",
        "spread_summary",
        "turnover",
        "turnover_summary",
    }


def test_spearman_pvalue_boundary():
    m = _load_adapter()
    # Perfect correlation (rho=1) => p ~ 0; n < 3 => nan.
    assert m._spearman_pvalue(1.0, 100) == 0.0
    assert np.isnan(m._spearman_pvalue(0.5, 2))
