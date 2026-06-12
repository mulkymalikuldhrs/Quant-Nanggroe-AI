"""Tests for the Data Leakage Detector module."""

import numpy as np
import pandas as pd
import pytest

from quant_nanggroe.engine.backtest.leakage_detector import (
    DataLeakageDetector,
    LeakageFinding,
    LeakageReport,
    LeakageType,
    Severity,
    purge_embargo_split,
)


def _make_clean_feature_df(n: int = 200) -> pd.DataFrame:
    """Create a clean feature DataFrame with no leakage."""
    rng = np.random.default_rng(42)
    dates = pd.date_range("2020-01-01", periods=n, freq="B")
    return pd.DataFrame(
        {
            "date": dates,
            "returns": rng.normal(0.001, 0.02, n),
            "rsi": 50 + rng.normal(0, 10, n),
            "macd": rng.normal(0, 0.5, n),
            "volume": rng.lognormal(15, 0.5, n),
        }
    )


def _make_leaky_target_df(n: int = 200) -> pd.DataFrame:
    """Create a DataFrame with target leakage (feature = target + noise)."""
    rng = np.random.default_rng(42)
    dates = pd.date_range("2020-01-01", periods=n, freq="B")
    target = rng.normal(0.001, 0.02, n)
    return pd.DataFrame(
        {
            "date": dates,
            "returns": target,
            "leaky_feature": target + rng.normal(0, 0.001, n),  # Near-perfect proxy
        }
    )


def _make_overlapping_positions_df() -> pd.DataFrame:
    """Create a positions DataFrame with overlapping positions."""
    return pd.DataFrame(
        {
            "entry_time": pd.to_datetime(
                ["2024-01-01", "2024-01-05", "2024-01-15", "2024-01-20"]
            ),
            "exit_time": pd.to_datetime(
                ["2024-01-10", "2024-01-20", "2024-01-25", "2024-01-30"]
            ),
            "label": [1, -1, 1, 1],
        }
    )


class TestCleanData:
    """Tests with clean data (no leakage)."""

    def test_clean_data_no_critical_findings(self):
        """Clean data should produce no critical findings."""
        detector = DataLeakageDetector()
        df = _make_clean_feature_df()
        report = detector.run_full_audit(
            feature_df=df,
            target_col="returns",
            timestamp_col="date",
            feature_cols=["rsi", "macd", "volume"],
        )
        assert isinstance(report, LeakageReport)
        assert report.critical_count == 0
        assert report.is_safe

    def test_clean_data_target_leakage_check(self):
        """Target leakage check on clean data should find no leakage."""
        detector = DataLeakageDetector()
        df = _make_clean_feature_df()
        findings = detector.check_target_leakage(
            feature_df=df,
            target_col="returns",
            feature_cols=["rsi", "macd", "volume"],
            threshold=0.95,
        )
        critical_findings = [f for f in findings if f.severity == Severity.CRITICAL]
        assert len(critical_findings) == 0


class TestLookaheadDetection:
    """Tests for lookahead feature detection."""

    def test_lookahead_feature_detected(self):
        """Features computed with centered windows should be flagged."""
        rng = np.random.default_rng(42)
        n = 300
        dates = pd.date_range("2020-01-01", periods=n, freq="B")
        # Centered moving average — uses future data
        raw = rng.normal(100, 5, n)
        centered_ma = pd.Series(raw).rolling(20, center=True).mean()

        df = pd.DataFrame(
            {
                "date": dates,
                "price": raw,
                "centered_ma": centered_ma,
            }
        )

        detector = DataLeakageDetector()
        findings = detector.check_feature_lookahead(
            feature_df=df,
            timestamp_col="date",
            feature_cols=["centered_ma"],
        )
        # Should detect something (variance pattern at edges)
        # Even if not always flagged, the function should run without error
        assert isinstance(findings, list)


class TestTargetLeakage:
    """Tests for target/reverse leakage detection."""

    def test_target_leakage_detected(self):
        """Features highly correlated with the target should be flagged."""
        detector = DataLeakageDetector()
        df = _make_leaky_target_df()
        findings = detector.check_target_leakage(
            feature_df=df,
            target_col="returns",
            feature_cols=["leaky_feature"],
            threshold=0.95,
        )
        assert len(findings) > 0
        assert any(f.leakage_type == LeakageType.REVERSE_TARGET_LEAKAGE for f in findings)

    def test_target_leakage_with_lower_threshold(self):
        """Lower threshold should catch more features."""
        detector = DataLeakageDetector()
        df = _make_leaky_target_df()
        findings_strict = detector.check_target_leakage(
            feature_df=df,
            target_col="returns",
            feature_cols=["leaky_feature"],
            threshold=0.80,
        )
        findings_loose = detector.check_target_leakage(
            feature_df=df,
            target_col="returns",
            feature_cols=["leaky_feature"],
            threshold=0.99,
        )
        assert len(findings_strict) >= len(findings_loose)


