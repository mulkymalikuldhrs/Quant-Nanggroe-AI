# engine.models.signal_generator

## Class: 

A trading signal with position recommendation.

Attributes:
    symbol: Trading symbol.
    direction: 1 (long), -1 (short), 0 (neutral).
    strength: Signal strength (0-1).
    confidence: Model confidence (0-1).
    suggested_size: Suggested position size as fraction of portfolio.
    models_agree: Whether all models agree on direction.
    metadata: Additional signal metadata.

*Line: 24*

---

## Class: 

ML Signal Generator.

Takes ML model predictions and converts them into actionable
trading signals with risk-adjusted position sizing.

Features:
- Multi-model signal aggregation
- Confidence-based position sizing
- Risk-adjusted signal filtering
- Signal strength normalization

**Methods:** __init__, add_model, generate_signals, _aggregate_predictions

*Line: 46*

---

## Function: 

Initialize signal generator.

Args:
    min_confidence: Minimum model confidence to generate signal.
    signal_threshold: Minimum signal strength to act on.
    max_position_fraction: Maximum position as fraction of portfolio.

*Line: 59*

---

## Function: 

Add an ML model to the signal generator.

Args:
    model: BaseModel instance.

*Line: 77*

---

## Function: 

Generate trading signals from features.

Args:
    features: Dict mapping symbol -> feature DataFrame.
    portfolio_value: Current portfolio value.

Returns:
    List of TradingSignal objects.

*Line: 85*

---

## Function: 

Aggregate multiple model predictions into a single signal.

Args:
    symbol: Trading symbol.
    predictions: List of PredictionResult objects.
    portfolio_value: Current portfolio value.

Returns:
    TradingSignal or None if no actionable signal.

*Line: 131*

---

