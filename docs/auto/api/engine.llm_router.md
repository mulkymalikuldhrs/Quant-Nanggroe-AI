# engine.llm_router

## Class: 

Supported LLM providers.

*Line: 41*

---

## Class: 

Model tier for request routing.

*Line: 51*

---

## Class: 

Provider health status.

*Line: 58*

---

## Class: 

Configuration for an LLM provider.

*Line: 71*

---

## Class: 

Health status of an LLM provider.

*Line: 83*

---

## Class: 

Cost tracking record for an LLM call.

*Line: 97*

---

## Class: 

Response from an LLM call.

*Line: 111*

---

## Class: 

Multi-provider LLM router with failover and cost tracking.

Routes LLM requests across multiple providers with automatic
failover, health monitoring, cooldown on failure, and cost tracking.

Usage::

    router = LLMRouter()
    router.add_provider(ProviderConfig(
        provider=LLMProvider.OPENAI,
        api_key="YOUR_API_KEY_HERE",
        priority=0,
    ))
    response = await router.chat("Explain market volatility", tier=ModelTier.QUICK)
    stats = router.get_cost_stats()

**Methods:** __init__, add_provider, remove_provider, get_provider_health, get_cost_stats, _get_provider_order, _record_success, _record_failure, _calculate_cost

*Line: 183*

---

## Function: 

Get or create the default LLMRouter instance.

*Line: 744*

---

## Function: 

*Line: 201*

---

## Function: 

Add an LLM provider configuration.

Args:
    config: ProviderConfig with provider details.

*Line: 208*

---

## Function: 

Remove an LLM provider.

Args:
    provider: Provider to remove.

*Line: 224*

---

## Function: 

Get health status of all providers.

Returns:
    Dict mapping provider name to health status.

*Line: 347*

---

## Function: 

Get cost tracking statistics.

Returns:
    Dict with cost statistics per provider and total.

*Line: 355*

---

## Function: 

Get provider order for failover routing.

*Line: 391*

---

## Function: 

Record a successful provider call.

*Line: 674*

---

## Function: 

Record a failed provider call.

*Line: 695*

---

## Function: 

Calculate approximate cost for an LLM call.

*Line: 725*

---

