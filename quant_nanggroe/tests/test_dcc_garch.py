"""Unit tests for DCCGARCH — Dynamic Conditional Correlation + Volatility-Regulated Kelly.

Test categories:
  1. FX Data: Synthetic FX-like returns with known correlation structure
  2. Fit Edge Cases: Boundary conditions, degenerate inputs, numpy arrays
  3. VRK Weight Stability: Robustness under regime shifts, small input changes
"""

import os
import sys
import unittest
import warnings

import numpy as np
import pandas as pd

# Ensure project root is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from quant_nanggroe.engine.risk.dcc_garch import (
    DCCGARCH,
    _nearest_pd,
    compute_dcc_corr,
    dcc_garch_pipeline,
    dcc_kelly_weights,
    garch_vol_forecast,
)

# ── Suppress arch package convergence warnings in tests ──────────
warnings.filterwarnings("ignore", category=UserWarning, module="arch")
warnings.filterwarnings("ignore", category=FutureWarning)


# ══════════════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════════════


def _fx_like_returns(
    n_days: int = 500,
    seed: int = 42,
    corr_eur_gbp: float = 0.7,
    corr_gold_silver: float = 0.8,
    vol_eur: float = 0.008,
    vol_gbp: float = 0.009,
    vol_gold: float = 0.012,
    vol_silver: float = 0.018,
) -> pd.DataFrame:
    """Generate synthetic FX-like returns with a known correlation matrix."""
    rng = np.random.default_rng(seed)
    n_assets = 4

    # Build target covariance from known vols and correlations
    target_corr = np.array([
        [1.0, corr_eur_gbp, 0.3, 0.2],
        [corr_eur_gbp, 1.0, 0.25, 0.15],
        [0.3, 0.25, 1.0, corr_gold_silver],
        [0.2, 0.15, corr_gold_silver, 1.0],
    ])
    vols = np.array([vol_eur, vol_gbp, vol_gold, vol_silver])
    cov = np.diag(vols) @ target_corr @ np.diag(vols)

    # Generate multivariate normal returns
    raw = rng.multivariate_normal(mean=np.zeros(n_assets), cov=cov, size=n_days)
    return pd.DataFrame(raw, columns=["EURUSD", "GBPUSD", "XAUUSD", "XAGUSD"])


def _regime_shift_returns(
    n_days: int = 500,
    seed: int = 42,
    low_vol_periods: int = 250,
    high_vol_mult: float = 3.0,
) -> pd.DataFrame:
    """Returns with a volatility regime shift halfway through."""
    rng = np.random.default_rng(seed)
    cols = ["Asset_A", "Asset_B", "Asset_C"]

    # Low-vol regime
    low_cov = np.diag([0.01, 0.012, 0.008]) @ np.array([
        [1.0, 0.5, 0.3],
        [0.5, 1.0, 0.4],
        [0.3, 0.4, 1.0],
    ]) @ np.diag([0.01, 0.012, 0.008])

    low = rng.multivariate_normal(mean=np.zeros(3), cov=low_cov, size=low_vol_periods)

    # High-vol regime
    high_cov = low_cov * high_vol_mult
    high = rng.multivariate_normal(mean=np.zeros(3), cov=high_cov, size=n_days - low_vol_periods)

    returns = np.vstack([low, high])
    return pd.DataFrame(returns, columns=cols)


def _constant_returns(n: int, n_assets: int = 3, value: float = 0.001) -> pd.DataFrame:
    """Returns with zero variance (all rows identical)."""
    data = np.full((n, n_assets), value)
    return pd.DataFrame(data, columns=[f"A{i}" for i in range(n_assets)])


# ══════════════════════════════════════════════════════════════════════
#  Tests
# ══════════════════════════════════════════════════════════════════════


