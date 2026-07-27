"""
XGBoost Alpha Strategy
======================
ML-driven return prediction using engineered features:
- Momentum features (1d, 5d, 10d, 20d, 60d returns)
- Volatility features (5d, 20d, 60d rolling vol)
- Volume features (volume ratio, volume MA)
- Price features (price vs MA, range position)

Fits in ~512MB RAM on Termux with restricted feature set.
"""

import logging
from typing import Dict, List, Optional

import numpy as np

log = logging.getLogger("QNA.XGBoost")


class XGBoostAlpha:
    def __init__(self, model_path: Optional[str] = None):
        self.model = None
        self.model_path = model_path
        self.feature_names = [
            "ret_1d", "ret_5d", "ret_10d", "ret_20d", "ret_60d",
            "vol_5d", "vol_20d", "vol_60d",
            "price_vs_ma10", "price_vs_ma50",
            "range_pos_20d",
        ]
        self.is_trained = False

    def _engineer_features(self, closes: np.ndarray,
                           highs: np.ndarray, lows: np.ndarray,
                           volumes: np.ndarray) -> np.ndarray:
        n = len(closes)
        if n < 60:
            return np.zeros((n, len(self.feature_names)))

        rets = np.diff(closes) / (closes[:-1] + 1e-10)

        features = []
        for i in range(n):
            f = np.zeros(len(self.feature_names))
            if i < 1:
                features.append(f)
                continue
            c = closes[:i + 1]
            r = rets[:i]
            h = highs[:i + 1]
            lo = lows[:i + 1]
            v = volumes[:i + 1]

            f[0] = r[-1] if len(r) >= 1 else 0
            f[1] = np.sum(r[-5:]) if len(r) >= 5 else 0
            f[2] = np.sum(r[-10:]) if len(r) >= 10 else 0
            f[3] = np.sum(r[-20:]) if len(r) >= 20 else 0
            f[4] = np.sum(r[-60:]) if len(r) >= 60 else 0

            f[5] = np.std(r[-5:]) if len(r) >= 5 else 0
            f[6] = np.std(r[-20:]) if len(r) >= 20 else 0
            f[7] = np.std(r[-60:]) if len(r) >= 60 else 0

            f[8] = (c[-1] - np.mean(c[-10:])) / (np.std(c[-10:]) + 1e-10) if len(c) >= 10 else 0
            f[9] = (c[-1] - np.mean(c[-50:])) / (np.std(c[-50:]) + 1e-10) if len(c) >= 50 else 0

            hi_20 = np.max(h[-20:]) if len(h) >= 20 else h[-1]
            lo_20 = np.min(lo[-20:]) if len(lo) >= 20 else lo[-1]
            f[10] = (c[-1] - lo_20) / (hi_20 - lo_20 + 1e-10)

            features.append(f)
        return np.array(features)

    def train(self, closes: np.ndarray, highs: np.ndarray,
              lows: np.ndarray, volumes: np.ndarray):
        try:
            import xgboost as xgb
        except ImportError:
            log.warning("xgboost not installed, skipping ML training")
            return

        n = len(closes)
        if n < 120:
            return

        X = self._engineer_features(closes, highs, lows, volumes)
        rets = np.diff(closes) / (closes[:-1] + 1e-10)
        y = np.concatenate([rets, [0]])  # align lengths

        train_n = int(n * 0.7)
        X_train, y_train = X[60:train_n], y[60:train_n]
        X_test = X[train_n:-1]
        y_test = y[train_n:-1]

        if len(X_train) < 10:
            return

        self.model = xgb.XGBRegressor(
            n_estimators=50, max_depth=3, learning_rate=0.1,
            subsample=0.8, colsample_bytree=0.8, random_state=42,
        )
        self.model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)
        self.is_trained = True
        log.info(f"XGBoost trained: {len(X_train)} train, {len(X_test)} test samples")

    def predict(self, closes: List[float], highs: List[float],
                lows: List[float], volumes: List[float]) -> Dict:
        arr_c = np.array(closes, dtype=np.float64)
        arr_h = np.array(highs, dtype=np.float64)
        arr_l = np.array(lows, dtype=np.float64)
        arr_v = np.array(volumes, dtype=np.float64)

        X = self._engineer_features(arr_c, arr_h, arr_l, arr_v)
        if len(X) == 0:
            return {"signal": "hold", "confidence": 0.0, "prediction": 0.0}

        last_features = X[-1:]

        if self.model is not None and self.is_trained:
            pred = float(self.model.predict(last_features)[0])
        else:
            pred = 0.0

        sig = "buy" if pred > 0.001 else ("sell" if pred < -0.001 else "hold")
        return {
            "signal": sig,
            "confidence": round(min(abs(pred) * 100, 1.0), 3),
            "prediction": round(pred * 100, 4),
            "trained": self.is_trained,
        }

    def __repr__(self):
        return f"XGBoostAlpha(trained={self.is_trained})"
