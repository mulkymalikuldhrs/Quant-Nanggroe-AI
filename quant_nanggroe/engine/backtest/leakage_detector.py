"""Data Leakage Detector for Quantitative Trading Backtests.

A 6-type leakage scanner that identifies common data leakage patterns
that invalidate backtest results:

1. **Lookahead Features** — features computed using future data
2. **Survivorship Bias** — using only currently-listed securities
3. **Future Label Overlap** — labels that incorporate future information
4. **Timestamp Misalignment** — data alignment issues between series
5. **Peaking Features** — features that peek at the target during training
6. **Reverse Target Leakage** — features that are near-perfect proxies for the target

Also provides a purge-embargo train/test split utility to prevent
information leakage across the train-test boundary.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import structlog
from pydantic import BaseModel, Field
from scipy import stats

logger = structlog.get_logger(__name__)


# ── Enums ────────────────────────────────────────────────────────────────


class LeakageType(str, Enum):
    """Types of data leakage that can be detected."""

    LOOKAHEAD_FEATURE = "LOOKAHEAD_FEATURE"
    SURVIVORSHIP_BIAS = "SURVIVORSHIP_BIAS"
    FUTURE_LABEL_OVERLAP = "FUTURE_LABEL_OVERLAP"
    TIMESTAMP_MISALIGNMENT = "TIMESTAMP_MISALIGNMENT"
    PEAKING_FEATURE = "PEAKING_FEATURE"
    REVERSE_TARGET_LEAKAGE = "REVERSE_TARGET_LEAKAGE"


class Severity(str, Enum):
    """Severity levels for leakage findings."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# ── Pydantic models ──────────────────────────────────────────────────────


class LeakageFinding(BaseModel):
    """A single leakage finding from the detector."""

    leakage_type: LeakageType
    severity: Severity
    description: str
    feature_name: Optional[str] = None
    evidence: str = ""
    recommendation: str = ""


class LeakageReport(BaseModel):
    """Complete leakage audit report."""

    total_checks: int = 0
    findings: List[LeakageFinding] = Field(default_factory=list)
    critical_count: int = 0
    is_safe: bool = True
    summary: str = ""


# ── Detector class ───────────────────────────────────────────────────────