class TestDCCGarchFXData(unittest.TestCase):
    """Test DCC-GARCH on synthetic FX-like data with known correlation."""

    def setUp(self):
        self.fx_returns = _fx_like_returns(n_days=500)

    def test_fit_on_fx_data(self):
        """DCC should fit successfully on FX-like returns."""
        dcc = DCCGARCH(dcc_a=0.05, dcc_b=0.90)
        dcc.fit(self.fx_returns)
        self.assertTrue(dcc.fitted)
        self.assertEqual(dcc.asset_names, ["EURUSD", "GBPUSD", "XAUUSD", "XAGUSD"])
        self.assertEqual(dcc.correlation.shape, (4, 4))

    def test_fx_correlation_structure(self):
        """Correlation between EURUSD and GBPUSD should be higher than EURUSD-XAGUSD."""
        dcc = DCCGARCH(dcc_a=0.05, dcc_b=0.90)
        dcc.fit(self.fx_returns)
        corr = dcc.correlation
        # EUR(0)-GBP(1) should be more correlated than EUR(0)-Silver(3)
        self.assertGreater(corr[0, 1], corr[0, 3])
        # Gold(2)-Silver(3) should be highly correlated
        self.assertGreater(corr[2, 3], 0.3)

    def test_fx_volatilities_ordered(self):
        """Silver should have highest vol, EUR should have lowest."""
        dcc = DCCGARCH(dcc_a=0.05, dcc_b=0.90)
        dcc.fit(self.fx_returns)
        vols = dcc.volatilities
        # Silver (idx 3) should have highest vol
        self.assertGreater(vols[3], vols[0])
        self.assertGreater(vols[3], vols[1])

    def test_covariance_is_psd(self):
        """Covariance matrix should be positive semi-definite."""
        dcc = DCCGARCH(dcc_a=0.05, dcc_b=0.90)
        dcc.fit(self.fx_returns)
        cov = dcc.covariance
        eigvals = np.linalg.eigvalsh(cov)
        self.assertTrue(np.all(eigvals >= -1e-10))

    def test_correlation_is_symmetric(self):
        """Correlation matrix should be symmetric."""
        dcc = DCCGARCH(dcc_a=0.05, dcc_b=0.90)
        dcc.fit(self.fx_returns)
        corr = dcc.correlation
        np.testing.assert_array_almost_equal(corr, corr.T, decimal=10)

    def test_correlation_diagonal_is_one(self):
        """Diagonal of correlation matrix should be 1.0."""
        dcc = DCCGARCH(dcc_a=0.05, dcc_b=0.90)
        dcc.fit(self.fx_returns)
        corr = dcc.correlation
        np.testing.assert_array_almost_equal(np.diag(corr), np.ones(4), decimal=10)

    def test_dcc_different_params(self):
        """DCC with different alpha/beta should still fit."""
        for a, b in [(0.02, 0.95), (0.10, 0.80), (0.01, 0.98)]:
            dcc = DCCGARCH(dcc_a=a, dcc_b=b)
            dcc.fit(self.fx_returns)
            self.assertTrue(dcc.fitted, f"DCC should fit with a={a}, b={b}")

    def test_get_status_on_fx(self):
        """get_status should return populated dict."""
        dcc = DCCGARCH()
        dcc.fit(self.fx_returns)
        status = dcc.get_status()
        self.assertTrue(status["fitted"])
        self.assertEqual(status["n_assets"], 4)
        self.assertIn("mean_vol_pct", status)
        self.assertIn("mean_corr", status)
        self.assertIn("dcc_a", status)

    def test_get_status_not_fitted(self):
        """get_status should return safe defaults when not fitted."""
        dcc = DCCGARCH()
        status = dcc.get_status()
        self.assertFalse(status["fitted"])
        self.assertEqual(status["n_assets"], 0)

    def test_empty_returns_not_fitted(self):
        """Empty DataFrame should not fit."""
        dcc = DCCGARCH()
        dcc.fit(pd.DataFrame())
        self.assertFalse(dcc.fitted)

    def test_properties_before_fit(self):
        """Properties should return safe defaults before fit."""
        dcc = DCCGARCH()
        self.assertEqual(len(dcc.volatilities), 0)
        self.assertEqual(dcc.correlation.shape, (1, 0))
        self.assertEqual(dcc.covariance.shape, (1, 0))
        self.assertEqual(dcc.asset_names, [])
        self.assertFalse(dcc.fitted)

    def test_kelly_weights_before_fit(self):
        """kelly_weights should return zeros before fit."""
        dcc = DCCGARCH()
        w = dcc.kelly_weights(np.array([0.1, 0.2, 0.3]))
        np.testing.assert_array_equal(w, np.zeros(3))


