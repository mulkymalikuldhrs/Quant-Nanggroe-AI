# engine.nvidia_nim.models

## Class: 

Task types for intelligent model routing.

Each task type maps to an optimal NIM model via the NIMModelRouter.

*Line: 21*

---

## Class: 

Chat message roles compatible with NIM chat completions API.

*Line: 35*

---

## Class: 

Reason for completion in a chat response.

*Line: 44*

---

## Class: 

Status of a NIM model endpoint.

*Line: 53*

---

## Class: 

A single chat message in a NIM conversation.

Follows the OpenAI-compatible chat format used by NVIDIA NIM.

*Line: 66*

---

## Class: 

Request payload for NIM chat completion endpoint.

Compatible with the OpenAI-format chat completions API at
``https://integrate.api.nvidia.com/v1/chat/completions``.

**Methods:** validate_messages

*Line: 80*

---

## Class: 

A single choice in a chat completion response.

*Line: 128*

---

## Class: 

Token usage and cost tracking for a NIM API call.

**Methods:** tokens_per_second

*Line: 138*

---

## Class: 

Response from a NIM chat completion request.

**Methods:** content, finish_reason

*Line: 159*

---

## Class: 

Delta content in a streaming chunk.

*Line: 195*

---

## Class: 

A single choice in a streaming chunk.

*Line: 202*

---

## Class: 

A single chunk in a streaming chat completion response.

**Methods:** delta_content

*Line: 210*

---

## Class: 

Request payload for NIM embeddings endpoint.

*Line: 236*

---

## Class: 

A single embedding vector in the response.

*Line: 258*

---

## Class: 

Response from a NIM embeddings request.

*Line: 266*

---

## Class: 

Request payload for NIM reranking endpoint.

*Line: 284*

---

## Class: 

A single reranking result.

*Line: 300*

---

## Class: 

Response from a NIM reranking request.

*Line: 312*

---

## Class: 

Metadata for an available NIM model.

*Line: 329*

---

## Class: 

List of available NIM models.

**Methods:** model_ids, get_model

*Line: 356*

---

## Class: 

Performance metrics tracked per NIM model by the router.

**Methods:** success_rate, avg_tokens_per_second

*Line: 381*

---

## Class: 

Result of a model routing decision by NIMModelRouter.

*Line: 415*

---

## Function: 

Ensure at least one user message is present.

*Line: 121*

---

## Function: 

Calculate tokens per second throughput.

*Line: 152*

---

## Function: 

Extract the first choice's message content.

*Line: 177*

---

## Function: 

Extract the first choice's finish reason.

*Line: 184*

---

## Function: 

Extract the delta text content from the first choice.

*Line: 225*

---

## Function: 

Extract all model IDs.

*Line: 365*

---

## Function: 

Find a model by its ID.

*Line: 369*

---

## Function: 

Calculate success rate (0.0-1.0).

*Line: 401*

---

## Function: 

Calculate average output throughput.

*Line: 408*

---

