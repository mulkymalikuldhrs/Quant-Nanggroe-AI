# engine.ml.model_manager

## Class: 

Model lifecycle status.

*Line: 25*

---

## Class: 

Model registration info.

*Line: 35*

---

## Class: 

Result from model training.

*Line: 52*

---

## Class: 

Result from model inference.

*Line: 64*

---

## Class: 

Model Manager for ML models.

Features:
- Model registration with versioning
- Training pipeline with metrics
- Inference pipeline with latency tracking
- Model health monitoring
- Model persistence (save/load)

**Methods:** __init__, register_model, train_model, predict, get_model_info, list_models, list_trained_models, health_check, deprecate_model, get_training_history

*Line: 75*

---

## Function: 

*Line: 86*

---

## Function: 

Register a model.

Args:
    name: Unique model name.
    model: Model object (must have train/predict methods).
    version: Model version string.

Returns:
    ModelInfo for the registered model.

*Line: 92*

---

## Function: 

Train a registered model.

Args:
    name: Model name.
    X: Feature DataFrame.
    y: Target Series.

Returns:
    TrainingResult with metrics.

*Line: 113*

---

## Function: 

Run inference with a trained model.

Args:
    name: Model name.
    X: Feature DataFrame.

Returns:
    InferenceResult with predictions.

*Line: 193*

---

## Function: 

Get model information.

*Line: 253*

---

## Function: 

List all registered model names.

*Line: 257*

---

## Function: 

List all trained model names.

*Line: 261*

---

## Function: 

Check model health.

Returns a health report including:
- Model status
- Last training time
- Feature count
- Sample count
- Metrics

*Line: 268*

---

## Function: 

Mark a model as deprecated.

*Line: 297*

---

## Function: 

Get training history for all models.

*Line: 305*

---

