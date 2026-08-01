"""Tests for autoencoder factor extraction."""

from __future__ import annotations

import numpy as np
import pytest

from engine.ml.autoencoder_factors import (
    AutoencoderConfig,
    AutoencoderFactorModel,
    FactorResult,
)


def _blobs(n_per: int = 40, dim: int = 12, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    centers = [rng.normal(scale=3.0, size=dim) for _ in range(3)]
    return np.vstack([c + rng.normal(scale=0.3, size=(n_per, dim)) for c in centers])


@pytest.fixture
def cfg() -> AutoencoderConfig:
    return AutoencoderConfig(
        input_dim=12, latent_dim=3, hidden_dims=(16, 8), epochs=60, n_clusters=3
    )


def test_shapes_and_roundtrip(cfg: AutoencoderConfig) -> None:
    X = _blobs()
    m = AutoencoderFactorModel(cfg)
    m.fit(X)
    z = m.encode(X)
    assert z.shape == (X.shape[0], cfg.latent_dim)


def test_training_reduces_error(cfg: AutoencoderConfig) -> None:
    X = _blobs()
    m = AutoencoderFactorModel(cfg)
    before = m.reconstruction_error(X)
    m.fit(X)
    assert m.reconstruction_error(X) < before


def test_extract_factors_clusters(cfg: AutoencoderConfig) -> None:
    X = _blobs()
    res = AutoencoderFactorModel(cfg).extract_factors(X)
    assert isinstance(res, FactorResult)
    assert res.cluster_labels is not None
    assert len(np.unique(res.cluster_labels)) == 3
    assert res.cluster_centers.shape == (3, cfg.latent_dim)
    assert res.reconstruction_error >= 0.0
    assert res.metadata["latent_dim"] == cfg.latent_dim


def test_determinism(cfg: AutoencoderConfig) -> None:
    X = _blobs()
    a = AutoencoderFactorModel(cfg).extract_factors(X)
    b = AutoencoderFactorModel(cfg).extract_factors(X)
    np.testing.assert_allclose(a.embeddings, b.embeddings, rtol=1e-5, atol=1e-6)


def test_bad_input_dim_raises(cfg: AutoencoderConfig) -> None:
    m = AutoencoderFactorModel(cfg)
    with pytest.raises(ValueError):
        m.fit(np.zeros((10, 5), dtype=np.float32))
