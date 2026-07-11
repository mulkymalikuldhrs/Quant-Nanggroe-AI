import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

logger = logging.getLogger(__name__)

try:
    from hmmlearn.hmm import GaussianHMM
    _HMM_AVAILABLE = True
except ImportError:
    _HMM_AVAILABLE = False
    GaussianHMM = None


class Regime(str, Enum):
    BULL = "BULL"
    BEAR = "BEAR"
    SIDEWAYS = "SIDEWAYS"
    CRISIS = "CRISIS"
    HIGH_VOL = "HIGH_VOL"
    LOW_VOL = "LOW_VOL"


class RegimeState(BaseModel):
    model_config = ConfigDict(frozen=False)
    regime: Regime = Regime.SIDEWAYS
    confidence: float = Field(default=0.0, ge=0.0)
    transition_probabilities: Dict[str, float] = Field(default_factory=dict)
    regime_index: int = Field(default=2, ge=0, le=3)
    method: str = "simple"
    features: Dict[str, Union[float, str]] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    result_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])

    @field_validator("confidence", mode="before")
    @classmethod
    def clamp_confidence(cls, v: Any) -> float:
        return max(0.0, min(1.0, float(v)))

    @model_validator(mode="after")
    def _auto_regime_index(self) -> "RegimeState":
        self.regime_index = _REGIME_INDEX.get(self.regime, 2)
        return self

    @property
    def is_stressed(self) -> bool:
        return self.regime in (Regime.BEAR, Regime.CRISIS)

    def to_api_dict(self) -> Dict[str, Any]:
        return {
            "regime": self.regime.value,
            "confidence": round(self.confidence, 4),
            "transition_probabilities": {k: round(v, 4) for k, v in self.transition_probabilities.items()},
            "regime_index": self.regime_index,
            "method": self.method,
            "features": {k: round(v, 6) if isinstance(v, float) else v for k, v in self.features.items()},
            "timestamp": self.timestamp.isoformat(),
            "result_id": self.result_id,
        }


_REGIME_ORDER = [Regime.BULL, Regime.SIDEWAYS, Regime.BEAR, Regime.CRISIS]
_REGIME_INDEX = {r: i for i, r in enumerate(_REGIME_ORDER)}


