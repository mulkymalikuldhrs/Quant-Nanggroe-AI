# connectors.llm_gateway

## Class: 

Universal LLM Gateway supporting multiple providers:
- LLM7 (Primary)
- OpenRouter
- CAMEL 
- OpenAI
- Anthropic
- Local models

**Methods:** __init__, _initialize_providers, _select_provider_and_model, _standardize_response, _check_rate_limit, _update_rate_limit, _get_alternative_provider, _get_fallback_provider, _generate_cache_key, _get_cached_response, _cache_response, _update_usage_stats, get_provider_status, get_available_providers, get_usage_summary

*Line: 20*

---

## Function: 

*Line: 31*

---

## Function: 

Initialize and test provider connections

*Line: 88*

---

## Function: 

Select optimal provider and model

*Line: 162*

---

## Function: 

Standardize response format across providers

*Line: 253*

---

## Function: 

Check if provider is within rate limits

*Line: 277*

---

## Function: 

Update rate limit tracking

*Line: 294*

---

## Function: 

Get alternative provider when current is rate limited

*Line: 301*

---

## Function: 

Get fallback provider when current fails

*Line: 316*

---

## Function: 

Generate cache key for request

*Line: 328*

---

## Function: 

Get cached response if available and not expired

*Line: 340*

---

## Function: 

Cache successful response

*Line: 351*

---

## Function: 

Update usage statistics

*Line: 369*

---

## Function: 

Get status of all LLM providers

*Line: 444*

---

## Function: 

Get list of available (non-disabled) provider names

*Line: 465*

---

## Function: 

Get overall usage summary

*Line: 472*

---

