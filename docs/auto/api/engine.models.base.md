# engine.models.base

## Class: 

Result from a model prediction.

Attributes:
    signal: Trading signal (-1, 0, 1) or continuous score.
    confidence: Confidence score (0-1).
    probabilities: Optional class probabilities.
    features_used: List of features used in prediction.
    model_name: Name of the model that produced this prediction.

*Line: 17*

---

## Class: 

Abstract base class for all ML models.

Every model must implement:
- train(X, y): Train the model on features and labels
- predict(X): Generate predictions from features
- feature_importance(): Return feature importance scores

**Methods:** name, is_trained, train, predict, feature_importance, validate_input

*Line: 35*

---

## Function: 

Model name identifier.

*Line: 46*

---

## Function: 

Whether the model has been trained.

*Line: 52*

---

## Function: 

Train the model.

Args:
    X: Feature DataFrame.
    y: Target Series.
    validation_split: Fraction of data for validation.
    **kwargs: Additional training parameters.

Returns:
    Dict with training metrics.

*Line: 57*

---

## Function: 

Generate predictions from features.

Args:
    X: Feature DataFrame.

Returns:
    List of PredictionResult objects.

*Line: 78*

---

## Function: 

Return feature importance scores.

Returns:
    Dict mapping feature name -> importance score.

*Line: 90*

---

## Function: 

Validate input features.

Args:
    X: Feature DataFrame.

Raises:
    ValueError: If input is invalid.

*Line: 98*

---