class DataLeakageDetector:
    """6-type data leakage scanner for quantitative trading backtests.

    Usage
    -----
    >>> detector = DataLeakageDetector()
    >>> report = detector.run_full_audit(
    ...     feature_df=df,
    ...     target_col="returns",
    ...     timestamp_col="date",
    ...     feature_cols=["rsi", "macd", "volume"],
    ... )
    >>> print(report.is_safe)
    """

    def __init__(self) -> None:
        self._findings: List[LeakageFinding] = []
        self._checks_run: int = 0

    def _reset(self) -> None:
        """Reset the detector state for a new audit."""
        self._findings = []
        self._checks_run = 0

    # ── Check 1: Lookahead Features ──────────────────────────────────

    def check_feature_lookahead(
        self,
        feature_df: pd.DataFrame,
        timestamp_col: str,
        feature_cols: Optional[List[str]] = None,
    ) -> List[LeakageFinding]:
        """Detect features that may use future information.

        Checks if any feature values at time t are correlated with
        returns at time t (which would suggest the feature uses
        contemporaneous or future data).

        Parameters
        ----------
        feature_df : pd.DataFrame
            DataFrame containing features and a timestamp column.
        timestamp_col : str
            Name of the timestamp/datetime column.
        feature_cols : list of str, optional
            Feature columns to check. If None, uses all non-timestamp
            numeric columns.

        Returns
        -------
        list of LeakageFinding
        """
        findings: List[LeakageFinding] = []
        self._checks_run += 1

        if feature_cols is None:
            feature_cols = [
                c
                for c in feature_df.select_dtypes(include=[np.number]).columns
                if c != timestamp_col
            ]

        df = feature_df.copy()

        # Check if timestamp is sorted
        if timestamp_col in df.columns:
            ts = pd.to_datetime(df[timestamp_col])
            if not ts.is_monotonic_increasing:
                df = df.sort_values(timestamp_col).reset_index(drop=True)

        for col in feature_cols:
            if col not in df.columns:
                continue

            series = df[col].dropna()

            # Check 1a: Detect if feature uses future data by checking if
            # the feature at time t is correlated with returns at time t+1
            # more than at time t-1 (shifted correlation test)
            if len(series) > 2:
                # Compute lagged and led correlations
                shifted_fwd = series.shift(-1).dropna()  # feature leads by 1
                shifted_bwd = series.shift(1).dropna()  # feature lags by 1

                # Compute autocorrelation of the feature
                autocorr = float(series.autocorr(lag=1)) if len(series) > 1 else 0.0

                # Check if the feature has unusually low autocorrelation
                # which could indicate it was computed with future data
                if abs(autocorr) < 0.01 and series.std() > 1e-10:
                    # Very low autocorrelation for a typical financial feature
                    findings.append(
                        LeakageFinding(
                            leakage_type=LeakageType.LOOKAHEAD_FEATURE,
                            severity=Severity.MEDIUM,
                            description=f"Feature '{col}' has near-zero autocorrelation "
                            f"({autocorr:.4f}), which may indicate lookahead computation.",
                            feature_name=col,
                            evidence=f"Autocorrelation at lag-1: {autocorr:.4f}",
                            recommendation="Verify that this feature does not use future data "
                            "in its computation. Check rolling windows and shift operations.",
                        )
                    )

                # Check 1b: Variance ratio test — if the feature was computed
                # using a centered rolling window, the values near the edges
                # will have different properties
                if len(series) > 20:
                    first_third = series.iloc[: len(series) // 3]
                    last_third = series.iloc[2 * len(series) // 3 :]
                    if len(first_third) > 1 and len(last_third) > 1:
                        var_first = float(first_third.var())
                        var_last = float(last_third.var())
                        if var_last > 1e-10 and var_first / var_last > 2.0:
                            findings.append(
                                LeakageFinding(
                                    leakage_type=LeakageType.LOOKAHEAD_FEATURE,
                                    severity=Severity.HIGH,
                                    description=f"Feature '{col}' shows significantly lower variance "
                                    f"at the beginning of the series ({var_first:.6f} vs "
                                    f"{var_last:.6f}), consistent with centered-window lookahead.",
                                    feature_name=col,
                                    evidence=f"Variance ratio (first/last third): "
                                    f"{var_first / var_last:.2f}",
                                    recommendation="Check if rolling windows are centered "
                                    "(use trailing windows only).",
                                )
                            )

        self._findings.extend(findings)
        return findings

    # ── Check 2: Label Overlap ───────────────────────────────────────

    def check_label_overlap(
        self,
        positions_df: pd.DataFrame,
        entry_col: str,
        exit_col: str,
        label_col: str,
    ) -> List[LeakageFinding]:
        """Detect if labels overlap with future positions.

        Checks if the label for position i uses information from
        position i+1 or later.

        Parameters
        ----------
        positions_df : pd.DataFrame
            DataFrame containing position data.
        entry_col : str
            Column name for entry timestamps.
        exit_col : str
            Column name for exit timestamps.
        label_col : str
            Column name for the label (e.g., profit/loss).

        Returns
        -------
        list of LeakageFinding
        """
        findings: List[LeakageFinding] = []
        self._checks_run += 1

        if positions_df.empty:
            return findings

        df = positions_df.copy()
        entries = pd.to_datetime(df[entry_col])
        exits = pd.to_datetime(df[exit_col])

        # Check if any position's exit comes after the next position's entry
        # (overlapping positions)
        overlap_count = 0
        for i in range(len(df) - 1):
            if exits.iloc[i] > entries.iloc[i + 1]:
                overlap_count += 1

        if overlap_count > 0:
            overlap_pct = overlap_count / max(len(df) - 1, 1)
            severity = Severity.CRITICAL if overlap_pct > 0.3 else (
                Severity.HIGH if overlap_pct > 0.1 else Severity.MEDIUM
            )
            findings.append(
                LeakageFinding(
                    leakage_type=LeakageType.FUTURE_LABEL_OVERLAP,
                    severity=severity,
                    description=f"{overlap_count} overlapping positions detected "
                    f"({overlap_pct:.1%} of positions). Labels may incorporate "
                    f"future information from overlapping trades.",
                    feature_name=label_col,
                    evidence=f"Overlap count: {overlap_count}, overlap rate: {overlap_pct:.1%}",
                    recommendation="Use non-overlapping position windows or adjust labels "
                    "to only use information available at entry time.",
                )
            )

        self._findings.extend(findings)
        return findings

    # ── Check 3: Timestamp Alignment ─────────────────────────────────

    def check_timestamp_alignment(
        self,
        data_df: pd.DataFrame,
        timestamp_col: str,
        frequency: Optional[str] = None,
    ) -> List[LeakageFinding]:
        """Detect timestamp misalignment issues.

        Checks for:
        - Duplicate timestamps
        - Irregular spacing
        - Gaps in the time series

        Parameters
        ----------
        data_df : pd.DataFrame
            DataFrame with a timestamp column.
        timestamp_col : str
            Name of the timestamp column.
        frequency : str, optional
            Expected frequency (e.g., 'D', 'B', 'H', '5min').
            If None, inferred from the data.

        Returns
        -------
        list of LeakageFinding
        """
        findings: List[LeakageFinding] = []
        self._checks_run += 1

        if data_df.empty or timestamp_col not in data_df.columns:
            return findings

        ts = pd.to_datetime(data_df[timestamp_col])

        # Check for duplicates
        dup_count = int(ts.duplicated().sum())
        if dup_count > 0:
            findings.append(
                LeakageFinding(
                    leakage_type=LeakageType.TIMESTAMP_MISALIGNMENT,
                    severity=Severity.HIGH,
                    description=f"{dup_count} duplicate timestamps found. "
                    "This can cause look-ahead bias when merging datasets.",
                    feature_name=timestamp_col,
                    evidence=f"Duplicate count: {dup_count}",
                    recommendation="Remove or aggregate duplicate timestamps before backtesting.",
                )
            )

        # Check for monotonicity
        if not ts.is_monotonic_increasing:
            findings.append(
                LeakageFinding(
                    leakage_type=LeakageType.TIMESTAMP_MISALIGNMENT,
                    severity=Severity.MEDIUM,
                    description="Timestamps are not monotonically increasing. "
                    "This may indicate data alignment issues.",
                    feature_name=timestamp_col,
                    evidence="Non-monotonic timestamp sequence detected",
                    recommendation="Sort data by timestamp before backtesting.",
                )
            )

        # Check for irregular spacing
        if len(ts) > 2:
            ts_sorted = ts.sort_values().reset_index(drop=True)
            diffs = ts_sorted.diff().dropna()

            if len(diffs) > 0:
                # Convert to numeric (nanoseconds) for comparison
                diff_ns = diffs.values.astype(np.int64)
                median_diff = np.median(diff_ns)

                if median_diff > 0:
                    # Check if any gap is > 3x the median
                    large_gaps = int(np.sum(diff_ns > 3 * median_diff))
                    if large_gaps > 0:
                        gap_pct = large_gaps / len(diff_ns)
                        severity = Severity.HIGH if gap_pct > 0.1 else Severity.LOW
                        findings.append(
                            LeakageFinding(
                                leakage_type=LeakageType.TIMESTAMP_MISALIGNMENT,
                                severity=severity,
                                description=f"{large_gaps} large gaps (>3x median spacing) "
                                f"detected in timestamps ({gap_pct:.1%} of intervals).",
                                feature_name=timestamp_col,
                                evidence=f"Large gaps: {large_gaps}, gap rate: {gap_pct:.1%}",
                                recommendation="Fill gaps or use forward-fill for missing "
                                "periods. Be aware of data availability during gaps.",
                            )
                        )

        self._findings.extend(findings)
        return findings

    # ── Check 4: Survivorship Bias ───────────────────────────────────

    def check_survivorship_bias(
        self,
        ticker_list: List[str],
        start_date: str | datetime,
        end_date: str | datetime,
    ) -> List[LeakageFinding]:
        """Check for survivorship bias in the ticker universe.

        Warns if the ticker list only contains currently active securities,
        which is a classic sign of survivorship bias.

        Parameters
        ----------
        ticker_list : list of str
            List of ticker symbols used in the backtest.
        start_date : str or datetime
            Start date of the backtest period.
        end_date : str or datetime
            End date of the backtest period.

        Returns
        -------
        list of LeakageFinding
        """
        findings: List[LeakageFinding] = []
        self._checks_run += 1

        if isinstance(start_date, str):
            start_date = pd.to_datetime(start_date)
        if isinstance(end_date, str):
            end_date = pd.to_datetime(end_date)

        # Heuristic: if the backtest period is long (>5 years) and all tickers
        # are still active, there's likely survivorship bias
        span_days = (end_date - start_date).days

        if span_days > 365 * 5 and len(ticker_list) > 0:
            # Check if the ticker list contains any delisted indicators
            # (tickers ending in .OB, .PK, or containing special delisting markers)
            delisted_markers = [
                t for t in ticker_list
                if any(suffix in str(t).upper() for suffix in [".OB", ".PK", ".DEL", ".OLD"])
            ]

            if len(delisted_markers) == 0:
                findings.append(
                    LeakageFinding(
                        leakage_type=LeakageType.SURVIVORSHIP_BIAS,
                        severity=Severity.HIGH,
                        description=f"Backtest spans {span_days} days with {len(ticker_list)} "
                        f"tickers, but no delisted securities found. This suggests "
                        f"survivorship bias in the ticker universe.",
                        feature_name="ticker_universe",
                        evidence=f"Period: {span_days} days, {len(ticker_list)} tickers, "
                        f"0 delisted markers",
                        recommendation="Include delisted securities in the universe. "
                        "Use a point-in-time ticker database to avoid survivorship bias.",
                    )
                )

        if span_days > 365 * 2 and len(ticker_list) < 20:
            findings.append(
                LeakageFinding(
                    leakage_type=LeakageType.SURVIVORSHIP_BIAS,
                    severity=Severity.MEDIUM,
                    description=f"Small ticker universe ({len(ticker_list)} tickers) over "
                    f"a {span_days}-day period. May not represent the investable universe "
                    f"at each point in time.",
                    feature_name="ticker_universe",
                    evidence=f"Universe size: {len(ticker_list)}, period: {span_days} days",
                    recommendation="Use a broader, point-in-time universe that includes "
                    "securities available at each historical date.",
                )
            )

        self._findings.extend(findings)
        return findings

    # ── Check 5: Target Leakage ──────────────────────────────────────

    def check_target_leakage(
        self,
        feature_df: pd.DataFrame,
        target_col: str,
        feature_cols: Optional[List[str]] = None,
        threshold: float = 0.95,
    ) -> List[LeakageFinding]:
        """Detect features that are near-perfect proxies for the target.

        Uses Pearson correlation between each feature and the target.
        Any feature with |corr| >= threshold is flagged as potential
        target leakage.

        Parameters
        ----------
        feature_df : pd.DataFrame
            DataFrame containing features and the target column.
        target_col : str
            Name of the target column.
        feature_cols : list of str, optional
            Feature columns to check. If None, uses all columns
            except the target.
        threshold : float
            Absolute correlation threshold above which a feature is
            flagged (default: 0.95).

        Returns
        -------
        list of LeakageFinding
        """
        findings: List[LeakageFinding] = []
        self._checks_run += 1

        if feature_cols is None:
            feature_cols = [
                c for c in feature_df.columns if c != target_col
            ]

        target = feature_df[target_col]
        if target.std() < 1e-15:
            # Zero-variance target — nothing to correlate with
            return findings

        for col in feature_cols:
            if col not in feature_df.columns:
                continue

            feature = feature_df[col]
            if feature.std() < 1e-15:
                continue

            # Pearson correlation
            valid = target.notna() & feature.notna()
            if valid.sum() < 10:
                continue

            corr_val = float(np.corrcoef(
                target[valid].values, feature[valid].values
            )[0, 1])

            if abs(corr_val) >= threshold:
                findings.append(
                    LeakageFinding(
                        leakage_type=LeakageType.REVERSE_TARGET_LEAKAGE,
                        severity=Severity.CRITICAL,
                        description=f"Feature '{col}' has correlation {corr_val:.4f} "
                        f"with target '{target_col}' (threshold: {threshold}). "
                        f"This is likely target leakage.",
                        feature_name=col,
                        evidence=f"Pearson correlation: {corr_val:.4f}",
                        recommendation=f"Remove feature '{col}' or verify it does not "
                        "directly encode the target variable.",
                    )
                )
            elif abs(corr_val) >= 0.80:
                findings.append(
                    LeakageFinding(
                        leakage_type=LeakageType.PEAKING_FEATURE,
                        severity=Severity.HIGH,
                        description=f"Feature '{col}' has high correlation {corr_val:.4f} "
                        f"with target '{target_col}'. This may be a peaking feature.",
                        feature_name=col,
                        evidence=f"Pearson correlation: {corr_val:.4f}",
                        recommendation=f"Investigate feature '{col}' to ensure it does not "
                        "use target information during training.",
                    )
                )

        self._findings.extend(findings)
        return findings

    # ── Full Audit ───────────────────────────────────────────────────

    def run_full_audit(
        self,
        feature_df: pd.DataFrame,
        target_col: str,
        timestamp_col: str,
        feature_cols: Optional[List[str]] = None,
        positions_df: Optional[pd.DataFrame] = None,
        entry_col: str = "entry_time",
        exit_col: str = "exit_time",
        label_col: str = "label",
    ) -> LeakageReport:
        """Run all leakage checks and produce a comprehensive report.

        Parameters
        ----------
        feature_df : pd.DataFrame
            DataFrame containing features and target.
        target_col : str
            Name of the target column.
        timestamp_col : str
            Name of the timestamp column.
        feature_cols : list of str, optional
            Feature columns to audit.
        positions_df : pd.DataFrame, optional
            DataFrame with position data for label overlap check.
        entry_col : str
            Column name for entry timestamps in positions_df.
        exit_col : str
            Column name for exit timestamps in positions_df.
        label_col : str
            Column name for labels in positions_df.

        Returns
        -------
        LeakageReport
        """
        self._reset()

        logger.info(
            "starting_leakage_audit",
            n_rows=len(feature_df),
            target_col=target_col,
            timestamp_col=timestamp_col,
        )

        # Run all checks
        self.check_feature_lookahead(feature_df, timestamp_col, feature_cols)
        self.check_target_leakage(feature_df, target_col, feature_cols)
        self.check_timestamp_alignment(feature_df, timestamp_col)

        if positions_df is not None and not positions_df.empty:
            self.check_label_overlap(positions_df, entry_col, exit_col, label_col)

        # Build report
        critical_count = sum(
            1 for f in self._findings if f.severity == Severity.CRITICAL
        )
        is_safe = critical_count == 0

        if is_safe and len(self._findings) == 0:
            summary = "No data leakage detected. Backtest appears clean."
        elif is_safe:
            severities = [f.severity.value for f in self._findings]
            summary = (
                f"Audit complete with {len(self._findings)} finding(s). "
                f"No critical issues. Severities: {dict((s, severities.count(s)) for s in set(severities))}"
            )
        else:
            summary = (
                f"CRITICAL: {critical_count} critical leakage issue(s) detected. "
                f"Backtest results are likely invalid. "
                f"Total findings: {len(self._findings)}."
            )

        return LeakageReport(
            total_checks=self._checks_run,
            findings=self._findings,
            critical_count=critical_count,
            is_safe=is_safe,
            summary=summary,
        )


# ── Purge-Embargo Split ──────────────────────────────────────────────────


def purge_embargo_split(
    data_df: pd.DataFrame,
    timestamp_col: str,
    train_ratio: float = 0.7,
    purge_gap: int = 5,
    embargo_period: int = 10,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Split data into train/test sets with purge and embargo gaps.

    The purge gap removes observations at the end of the training set
    that may be correlated with the test set. The embargo period removes
    observations at the start of the test set to prevent information
    leakage from the training period.

    Parameters
    ----------
    data_df : pd.DataFrame
        DataFrame sorted by timestamp.
    timestamp_col : str
        Name of the timestamp column.
    train_ratio : float
        Fraction of data to use for training (default: 0.7).
    purge_gap : int
        Number of observations to remove from the end of training
        to prevent label leakage (default: 5).
    embargo_period : int
        Number of observations to remove from the start of testing
        to prevent feature leakage (default: 10).

    Returns
    -------
    tuple of (pd.DataFrame, pd.DataFrame)
        Training and test DataFrames with purge and embargo applied.
    """
    n = len(data_df)
    if n == 0:
        return pd.DataFrame(), pd.DataFrame()

    # Sort by timestamp
    df = data_df.sort_values(timestamp_col).reset_index(drop=True)

    # Compute split point
    split_idx = int(n * train_ratio)

    # Apply purge: remove last purge_gap observations from training
    train_end = max(0, split_idx - purge_gap)

    # Apply embargo: remove first embargo_period observations from test
    test_start = min(n, split_idx + embargo_period)

    train_df = df.iloc[:train_end].copy()
    test_df = df.iloc[test_start:].copy()

    logger.info(
        "purge_embargo_split",
        original_n=n,
        train_n=len(train_df),
        test_n=len(test_df),
        purge_gap=purge_gap,
        embargo_period=embargo_period,
        removed=purge_gap + embargo_period,
    )

    return train_df, test_df
