# engine.models.ensemble

## Class: 

Simplified Random Forest using decision stumps.

Uses a collection of decision trees with random feature subsets
for ensemble prediction. Implementation is pure numpy/pandas
without sklearn dependency.

**Methods:** __init__, fit, predict_proba, _build_tree, _predict_tree

*Line: 28*

---

## Class: 

Simplified Gradient Boosting implementation.

Sequentially fits trees to the residuals of previous predictions.

**Methods:** __init__, fit, predict, _build_stump, _predict_tree

*Line: 134*

---

## Class: 

RF + GBM Ensemble Model.

Combines Random Forest and Gradient Boosting predictions
using confidence-weighted averaging.

**Methods:** __init__, name, is_trained, train, predict, feature_importance, _count_feature_usage

*Line: 209*

---

## Function: 

*Line: 36*

---

## Function: 

Fit the random forest.

*Line: 42*

---

## Function: 

Predict class probabilities.

*Line: 62*

---

## Function: 

Build a simple decision tree.

*Line: 68*

---

## Function: 

Predict using a single tree.

*Line: 115*

---

## Function: 

*Line: 140*

---

## Function: 

Fit gradient boosting model.

*Line: 148*

---

## Function: 

Generate predictions.

*Line: 161*

---

## Function: 

Build a single decision stump.

*Line: 168*

---

## Function: 

Predict using a single stump.

*Line: 202*

---

## Function: 

*Line: 216*

---

## Function: 

*Line: 234*

---

## Function: 

*Line: 238*

---

## Function: 

Train the ensemble model.

Args:
    X: Feature DataFrame.
    y: Target Series (forward returns or signals).
    validation_split: Fraction for validation.

Returns:
    Dict with training metrics.

*Line: 241*

---

## Function: 

Generate predictions with confidence scores.

Args:
    X: Feature DataFrame.

Returns:
    List of PredictionResult with signals and confidence.

*Line: 307*

---

## Function: 

Return feature importance from Random Forest.

*Line: 354*

---

## Function: 

Count how often a feature is used in a tree.

*Line: 373*

---