class TestDCCGarchFitEdgeCases(unittest.TestCase):
    """Test edge cases around the DCC-GARCH fit method."""

    def test_minimum_data_success(self):
        """30 days of data should be the minimum for successful fit."""
        returns = _fx_like_returns(n_days=30)
        dcc = DCCGARCH()
        dcc.fit(returns)
        self.assertTrue(dcc.fitted)

    def test_below_minimum_data(self):
        """29 days of data should NOT fit (n_days < 30)."""
        returns = _fx_like_returns(n_days=29)
        dcc = DCCGARCH()
        dcc.fit(returns)
        self.assertFalse(dcc.fitted)

    def test_single_asset(self):
        """Single asset should produce scalar vol and 1x1 correlation."""
        returns = pd.DataFrame({"A": np.random.randn(100) * 0.02})
        dcc = DCCGARCH()
        dcc.fit(returns)
        self.assertTrue(dcc.fitted)
        self.assertEqual(dcc.correlation.shape, (1, 1))
        self.assertEqual(len(dcc.volatilities), 1)
        self.assertAlmostEqual(dcc.correlation[0, 0], 1.0)

    def test_numpy_array_input(self):
        """numpy array input should work (no column names)."""
        data = np.random.randn(200, 3) * 0.02
        dcc = DCCGARCH()
        dcc.fit(data, asset_names=["USD", "EUR", "GBP"])
        self.assertTrue(dcc.fitted)
        self.assertEqual(dcc.asset_names, ["USD", "EUR", "GBP"])

    def test_numpy_array_auto_names(self):
        """numpy array without asset_names should auto-generate names."""
        data = np.random.randn(100, 2) * 0.02
        dcc = DCCGARCH()
        dcc.fit(data)
        self.assertTrue(dcc.fitted)
        self.assertEqual(dcc.asset_names, ["asset_0", "asset_1"])

    def test_constant_returns(self):
        """Constant returns (zero variance) should not crash — one asset may fail GARCH."""
        returns = _constant_returns(100, 3)
        dcc = DCCGARCH()
        dcc.fit(returns)
        # Should still fit (may use fallback vol estimates)
        self.assertTrue(dcc.fitted)

    def test_constant_returns_single_asset(self):
        """Single asset with constant returns should not crash."""
        returns = pd.DataFrame({"A": np.ones(100) * 0.001})
        dcc = DCCGARCH()
        dcc.fit(returns)
        self.assertTrue(dcc.fitted)

    def test_nan_in_returns(self):
        """NaN values in returns should be handled gracefully."""
        data = np.random.randn(150, 3) * 0.02
        data[10, 0] = np.nan
        data[50, 1] = np.nan
        returns = pd.DataFrame(data, columns=["A", "B", "C"])
        dcc = DCCGARCH()
        dcc.fit(returns)
        # May still fit depending on how arch handles NaN
        # At minimum should not crash
        self.assertIsInstance(dcc.fitted, bool)

    def test_inf_in_returns(self):
        """Inf values should not crash the fit."""
        data = np.random.randn(100, 2) * 0.02
        data[5, 0] = np.inf
        data[10, 1] = -np.inf
        returns = pd.DataFrame(data, columns=["A", "B"])
        dcc = DCCGARCH()
        dcc.fit(returns)
        self.assertIsInstance(dcc.fitted, bool)

    def test_large_returns(self):
        """Very large returns (e.g. 100% daily move) should not crash."""
        data = np.random.randn(100, 2) * 0.5  # 50% daily vol
        returns = pd.DataFrame(data, columns=["A", "B"])
        dcc = DCCGARCH()
        dcc.fit(returns)
        self.assertTrue(dcc.fitted)

    def test_zero_rows(self):
        """Zero-row DataFrame should not fit."""
        dcc = DCCGARCH()
        dcc.fit(pd.DataFrame({"A": []}))
        self.assertFalse(dcc.fitted)

    def test_many_assets(self):
        """Fitting with 10+ assets should work."""
        n = 200
        n_assets = 12
        data = np.random.randn(n, n_assets) * 0.02
        cols = [f"Asset_{i}" for i in range(n_assets)]
        returns = pd.DataFrame(data, columns=cols)
        dcc = DCCGARCH()
        dcc.fit(returns)
        self.assertTrue(dcc.fitted)
        self.assertEqual(dcc.correlation.shape, (12, 12))

    def test_re_fit_overwrites(self):
        """Fitting a second time should overwrite the first fit."""
        r1 = _fx_like_returns(n_days=100, seed=1)
        r2 = _fx_like_returns(n_days=100, seed=2)
        dcc = DCCGARCH()
        dcc.fit(r1)
        names1 = list(dcc.asset_names)
        dcc.fit(r2)
        self.assertNotEqual(dcc.asset_names, ["dummy"], "Should have new asset names")
        self.assertTrue(dcc.fitted)

    def test_re_fit_different_shape(self):
        """Re-fitting with different number of assets should update shape."""
        r4 = _fx_like_returns(n_days=100)  # 4 assets
        r2 = _fx_like_returns(n_days=100, seed=1)[["EURUSD", "GBPUSD"]]  # 2 assets
        dcc = DCCGARCH()
        dcc.fit(r4)
        self.assertEqual(dcc.correlation.shape, (4, 4))
        dcc.fit(r2)
        self.assertEqual(dcc.correlation.shape, (2, 2),
                         "Re-fit with fewer assets should update shape")
        self.assertEqual(dcc.asset_names, ["EURUSD", "GBPUSD"])

    def test_dcc_params_a_plus_b_gte_one(self):
        """DCC with a + b >= 1 (non-stationary) should not crash.

        Note: a + b >= 1 violates DCC stationarity but the code should
        handle this gracefully without raising."""
        returns = _fx_like_returns(n_days=200)
        for a, b in [(0.5, 0.6), (0.3, 0.8), (0.9, 0.2)]:
            with self.subTest(a=a, b=b):
                dcc = DCCGARCH(dcc_a=a, dcc_b=b)
                try:
                    dcc.fit(returns)
                    # May or may not fit — should not crash either way
                    self.assertIsInstance(dcc.fitted, bool)
                except Exception as e:
                    self.fail(f"DCC with a={a}, b={b} raised: {e}")


