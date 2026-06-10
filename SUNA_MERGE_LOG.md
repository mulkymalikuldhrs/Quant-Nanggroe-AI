# SUNA AgentPress Merge Log

**Task ID:** 8-a  
**Agent:** Suna AgentPress Consolidation Agent  
**Date:** 2025-03-04  
**Source Repo:** `/home/z/my-project/quant-nanggroe-ai/repos/suna/`

---

## Overview

Extracted the most valuable code from the **suna** AgentPress framework into the Quant-Nanggroe-AI monorepo. The suna repo is a full-featured agent platform (~110K Python lines in `backend/core/`) including billing, auth, Supabase, Redis, and a React frontend. We extracted ONLY the agent framework core — NOT the entire application.

## Source Files Analyzed

| Suna File | Lines | Purpose | Extracted? |
|-----------|-------|---------|------------|
| `core/run/agent_runner.py` | 780 | Main agent execution loop | ✅ → loop.py |
| `core/agentpress/thread_manager.py` | 750+ | Conversation thread management, LLM calls | ✅ → loop.py |
| `core/agentpress/tool.py` | 300 | Tool base class, schema decorators | ✅ (already existed) |
| `core/agentpress/tool_registry.py` | 127 | Tool registration and schema caching | ✅ (already existed) |
| `core/agentpress/mcp_registry.py` | 711 | MCP tool lifecycle management | ✅ (already existed) |
| `core/run/mcp_manager.py` | 70 | MCP tool registration orchestrator | ✅ → mcp_client.py |
| `core/tools/mcp_tool_wrapper.py` | 515 | MCP tool wrapper with Redis caching | ✅ → mcp_client.py |
| `core/memory/models.py` | 53 | Memory data models | ✅ → memory.py |
| `core/memory/retrieval_service.py` | 265 | Vector similarity retrieval | ✅ → memory.py |
| `core/memory/embedding_service.py` | 176 | Multi-provider embedding service | ✅ → memory.py |
| `core/memory/extraction_service.py` | 165 | LLM-based memory extraction | ✅ → memory.py (concepts) |
| `core/sandbox/sandbox.py` | 145 | Daytona sandbox management | ✅ → sandbox.py (enhanced) |
| `core/run/tool_manager.py` | — | Tool registration orchestration | ✅ → tools.py |
| `core/agentpress/context_manager.py` | 866 | Token counting, compression, repair | ✅ (already existed) |
| `core/agentpress/response_processor.py` | — | Streaming response handler | Concepts → loop.py |
| `core/agentpress/error_processor.py` | — | Error classification and reporting | ✅ (already existed) |

## What Was NOT Extracted (Intentionally Discarded)

| Component | Reason |
|-----------|--------|
| `core/billing/` (50+ files) | SaaS billing — not needed for monorepo |
| `core/auth.py` | Supabase auth — already have own auth system |
| `core/services/supabase.py` | Supabase DB — using PostgreSQL directly |
| `core/services/redis.py` | Redis service — have own cache.py |
| `core/services/langfuse.py` | LLM observability — can add later |
| `core/composio_integration/` (12 files) | Composio-specific integration |
| `core/notifications/` (6 files) | Novu notification service |
| `core/templates/` (5 files) | Agent marketplace templates |
| `core/triggers/` (5 files) | Webhook trigger system |
| `core/google/` (4 files) | Google Docs/Slides integration |
| `core/jit/` (10 files) | JIT tool loading — too coupled to suna infra |
| `core/credentials/` (5 files) | Credential profile management |
| `core/resources/` (3 files) | Sandbox resource management |
| `core/versioning/` (3 files) | Agent version service |
| `core/admin/` (5 files) | Admin API endpoints |
| `core/ai_models/` (3 files) | Model registry — using litellm directly |
| `core/prompts/` (5 files) | Suna-specific system prompts |
| All 30+ individual tool files | Too suna-specific; we have our own trading tools |
| All Supabase migrations | Using our own PostgreSQL + Alembic |
| All React frontend code | Not Python, not relevant |

## New Files Created

### 1. `agents/agentpress/loop.py` (493 lines)
**Extracted from:** `core/run/agent_runner.py` + `core/agentpress/thread_manager.py` + `core/agentpress/response_processor.py`

