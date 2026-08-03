"""Unit tests for the 4 new archive-upgrade modules (goal #15, roadmap C4/C8/QS12/QS18).

Pure-pandas/numpy tests; no network, no heavy deps, no Polars required.
"""
import numpy as np
import pandas as pd
import pytest


# ---- downside_deviation ----
from quant_nanggroe.engine.risk.downside_deviation import downside_deviation, sortino_ratio

def _rets(n=100, seed=1):
    rng = np.random.default_rng(seed)
    return pd.Series(rng.normal(0.001, 0.02, n))

def test_downside_deviation_nonneg():
    r = _rets()
    dd = downside_deviation(r)
    assert dd >= 0.0

def test_downside_deviation_zero_when_all_above_mar():
    r = pd.Series([0.01, 0.02, 0.03])
    assert downside_deviation(r, mar=0.0) == 0.0

def test_sortino_no_div_zero():
    r = pd.Series([0.01, 0.01, 0.01])  # no downside
    assert sortino_ratio(r) == 0.0


# ---- data quality ----
from quant_nanggroe.engine.data.quality import assess, check_ohlc_sanity, check_staleness, check_gaps

def _ohlc(n=50, seed=2):
    rng = np.random.default_rng(seed)
    close = 100 + np.cumsum(rng.normal(0, 1, n))
    high = close + np.abs(rng.normal(0, 0.5, n))
    low = close - np.abs(rng.normal(0, 0.5, n))
    df = pd.DataFrame({
        "open": np.clip(close + rng.normal(0, 0.1, n), low, high),  # keep open in [low, high]
        "high": np.maximum.reduce([high, close]),
        "low": np.minimum.reduce([low, close]),
        "close": close,
        "volume": np.abs(rng.normal(1000, 100, n)),
        "timestamp": np.arange(int(1.7e9), int(1.7e9) + n),
    })
    return df

def test_quality_clean_ok():
    df = _ohlc()
    now_ts = float(df["timestamp"].iloc[-1]) + 1  # fresh relative to last bar
    rep = assess(df, "TEST", now_ts=now_ts)
    assert rep.ok is True
    assert "ohlc_sane" in rep.checks

def test_quality_detects_negative_price():
    df = _ohlc()
    df.loc[0, "close"] = -5.0
    rep = check_ohlc_sanity(df, "TEST")
    assert rep.ok is False
    assert any("non-positive" in w for w in rep.warnings)

def test_quality_staleness_flag():
    df = _ohlc()
    df["timestamp"] = df["timestamp"] - 10**7  # very old
    rep = check_staleness(df, "TEST", now_ts=float(pd.Timestamp.utcnow().timestamp()), max_age_seconds=86_400)
    assert rep.ok is False


# ---- feature_engine ----
from quant_nanggroe.engine.factors.feature_engine import generate_features, feature_names, rsi

def test_generate_features_columns():
    df = generate_features(_ohlc(), use_polars=False)
    for col in feature_names():
        assert col in df.columns

def test_rsi_bounds():
    r = rsi(pd.Series(np.linspace(1, 2, 60)))
    assert r.dropna().between(0, 100).all()


# ---- alerting ----
from quant_nanggroe.engine.alerting import AlertManager, AlertLevel, build_telegram_transport

def test_alert_manager_levels():
    sent = []
    mgr = AlertManager(transport=lambda a: sent.append(a))
    mgr.critical("boom")
    mgr.warning("careful")
    mgr.info("note")
    assert len(sent) == 3
    assert sent[0].level == AlertLevel.CRITICAL

def test_telegram_transport_import_safe():
    # token not installed -> transport must not raise at build time
    t = build_telegram_transport("FAKE", "FAKE")
    # calling with missing telegram dep should fall back to log, not crash
    t.__call__  # just ensure callable
