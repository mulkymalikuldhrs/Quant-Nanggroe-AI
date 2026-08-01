"""Autoencoder Factors — Unsupervised latent factor extraction for assets.

Learns a low-dimensional latent representation of asset feature vectors
(returns, volatility, cross-sectional features) using a symmetric
autoencoder, then clusters the learned embeddings to discover latent
"factor groups" (regimes / style clusters).

Architecture
------------
- Encoder: MLP  input_dim -> hidden_dims -> latent_dim  (ReLU, optional dropout)
- Decoder: MLP  latent_dim -> reversed(hidden_dims) -> input_dim
- Loss: MSE reconstruction
- Embeddings: encoder(latent) outputs, optionally clustered via KMeans
  into factor groups.

Falls back gracefully if torch / sklearn are unavailable.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

logger = logging.getLogger(__name__)

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset

    _TORCH_AVAILABLE = True
except Exception:  # pragma: no cover
    torch = None  # type: ignore
    nn = None  # type: ignore
    DataLoader = None  # type: ignore
    TensorDataset = None  # type: ignore
    _TORCH_AVAILABLE = False

try:
    from sklearn.cluster import KMeans

    _SKLEARN_AVAILABLE = True
except Exception:  # pragma: no cover
    KMeans = None  # type: ignore
    _SKLEARN_AVAILABLE = False


@dataclass
class AutoencoderConfig:
    """Configuration for the autoencoder factor model."""

    input_dim: int
    latent_dim: int = 8
    hidden_dims: Sequence[int] = (64, 32)
    dropout: float = 0.0
    learning_rate: float = 1e-3
    weight_decay: float = 0.0
    epochs: int = 100
    batch_size: int = 64
    n_clusters: int = 4
    seed: int = 42
    device: str = "cpu"


@dataclass
class FactorResult:
    """Result of embedding + clustering."""

    embeddings: np.ndarray
    cluster_labels: Optional[np.ndarray] = None
    reconstruction_error: float = 0.0
    cluster_centers: Optional[np.ndarray] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


if _TORCH_AVAILABLE:

    def _build_mlp(dims: Sequence[int], dropout: float) -> "nn.Sequential":
        """Build an MLP with ReLU activations between successive Linear layers.

        No activation is applied after the final layer.
        """
        layers: List[nn.Module] = []
        for i in range(len(dims) - 1):
            layers.append(nn.Linear(dims[i], dims[i + 1]))
            if i < len(dims) - 2:
                layers.append(nn.ReLU())
                if dropout > 0:
                    layers.append(nn.Dropout(dropout))
        return nn.Sequential(*layers)

    class Autoencoder(nn.Module):
        """Symmetric feed-forward autoencoder."""

        def __init__(self, config: AutoencoderConfig) -> None:
            super().__init__()
            self.config = config
            hidden = list(config.hidden_dims)

            enc_dims = [config.input_dim, *hidden, config.latent_dim]
            dec_dims = [config.latent_dim, *reversed(hidden), config.input_dim]

            self.encoder = _build_mlp(enc_dims, config.dropout)
            self.decoder = _build_mlp(dec_dims, config.dropout)

        def encode(self, x: "torch.Tensor") -> "torch.Tensor":
            return self.encoder(x)

        def decode(self, z: "torch.Tensor") -> "torch.Tensor":
            return self.decoder(z)

        def forward(self, x: "torch.Tensor") -> Tuple["torch.Tensor", "torch.Tensor"]:
            z = self.encode(x)
            recon = self.decode(z)
            return recon, z


class AutoencoderFactorModel:
    """High-level trainer / embedder for autoencoder-based factor extraction."""

    def __init__(self, config: AutoencoderConfig) -> None:
        if not _TORCH_AVAILABLE:
            raise RuntimeError("torch is required for AutoencoderFactorModel")
        self.config = config
        torch.manual_seed(config.seed)
        np.random.seed(config.seed)
        self.device = torch.device(config.device)
        self.model = Autoencoder(config).to(self.device)
        self._fitted = False

    def _to_tensor(self, X: np.ndarray) -> "torch.Tensor":
        return torch.as_tensor(np.asarray(X, dtype=np.float32), device=self.device)

    def fit(self, X: np.ndarray) -> Dict[str, float]:
        """Train the autoencoder on feature matrix X (n_samples, input_dim)."""
        X = np.asarray(X, dtype=np.float32)
        if X.ndim != 2 or X.shape[1] != self.config.input_dim:
            raise ValueError(
                f"X must be (n, {self.config.input_dim}); got {X.shape}"
            )

        dataset = TensorDataset(self._to_tensor(X))
        loader = DataLoader(
            dataset,
            batch_size=min(self.config.batch_size, len(dataset)),
            shuffle=True,
        )

        optimizer = torch.optim.Adam(
            self.model.parameters(),
            lr=self.config.learning_rate,
            weight_decay=self.config.weight_decay,
        )
        loss_fn = nn.MSELoss()

        self.model.train()
        last_loss = 0.0
        for epoch in range(self.config.epochs):
            epoch_loss = 0.0
            for (batch,) in loader:
                optimizer.zero_grad()
                recon, _ = self.model(batch)
                loss = loss_fn(recon, batch)
                loss.backward()
                optimizer.step()
                epoch_loss += float(loss.item()) * batch.size(0)
            last_loss = epoch_loss / len(dataset)
            if epoch % max(1, self.config.epochs // 10) == 0:
                logger.debug("epoch %d recon_mse=%.6f", epoch, last_loss)

        self._fitted = True
        return {"reconstruction_error": last_loss, "epochs": float(self.config.epochs)}

    def encode(self, X: np.ndarray) -> np.ndarray:
        """Return latent embeddings for X."""
        self.model.eval()
        with torch.no_grad():
            z = self.model.encode(self._to_tensor(np.asarray(X, dtype=np.float32)))
        return z.cpu().numpy()

    def reconstruction_error(self, X: np.ndarray) -> float:
        """Mean squared reconstruction error over X."""
        self.model.eval()
        with torch.no_grad():
            t = self._to_tensor(np.asarray(X, dtype=np.float32))
            recon, _ = self.model(t)
            err = torch.mean((recon - t) ** 2)
        return float(err.item())

    def cluster_embeddings(
        self, embeddings: np.ndarray, n_clusters: Optional[int] = None
    ) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """Cluster embeddings into factor groups via KMeans.

        Returns (labels, centers) or (None, None) if sklearn is unavailable.
        """
        if not _SKLEARN_AVAILABLE:
            logger.warning("sklearn unavailable; skipping clustering")
            return None, None
        k = n_clusters or self.config.n_clusters
        k = min(k, len(embeddings))
        if k < 1:
            return None, None
        km = KMeans(n_clusters=k, random_state=self.config.seed, n_init=10)
        labels = km.fit_predict(embeddings)
        return labels, km.cluster_centers_

    def extract_factors(
        self, X: np.ndarray, n_clusters: Optional[int] = None
    ) -> FactorResult:
        """Full pipeline: encode X, cluster embeddings, report reconstruction."""
        if not self._fitted:
            self.fit(X)
        embeddings = self.encode(X)
        labels, centers = self.cluster_embeddings(embeddings, n_clusters)
        recon_err = self.reconstruction_error(X)
        return FactorResult(
            embeddings=embeddings,
            cluster_labels=labels,
            cluster_centers=centers,
            reconstruction_error=recon_err,
            metadata={
                "latent_dim": self.config.latent_dim,
                "n_samples": int(X.shape[0]),
                "input_dim": self.config.input_dim,
            },
        )


__all__ = [
    "AutoencoderConfig",
    "FactorResult",
    "AutoencoderFactorModel",
]
