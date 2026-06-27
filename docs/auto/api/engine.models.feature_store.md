# engine.models.feature_store

## Class: 

Configuration for feature engineering.

Attributes:
    normalize: Whether to normalize features.
    fill_method: Method for filling NaN values ('ffill', 'bfill', 'zero', 'drop').
    lookback: Default lookback window for rolling features.
    include_returns: Whether to include return features.
    include_volume: Whether to include volume features.
    include_volatility: Whether to include volatility features.

*Line: 20*

---

## Class: 

Feature Store for ML Models.

Manages feature engineering, transformation, and storage.
Provides a centralized repository for features used by ML models.

Features:
- Configurable feature engineering pipeline
- Feature normalization (z-score, min-max)
- Feature caching for performance
- Feature selection and filtering
- Automatic lookahead prevention

**Methods:** __init__, engineer_features, add_transform, get_cached, prepare_training_data, _fill_nan, _normalize

*Line: 40*

---

## Function: 

*Line: 54*

---

## Function: 

Engineer features from OHLCV data.

Args:
    df: DataFrame with OHLCV columns.
    symbol: Optional symbol for caching.

Returns:
    DataFrame with engineered features.

*Line: 59*

---

## Function: 

Add a custom feature transform.

Args:
    name: Feature name.
    transform: Callable that takes a DataFrame and returns a Series.

*Line: 172*

---

## Function: 

Get cached features for a symbol.

Args:
    symbol: Trading symbol.

Returns:
    Cached feature DataFrame or None.

*Line: 181*

---

## Function: 

Prepare features and labels for model training.

Args:
    features: Feature DataFrame.
    forward_returns: Forward return series.
    lookahead_bars: Number of bars to look ahead for labels.

Returns:
    Tuple of (X, y) DataFrames with aligned indices.

*Line: 192*

---

## Function: 

Fill NaN values using configured method.

*Line: 223*

---

## Function: 

Z-score normalize features.

*Line: 237*

---