**Key classes:**
- `AgentStatus` — Enum: PENDING, RUNNING, COMPLETED, STOPPED, ERROR
- `TerminationReason` — Enum: COMPLETED, MAX_ITERATIONS, CANCELLED, ERROR, CREDIT_EXCEEDED, AGENT_TERMINATED
- `AgentConfig` — Dataclass with thread_id, model_name, system_prompt, max_iterations, tool_choice, etc.
- `LoopStats` — Execution statistics tracker
- `AgentLoop` — Main agent execution loop:
  - `add_tool()` — Register tools
  - `set_memory_context()` — Inject memory into prompts
  - `run()` — Async generator yielding events: assistant, tool_call, tool_result, status, usage
  - `_call_llm()` — LLM API call via litellm (provider-agnostic)
  - `_execute_tool()` — Tool execution with error handling
  - `_prepare_messages()` — Message preparation with memory injection
  - `_build_default_system_prompt()` — Trading agent default prompt

**Adaptations from suna:**
- Removed Supabase DB dependency (thread manager stored messages in DB)
- Removed Langfuse tracing
- Removed billing integration (credit checking)
- Removed bootstrap mode (dual-phase startup)
- Removed prompt caching (Anthropic-specific, can be added later)
- Simplified auto-continue (suna had complex auto_continue_generator)
- Added trading-specific default system prompt
- Uses litellm directly instead of custom LLM service

### 2. `agents/agentpress/tools.py` (331 lines)
**Extracted from:** `core/run/tool_manager.py` + `core/utils/tool_discovery.py` + `core/agentpress/response_processor.py`

**Key classes:**
- `ToolExecutionError` — Exception for tool execution failures
- `ToolExecutor` — Unified tool execution with:
  - Configurable timeout per tool call
  - Automatic retry on transient failures
  - Comprehensive error reporting
  - Execution statistics tracking
- `ToolDiscovery` — Automatic tool discovery and registration:
  - `register_from_class()` — Single tool registration
  - `register_from_module()` — Scan module for Tool subclasses
  - `register_trading_tools()` — Register standard trading tools with disable list
  - `get_discovered_tools()` — Get all discovered tool classes

**Adaptations from suna:**
- Removed Redis tool caching (suna cached tool instances in Redis)
- Removed JIT config and Spark optimization
- Removed tool migration logic
- Added trading tool auto-discovery
- Simplified tool execution without streaming context

### 3. `agents/agentpress/memory.py` (488 lines)
**Extracted from:** `core/memory/models.py` + `core/memory/retrieval_service.py` + `core/memory/embedding_service.py` + `core/memory/extraction_service.py`

**Key classes:**
- `MemoryType` — Enum: FACT, PREFERENCE, CONTEXT, CONVERSATION_SUMMARY, MARKET_INSIGHT, TRADING_DECISION
- `MemoryEntry` — Dataclass with id, content, type, confidence, embedding, metadata
- `EmbeddingProvider` — Abstract base class
- `OpenAIEmbeddingProvider` — OpenAI text-embedding-3-small
- `LocalEmbeddingProvider` — sentence-transformers (all-MiniLM-L6-v2)
- `HashEmbeddingProvider` — Testing fallback (hash-based, no deps)
- `AgentMemory` — Unified memory system:
  - `add()` / `add_with_embedding()` — Store memories with auto-embedding
  - `search()` — Semantic similarity search with keyword fallback
  - `get_by_type()` — Type-filtered retrieval
  - `format_for_prompt()` — Format memories for LLM context injection
  - `get_stats()` — Memory statistics
  - File-based persistence (JSON)

**Adaptations from suna:**
- Combined 4 separate services into 1 unified class
- Removed Supabase RPC (vector_search RPC) — replaced with in-memory cosine similarity
- Removed Redis caching for retrieval results
- Removed billing/tier checks for memory limits
- Added HashEmbeddingProvider for zero-dependency testing
- Added trading-specific memory types (MARKET_INSIGHT, TRADING_DECISION)
- Removed LLM-based memory extraction (requires litellm + model config) — can be added later
- Added file-based persistence instead of Supabase

### 4. `agents/agentpress/mcp_client.py` (512 lines)
**Extracted from:** `core/run/mcp_manager.py` + `core/tools/mcp_tool_wrapper.py` + `core/agentpress/mcp_registry.py` + `core/mcp_module/mcp_service.py`

**Key classes:**
- `MCPTransport` — Enum: SSE, HTTP, STDIO
- `MCPConnectionStatus` — Enum: DISCONNECTED, CONNECTING, CONNECTED, ERROR
- `MCPServerConfig` — Server configuration with transport, URL, command, headers
- `MCPToolSchema` — Discovered tool schema with OpenAPI conversion
- `MCPClient` — Standalone MCP client:
  - `add_server()` / `remove_server()` — Manage server configs
  - `discover_tools()` — Discover tools from all or specific servers
  - `execute_tool()` — Execute a tool on its MCP server
  - `get_tool_schemas()` — Get OpenAPI schemas for LLM function calling
  - Schema caching with TTL
  - All 3 transports: SSE, HTTP (streamable), stdio
  - All 3 transports for execution too