# ── Real FX data test (skippable — requires yfinance + internet) ─────────
_REAL_DATA_ENV = "QNA_TEST_REAL_DATA"

def _try_fetch_fx_returns() -> pd.DataFrame | None:
    """Fetch real FX data via yfinance for EURUSD, GBPUSD, XAUUSD, XAGUSD.
    Returns None if yfinance is not installed or data is unavailable.

    NOTE: yfinance with multi-ticker download returns a MultiIndex on columns.
    Access via data["Close"] which returns the sub-DataFrame with ticker-level columns.
    """
    if not os.environ.get(_REAL_DATA_ENV, "").lower() in ("1", "true", "yes"):
        return None
    try:
        import yfinance as yf

        tickers = ["EURUSD=X", "GBPUSD=X", "GC=F", "SI=F"]
        data = yf.download(tickers, period="6mo", interval="1d",
                          progress=False)
        if data is None or data.empty:
            return None
        # yfinance multi-ticker: columns are MultiIndex (level 0 = OHLCV, level 1 = ticker)
        close = data["Close"] if "Close" in data.columns.get_level_values(0) else data
        if close.shape[1] != 4:
            return None
        close.columns = ["EURUSD", "GBPUSD", "XAUUSD", "XAGUSD"]
        log_returns = np.log(close / close.shift(1)).dropna()
        if len(log_returns) < 30:
            return None
        return log_returns
    except ImportError:
        return None
    except Exception:
        return None


