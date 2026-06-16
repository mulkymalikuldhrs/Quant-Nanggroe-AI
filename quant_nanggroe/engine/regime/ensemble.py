import logging
from typing import Any, Dict, List
from quant_nanggroe.engine.regime.hmm_detector import RegimeState, Regime

logger = logging.getLogger(__name__)

_WEIGHTS = {
    "hmm": 0.35,
    "volatility": 0.25,
    "macro": 0.20,
    "correlation": 0.20,
}


class RegimeEnsemble:
    def __init__(self, detectors: List[Any]):
        self.detectors = detectors
        self.weights = _WEIGHTS.copy()

    def predict(self, **kwargs: Any) -> RegimeState:
        votes: Dict[Regime, float] = {}
        feature_accum: Dict[str, float] = {}
        methods_used: List[str] = []
        total_weight = 0.0

        for detector in self.detectors:
            name = detector.__class__.__name__.replace("RegimeDetector", "").lower()
            if not name:
                name = detector.__class__.__name__.lower()
            weight = self.weights.get(name, 0.15)

            try:
                detector_kwargs = self._extract_kwargs(detector, kwargs)
                result = detector.predict(**kwargs)
                if result and isinstance(result, RegimeState):
                    r = result.regime
                    votes[r] = votes.get(r, 0.0) + weight * result.confidence
                    feature_accum.update(result.features)
                    methods_used.append(f"{result.method}:{r.value}")
                    total_weight += weight
            except Exception:
                continue

        if not votes:
            return RegimeState(regime=Regime.SIDEWAYS, confidence=0.0, method="ensemble_empty")

        best_regime = max(votes, key=votes.get)
        ensemble_confidence = min(1.0, votes[best_regime] / max(total_weight, 0.01))

        return RegimeState(
            regime=best_regime, confidence=ensemble_confidence,
            method="ensemble", features={**feature_accum, "methods_used": ",".join(methods_used)},
        )

    @staticmethod
    def _extract_kwargs(detector: Any, all_kwargs: Dict) -> Dict:
        import inspect
        sig = inspect.signature(detector.predict)
        return {k: v for k, v in all_kwargs.items() if k in sig.parameters}
