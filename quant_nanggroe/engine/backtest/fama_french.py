"""Fama-French 5-Factor Model.

Implements factor analysis using the Fama-French 5-factor model:
1. Market Risk Premium (Rm - Rf)
2. SMB (Small Minus Big) - Size factor
3. HML (High Minus Low) - Value factor
4. RMW (Robust Minus Weak) - Profitability factor
5. CMA (Conservative Minus Aggressive) - Investment factor

Plus optional Momentum (UMD/WML) factor for the 6-factor model.

Data Source: Kenneth French Data Library
https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html

References:
- Fama & French (2015), "A Five-Factor Asset Pricing Model"
- Carhart (1997), "On Persistence in Mutual Fund Performance"
- Fama & French (1993), "Common Risk Factors in the Returns on Stocks and Bonds"
"""

from __future__ import annotations

import io
import logging
import os
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
from scipy import stats as sp_stats

logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════════════════════
# Kenneth French Data Library URLs
# ══════════════════════════════════════════════════════════════════════

FRENCH_DATA_BASE = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"

# US research factor datasets
FF3_DAILY_URL = FRENCH_DATA_BASE + "F-F_Research_Data_Factors_daily_CSV.zip"
FF3_MONTHLY_URL = FRENCH_DATA_BASE + "F-F_Research_Data_Factors_CSV.zip"
FF5_DAILY_URL = FRENCH_DATA_BASE + "F-F_Research_Data_5_Factors_2x3_daily_CSV.zip"
FF5_MONTHLY_URL = FRENCH_DATA_BASE + "F-F_Research_Data_5_Factors_2x3_CSV.zip"
MOMENTUM_DAILY_URL = FRENCH_DATA_BASE + "F-F_Momentum_Factor_daily_CSV.zip"
MOMENTUM_MONTHLY_URL = FRENCH_DATA_BASE + "F-F_Momentum_Factor_CSV.zip"

# Default cache directory
_DEFAULT_CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "quant_nanggroe", "french_data")


# ══════════════════════════════════════════════════════════════════════
# Data Classes
# ══════════════════════════════════════════════════════════════════════


@dataclass
class FactorExposure:
    """Factor exposure (beta) from regression.

    Attributes:
        factor_name: Name of the factor.
        beta: Factor loading (coefficient from regression).
        t_stat: t-statistic for the coefficient.
        p_value: p-value for the coefficient.
        std_error: Standard error of the coefficient.
    """

    factor_name: str
    beta: float
    t_stat: float
    p_value: float
    std_error: float


@dataclass
class FactorRegressionResult:
    """Result from factor regression.

    The model estimated is:
        R_i - R_f = alpha + beta1*MktRF + beta2*SMB + beta3*HML
                  + beta4*RMW + beta5*CMA + [beta6*UMD] + epsilon

    Attributes:
        alphas: Intercept (alpha) per regression.
        exposures: List of FactorExposure objects.
        r_squared: R-squared of the regression.
        adj_r_squared: Adjusted R-squared.
        f_stat: F-statistic for overall significance.
        f_pvalue: p-value of F-statistic.
        residuals: Residuals from the regression.
        n_observations: Number of observations used.
        factor_names: Names of the factors used in regression.
    """

    alphas: List[FactorExposure]
    exposures: List[FactorExposure]
    r_squared: float
    adj_r_squared: float
    f_stat: float
    f_pvalue: float
    residuals: np.ndarray
    n_observations: int
    factor_names: List[str] = field(default_factory=list)


@dataclass
class FactorAttribution:
    """Factor attribution decomposition.

    Decomposes portfolio returns:
        R_p = alpha + sum(beta_i * f_i) + epsilon

    Total return = Alpha + Sum(factor_beta * factor_mean_return) + Specific

    Attributes:
        total_return: Total portfolio return (annualized).
        factor_return: Return explained by factors (annualized).
        specific_return: Return not explained by factors (alpha + residual).
        alpha: Intercept (skill) component (annualized).
        factor_contributions: Dict of factor_name -> contribution.
    """

    total_return: float
    factor_return: float
    specific_return: float
    alpha: float
    factor_contributions: Dict[str, float]


