# engine.ml.feature_engineer

## Class: 

Feature categories.

*Line: 20*

---

## Class: 

Configuration for feature engineering.

*Line: 32*

---

## Class: 

Feature Engineer for ML models.

Creates comprehensive feature sets from OHLCV data and optional
fundamental/sentiment/macro data sources.

Features:
- Technical features from factor library
- Fundamental features
- Sentiment features
- Macro features
- Feature selection and importance
- Custom transform pipeline

**Methods:** __init__, engineer_features, add_transform, select_features, set_feature_importance, get_feature_importance, create_target, _add_technical_features, _add_volume_features, _add_statistical_features, _add_fundamental_features, _add_sentiment_features, _add_macro_features, _fill_nan, _normalize

*Line: 46*

---

## Function: 

*Line: 61*

---

## Function: 

Engineer features from OHLCV data and optional sources.

Args:
    df: DataFrame with OHLCV columns.
    fundamental_data: Optional fundamental data dict.
    sentiment_data: Optional sentiment data dict.
    macro_data: Optional macro data dict.

Returns:
    DataFrame with engineered features.

*Line: 66*

---

## Function: 

Add a custom feature transform.

*Line: 120*

---

## Function: 

Select top features by importance.

Args:
    features: Feature DataFrame.
    target: Optional target series for correlation-based selection.
    top_k: Number of features to select.
    method: 'variance', 'correlation', or 'importance'.

Returns:
    DataFrame with selected features.

*Line: 124*

---

## Function: 

Set feature importance scores (from model training).

*Line: 163*

---

## Function: 

Get feature importance scores.

*Line: 167*

---

## Function: 

Create target variable for classification.

Args:
    df: DataFrame with close prices.
    forward_periods: Number of periods to predict ahead.
    threshold: Threshold for BUY/SELL classification.

Returns:
    Target series (1=BUY, 0=HOLD, -1=SELL).

*Line: 171*

---

## Function: 

Add technical indicator features.

*Line: 200*

---

## Function: 

Add volume-based features.

*Line: 238*

---

## Function: 

Add statistical features.

*Line: 256*

---

## Function: 

Add fundamental features.

*Line: 279*

---

## Function: 

Add sentiment features.

*Line: 288*

---

## Function: 

Add macro features.

*Line: 297*

---

## Function: 

Fill NaN values.

*Line: 306*

---

## Function: 

Z-score normalize features.

*Line: 320*

---