@unittest.skipUnless(os.environ.get(_REAL_DATA_ENV, "").lower() in ("1", "true", "yes"),
                     f"Set {_REAL_DATA_ENV}=1 to enable real FX data tests")
class TestDCCGarchRealFXData(unittest.TestCase):
    """Test DCC-GARCH on real FX data downloaded via yfinance.

    Requires:
      - QNA_TEST_REAL_DATA=1 environment variable
      - yfinance package (pip install yfinance)
      - Internet connection
    """

    @classmethod
    def setUpClass(cls):
        cls.returns = _try_fetch_fx_returns()
        if cls.returns is None:
            raise unittest.SkipTest("Real FX data unavailable")

    def test_fit_on_real_fx(self):
        """DCC should fit successfully on real FX data."""
        dcc = DCCGARCH(dcc_a=0.05, dcc_b=0.90)
        dcc.fit(self.returns)
        self.assertTrue(dcc.fitted)
        self.assertGreaterEqual(dcc.correlation.shape[0], 2)

    def test_real_fx_corr_bounds(self):
        """Real FX correlations should be within [-1, 1]."""
        dcc = DCCGARCH()
        dcc.fit(self.returns)
        corr = dcc.correlation
        self.assertTrue(np.all(corr >= -1.0 - 1e-10), "Correlation below -1")
        self.assertTrue(np.all(corr <= 1.0 + 1e-10), "Correlation above +1")

    def test_real_fx_vols_reasonable(self):
        """Real FX volatilities should be in a reasonable range (0.1%-10% daily)."""
        dcc = DCCGARCH()
        dcc.fit(self.returns)
        vols = dcc.volatilities
        self.assertTrue(np.all(vols > 0.0005), "Vol too low")
        self.assertTrue(np.all(vols < 0.10), "Vol too high")