@dataclass
class AlphaSignificance:
    """Alpha significance test result.

    Attributes:
        alpha: Estimated alpha (per-bar).
        alpha_annual: Annualized alpha.
        t_stat: t-statistic for alpha.
        p_value: p-value for alpha (two-tailed).
        is_significant: Whether alpha is significant at given level.
        confidence_level: Confidence level used for significance test.
        information_ratio: Alpha / residual_volatility (annualized).
    """

    alpha: float
    alpha_annual: float
    t_stat: float
    p_value: float
    is_significant: bool
    confidence_level: float
    information_ratio: float


# ══════════════════════════════════════════════════════════════════════
# Kenneth French Data Downloader
# ══════════════════════════════════════════════════════════════════════


class KennethFrenchDataDownloader:
    """Download and parse factor data from Kenneth French's Data Library.

    Downloads daily and monthly factor data from French's website,
    parses the fixed-width format files, and caches data locally.

    Supports:
    - 3-factor model: Mkt-RF, SMB, HML
    - 5-factor model: Mkt-RF, SMB, HML, RMW, CMA
    - Momentum factor: UMD (Up Minus Down)

    Usage:
        downloader = KennethFrenchDataDownloader()
        ff5_daily = downloader.download("5_factor", frequency="daily")
        ff3_monthly = downloader.download("3_factor", frequency="monthly")
        momentum = downloader.download("momentum", frequency="daily")
    """

    DATASET_URLS = {
        "3_factor": {
            "daily": FF3_DAILY_URL,
            "monthly": FF3_MONTHLY_URL,
        },
        "5_factor": {
            "daily": FF5_DAILY_URL,
            "monthly": FF5_MONTHLY_URL,
        },
        "momentum": {
            "daily": MOMENTUM_DAILY_URL,
            "monthly": MOMENTUM_MONTHLY_URL,
        },
    }

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        cache_expiry_days: int = 7,
    ) -> None:
        """Initialize the downloader.

        Args:
            cache_dir: Directory for caching downloaded data.
                Defaults to ~/.cache/quant_nanggroe/french_data.
            cache_expiry_days: Number of days before cache expires.
        """
        self.cache_dir = cache_dir or _DEFAULT_CACHE_DIR
        self.cache_expiry_days = cache_expiry_days

    def download(
        self,
        dataset: str = "5_factor",
        frequency: str = "daily",
    ) -> pd.DataFrame:
        """Download factor data from Kenneth French's website.

        Tries to load from cache first, then downloads if needed.

        Args:
            dataset: Dataset type ('3_factor', '5_factor', 'momentum').
            frequency: 'daily' or 'monthly'.

        Returns:
            DataFrame with factor returns (decimal form).

        Raises:
            ValueError: If dataset or frequency is invalid.
            ConnectionError: If data cannot be downloaded.
        """
        if dataset not in self.DATASET_URLS:
            raise ValueError(
                f"Unknown dataset '{dataset}'. "
                f"Choose from: {list(self.DATASET_URLS.keys())}"
            )
        if frequency not in ("daily", "monthly"):
            raise ValueError(
                f"Invalid frequency '{frequency}'. Choose 'daily' or 'monthly'."
            )

        # Try cache first
        cached = self._load_from_cache(dataset, frequency)
        if cached is not None:
            return cached

        # Download
        url = self.DATASET_URLS[dataset][frequency]
        try:
            logger.info("Fetching factor data from: %s", url)
            df = self._download_and_parse(url)

            # Cache the result
            self._save_to_cache(df, dataset, frequency)

            return df
        except Exception as e:
            logger.error("Failed to fetch factor data: %s", e)
            raise ConnectionError(f"Failed to fetch factor data from {url}: {e}")

    def _download_and_parse(self, url: str) -> pd.DataFrame:
        """Download a zip file from French's website and parse the CSV."""
        import urllib.request

        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as response:
            zip_data = response.read()

        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            csv_names = [n for n in zf.namelist() if n.endswith(".csv")]
            if not csv_names:
                raise ValueError("No CSV file found in zip archive")

            with zf.open(csv_names[0]) as csv_file:
                content = csv_file.read().decode("utf-8", errors="replace")

        return self._parse_french_csv(content)

    @staticmethod
    def _parse_french_csv(content: str) -> pd.DataFrame:
        """Parse Kenneth French CSV format.

        French data files have a specific format:
        - Header rows with metadata (skip until we find column names)
        - Data in CSV format with date as first column
        - Footer rows with -99.99 or -999 placeholder for missing data
        - Values typically in percentage form (need conversion)
        """
        lines = content.strip().split("\n")

        # Find the header row (contains column names like Mkt-RF, SMB, HML)
        header_idx = None
        for i, line in enumerate(lines):
            if any(keyword in line for keyword in ["Mkt-RF", "SMB", "HML", "Mom"]):
                header_idx = i
                break

        if header_idx is None:
            # Try to parse as regular CSV
            from io import StringIO
            return pd.read_csv(StringIO(content), index_col=0, parse_dates=True)

        # Skip to header and parse data rows
        data_lines = lines[header_idx:]
        cleaned: List[str] = []
        for line in data_lines:
            parts = line.strip().split(",")
            if len(parts) >= 2:
                try:
                    float(parts[1].strip())
                    cleaned.append(line)
                except ValueError:
                    continue

        from io import StringIO
        csv_content = "\n".join(cleaned)
        df = pd.read_csv(StringIO(csv_content), index_col=0, parse_dates=True)

        # Clean: remove rows with -99.99 or -999 (French placeholder for missing)
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df.replace(-99.99, np.nan).replace(-999, np.nan).dropna()

        # Convert from percentage to decimal (French data is in %)
        for col in df.columns:
            if df[col].abs().mean() > 0.1:
                df[col] = df[col] / 100.0

        return df

    def _cache_path(self, dataset: str, frequency: str) -> str:
        """Get the cache file path for a dataset."""
        return os.path.join(self.cache_dir, f"{dataset}_{frequency}.parquet")

    def _load_from_cache(
        self, dataset: str, frequency: str
    ) -> Optional[pd.DataFrame]:
        """Load data from local cache if available and fresh."""
        path = self._cache_path(dataset, frequency)

        if not os.path.exists(path):
            return None

        # Check cache age
        import time
        file_age_days = (time.time() - os.path.getmtime(path)) / 86400
        if file_age_days > self.cache_expiry_days:
            logger.info("Cache expired for %s/%s (%.1f days old)",
                        dataset, frequency, file_age_days)
            return None

        try:
            df = pd.read_parquet(path)
            logger.info("Loaded from cache: %s/%s (%d rows)",
                        dataset, frequency, len(df))
            return df
        except Exception as e:
            logger.warning("Failed to load cache: %s", e)
            return None

    def _save_to_cache(
        self, df: pd.DataFrame, dataset: str, frequency: str
    ) -> None:
        """Save data to local cache."""
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
            path = self._cache_path(dataset, frequency)
            df.to_parquet(path)
            logger.info("Cached %s/%s (%d rows)", dataset, frequency, len(df))
        except Exception as e:
            logger.warning("Failed to save cache: %s", e)


