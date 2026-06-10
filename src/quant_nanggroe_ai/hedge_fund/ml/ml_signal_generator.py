"""
Machine Learning Signal Generator
Advanced ML models for generating trading signals.
Includes ensemble methods, neural networks, and feature engineering.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from enum import Enum
from abc import ABC, abstractmethod

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.ensemble import (
    RandomForestClassifier, 
    GradientBoostingClassifier,
    AdaBoostClassifier,
    VotingClassifier,
    StackingClassifier
)
from sklearn.linear_model import LogisticRegression, RidgeClassifier
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    classification_report, confusion_matrix, roc_auc_score
)
from sklearn.pipeline import Pipeline

logger = logging.getLogger(__name__)


class SignalDirection(Enum):
    """Signal directions"""
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


@dataclass
class MLSignal:
    """ML-generated trading signal"""
    signal: SignalDirection
    confidence: float  # 0-1
    probability_buy: float
    probability_sell: float
    model_name: str
    feature_importance: Dict[str, float]
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ModelPerformance:
    """Model performance metrics"""
    model_name: str
    accuracy: float
    precision: float
    recall: float
    f1: float
    roc_auc: float
    cv_scores: List[float]
    feature_importance: Dict[str, float]


class FeatureEngineer:
    """
    Feature engineering for ML models.
    Creates technical, statistical, and derived features.
    """
    
    def __init__(self, lookback_periods: List[int] = None):
        """
        Initialize feature engineer.
        
        Args:
            lookback_periods: Periods for feature calculation
        """
        self.lookback_periods = lookback_periods or [5, 10, 20, 50]
    
    def create_features(
        self,
        data: pd.DataFrame,
        include_price_features: bool = True,
        include_technical_features: bool = True,
        include_statistical_features: bool = True,
        include_volume_features: bool = True
    ) -> pd.DataFrame:
        """
        Create comprehensive feature set.
        
        Args:
            data: DataFrame with OHLCV data
            include_price_features: Include price-based features
            include_technical_features: Include technical indicators
            include_statistical_features: Include statistical features
            include_volume_features: Include volume-based features
            
        Returns:
            DataFrame with engineered features
        """
        df = data.copy()
        
        if include_price_features:
            df = self._add_price_features(df)
        
        if include_technical_features:
            df = self._add_technical_features(df)
        
        if include_statistical_features:
            df = self._add_statistical_features(df)
        
        if include_volume_features:
            df = self._add_volume_features(df)
        
        return df
    
    def _add_price_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add price-based features"""
        # Returns at multiple timeframes
        for period in self.lookback_periods:
            df[f'return_{period}d'] = df['close'].pct_change(period)
        
        # Price relative to moving averages
        for period in self.lookback_periods:
            sma = df['close'].rolling(period).mean()
            df[f'price_vs_sma_{period}'] = (df['close'] - sma) / sma
        
        # High-Low range
        df['hl_range'] = (df['high'] - df['low']) / df['low']
        df['hl_range_ma'] = df['hl_range'].rolling(20).mean()
        
        # Close position in range
        df['close_position'] = (df['close'] - df['low']) / (df['high'] - df['low'] + 1e-10)
        
        # Gap features
        df['gap'] = (df['open'] - df['close'].shift(1)) / df['close'].shift(1)
        
        return df
    
    def _add_technical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicator features"""
        # RSI
        for period in [7, 14, 21]:
            df[f'rsi_{period}'] = self._calculate_rsi(df['close'], period)
        
        # MACD
        ema_12 = df['close'].ewm(span=12).mean()
        ema_26 = df['close'].ewm(span=26).mean()
        macd = ema_12 - ema_26
        signal = macd.ewm(span=9).mean()
        df['macd'] = macd
        df['macd_signal'] = signal
        df['macd_histogram'] = macd - signal
        
        # Bollinger Bands
        for period in [20]:
            sma = df['close'].rolling(period).mean()
            std = df['close'].rolling(period).std()
            df[f'bb_upper_{period}'] = (sma + 2 * std - df['close']) / (4 * std + 1e-10)
            df[f'bb_lower_{period}'] = (df['close'] - (sma - 2 * std)) / (4 * std + 1e-10)
        
        # Stochastic
        for period in [14]:
            low = df['low'].rolling(period).min()
            high = df['high'].rolling(period).max()
            df[f'stoch_k_{period}'] = 100 * (df['close'] - low) / (high - low + 1e-10)
            df[f'stoch_d_{period}'] = df[f'stoch_k_{period}'].rolling(3).mean()
        
        # ATR
        df['atr'] = self._calculate_atr(df)
        df['atr_pct'] = df['atr'] / df['close']
        
        # ADX
        df['adx'] = self._calculate_adx(df)
        
        return df
    
    def _add_statistical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add statistical features"""
        for period in [10, 20, 50]:
            returns = df['close'].pct_change().rolling(period)
            
            df[f'skew_{period}d'] = returns.skew()
            df[f'kurtosis_{period}d'] = returns.kurt()
            df[f'volatility_{period}d'] = returns.std() * np.sqrt(252)
        
        # Rolling z-score
        for period in [20, 50]:
            mean = df['close'].rolling(period).mean()
            std = df['close'].rolling(period).std()
            df[f'zscore_{period}'] = (df['close'] - mean) / (std + 1e-10)
        
        # Momentum
        for period in [5, 10, 20]:
            df[f'momentum_{period}'] = df['close'] / df['close'].shift(period) - 1
        
        # Rate of change
        for period in [5, 10, 20]:
            df[f'roc_{period}'] = (df['close'] - df['close'].shift(period)) / df['close'].shift(period)
        
        return df
    
    def _add_volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add volume-based features"""
        if 'volume' not in df.columns:
            return df
        
        # Volume change
        df['volume_change'] = df['volume'].pct_change()
        
        # Volume moving average
        for period in [10, 20]:
            df[f'volume_ma_{period}'] = df['volume'].rolling(period).mean()
            df[f'volume_ratio_{period}'] = df['volume'] / df[f'volume_ma_{period}']
        
        # Volume and price divergence
        df['volume_price_corr'] = df['close'].rolling(10).corr(df['volume'])
        
        # On Balance Volume
        df['obv'] = (np.sign(df['close'].diff()) * df['volume']).cumsum()
        df['obv_ma'] = df['obv'].rolling(20).mean()
        
        return df
    
    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        """Calculate RSI"""
        delta = prices.diff()
        gain = delta.where(delta > 0, 0)
        loss = (-delta.where(delta < 0, 0))
        
        avg_gain = gain.rolling(period).mean()
        avg_loss = loss.rolling(period).mean()
        
        rs = avg_gain / (avg_loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate ATR"""
        tr1 = df['high'] - df['low']
        tr2 = abs(df['high'] - df['close'].shift(1))
        tr3 = abs(df['low'] - df['close'].shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        return tr.rolling(period).mean()
    
    def _calculate_adx(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate ADX"""
        high = df['high']
        low = df['low']
        close = df['close']
        
        plus_dm = high.diff()
        minus_dm = -low.diff()
        
        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)
        
        tr = self._calculate_atr(df)
        
        plus_di = 100 * (plus_dm.rolling(period).mean() / tr)
        minus_di = 100 * (minus_dm.rolling(period).mean() / tr)
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-10)
        return dx.rolling(period).mean()
    
    def create_lagged_features(
        self, 
        df: pd.DataFrame, 
        features: List[str], 
        lags: List[int] = [1, 2, 3, 5]
    ) -> pd.DataFrame:
        """Create lagged versions of features"""
        result = df.copy()
        
        for feature in features:
            for lag in lags:
                result[f'{feature}_lag{lag}'] = result[feature].shift(lag)
        
        return result
    
    def create_target(
        self,
        df: pd.DataFrame,
        forward_periods: int = 5,
        threshold: float = 0.02
    ) -> pd.Series:
        """
        Create target variable for classification.
        
        Args:
            df: DataFrame with close prices
            forward_periods: Number of periods to predict ahead
            threshold: Threshold for BUY/SELL classification
            
        Returns:
            Target series (1=BUY, 0=HOLD, -1=SELL)
        """
        future_return = df['close'].shift(-forward_periods) / df['close'] - 1
        
        target = pd.cut(
            future_return,
            bins=[-np.inf, -threshold, threshold, np.inf],
            labels=[-1, 0, 1]
        )
        
        target = target.astype(object)
        target[future_return.isna()] = np.nan
        target = pd.to_numeric(target, errors='coerce')
        target.name = 'target'  # Rename to avoid conflict with features
        
        return target


class MLTradingModel(ABC):
    """Abstract base class for ML trading models"""
    
    @abstractmethod
    def train(self, X: pd.DataFrame, y: pd.Series) -> ModelPerformance:
        pass
    
    @abstractmethod
    def predict(self, X: pd.DataFrame) -> MLSignal:
        pass


class RandomForestModel(MLTradingModel):
    """Random Forest classifier for trading signals"""
    
    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: int = 10,
        min_samples_split: int = 20,
        random_state: int = 42
    ):
        self.model = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            min_samples_split=min_samples_split,
            random_state=random_state,
            n_jobs=-1
        )
        self.scaler = StandardScaler()
        self.feature_names = None
        self.performance = None
    
    def train(
        self, 
        X: pd.DataFrame, 
        y: pd.Series,
        cv_folds: int = 5
    ) -> ModelPerformance:
        """Train the model"""
        self.feature_names = X.columns.tolist()
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Time series cross-validation
        tscv = TimeSeriesSplit(n_splits=cv_folds)
        
        # Train model
        self.model.fit(X_scaled, y)
        
        # Cross-validation scores
        cv_scores = cross_val_score(self.model, X_scaled, y, cv=tscv, scoring='accuracy')
        
        # Feature importance
        importance = dict(zip(self.feature_names, self.model.feature_importances_))
        
        # In-sample predictions
        y_pred = self.model.predict(X_scaled)
        
        self.performance = ModelPerformance(
            model_name="RandomForest",
            accuracy=accuracy_score(y, y_pred),
            precision=precision_score(y, y_pred, average='weighted', zero_division=0),
            recall=recall_score(y, y_pred, average='weighted', zero_division=0),
            f1=f1_score(y, y_pred, average='weighted', zero_division=0),
            roc_auc=roc_auc_score(y, self.model.predict_proba(X_scaled), multi_class='ovr'),
            cv_scores=cv_scores.tolist(),
            feature_importance=importance
        )
        
        return self.performance
    
    def predict(self, X: pd.DataFrame) -> MLSignal:
        """Generate trading signal"""
        if self.feature_names is None:
            raise ValueError("Model not trained yet")
        
        # Scale and reorder features
        X_scaled = self.scaler.transform(X[self.feature_names])
        
        # Get predictions and probabilities
        classes = self.model.classes_
        proba = self.model.predict_proba(X_scaled)[0]
        
        # Get prediction
        pred_idx = np.argmax(proba)
        prediction = classes[pred_idx]
        
        # Map to signal
        signal_map = {-1: SignalDirection.SELL, 0: SignalDirection.HOLD, 1: SignalDirection.BUY}
        signal = signal_map.get(prediction, SignalDirection.HOLD)
        
        # Confidence based on probability
        confidence = proba[pred_idx]
        
        # Get probability of buy/sell
        prob_buy = proba[list(classes).index(1)] if 1 in classes else 0
        prob_sell = proba[list(classes).index(-1)] if -1 in classes else 0
        
        return MLSignal(
            signal=signal,
            confidence=confidence,
            probability_buy=prob_buy,
            probability_sell=prob_sell,
            model_name="RandomForest",
            feature_importance=self.performance.feature_importance if self.performance else {}
        )


class GradientBoostingModel(MLTradingModel):
    """Gradient Boosting classifier"""
    
    def __init__(
        self,
        n_estimators: int = 100,
        max_depth: int = 5,
        learning_rate: float = 0.1,
        random_state: int = 42
    ):
        self.model = GradientBoostingClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            random_state=random_state
        )
        self.scaler = StandardScaler()
        self.feature_names = None
        self.performance = None
    
    def train(self, X: pd.DataFrame, y: pd.Series, cv_folds: int = 5) -> ModelPerformance:
        self.feature_names = X.columns.tolist()
        X_scaled = self.scaler.fit_transform(X)
        
        tscv = TimeSeriesSplit(n_splits=cv_folds)
        self.model.fit(X_scaled, y)
        
        cv_scores = cross_val_score(self.model, X_scaled, y, cv=tscv, scoring='accuracy')
        
        importance = dict(zip(self.feature_names, self.model.feature_importances_))
        y_pred = self.model.predict(X_scaled)
        
        self.performance = ModelPerformance(
            model_name="GradientBoosting",
            accuracy=accuracy_score(y, y_pred),
            precision=precision_score(y, y_pred, average='weighted', zero_division=0),
            recall=recall_score(y, y_pred, average='weighted', zero_division=0),
            f1=f1_score(y, y_pred, average='weighted', zero_division=0),
            roc_auc=roc_auc_score(y, self.model.predict_proba(X_scaled), multi_class='ovr'),
            cv_scores=cv_scores.tolist(),
            feature_importance=importance
        )
        
        return self.performance
    
    def predict(self, X: pd.DataFrame) -> MLSignal:
        if self.feature_names is None:
            raise ValueError("Model not trained yet")
        
        X_scaled = self.scaler.transform(X[self.feature_names])
        classes = self.model.classes_
        proba = self.model.predict_proba(X_scaled)[0]
        
        pred_idx = np.argmax(proba)
        prediction = classes[pred_idx]
        
        signal_map = {-1: SignalDirection.SELL, 0: SignalDirection.HOLD, 1: SignalDirection.BUY}
        signal = signal_map.get(prediction, SignalDirection.HOLD)
        
        prob_buy = proba[list(classes).index(1)] if 1 in classes else 0
        prob_sell = proba[list(classes).index(-1)] if -1 in classes else 0
        
        return MLSignal(
            signal=signal,
            confidence=proba[pred_idx],
            probability_buy=prob_buy,
            probability_sell=prob_sell,
            model_name="GradientBoosting",
            feature_importance=self.performance.feature_importance if self.performance else {}
        )


class EnsembleModel(MLTradingModel):
    """Ensemble of multiple ML models using voting"""
    
    def __init__(self):
        self.models = {
            'rf': RandomForestModel(),
            'gb': GradientBoostingModel(),
            'lr': LogisticRegression(max_iter=1000)
        }
        self.ensemble = None
        self.scaler = StandardScaler()
        self.feature_names = None
        self.performance = None
    
    def train(self, X: pd.DataFrame, y: pd.Series, cv_folds: int = 5) -> ModelPerformance:
        self.feature_names = X.columns.tolist()
        X_scaled = self.scaler.fit_transform(X)
        
        # Train individual models
        for name, model in self.models.items():
            if hasattr(model, 'train'):
                model.train(X, y)
        
        # Create voting ensemble
        self.ensemble = VotingClassifier(
            estimators=[
                ('rf', self.models['rf'].model),
                ('gb', self.models['gb'].model),
                ('lr', LogisticRegression(max_iter=1000))
            ],
            voting='soft'
        )
        
        self.ensemble.fit(X_scaled, y)
        
        y_pred = self.ensemble.predict(X_scaled)
        
        self.performance = ModelPerformance(
            model_name="Ensemble",
            accuracy=accuracy_score(y, y_pred),
            precision=precision_score(y, y_pred, average='weighted', zero_division=0),
            recall=recall_score(y, y_pred, average='weighted', zero_division=0),
            f1=f1_score(y, y_pred, average='weighted', zero_division=0),
            roc_auc=roc_auc_score(y, self.ensemble.predict_proba(X_scaled), multi_class='ovr'),
            cv_scores=[],
            feature_importance={}
        )
        
        return self.performance
    
    def predict(self, X: pd.DataFrame) -> MLSignal:
        if self.ensemble is None:
            raise ValueError("Model not trained yet")
        
        X_scaled = self.scaler.transform(X[self.feature_names])
        classes = self.ensemble.classes_
        proba = self.ensemble.predict_proba(X_scaled)[0]
        
        pred_idx = np.argmax(proba)
        prediction = classes[pred_idx]
        
        signal_map = {-1: SignalDirection.SELL, 0: SignalDirection.HOLD, 1: SignalDirection.BUY}
        signal = signal_map.get(prediction, SignalDirection.HOLD)
        
        prob_buy = proba[list(classes).index(1)] if 1 in classes else 0
        prob_sell = proba[list(classes).index(-1)] if -1 in classes else 0
        
        # Get average feature importance from base models
        importance = {}
        for name, model in self.models.items():
            if hasattr(model, 'performance') and model.performance:
                for k, v in model.performance.feature_importance.items():
                    importance[k] = importance.get(k, 0) + v / len(self.models)
        
        return MLSignal(
            signal=signal,
            confidence=proba[pred_idx],
            probability_buy=prob_buy,
            probability_sell=prob_sell,
            model_name="Ensemble",
            feature_importance=importance
        )


class MLPNeuralNetworkModel(MLTradingModel):
    """Multi-Layer Perceptron Neural Network"""
    
    def __init__(
        self,
        hidden_layer_sizes: Tuple[int] = (100, 50),
        max_iter: int = 500,
        random_state: int = 42
    ):
        self.model = MLPClassifier(
            hidden_layer_sizes=hidden_layer_sizes,
            max_iter=max_iter,
            random_state=random_state,
            early_stopping=True,
            validation_fraction=0.1
        )
        self.scaler = StandardScaler()
        self.feature_names = None
        self.performance = None
    
    def train(self, X: pd.DataFrame, y: pd.Series, cv_folds: int = 5) -> ModelPerformance:
        self.feature_names = X.columns.tolist()
        X_scaled = self.scaler.fit_transform(X)
        
        self.model.fit(X_scaled, y)
        
        y_pred = self.model.predict(X_scaled)
        
        self.performance = ModelPerformance(
            model_name="MLP",
            accuracy=accuracy_score(y, y_pred),
            precision=precision_score(y, y_pred, average='weighted', zero_division=0),
            recall=recall_score(y, y_pred, average='weighted', zero_division=0),
            f1=f1_score(y, y_pred, average='weighted', zero_division=0),
            roc_auc=roc_auc_score(y, self.model.predict_proba(X_scaled), multi_class='ovr'),
            cv_scores=[],
            feature_importance={}
        )
        
        return self.performance
    
    def predict(self, X: pd.DataFrame) -> MLSignal:
        if self.feature_names is None:
            raise ValueError("Model not trained yet")
        
        X_scaled = self.scaler.transform(X[self.feature_names])
        classes = self.model.classes_
        proba = self.model.predict_proba(X_scaled)[0]
        
        pred_idx = np.argmax(proba)
        prediction = classes[pred_idx]
        
        signal_map = {-1: SignalDirection.SELL, 0: SignalDirection.HOLD, 1: SignalDirection.BUY}
        signal = signal_map.get(prediction, SignalDirection.HOLD)
        
        prob_buy = proba[list(classes).index(1)] if 1 in classes else 0
        prob_sell = proba[list(classes).index(-1)] if -1 in classes else 0
        
        return MLSignal(
            signal=signal,
            confidence=proba[pred_idx],
            probability_buy=prob_buy,
            probability_sell=prob_sell,
            model_name="MLP",
            feature_importance={}
        )


class MLSignalGenerator:
    """
    ML Signal Generator combining multiple models.
    
    Features:
    - Automatic feature engineering
    - Multiple model support
    - Ensemble predictions
    - Model performance tracking
    """
    
    def __init__(self):
        self.feature_engineer = FeatureEngineer()
        self.models: Dict[str, MLTradingModel] = {}
        self.performance_history: List[ModelPerformance] = []
    
    def add_model(self, name: str, model: MLTradingModel):
        """Add a model to the generator"""
        self.models[name] = model
    
    def train_all_models(
        self,
        data: pd.DataFrame,
        target_period: int = 5,
        cv_folds: int = 5,
        min_samples: int = 100
    ) -> Dict[str, ModelPerformance]:
        """
        Train all models on the data.
        
        Args:
            data: OHLCV DataFrame
            target_period: Forward period for target
            cv_folds: Cross-validation folds
            min_samples: Minimum samples required
            
        Returns:
            Dict of model performances
        """
        # Create features
        features = self.feature_engineer.create_features(data)
        
        # Create target
        target = self.feature_engineer.create_target(data, target_period)
        
        # Drop NaN and insufficient samples
        combined = pd.concat([features, target], axis=1).dropna()
        if len(combined) < min_samples:
            logger.warning(f"Insufficient samples: {len(combined)} < {min_samples}")
            return {}
        
        X = combined.drop(columns=[target.name])
        y = combined[target.name]
        
        # Train models
        performances = {}
        for name, model in self.models.items():
            try:
                perf = model.train(X, y, cv_folds)
                performances[name] = perf
                self.performance_history.append(perf)
                logger.info(f"Model {name}: Accuracy={perf.accuracy:.3f}, F1={perf.f1:.3f}")
            except Exception as e:
                logger.error(f"Error training model {name}: {e}")
        
        return performances
    
    def generate_ensemble_signal(
        self,
        data: pd.DataFrame
    ) -> MLSignal:
        """
        Generate ensemble signal from all models.
        
        Args:
            data: Current OHLCV data
            
        Returns:
            Combined MLSignal
        """
        if not self.models:
            raise ValueError("No models trained")
        
        # Create features
        features = self.feature_engineer.create_features(data)
        X = features.tail(1)
        
        if X.isna().all().all():
            return MLSignal(
                signal=SignalDirection.HOLD,
                confidence=0.5,
                probability_buy=0.33,
                probability_sell=0.33,
                model_name="Ensemble",
                feature_importance={}
            )
        
        # Get signals from all models
        signals = []
        for name, model in self.models.items():
            try:
                signal = model.predict(X)
                signals.append(signal)
            except Exception as e:
                logger.warning(f"Error getting signal from {name}: {e}")
        
        if not signals:
            return MLSignal(
                signal=SignalDirection.HOLD,
                confidence=0.5,
                probability_buy=0.33,
                probability_sell=0.33,
                model_name="Ensemble",
                feature_importance={}
            )
        
        # Combine signals
        signal_scores = {
            SignalDirection.STRONG_BUY: 2,
            SignalDirection.BUY: 1,
            SignalDirection.HOLD: 0,
            SignalDirection.SELL: -1,
            SignalDirection.STRONG_SELL: -2
        }
        
        # Weighted average based on model performance
        total_confidence = 0
        weighted_score = 0
        avg_prob_buy = 0
        avg_prob_sell = 0
        
        for signal in signals:
            # Use confidence as weight
            weight = signal.confidence
            weighted_score += signal_scores.get(signal.signal, 0) * weight
            total_confidence += weight
            avg_prob_buy += signal.probability_buy * weight
            avg_prob_sell += signal.probability_sell * weight
        
        if total_confidence > 0:
            avg_score = weighted_score / total_confidence
            avg_prob_buy /= total_confidence
            avg_prob_sell /= total_confidence
        else:
            avg_score = 0
        
        # Map score to signal
        if avg_score >= 1.5:
            final_signal = SignalDirection.STRONG_BUY
        elif avg_score >= 0.5:
            final_signal = SignalDirection.BUY
        elif avg_score >= -0.5:
            final_signal = SignalDirection.HOLD
        elif avg_score >= -1.5:
            final_signal = SignalDirection.SELL
        else:
            final_signal = SignalDirection.STRONG_SELL
        
        # Combine feature importance
        importance = {}
        for signal in signals:
            for k, v in signal.feature_importance.items():
                importance[k] = importance.get(k, 0) + v / len(signals)
        
        return MLSignal(
            signal=final_signal,
            confidence=min(1.0, total_confidence / len(signals)),
            probability_buy=avg_prob_buy,
            probability_sell=avg_prob_sell,
            model_name="Ensemble",
            feature_importance=importance
        )
    
    def get_model_performances(self) -> List[ModelPerformance]:
        """Get all model performances"""
        return self.performance_history
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get aggregated feature importance across all models"""
        importance = {}
        count = 0
        
        for perf in self.performance_history:
            for k, v in perf.feature_importance.items():
                importance[k] = importance.get(k, 0) + v
                count += 1
        
        if count > 0:
            # Normalize
            total = sum(importance.values())
            importance = {k: v / total for k, v in importance.items()}
        
        return importance


# Example usage
if __name__ == "__main__":
    import pandas as pd
    import numpy as np
    
    # Generate sample data
    np.random.seed(42)
    dates = pd.date_range(start='2020-01-01', periods=1000, freq='D')
    
    data = pd.DataFrame({
        'open': 100 + np.cumsum(np.random.randn(1000) * 0.5),
        'high': 100 + np.cumsum(np.random.randn(1000) * 0.5) + np.random.rand(1000) * 2,
        'low': 100 + np.cumsum(np.random.randn(1000) * 0.5) - np.random.rand(1000) * 2,
        'close': 100 + np.cumsum(np.random.randn(1000) * 0.5),
        'volume': np.random.randint(1000000, 10000000, 1000)
    }, index=dates)
    
    # Initialize ML Signal Generator
    ml_generator = MLSignalGenerator()
    ml_generator.add_model('rf', RandomForestModel())
    ml_generator.add_model('gb', GradientBoostingModel())
    ml_generator.add_model('mlp', MLPNeuralNetworkModel())
    
    # Train all models
    print("Training ML Models...")
    performances = ml_generator.train_all_models(data, target_period=5)
    
    print("\nModel Performance Summary:")
    print("=" * 60)
    for name, perf in performances.items():
        print(f"{name:20} | Acc: {perf.accuracy:.3f} | F1: {perf.f1:.3f} | AUC: {perf.roc_auc:.3f}")
    
    # Generate ensemble signal
    print("\nGenerating Ensemble Signal...")
    signal = ml_generator.generate_ensemble_signal(data)
    
    print(f"\nEnsemble Signal:")
    print(f"  Signal: {signal.signal.value}")
    print(f"  Confidence: {signal.confidence:.2%}")
    print(f"  Probability Buy: {signal.probability_buy:.2%}")
    print(f"  Probability Sell: {signal.probability_sell:.2%}")
    
    # Feature importance
    print("\nTop 10 Features:")
    importance = ml_generator.get_feature_importance()
    sorted_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:10]
    for feature, imp in sorted_features:
        print(f"  {feature:30} {imp:.4f}")