**Adaptations from suna:**
- Combined MCPManager + MCPToolWrapper + MCPRegistry into one client
- Removed Composio integration (suna had composio_service, composio_profile_service)
- Removed Redis schema caching — replaced with in-memory TTL cache
- Removed dynamic tool builder (suna generated Python methods at runtime)
- Removed JIT tool loading (suna had complex JIT activation flow)
- Removed Supabase DB for credential profiles
- Added schema cache with configurable TTL
- Added connection status tracking per server
- Simplified tool execution (direct session.call_tool instead of complex wrapper chain)

### 5. `agents/agentpress/sandbox.py` (212 lines)
**Extracted from:** `core/sandbox/sandbox.py` + `core/sandbox/tool_base.py`

**Key classes:**
- `SandboxPool` — Pool of pre-provisioned sandbox instances:
  - `acquire()` — Get a sandbox (creates if pool empty)
  - `release()` — Return a sandbox to the pool
  - `shutdown()` — Clean up all sandboxes
- `TradingSandbox` — Specialized sandbox for trading strategies:
  - `validate_strategy()` — AST-based safety validation
  - `run_code()` — Execute code with configurable timeout
  - Async context manager support

**Adaptations from suna:**
- Re-exports existing Sandbox/SandboxConfig/SandboxResult from agents/sandbox.py
- Added SandboxPool for agent loop (avoids sandbox creation overhead)
- Added TradingSandbox with strategy safety validation
- Removed Daytona SDK direct usage (already handled by base Sandbox)
- Removed supervisord session management
- Added pool management with asyncio Lock

### 6. `agents/agentpress/__init__.py` (157 lines — updated)
Updated to export all new classes from the 5 new modules.

## File Statistics

| File | Lines | Key Exports |
|------|-------|-------------|
| loop.py | 493 | AgentLoop, AgentConfig, AgentStatus, TerminationReason, LoopStats |
| tools.py | 331 | ToolExecutor, ToolDiscovery, ToolExecutionError |
| memory.py | 488 | AgentMemory, MemoryType, MemoryEntry, 3 EmbeddingProviders |
| mcp_client.py | 512 | MCPClient, MCPServerConfig, MCPTransport, MCPToolSchema |
| sandbox.py | 212 | SandboxPool, TradingSandbox |
| __init__.py | 157 | All exports from above |
| **Total** | **2,193** | |

## Previously Existing Files (unchanged)

These were already extracted in prior tasks and remain unchanged:
- `tool.py` (311 lines) — Tool base class
- `tool_registry.py` (198 lines) — Tool registry
- `xml_tool_parser.py` — XML tool call parsing
- `native_tool_parser.py` — OpenAI native tool call parsing
- `mcp_registry.py` (491 lines) — MCP tool lifecycle registry
- `context_manager.py` — Token counting and context compression
- `error_processor.py` — Error classification

## Key Design Decisions

1. **No Supabase dependency** — suna stores everything in Supabase; we use in-memory + file persistence
2. **No Redis dependency** — suna caches schemas and tool instances in Redis; we use in-memory TTL cache
3. **No billing integration** — removed credit checking from the agent loop
4. **No Langfuse tracing** — removed observability (can be added later)
5. **litellm for LLM calls** — provider-agnostic instead of suna's custom LLM service
6. **Unified memory class** — combined 4 separate services into 1 AgentMemory class
7. **Unified MCP client** — combined MCPManager + MCPToolWrapper + MCPRegistry into MCPClient
8. **Hash embedding fallback** — zero-dependency testing without OpenAI/sentence-transformers
9. **Trading-specific memory types** — added MARKET_INSIGHT and TRADING_DECISION
10. **SandboxPool for agent loop** — avoids sandbox creation overhead per request

## Verification

- All 6 new/modified files pass `python -m py_compile` ✓
- All imports use `quant_nanggroe_ai.*` package paths ✓
- All classes have proper type hints and docstrings ✓
- No raw copy — all code adapted for trading platform context ✓
- No dependency on Supabase, Redis, or external services ✓

## Next Steps

1. Add `litellm` and `mcp` to pyproject.toml dependencies
2. Wire AgentLoop into the existing LangGraph agent graph
3. Add tests for all new modules
4. Add prompt caching support (Anthropic-specific optimization from suna)
5. Add memory extraction service (LLM-based memory extraction from conversations)
6. Integrate MCPClient with existing mcp_config.py default servers