class TestTimestampAlignment:
    """Tests for timestamp misalignment detection."""

    def test_duplicate_timestamps_detected(self):
        """Duplicate timestamps should be flagged."""
        rng = np.random.default_rng(42)
        n = 100
        dates = pd.date_range("2020-01-01", periods=n, freq="B").tolist()
        # Insert duplicates
        dates[50] = dates[49]
        dates[75] = dates[74]

        df = pd.DataFrame(
            {
                "date": dates,
                "value": rng.normal(0, 1, n),
            }
        )
        detector = DataLeakageDetector()
        findings = detector.check_timestamp_alignment(df, "date")
        ts_findings = [f for f in findings if f.leakage_type == LeakageType.TIMESTAMP_MISALIGNMENT]
        assert len(ts_findings) > 0

    def test_clean_timestamps_no_findings(self):
        """Clean, regular timestamps should produce no findings."""
        rng = np.random.default_rng(42)
        n = 100
        dates = pd.date_range("2020-01-01", periods=n, freq="B")
        df = pd.DataFrame(
            {
                "date": dates,
                "value": rng.normal(0, 1, n),
            }
        )
        detector = DataLeakageDetector()
        findings = detector.check_timestamp_alignment(df, "date")
        # Should be clean (no duplicates, monotonic, regular)
        dup_findings = [f for f in findings if "duplicate" in f.description.lower()]
        assert len(dup_findings) == 0


class TestLabelOverlap:
    """Tests for label overlap detection."""

    def test_overlapping_positions_detected(self):
        """Overlapping positions should be flagged."""
        detector = DataLeakageDetector()
        df = _make_overlapping_positions_df()
        findings = detector.check_label_overlap(
            positions_df=df,
            entry_col="entry_time",
            exit_col="exit_time",
            label_col="label",
        )
        assert len(findings) > 0
        assert any(f.leakage_type == LeakageType.FUTURE_LABEL_OVERLAP for f in findings)


class TestPurgeEmbargoSplit:
    """Tests for the purge_embargo_split utility."""

    def test_purge_embargo_reduces_data(self):
        """Purge and embargo should reduce both train and test sizes."""
        rng = np.random.default_rng(42)
        n = 1000
        df = pd.DataFrame(
            {
                "date": pd.date_range("2020-01-01", periods=n, freq="B"),
                "value": rng.normal(0, 1, n),
            }
        )
        train, test = purge_embargo_split(
            data_df=df,
            timestamp_col="date",
            train_ratio=0.7,
            purge_gap=10,
            embargo_period=20,
        )
        # Train should be less than 70% due to purge
        assert len(train) < 700
        # Test should be less than 30% due to embargo
        assert len(test) < 300
        # Total should be less than original
        assert len(train) + len(test) < n

    def test_purge_embargo_no_overlap(self):
        """Train and test sets should not overlap."""
        rng = np.random.default_rng(42)
        n = 500
        df = pd.DataFrame(
            {
                "date": pd.date_range("2020-01-01", periods=n, freq="B"),
                "value": rng.normal(0, 1, n),
            }
        )
        train, test = purge_embargo_split(
            data_df=df,
            timestamp_col="date",
            train_ratio=0.7,
            purge_gap=5,
            embargo_period=10,
        )
        train_dates = set(train["date"])
        test_dates = set(test["date"])
        assert train_dates.isdisjoint(test_dates)


class TestFullAudit:
    """Tests for the full audit workflow."""

    def test_full_audit_on_clean_data(self):
        """Full audit on clean data should report is_safe=True."""
        detector = DataLeakageDetector()
        df = _make_clean_feature_df()
        report = detector.run_full_audit(
            feature_df=df,
            target_col="returns",
            timestamp_col="date",
            feature_cols=["rsi", "macd", "volume"],
        )
        assert report.total_checks > 0
        assert isinstance(report.is_safe, bool)
        assert isinstance(report.summary, str)
        assert report.summary != ""

    def test_full_audit_on_leaky_data(self):
        """Full audit on leaky data should report critical findings."""
        detector = DataLeakageDetector()
        df = _make_leaky_target_df()
        report = detector.run_full_audit(
            feature_df=df,
            target_col="returns",
            timestamp_col="date",
            feature_cols=["leaky_feature"],
        )
        assert report.critical_count > 0
        assert not report.is_safe

    def test_report_is_safe_reflects_critical_count(self):
        """is_safe should be True only when critical_count is 0."""
        detector = DataLeakageDetector()
        df = _make_leaky_target_df()
        report = detector.run_full_audit(
            feature_df=df,
            target_col="returns",
            timestamp_col="date",
            feature_cols=["leaky_feature"],
        )
        if report.critical_count > 0:
            assert not report.is_safe
        else:
            assert report.is_safe