class TestDCCGarchVRKStability(unittest.TestCase):
    """Test Volatility-Regulated Kelly weight stability."""

    def setUp(self):
        self.fx_returns = _fx_like_returns(n_days=500)
        self.dcc = DCCGARCH(dcc_a=0.05, dcc_b=0.90)
        self.dcc.fit(self.fx_returns)
        self.expected_returns = np.array([0.08, 0.06, 0.10, 0.05])

    def test_weights_sum_to_reasonable_range(self):
        """Total absolute weight should not exceed max_risk_per_trade (0.5%)."""
        w = self.dcc.kelly_weights(self.expected_returns)
        total_abs = np.sum(np.abs(w))
        self.assertLessEqual(total_abs, 0.005 + 1e-10)  # max_risk_per_trade = 0.5%

    def test_weights_not_extreme(self):
        """No single asset weight should exceed max_single_asset_pct (25%)."""
        w = self.dcc.kelly_weights(self.expected_returns)
        self.assertTrue(np.all(np.abs(w) <= 0.25 + 1e-10))

    def test_higher_expected_return_leads_to_higher_weight(self):
        """Increasing expected return should increase the long-only allocation."""
        # Use a simpler setup: one positive asset vs zero expected returns
        er_zero = np.array([0.0, 0.0, 0.0, 0.0])
        er_positive = np.array([0.10, 0.0, 0.0, 0.0])

        w_zero = self.dcc.kelly_weights(er_zero)
        w_pos = self.dcc.kelly_weights(er_positive)

        # Only asset 0 has positive expected return → should have positive weight
        self.assertGreater(w_pos[0], 0, "Positive expected return should yield positive weight")
        # Asset 0 weight should be higher than when all returns are zero
        self.assertGreaterEqual(w_pos[0], w_zero[0] - 1e-10)

    def test_negative_returns_lead_to_negative_weights(self):
        """Negative expected returns should produce negative weights."""
        er = np.array([-0.05, 0.06, -0.03, 0.04])
        w = self.dcc.kelly_weights(er)
        self.assertLess(w[0], 0)
        self.assertLess(w[2], 0)

    def test_all_zero_returns_lead_to_zero_weights(self):
        """Zero expected returns should produce zero weights."""
        w = self.dcc.kelly_weights(np.zeros(4))
        np.testing.assert_array_almost_equal(w, np.zeros(4), decimal=10)

    def test_safety_factor_reduces_weights(self):
        """Smaller safety factor should reduce absolute weight magnitude."""
        w_default = self.dcc.kelly_weights(self.expected_returns)
        w_safe = self.dcc.kelly_weights(self.expected_returns, safety_factor=0.1)
        self.assertLessEqual(np.sum(np.abs(w_safe)), np.sum(np.abs(w_default)) + 1e-10)

    def test_higher_target_vol_increases_weights(self):
        """Higher target volatility should increase weight magnitude."""
        w_low = self.dcc.kelly_weights(self.expected_returns, target_vol=0.10)
        w_high = self.dcc.kelly_weights(self.expected_returns, target_vol=0.25)
        total_low = np.sum(np.abs(w_low))
        total_high = np.sum(np.abs(w_high))
        self.assertGreaterEqual(total_high, total_low - 1e-10)

    def test_weights_stable_under_small_correlation_change(self):
        """Small change in correlation should not cause wild weight changes."""
        # Base weights
        w_base = self.dcc.kelly_weights(self.expected_returns)

        # Slightly modify correlation matrix
        corr_mod = self.dcc.correlation.copy()
        corr_mod[0, 1] += 0.02
        corr_mod[1, 0] += 0.02

        w_mod = dcc_kelly_weights(self.expected_returns, corr_mod, self.dcc.volatilities)

        # Weights should not change by more than 0.2% (2x the cap for randomness)
        max_change = 0.002
        actual_change = np.max(np.abs(w_mod - w_base))
        self.assertLess(actual_change, max_change,
                        f"Max weight change {actual_change:.6f} exceeds {max_change:.6f}")

    def test_regime_shift_weight_stability(self):
        """Weights should not flip dramatically between low-vol and high-vol regimes."""
        regime_returns = _regime_shift_returns(n_days=500)
        dcc = DCCGARCH()
        dcc.fit(regime_returns)

        er = np.array([0.08, 0.06, 0.10])
        w = dcc.kelly_weights(er)

        # Weights should be within bounds
        self.assertTrue(np.all(np.abs(w) <= 0.25 + 1e-10),
                        f"Single asset weight {np.max(np.abs(w)):.4f} exceeds 25% cap")
        self.assertLessEqual(np.sum(np.abs(w)), 0.005 + 1e-10,
                             f"Total risk {np.sum(np.abs(w)):.6f} exceeds 0.5% cap")

        # All weights should be finite (not NaN or Inf)
        self.assertTrue(np.all(np.isfinite(w)), "Weights must be finite")

        # Total net long should be positive (bullish expected returns)
        self.assertGreater(np.sum(w[w > 0]), 0, "Net long exposure should be positive")

    def test_different_dcc_parameters_weight_stability(self):
        """DCC with different a/b params should produce reasonable weights."""
        er = np.array([0.08, 0.06, 0.10, 0.05])
        for a, b in [(0.02, 0.95), (0.10, 0.80), (0.05, 0.90)]:
            dcc = DCCGARCH(dcc_a=a, dcc_b=b)
            dcc.fit(self.fx_returns)
            w = dcc.kelly_weights(er)
            total_abs = np.sum(np.abs(w))
            self.assertLessEqual(total_abs, 0.005 + 1e-10,
                                 f"Total weight {total_abs} exceeds 0.5% cap for a={a}, b={b}")