class HMMRegimeDetector:
    def __init__(
        self,
        n_regimes: int = 4,
        lookback: int = 252,
        volatility_window: int = 20,
        random_state: int = 42,
    ) -> None:
        self.n_regimes = n_regimes
        self.lookback = lookback
        self.volatility_window = volatility_window
        self.random_state = random_state
        self.hmm: Any = None
        self.is_fitted: bool = False
        self.use_hmm: bool = _HMM_AVAILABLE
        self._state_map: Dict[int, Regime] = {}
        self._last_transition_matrix: Optional[np.ndarray] = None
        self._features_cache: Optional[np.ndarray] = None

    def fit(
        self,
        returns: List[float],
        volumes: Optional[List[float]] = None,
    ) -> "HMMRegimeDetector":
        if len(returns) < max(50, self.lookback // 2):
            logger.warning("regime_detector_insufficient_data", extra={"n_points": len(returns)})
            self.is_fitted = False
            return self

        self._features_cache = self._build_features(returns, volumes)

        if not self.use_hmm or not _HMM_AVAILABLE:
            self.is_fitted = True
            return self

        try:
            self.hmm = GaussianHMM(
                n_components=self.n_regimes,
                covariance_type="full",
                n_iter=100,
                random_state=self.random_state,
                tol=1e-4,
            )
            self.hmm.fit(self._features_cache)
            self._build_state_map()
            self._last_transition_matrix = self.hmm.transmat_.copy()
            self.is_fitted = True
        except Exception:
            self.use_hmm = False
            self.is_fitted = True

        return self

    def predict(
        self,
        recent_returns: List[float],
        recent_volumes: Optional[List[float]] = None,
    ) -> RegimeState:
        if not self.is_fitted:
            if len(recent_returns) >= 50:
                self.fit(recent_returns, recent_volumes)
            else:
                return RegimeState(regime=Regime.SIDEWAYS, confidence=0.0, method="unfitted")

        if self.use_hmm and self.hmm is not None:
            return self._predict_hmm(recent_returns, recent_volumes)
        else:
            return self._compute_regime_simple(recent_returns, recent_volumes)

    def _predict_hmm(self, returns: List[float], volumes: Optional[List[float]] = None) -> RegimeState:
        features = self._build_features(returns, volumes)
        try:
            state_sequence = self.hmm.predict(features)
            posteriors = self.hmm.predict_proba(features)
            current_state_idx = int(state_sequence[-1])
            current_posterior = posteriors[-1]
            regime = self._state_map.get(current_state_idx, Regime.SIDEWAYS)
            confidence = float(np.max(current_posterior))
            trans_probs: Dict[str, float] = {}
            if self._last_transition_matrix is not None:
                for j in range(self.n_regimes):
                    target_regime = self._state_map.get(j, Regime.SIDEWAYS)
                    trans_probs[target_regime.value] = float(self._last_transition_matrix[current_state_idx, j])
            feature_summary = {
                "mean_return": float(np.mean(returns)),
                "volatility": float(np.std(returns)),
                "max_drawdown": float(min(0.0, min(np.cumsum(returns)))),
            }
            return RegimeState(
                regime=regime, confidence=min(1.0, confidence),
                transition_probabilities=trans_probs,
                regime_index=_REGIME_INDEX.get(regime, 2), method="hmm", features=feature_summary,
            )
        except Exception:
            return self._compute_regime_simple(returns, volumes)

    def _compute_regime_simple(self, returns: List[float], volumes: Optional[List[float]] = None) -> RegimeState:
        if len(returns) < 5:
            return RegimeState(regime=Regime.SIDEWAYS, confidence=0.0, method="simple")
        arr = np.array(returns)
        mean_return = float(np.mean(arr))
        volatility = float(np.std(arr))
        max_drawdown = float(min(0.0, min(np.cumsum(arr))))
        min_return = float(np.min(arr))
        adx = self._compute_adx_approx(returns)
        vol_ratio = 1.0
        if volumes and len(volumes) >= 10:
            recent_vol = np.mean(volumes[-5:])
            avg_vol = np.mean(volumes)
            if avg_vol > 0:
                vol_ratio = float(recent_vol / avg_vol)
        confidence = 0.5
        regime = Regime.SIDEWAYS
        if volatility > 0.03:
            if mean_return < -0.005:
                regime = Regime.BEAR
                confidence = 0.7 + min(0.2, abs(mean_return) * 10)
            else:
                regime = Regime.SIDEWAYS
                confidence = 0.5
        elif min_return < -0.05 or max_drawdown < -0.10:
            regime = Regime.CRISIS
            confidence = 0.85 + min(0.15, abs(min_return) * 2)
        elif mean_return > 0.002 and adx > 25:
            regime = Regime.BULL
            confidence = 0.6 + min(0.3, (adx - 25) / 50)
        elif mean_return < -0.002 and adx > 25:
            regime = Regime.BEAR
            confidence = 0.6 + min(0.3, (adx - 25) / 50)
        elif adx < 20 and abs(mean_return) < 0.002:
            regime = Regime.SIDEWAYS
            confidence = 0.6 + min(0.3, (20 - adx) / 20)
        elif mean_return > 0:
            regime = Regime.BULL
            confidence = 0.4
        else:
            regime = Regime.BEAR
            confidence = 0.4
        if vol_ratio > 1.5 and regime in (Regime.BULL, Regime.BEAR):
            confidence = min(0.95, confidence + 0.05)
        trans_probs = self._compute_simple_transitions(regime, mean_return, volatility, adx)
        return RegimeState(
            regime=regime, confidence=min(1.0, confidence),
            transition_probabilities=trans_probs,
            regime_index=_REGIME_INDEX.get(regime, 2), method="simple",
            features={"mean_return": mean_return, "volatility": volatility, "max_drawdown": max_drawdown,
                       "min_return": min_return, "adx_approx": adx, "volume_ratio": vol_ratio},
        )

    @staticmethod
    def _compute_adx_approx(returns: List[float]) -> float:
        if len(returns) < 3:
            return 0.0
        up_moves = sum(r for r in returns if r > 0)
        down_moves = sum(abs(r) for r in returns if r < 0)
        total = up_moves + down_moves
        if total == 0:
            return 0.0
        return min(100.0, abs(up_moves - down_moves) / total * 100)

    def _compute_simple_transitions(self, current: Regime, mean_return: float, volatility: float, adx: float) -> Dict[str, float]:
        base: Dict[Regime, Dict[Regime, float]] = {
            Regime.BULL: {Regime.BULL: 0.65, Regime.SIDEWAYS: 0.20, Regime.BEAR: 0.10, Regime.CRISIS: 0.05},
            Regime.BEAR: {Regime.BEAR: 0.55, Regime.SIDEWAYS: 0.20, Regime.BULL: 0.10, Regime.CRISIS: 0.15},
            Regime.SIDEWAYS: {Regime.SIDEWAYS: 0.50, Regime.BULL: 0.25, Regime.BEAR: 0.20, Regime.CRISIS: 0.05},
            Regime.CRISIS: {Regime.CRISIS: 0.30, Regime.BEAR: 0.35, Regime.SIDEWAYS: 0.25, Regime.BULL: 0.10},
        }
        probs = base.get(current, base[Regime.SIDEWAYS]).copy()
        if volatility > 0.03:
            probs[Regime.CRISIS] += 0.05
            probs[Regime.BEAR] += 0.05
            probs[Regime.SIDEWAYS] -= 0.05
            probs[Regime.BULL] -= 0.05
        if mean_return > 0.005:
            probs[Regime.BULL] += 0.05
            probs[Regime.BEAR] -= 0.05
        elif mean_return < -0.005:
            probs[Regime.BEAR] += 0.05
            probs[Regime.BULL] -= 0.05
        total = sum(probs.values())
        if total > 0:
            for k in probs:
                probs[k] = max(0.0, probs[k] / total)
        return {r.value: round(p, 4) for r, p in probs.items()}

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "is_fitted": self.is_fitted, "use_hmm": self.use_hmm,
            "n_regimes": self.n_regimes, "hmm_available": _HMM_AVAILABLE,
            "state_map": {k: v.value for k, v in self._state_map.items()},
        }

    @staticmethod
    def _compute_rolling_volatility(returns: List[float], window: int = 20) -> List[float]:
        if len(returns) < window:
            if not returns:
                return []
            return [float(np.std(returns))] * len(returns)
        arr = np.array(returns)
        vol = np.full(len(returns), np.nan)
        for i in range(window - 1, len(returns)):
            vol[i] = float(np.std(arr[i - window + 1: i + 1]))
        first_valid = vol[window - 1] if window - 1 < len(vol) else 0.0
        vol[:window - 1] = first_valid
        return vol.tolist()

    @staticmethod
    def _compute_volume_change(volumes: List[float]) -> List[float]:
        if len(volumes) < 2:
            return [0.0] * len(volumes)
        changes = [0.0]
        for i in range(1, len(volumes)):
            prev = volumes[i - 1]
            changes.append((volumes[i] - prev) / prev if prev > 0 else 0.0)
        return changes

    def _build_features(self, returns: List[float], volumes: Optional[List[float]] = None) -> np.ndarray:
        vol = self._compute_rolling_volatility(returns, self.volatility_window)
        vol_change = self._compute_volume_change(volumes) if volumes and len(volumes) == len(returns) else [0.0] * len(returns)
        features = np.column_stack([np.array(returns), np.array(vol), np.array(vol_change)])
        return np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)

    def _build_state_map(self) -> None:
        if self.hmm is None:
            return
        means = self.hmm.means_[:, 0]
        sorted_indices = np.argsort(-means)
        self._state_map = {}
        for rank, idx in enumerate(sorted_indices):
            if rank == 0:
                self._state_map[int(idx)] = Regime.BULL
            elif rank == 1:
                self._state_map[int(idx)] = Regime.SIDEWAYS
            elif rank == 2:
                self._state_map[int(idx)] = Regime.BEAR
            else:
                self._state_map[int(idx)] = Regime.CRISIS