# ══════════════════════════════════════════════════════════════════════
# Fama-French 5-Factor Model
# ══════════════════════════════════════════════════════════════════════


class FF5FactorModel:
    """Fama-French 5-Factor Model with optional momentum.

    Implements the factor regression:
        R_i - R_f = alpha + beta1*MktRF + beta2*SMB + beta3*HML
                  + beta4*RMW + beta5*CMA + [beta6*UMD] + epsilon

    Supports:
    - 3-factor model (Fama & French, 1993): Mkt-RF, SMB, HML
    - 5-factor model (Fama & French, 2015): Mkt-RF, SMB, HML, RMW, CMA
    - 6-factor model (Carhart, 1997 + FF5): FF5 + UMD momentum

    Usage:
        model = FF5FactorModel()
        # Load factor data
        model.load_factor_data(ff_data_df)
        # Run 5-factor regression
        result = model.regress(portfolio_returns, n_factors=5)
        # Run 3-factor regression
        result = model.regress(portfolio_returns, n_factors=3)
        # Factor attribution
        attribution = model.factor_attribution(portfolio_returns, factor_data)
        # Alpha significance test
        sig = model.alpha_significance(result)
        # Information ratio
        ir = model.information_ratio(result)
    """

    # Standard factor name sets
    FACTOR_NAMES_3 = ["Mkt-RF", "SMB", "HML"]
    FACTOR_NAMES_5 = ["Mkt-RF", "SMB", "HML", "RMW", "CMA"]
    FACTOR_NAMES_6 = ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "UMD"]

    def __init__(
        self,
        risk_free_rate: float = 0.02,
        bars_per_year: int = 252,
    ) -> None:
        """Initialize Fama-French model.

        Args:
            risk_free_rate: Annual risk-free rate (used when FF data not available).
            bars_per_year: Bars per year for annualization.
        """
        self.risk_free_rate = risk_free_rate
        self.bars_per_year = bars_per_year
        self._factor_data: Optional[pd.DataFrame] = None
        self._downloader = KennethFrenchDataDownloader()

    @property
    def factor_data(self) -> Optional[pd.DataFrame]:
        """Get loaded factor data."""
        return self._factor_data

    @property
    def has_factor_data(self) -> bool:
        """Check if factor data is loaded."""
        return self._factor_data is not None and len(self._factor_data) > 0

    # ══════════════════════════════════════════════════════════════════
    # Data Loading
    # ══════════════════════════════════════════════════════════════════

    def load_factor_data(
        self,
        factor_df: pd.DataFrame,
        date_column: str = "Date",
    ) -> None:
        """Load factor data from a DataFrame.

        Expected columns: Mkt-RF, SMB, HML, RMW, CMA, RF
        Optional columns: UMD (momentum)

        Args:
            factor_df: DataFrame with factor returns.
            date_column: Name of the date column.
        """
        df = factor_df.copy()

        # Ensure date index
        if date_column in df.columns:
            df[date_column] = pd.to_datetime(df[date_column])
            df = df.set_index(date_column)

        # Convert percentage returns to decimal
        for col in df.columns:
            if df[col].dtype in (np.float64, np.int64, float, int):
                if df[col].abs().mean() > 0.1:  # Likely percentage
                    df[col] = df[col] / 100.0

        self._factor_data = df
        logger.info("Loaded factor data: %d rows, columns: %s", len(df), list(df.columns))

    def fetch_factor_data(
        self,
        n_factors: int = 5,
        frequency: str = "daily",
        include_momentum: bool = False,
    ) -> pd.DataFrame:
        """Fetch factor data from Kenneth French's data library.

        Downloads the Fama-French factor data from the Kenneth French
        Data Library and optionally merges momentum data.

        Args:
            n_factors: Number of factors (3 or 5).
            frequency: 'daily' or 'monthly'.
            include_momentum: Whether to include the UMD momentum factor.

        Returns:
            DataFrame with factor returns (decimal form).

        Raises:
            ConnectionError: If data cannot be fetched.
        """
        dataset = "3_factor" if n_factors == 3 else "5_factor"

        ff_data = self._downloader.download(dataset, frequency)

        if include_momentum:
            try:
                mom_data = self._downloader.download("momentum", frequency)
                # Align on common dates
                common_idx = ff_data.index.intersection(mom_data.index)
                if len(common_idx) > 0:
                    ff_data = ff_data.loc[common_idx].join(
                        mom_data.loc[common_idx], how="left"
                    )
                else:
                    logger.warning("No overlapping dates for momentum data")
            except Exception as e:
                logger.warning("Could not fetch momentum data: %s", e)

        self._factor_data = ff_data
        return ff_data

    # ══════════════════════════════════════════════════════════════════
    # Factor Regression
    # ══════════════════════════════════════════════════════════════════

    def regress(
        self,
        returns: pd.Series,
        factor_data: Optional[pd.DataFrame] = None,
        n_factors: int = 5,
        include_momentum: bool = False,
    ) -> FactorRegressionResult:
        """Run Fama-French factor regression.

        Regresses portfolio excess returns on factor returns:
            R_p - R_f = alpha + beta1*MktRF + beta2*SMB + beta3*HML
                      + beta4*RMW + beta5*CMA + [beta6*UMD] + epsilon

        Uses OLS regression via numpy: beta = (X'X)^(-1) X'y

        Args:
            returns: Series of portfolio returns.
            factor_data: Factor data DataFrame. Uses loaded data if None.
            n_factors: Number of factors (3 or 5).
            include_momentum: Include UMD momentum factor.

        Returns:
            FactorRegressionResult with all regression statistics.
        """
        ff_data = factor_data if factor_data is not None else self._factor_data

        if ff_data is None:
            return self._simple_regression(returns)

        # Determine factor names based on model type
        if n_factors == 3:
            factor_names = list(self.FACTOR_NAMES_3)
        elif n_factors == 5:
            factor_names = list(self.FACTOR_NAMES_5)
        else:
            factor_names = list(self.FACTOR_NAMES_5)

        if include_momentum:
            if "UMD" not in factor_names:
                factor_names.append("UMD")

        # Align dates
        common_idx = returns.index.intersection(ff_data.index)
        if len(common_idx) < 20:
            logger.warning(
                "Insufficient overlapping data: %d observations", len(common_idx)
            )
            return self._simple_regression(returns)

        port_ret = returns.reindex(common_idx).fillna(0.0)
        ff = ff_data.reindex(common_idx).fillna(0.0)

        # Get risk-free rate
        if "RF" in ff.columns:
            rf = ff["RF"]
        else:
            rf = pd.Series(self.risk_free_rate / self.bars_per_year, index=common_idx)

        # Excess returns: R_p - R_f
        excess_returns = port_ret - rf

        # Build factor matrix using only available factors
        available_factor_names: List[str] = []
        factor_cols: List[np.ndarray] = []

        for name in factor_names:
            if name in ff.columns:
                available_factor_names.append(name)
                factor_cols.append(ff[name].values)

        if not factor_cols:
            return self._simple_regression(returns)

        # Design matrix: [ones, factor1, factor2, ...]
        n = len(common_idx)
        X = np.column_stack([np.ones(n)] + factor_cols)
        y = excess_returns.values

        result = self._ols_regression(X, y, ["Alpha"] + available_factor_names)
        result.factor_names = available_factor_names

        return result

    def rolling_regression(
        self,
        returns: pd.Series,
        factor_data: Optional[pd.DataFrame] = None,
        window: int = 60,
        n_factors: int = 5,
        include_momentum: bool = False,
    ) -> pd.DataFrame:
        """Rolling factor exposure estimation.

        Runs factor regression on a rolling window to track how
        factor exposures change over time.

        Args:
            returns: Series of portfolio returns.
            factor_data: Factor data DataFrame.
            window: Rolling window size in bars.
            n_factors: Number of factors (3 or 5).
            include_momentum: Include momentum factor.

        Returns:
            DataFrame with rolling factor betas (index=timestamp, columns=factors).
        """
        ff_data = factor_data if factor_data is not None else self._factor_data

        if ff_data is None:
            logger.warning("No factor data available for rolling regression")
            return pd.DataFrame()

        common_idx = returns.index.intersection(ff_data.index)
        if len(common_idx) < window:
            logger.warning(
                "Insufficient data for rolling regression: %d < %d",
                len(common_idx), window,
            )
            return pd.DataFrame()

        port_ret = returns.reindex(common_idx)
        ff = ff_data.reindex(common_idx)

        # Get risk-free rate
        if "RF" in ff.columns:
            rf = ff["RF"]
        else:
            rf = pd.Series(self.risk_free_rate / self.bars_per_year, index=common_idx)

        excess_returns = port_ret - rf

        # Determine factor names
        if n_factors == 3:
            base_names = list(self.FACTOR_NAMES_3)
        else:
            base_names = list(self.FACTOR_NAMES_5)

        factor_names = [n for n in base_names if n in ff.columns]
        if include_momentum and "UMD" in ff.columns:
            factor_names.append("UMD")

        if not factor_names:
            return pd.DataFrame()

        # Rolling regression
        results: Dict[str, List[float]] = {f: [] for f in ["Alpha"] + factor_names}
        timestamps: List[pd.Timestamp] = []

        for i in range(window, len(common_idx)):
            window_excess = excess_returns.iloc[i - window : i].values
            window_factors = np.column_stack(
                [np.ones(window)]
                + [ff[name].iloc[i - window : i].values for name in factor_names]
            )

            try:
                betas = np.linalg.lstsq(window_factors, window_excess, rcond=None)[0]
                results["Alpha"].append(float(betas[0]))
                for j, name in enumerate(factor_names):
                    results[name].append(float(betas[j + 1]))
                timestamps.append(common_idx[i])
            except np.linalg.LinAlgError:
                continue

        if not timestamps:
            return pd.DataFrame()

        return pd.DataFrame(results, index=timestamps)

    # ══════════════════════════════════════════════════════════════════
    # Factor Attribution
    # ══════════════════════════════════════════════════════════════════

    def factor_attribution(
        self,
        returns: pd.Series,
        factor_data: Optional[pd.DataFrame] = None,
        n_factors: int = 5,
        include_momentum: bool = False,
    ) -> FactorAttribution:
        """Decompose returns into factor contributions.

        Runs the factor regression first, then decomposes the total
        return into contributions from each factor:

            R_p = alpha + sum(beta_i * mean(f_i)) + epsilon

        Total return = Alpha + Factor contributions + Specific return

        Args:
            returns: Series of portfolio returns.
            factor_data: Factor data DataFrame.
            n_factors: Number of factors (3 or 5).
            include_momentum: Include momentum factor.

        Returns:
            FactorAttribution with decomposition.
        """
        ff_data = factor_data if factor_data is not None else self._factor_data

        if ff_data is None:
            total_return = float(returns.mean()) * self.bars_per_year
            return FactorAttribution(
                total_return=round(total_return, 6),
                factor_return=0.0,
                specific_return=round(total_return, 6),
                alpha=round(total_return, 6),
                factor_contributions={},
            )

        # Run regression
        reg_result = self.regress(
            returns, factor_data=ff_data,
            n_factors=n_factors, include_momentum=include_momentum,
        )

        # Align dates for factor means
        common_idx = returns.index.intersection(ff_data.index)
        if len(common_idx) == 0:
            total_return = float(returns.mean()) * self.bars_per_year
            return FactorAttribution(
                total_return=round(total_return, 6),
                factor_return=0.0,
                specific_return=round(total_return, 6),
                alpha=round(total_return, 6),
                factor_contributions={},
            )

        ff_aligned = ff_data.reindex(common_idx)

        total_return = float(returns.reindex(common_idx).mean()) * self.bars_per_year

        alpha = reg_result.alphas[0].beta if reg_result.alphas else 0.0
        alpha_annual = alpha * self.bars_per_year

        # Factor contributions: beta_i * mean(f_i) * bars_per_year
        factor_contributions: Dict[str, float] = {}
        factor_return = 0.0

        for exposure in reg_result.exposures:
            if exposure.factor_name in ff_aligned.columns:
                factor_mean = float(ff_aligned[exposure.factor_name].mean())
            else:
                factor_mean = 0.0

            contribution = exposure.beta * factor_mean * self.bars_per_year
            factor_contributions[exposure.factor_name] = round(contribution, 6)
            factor_return += contribution

        specific_return = total_return - factor_return

        return FactorAttribution(
            total_return=round(total_return, 6),
            factor_return=round(factor_return, 6),
            specific_return=round(specific_return, 6),
            alpha=round(alpha_annual, 6),
            factor_contributions=factor_contributions,
        )

    # ══════════════════════════════════════════════════════════════════
    # Alpha Significance and Information Ratio
    # ══════════════════════════════════════════════════════════════════

    def alpha_significance(
        self,
        regression_result: FactorRegressionResult,
        confidence_level: float = 0.05,
    ) -> AlphaSignificance:
        """Test if alpha is statistically significant.

        Uses the t-statistic from the regression to test:
            H0: alpha = 0
            H1: alpha != 0

        Args:
            regression_result: Result from factor regression.
            confidence_level: Significance level (e.g., 0.05 for 5%).

        Returns:
            AlphaSignificance with test results.
        """
        if not regression_result.alphas:
            return AlphaSignificance(
                alpha=0.0,
                alpha_annual=0.0,
                t_stat=0.0,
                p_value=1.0,
                is_significant=False,
                confidence_level=confidence_level,
                information_ratio=0.0,
            )

        alpha_exp = regression_result.alphas[0]
        alpha_per_bar = alpha_exp.beta
        alpha_annual = alpha_per_bar * self.bars_per_year
        t_stat = alpha_exp.t_stat
        p_value = alpha_exp.p_value

        # Compute information ratio: alpha / residual volatility (annualized)
        residuals = regression_result.residuals
        if len(residuals) > 1 and np.std(residuals, ddof=1) > 1e-10:
            residual_vol = float(np.std(residuals, ddof=1)) * np.sqrt(self.bars_per_year)
            information_ratio = alpha_annual / residual_vol
        else:
            information_ratio = 0.0

        return AlphaSignificance(
            alpha=round(alpha_per_bar, 8),
            alpha_annual=round(alpha_annual, 6),
            t_stat=round(t_stat, 4),
            p_value=round(p_value, 6),
            is_significant=p_value < confidence_level,
            confidence_level=confidence_level,
            information_ratio=round(information_ratio, 4),
        )

    def information_ratio(
        self,
        regression_result: FactorRegressionResult,
    ) -> float:
        """Calculate the Information Ratio from factor regression.

        IR = alpha / residual_volatility (annualized)

        The information ratio measures the excess return per unit of
        idiosyncratic risk. A higher IR indicates better risk-adjusted
        performance relative to the factor model.

        Args:
            regression_result: Result from factor regression.

        Returns:
            Information ratio (annualized).
        """
        if not regression_result.alphas:
            return 0.0

        alpha_per_bar = regression_result.alphas[0].beta
        alpha_annual = alpha_per_bar * self.bars_per_year

        residuals = regression_result.residuals
        if len(residuals) > 1 and np.std(residuals, ddof=1) > 1e-10:
            residual_vol = float(np.std(residuals, ddof=1)) * np.sqrt(self.bars_per_year)
            return round(alpha_annual / residual_vol, 4)
        else:
            return 0.0

    # ══════════════════════════════════════════════════════════════════
    # Internal Methods
    # ══════════════════════════════════════════════════════════════════

    def _simple_regression(
        self,
        returns: pd.Series,
    ) -> FactorRegressionResult:
        """Simple market-model regression when factor data unavailable.

        Uses a single market factor estimated from the returns themselves.
        """
        n = len(returns)
        if n < 20:
            return FactorRegressionResult(
                alphas=[], exposures=[],
                r_squared=0.0, adj_r_squared=0.0,
                f_stat=0.0, f_pvalue=1.0,
                residuals=np.array([]), n_observations=n,
                factor_names=[],
            )

        # Use excess returns over risk-free rate
        rf_per_bar = self.risk_free_rate / self.bars_per_year
        excess = returns - rf_per_bar

        # Simple: just estimate alpha and residual
        alpha = float(excess.mean())
        residuals = excess.values - alpha
        std_err = float(np.std(residuals, ddof=1) / np.sqrt(n))
        t_stat = alpha / std_err if std_err > 1e-10 else 0.0
        p_value = 2 * (1 - sp_stats.t.cdf(abs(t_stat), df=n - 1))

        alpha_exposure = FactorExposure(
            factor_name="Alpha",
            beta=round(alpha, 6),
            t_stat=round(t_stat, 4),
            p_value=round(p_value, 6),
            std_error=round(std_err, 6),
        )

        return FactorRegressionResult(
            alphas=[alpha_exposure],
            exposures=[],
            r_squared=0.0,
            adj_r_squared=0.0,
            f_stat=t_stat ** 2,
            f_pvalue=p_value,
            residuals=residuals,
            n_observations=n,
            factor_names=[],
        )

    @staticmethod
    def _ols_regression(
        X: np.ndarray,
        y: np.ndarray,
        var_names: List[str],
    ) -> FactorRegressionResult:
        """OLS regression using numpy: beta = (X'X)^(-1) X'y.

        Computes:
        - Coefficients (betas): beta = (X'X)^(-1) X'y
        - Standard errors: se(beta_j) = sqrt(sigma^2 * [(X'X)^(-1)]_{jj})
        - t-statistics: t_j = beta_j / se(beta_j)
        - p-values: two-tailed t-test with n-k degrees of freedom
        - R-squared: 1 - RSS/TSS
        - Adjusted R-squared: 1 - (1 - R^2)(n-1)/(n-k)
        - F-statistic: ((TSS - RSS)/(k-1)) / (RSS/(n-k))

        Args:
            X: Design matrix (n x k) with intercept column.
            y: Dependent variable (n,).
            var_names: Names of variables (including intercept).

        Returns:
            FactorRegressionResult with all statistics.
        """
        n, k = X.shape

        # OLS: beta = (X'X)^(-1) X'y
        betas, _, rank, _ = np.linalg.lstsq(X, y, rcond=None)

        # Residuals: e = y - X*beta
        y_hat = X @ betas
        residuals = y - y_hat

        # Residual sum of squares: RSS = e'e
        rss = float(np.sum(residuals ** 2))

        # Total sum of squares: TSS = (y - y_bar)'(y - y_bar)
        tss = float(np.sum((y - np.mean(y)) ** 2))

        # R-squared: R^2 = 1 - RSS/TSS
        r_squared = 1 - rss / tss if tss > 0 else 0.0

        # Adjusted R-squared: 1 - (1-R^2)(n-1)/(n-k)
        adj_r_squared = 1 - (1 - r_squared) * (n - 1) / (n - k) if n > k else 0.0

        # Variance-covariance matrix: Var(beta) = sigma^2 * (X'X)^(-1)
        # sigma^2 = RSS / (n - k)
        sigma2 = rss / (n - k) if n > k else rss

        try:
            xtx_inv = np.linalg.inv(X.T @ X)
        except np.linalg.LinAlgError:
            xtx_inv = np.linalg.pinv(X.T @ X)

        var_betas = sigma2 * xtx_inv
        std_errors = np.sqrt(np.diag(var_betas))

        # t-statistics: t_j = beta_j / se(beta_j)
        t_stats = betas / std_errors

        # p-values (two-tailed): P(|T| > |t_j|)
        p_values = 2 * (1 - sp_stats.t.cdf(np.abs(t_stats), df=n - k))

        # F-statistic for overall significance
        if k > 1 and rss > 0:
            f_stat = ((tss - rss) / (k - 1)) / (rss / (n - k))
            f_pvalue = 1 - sp_stats.f.cdf(f_stat, k - 1, n - k)
        else:
            f_stat = 0.0
            f_pvalue = 1.0

        # Build exposure objects
        alphas: List[FactorExposure] = []
        exposures: List[FactorExposure] = []

        for i, name in enumerate(var_names):
            exposure = FactorExposure(
                factor_name=name,
                beta=round(float(betas[i]), 6),
                t_stat=round(float(t_stats[i]), 4),
                p_value=round(float(p_values[i]), 6),
                std_error=round(float(std_errors[i]), 6),
            )
            if name == "Alpha":
                alphas.append(exposure)
            else:
                exposures.append(exposure)

        return FactorRegressionResult(
            alphas=alphas,
            exposures=exposures,
            r_squared=round(float(r_squared), 6),
            adj_r_squared=round(float(adj_r_squared), 6),
            f_stat=round(float(f_stat), 4),
            f_pvalue=round(float(f_pvalue), 6),
            residuals=residuals,
            n_observations=n,
        )


# ══════════════════════════════════════════════════════════════════════
# Backward Compatibility Alias
# ══════════════════════════════════════════════════════════════════════

FamaFrenchModel = FF5FactorModel