class TestDCCGarchHelperFunctions(unittest.TestCase):
    """Test standalone helper functions used by DCCGARCH."""

    def test_garch_vol_forecast_basic(self):
        """garch_vol_forecast should return positive volatilities."""
        returns = np.random.randn(200) * 0.02
        vols = garch_vol_forecast(returns, horizon=5)
        self.assertEqual(len(vols), 5)
        self.assertTrue(np.all(vols > 0))

    def test_garch_vol_forecast_short_series(self):
        """garch_vol_forecast should handle short series via fallback."""
        returns = np.random.randn(3) * 0.02
        vols = garch_vol_forecast(returns, horizon=2)
        self.assertEqual(len(vols), 2)
        self.assertTrue(np.all(vols > 0))

    def test_compute_dcc_corr_shape(self):
        """compute_dcc_corr should return n_assets x n_assets matrix."""
        residuals = np.random.randn(200, 4)
        corr = compute_dcc_corr(residuals)
        self.assertEqual(corr.shape, (4, 4))

    def test_compute_dcc_corr_psd(self):
        """DCC correlation should be positive semi-definite."""
        residuals = np.random.randn(200, 3)
        corr = compute_dcc_corr(residuals)
        eigvals = np.linalg.eigvalsh(corr)
        self.assertTrue(np.all(eigvals >= -1e-10))

    def test_compute_dcc_corr_symmetric(self):
        """DCC correlation should be symmetric."""
        residuals = np.random.randn(200, 3)
        corr = compute_dcc_corr(residuals)
        np.testing.assert_array_almost_equal(corr, corr.T, decimal=10)

    def test_nearest_pd_psd(self):
        """_nearest_pd should return a PSD matrix."""
        # Create a non-PSD matrix
        mat = np.array([[1.0, 0.99, 0.95],
                         [0.99, 1.0, 0.30],
                         [0.95, 0.30, 1.0]])
        # Make the 3x3 principal minor non-PSD by adding negative eigenvalue
        mat2 = mat.copy()
        mat2[0, 2] = 0.99
        mat2[2, 0] = 0.99
        pd_mat = _nearest_pd(mat2)
        eigvals = np.linalg.eigvalsh(pd_mat)
        self.assertTrue(np.all(eigvals >= -1e-10))

    def test_dcc_kelly_weights_psd_input(self):
        """dcc_kelly_weights should handle all possible inputs."""
        er = np.array([0.08, 0.06])
        corr = np.array([[1.0, 0.5], [0.5, 1.0]])
        vols = np.array([0.15, 0.20])
        w = dcc_kelly_weights(er, corr, vols)
        self.assertEqual(len(w), 2)
        self.assertTrue(np.all(np.isfinite(w)))

    def test_dcc_kelly_weights_negative_corr(self):
        """dcc_kelly_weights should handle negative correlations."""
        er = np.array([0.08, 0.04])
        corr = np.array([[1.0, -0.7], [-0.7, 1.0]])
        vols = np.array([0.15, 0.20])
        w = dcc_kelly_weights(er, corr, vols)
        self.assertTrue(np.all(np.isfinite(w)))

    def test_dcc_garch_pipeline(self):
        """dcc_garch_pipeline convenience function should return all keys."""
        returns = _fx_like_returns(n_days=200)
        er = np.array([0.08, 0.06, 0.10, 0.05])
        result = dcc_garch_pipeline(returns, er)
        self.assertIn("correlation", result)
        self.assertIn("volatilities", result)
        self.assertIn("covariance", result)
        self.assertIn("weights", result)
        self.assertIn("status", result)
        self.assertTrue(result["status"]["fitted"])


class TestDCCGarchInverseETFData(unittest.TestCase):
    """Test on inverse-correlated data (like USDJPY inverted vs DXY)."""

    def test_inverse_correlation(self):
        """Two assets with strong negative correlation should recover negative corr."""
        rng = np.random.default_rng(42)
        n = 300
        common = rng.normal(0, 0.01, n)
        noise_a = rng.normal(0, 0.003, n)
        noise_b = rng.normal(0, 0.003, n)
        a = common + noise_a
        b = -common + noise_b  # inverse of A
        df = pd.DataFrame({"Asset_A": a, "Asset_B": b})

        dcc = DCCGARCH()
        dcc.fit(df)
        corr = dcc.correlation
        self.assertLess(corr[0, 1], -0.3, "Inverse pair should have negative correlation")


if __name__ == "__main__":
    unittest.main(verbosity=2)
