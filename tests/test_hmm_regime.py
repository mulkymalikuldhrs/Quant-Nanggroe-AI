"""Tests for HMM regime detection upgrade."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from quant_nanggroe.engine.regime.hmm_regime import (
    HMMRegimeDetector,
    REGIME_LABELS,
    RegimeDetectionResult,
    _coerce_probabilities,
    _decode,
    build_features,
    regime_probabilities_from_context,
)


@pytest.fixture()
def stable_regime_df():
    """Stable daily history: 300 bars across 6 observables."""
    np.random.seed(0)
    idx = pd.date_range("2024-01-01", periods=300, freq="B")
    df = pd.DataFrame(
        {
            "DXY": np.linspace(102, 107, 300) + np.random.normal(0, 0.3, 300),
            "ZB1": np.linspace(117, 122, 300) + np.random.normal(0, 0.25, 300),
            "VIX": np.clip(np.random.normal(16, 3, 300), 8, None),
            "GC1": np.linspace(1950, 2100, 300) + np.random.normal(0, 8, 300),
            "ES1": np.linspace(4800, 5200, 300) + np.random.normal(0, 40, 300),
            "NQ1": np.linspace(17000, 18500, 300) + np.random.normal(0, 120, 300),
        },
        index=idx,
    )
    return df


def test_regime_labels_constant():
    assert REGIME_LABELS == ["RISK_ON", "RISK_OFF", "STAGFLATION", "LIQUIDITY_CRISIS"]


def test_hmm_detector_returns_four_probs(stable_regime_df):
    feat = build_features(stable_regime_df)
    det = HMMRegimeDetector(window=252, seed=7, use_hmmlearn=True)
    result = det.fit_predict(feat, current_row=feat.iloc[-1])
    assert isinstance(result, RegimeDetectionResult)
    assert set(result.probabilities.keys()) == set(REGIME_LABELS)
    assert abs(sum(result.probabilities.values()) - 1.0) < 1e-3
    assert 0.0 <= result.confidence <= 1.0
    assert result.dominant_state() in REGIME_LABELS


def test_hmm_detector_uses_four_states(stable_regime_df):
    feat = build_features(stable_regime_df)
    det = HMMRegimeDetector(window=252, seed=13, use_hmmlearn=False)  # GMM fallback
    result = det.fit_predict(feat, current_row=feat.iloc[-1])
    assert len(result.probabilities) == 4
    assert abs(sum(result.probabilities.values()) - 1.0) < 1e-3


def test_gmm_backend_produces_argmax_regime(stable_regime_df):
    feat = build_features(stable_regime_df)
    det = HMMRegimeDetector(window=252, seed=1, use_hmmlearn=False)
    result = det.fit_predict(feat, current_row=feat.iloc[-1])
    probs = np.array([result.probabilities[k] for k in REGIME_LABELS])
    assert result.label == REGIME_LABELS[int(np.argmax(probs))]


def test_small_data_falls_back_to_neutral():
    small = pd.DataFrame(
        {
            "DXY": np.linspace(100, 103, 5),
            "ZB1": np.linspace(115, 119, 5),
            "VIX": np.full(5, 18.0),
            "GC1": np.linspace(1950, 1970, 5),
            "ES1": np.linspace(4800, 4850, 5),
            "NQ1": np.linspace(17000, 17200, 5),
        }
    )
    det = HMMRegimeDetector(window=252, seed=0, use_hmmlearn=True)
    result = det.fit_predict(small, current_row=small.iloc[-1])
    assert result.label == "NEUTRAL"
    assert result.confidence == 0.0
    assert len(result.probabilities) == 4


def test_empty_dataframe_returns_neutral():
    empty = pd.DataFrame(columns=REGIME_LABELS)
    det = HMMRegimeDetector(window=252, seed=0, use_hmmlearn=True)
    result = det.fit_predict(empty, current_row=None)
    assert result.label == "NEUTRAL"
    assert result.confidence == 0.0


def test_build_features_shape(stable_regime_df):
    feat = build_features(stable_regime_df)
    assert not feat.empty
    assert "ret_DXY" in feat.columns and "level_VIX" in feat.columns
    assert feat.shape[1] >= 6


def test_coerce_probabilities_normalizes():
    probs = _coerce_probabilities(np.array([0.2, 0.3, 0.1, 0.05]), n_states=4)
    assert abs(probs.sum() - 1.0) < 1e-9
    assert probs.shape == (4,)


def test_coerce_probabilities_handles_zeros():
    probs = _coerce_probabilities(np.zeros(4), n_states=4)
    assert abs(probs.sum() - 1.0) < 1e-9
    assert np.allclose(probs, 0.25)


def test_decode_returns_label_and_confidence():
    label, confidence = _decode(np.array([0.12, 0.55, 0.18, 0.15]))
    assert label == "RISK_OFF"
    assert abs(confidence - 0.55) < 1e-9


def test_regime_probabilities_from_context_liquidity_crisis():
    probs = regime_probabilities_from_context(
        dxy_change_pct=0.5, bond_zb_change_pct=0.5, vix_level=40.0
    )
    assert probs["LIQUIDITY_CRISIS"] >= 0.3
    assert abs(sum(probs.values()) - 1.0) < 1e-6


def test_regime_probabilities_from_context_risk_on():
    probs = regime_probabilities_from_context(
        dxy_change_pct=-0.6, bond_zb_change_pct=-0.3, vix_level=14.0
    )
    assert probs["RISK_ON"] >= 0.5
    assert abs(sum(probs.values()) - 1.0) < 1e-6
