# engine.nvidia_nim.router

## Class: 

Intelligent model router for NVIDIA NIM inference microservices.

Routes different task types to optimal models, implements fallback
chains when primary models are unavailable, tracks per-model
performance metrics, and optimises for cost when quality differences
are marginal.

Args:
    client: An initialised NIMClient instance.
    config: Optional NIMConfig (uses global default if not provided).

**Methods:** __init__, _initialize_metrics, route, get_metrics, get_task_model_map, mark_model_unavailable, mark_model_available, _find_cheaper_alternative, _estimate_call_cost, _record_success, _record_failure

*Line: 111*

---

## Function: 

*Line: 124*

---

## Function: 

Pre-populate metrics for all known models.

*Line: 138*

---

## Function: 

Determine the optimal model for a given task type.

Selects the primary model or, if it is unhealthy/rate-limited,
walks the fallback chain.  When ``prefer_cheaper`` is True and
the primary model's success rate is within the cost-optimisation
threshold of a cheaper alternative, the cheaper model is chosen.

Args:
    task_type: The task being routed.
    prefer_cheaper: Prefer cheaper models when quality is close.

Returns:
    NIMRoutingDecision with the selected model and reasoning.

*Line: 152*

---

## Function: 

Get model performance metrics.

Args:
    model_id: If provided, return metrics for a specific model.
        If None, return metrics for all models.

Returns:
    Dict with metrics data.

*Line: 318*

---

## Function: 

Return the current task-to-model mapping configuration.

Returns:
    Dict mapping TaskType values to their model configurations.

*Line: 339*

---

## Function: 

Manually mark a model as unavailable.

Args:
    model_id: NIM model identifier.
    reason: Reason for marking unavailable.

*Line: 355*

---

## Function: 

Manually mark a model as available.

Args:
    model_id: NIM model identifier.

*Line: 367*

---

## Function: 

Check if a cheaper fallback is within quality threshold.

Compares the primary model's success rate with each fallback.
If a cheaper model's success rate is within the cost-optimisation
threshold, it is returned.

Args:
    primary: Primary model identifier.
    fallbacks: Fallback model identifiers.

Returns:
    Cheaper model identifier or None.

*Line: 383*

---

## Function: 

Estimate cost for a single chat call.

Uses a heuristic of input ≈ max_tokens/2 and output ≈ max_tokens/2.

Args:
    model: NIM model identifier.
    max_tokens: Max output tokens for the request.

Returns:
    Estimated cost in USD.

*Line: 426*

---

## Function: 

Record a successful call in the metrics.

*Line: 442*

---

## Function: 

Record a failed call in the metrics.

*Line: 478*

---

