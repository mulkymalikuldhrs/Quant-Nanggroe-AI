# C2 Repository Deep Audit Report

**Date:** 2025-06-11  
**Auditor:** Task 6 — C2 Candidate Audit Agent  
**Scope:** 31 remaining repos NOT in Cluster 1 or DISCARD list  

---

## Executive Summary

Of the 31 repos audited, **6 qualify as C2-CORE** (substantial trading/AI/quant code for direct merge), **7 as C2-SUPPORT** (useful infrastructure/tools/patterns), **6 as C2-REFERENCE** (useful concepts but not for direct merge), and **12 as DISCARD** (boilerplate, awesome-lists, portfolios, or no valuable code). The top 19 repos are ranked below.

**Key finding:** Most C2 candidates are general-purpose AI agent platforms or content tools — NOT trading-specific. The truly valuable repos for Quant-Nanggroe-AI are those with agent orchestration frameworks (suna, ai-manus), financial data integrations (ai-financial-agent, polymarket-cli, mnemosyne finance skills), and engineering patterns (ai-engineering-hub, ghoststudio-ai engine).

---

## Classification Summary

| Category | Count | Repos |
|----------|-------|-------|
| **C2-CORE** | 6 | suna, ai-manus, ai-financial-agent, polymarket-cli, mnemosyne, ghoststudio-ai |
| **C2-SUPPORT** | 7 | ai-engineering-hub, agenticSeek, agentcloud, nanggroe-iot, pase-fx, bloomberg-terminal, rtk-reduce-tokenLLM |
| **C2-REFERENCE** | 6 | openhuman, skales, aikit, superpowers, yolobox, sled |
| **DISCARD** | 12 | awesome-quant, awesome-vibe-coding, developer-portfolios, founders-kit, free-AI-Project-Gallery, famlyzer-ai, autonomous-organism, cyber-shell-x-nexus, project-nomad-offline, PromptForgeAI, sim (already partially merged) |

---

## Ranked Top 19 C2 Repositories

### Rank 1: suna — C2-CORE
| Attribute | Value |
|-----------|-------|
| **Language** | Python (110,559 lines) + TypeScript (251,469 lines) |
| **Branches** | 3 (main only) |
| **Total LOC** | ~362,000+ |
| **What it is** | Kortix/Suna — Complete autonomous AI agent platform with agent builder, sandbox, MCP, memory, tools |

**Unique Value for QNAI:**
- **AgentPress framework** — Production-grade agent orchestration with thread management, tool registry, XML tool parsing, prompt caching, and error processing. This is a complete agent execution framework.
- **30+ tool implementations** — browser, company search, file ops, git sync, KB, shell, spreadsheet, vision, web search, MCP wrapper, etc.
- **Sandbox system** — Docker-based code execution sandbox for agent tool use
- **Memory system** — Embedding service, extraction service, retrieval service with background jobs
- **Agent runner** — Full agent lifecycle: bootstrap → tool setup → MCP connection → execution → billing
- **MCP integration** — MCP manager, MCP tool wrapper, MCP registry
- **JIT (Just-In-Time) tool system** — Dynamic tool configuration per agent run

**Merge Strategy:** Port AgentPress framework, memory system, sandbox, and key tools as `quant_nanggroe_ai.agent_press` package. Adapt thread manager for trading agent graph.

---

### Rank 2: ai-manus — C2-CORE
| Attribute | Value |
|-----------|-------|
| **Language** | Python (13,938 lines) + TypeScript (3,483 lines) |
| **Branches** | 15 (3 with unique code already merged in Task 3-d) |
| **Total LOC** | ~17,400+ |
| **What it is** | General-purpose AI Agent system with sandbox, MCP, browser use |

**Unique Value for QNAI:**
- **Clean DDD architecture** — application/core/domain/infrastructure/interfaces layers
- **Domain models** — agent.py, auth.py, event.py, file.py, mcp_config.py, memory.py, message.py, plan.py, sandbox, search.py, session.py, tool_result.py, user.py
- **Infrastructure layer** — browser, cache, file, llm, message_queue, sandbox, search, task
- **Agent task runner** — agent_task_runner.py with flow orchestration
- **Agent flows and prompts** — Structured agent definition system
- **Already partially merged** — Auth (JWT), file ops, MCP config merged in Task 3-d

**Merge Strategy:** Port remaining domain models, infrastructure adapters, and agent flow system. Already has auth and file ops in monorepo.

---

### Rank 3: ai-financial-agent — C2-CORE
| Attribute | Value |
|-----------|-------|
| **Language** | TypeScript (14,119 lines) |
| **Branches** | 3 (main only) |
| **Total LOC** | ~14,600+ |
| **What it is** | AI financial research agent with stock data tools and chat interface |

**Unique Value for QNAI:**
- **Financial Tools Manager** — 7 financial data tools: getStockPrices, getIncomeStatements, getBalanceSheets, getCashFlowStatements, getFinancialMetrics, searchStocksByFilters, getNews
- **FinancialDatasets.ai API integration** — Complete TypeScript implementation for financial data API
- **Stock filter system** — stock-filters.ts with valid filter parameters
- **AI chat interface** — Next.js app with Vercel AI SDK, financial prompts, document blocks
- **Drizzle ORM** — Database schema for financial data
- **Tool deduplication** — shouldExecuteToolCall() prevents duplicate API calls

**Merge Strategy:** Port financial tools as Python async methods in `quant_nanggroe_ai.agents.tools.financial_data.py`. Port stock filters and API integration patterns.

---

### Rank 4: polymarket-cli — C2-CORE
| Attribute | Value |
|-----------|-------|
| **Language** | Rust (8,668 lines) |
| **Branches** | 3 (main only) |
| **Total LOC** | ~8,700+ |
| **What it is** | Official Polymarket CLI for browsing markets, placing orders, managing positions |

**Unique Value for QNAI:**
- **Complete Polymarket CLOB integration** — 16 command modules: approve, bridge, clob, comments, ctf, data, events, markets, profiles, series, setup, sports, tags, upgrade, wallet
- **Authentication system** — auth.rs with Polymarket key management
- **Configuration** — config.rs with profiles, API endpoints
- **Shell integration** — shell.rs for interactive CLI mode
- **JSON API output** — Script/agent-friendly output format

**Merge Strategy:** Already have Polymarket broker in execution layer. Reference this for CLOB API completeness — the CLI covers endpoints our broker doesn't (events, series, tags, sports, comments, bridge, CTF). Port missing API endpoints to Python.

---

### Rank 5: mnemosyne — C2-CORE
| Attribute | Value |
|-----------|-------|
| **Language** | Python (30,681 lines) + TypeScript (45,941 lines) |
| **Branches** | 4 (1 remote with 0 unique commits) |
| **Total LOC** | ~76,600+ |
| **What it is** | Multi-LLM Hub + AI Memory Center with 50+ skills, MCP server, BYOK, PWA |

**Unique Value for QNAI:**
- **Finance skill** — Comprehensive Finance API integration for real-time and historical financial data, market research, stock screening, technical analysis
- **Stock Analysis skill** — A-share/HK/US stock analysis with buy/sell/hold recommendations, K-line pattern recognition, watchlist management, dividend analysis, rumor scanning
- **Market Research Reports skill** — 50+ page consulting-grade market research with Porter's Five Forces, PESTLE, SWOT, TAM/SAM/SOM, BCG Matrix
- **40+ other AI skills** — ASR, TTS, VLM, web-search, web-reader, charts, docx, xlsx, pdf, coding-agent, image-generation, video-understand, etc.
- **MCP server** — Full MCP server implementation
- **Multi-LLM support** — 500+ free AI models via Puter.js, BYOK
- **Skill system** — Structured skill definitions with SKILL.md metadata, commands, input schemas

**Merge Strategy:** Port finance and stock-analysis skills as trading analysis tools. Port MCP server patterns. Reference skill definition format for QNAI tool system.

---

### Rank 6: ghoststudio-ai — C2-CORE
| Attribute | Value |
|-----------|-------|
| **Language** | Python (27,563 lines) + TypeScript (35,522 lines) |
| **Branches** | 3 (main only) |
| **Total LOC** | ~63,200+ |
| **What it is** | AI faceless content generation platform with 8-agent pipeline, 20+ publishers |

**Unique Value for QNAI:**
- **AI Engine Core** (engine/core.py) — Orchestration engine with content generation pipeline: Draft → Humanize → SEO → Score → Publish
- **8 Specialized Agents** — DraftAgent, HumanicAgent, SEOAgent, RepurposeAgent, ScoringAgent, MemoryAgent, TrendAgent + apifree_adapter
- **8-Layer Failsafe System** (engine/failsafe.py) — Safe mode, review mode, dry run, error threshold, quality gate, duplicate detection, rate limit, budget limit
- **Scheduler + Queue** (engine/scheduler.py) — SQLite-backed persistent job queue with cron scheduling, status tracking
- **Memory System** (engine/memory.py) — Content memory with similarity detection
- **20+ Publishers** — Medium, Substack, WordPress, Ghost, DevTo, Hashnode, YouTube, TikTok, Instagram, Blogger, etc.
- **BioWallet** — Biometric authentication component

**Merge Strategy:** Port failsafe system (8-layer safety pipeline) as `quant_nanggroe_ai.engine.failsafe`. Port scheduler as `quant_nanggroe_ai.engine.scheduler`. Port agent orchestration patterns for trading pipeline. Publishers not needed for QNAI.

---

### Rank 7: ai-engineering-hub — C2-SUPPORT
| Attribute | Value |
|-----------|-------|
| **Language** | Python (40,928 lines) + TypeScript (45,512 lines) |
| **Branches** | 3 (main only) |
| **Total LOC** | ~86,400+ |
| **What it is** | 93+ production-ready AI engineering projects/tutorials |

**Unique Value for QNAI:**
- **stock-portfolio-analysis-agent** — Complete Python stock portfolio analysis agent with prompts, stock_analysis module
- **financial-analyst-deepseek** — CrewAI-based financial analyst with query parser + code writer agents, yfinance integration
- **autogen-stock-analyst** — AutoGen-based stock analyst notebook
- **agentic_rag / agentic_rag_deepseek** — RAG agent implementations
- **Multi-Agent-deep-researcher-mcp** — MCP-based multi-agent researcher
- **agent-with-mcp-memory** — MCP memory integration pattern
- **agent2agent-demo** — Agent-to-agent communication demo
- **93+ reference implementations** — RAG, agents, fine-tuning, podcasts, etc.

**Merge Strategy:** Port stock-portfolio-analysis-agent and financial-analyst-deepseek as reference agents. Port MCP patterns and agent2agent communication. Rest is tutorial/reference.

---

### Rank 8: agenticSeek — C2-SUPPORT
| Attribute | Value |
|-----------|-------|
| **Language** | Python (7,183 lines) |
| **Branches** | 3 (main only) |
| **Total LOC** | ~7,200+ |
| **What it is** | Local Manus AI alternative — voice-enabled AI assistant with autonomous browsing/coding |

**Unique Value for QNAI:**
- **Agent Router** (sources/router.py) — Intelligent agent selection with zero-shot BART classification + AdaptiveClassifier for task routing. This is a production ML-based router.
- **6 Specialized Agents** — CoderAgent, BrowserAgent, FileAgent, CasualAgent, PlannerAgent, MCPAgent
- **Agent base class** — Clean abstract agent with tool registry, memory, execution
- **Tool system** — BashInterpreter, PyInterpreter, CInterpreter, JavaInterpreter, webSearch, searxSearch, flightSearch, mcpFinder, safety
- **Memory system** — sources/memory.py
- **Speech pipeline** — speech_to_text.py, text_to_speech.py
- **Safety module** — tools/safety.py

**Merge Strategy:** Port Agent Router as `quant_nanggroe_ai.agents.router` for intelligent task routing. Port safety module. Reference agent base class pattern.

---

### Rank 9: agentcloud — C2-SUPPORT
| Attribute | Value |
|-----------|-------|
| **Language** | Python (5,236 lines backend) + TypeScript (66,195 lines) + Rust (5,508 lines) |
| **Branches** | 3 (main only) |
| **Total LOC** | ~77,000+ |
| **What it is** | Open-source platform for building and deploying private LLM chat apps with RAG |

**Unique Value for QNAI:**
- **CrewAI integration** — src/crew/ with build_crew.py, task helpers, component assembly
- **RAG tool** — rag_tool.py with retrievers for document-based Q&A
- **Code execution tools** — Docker notebook execution, code execution tool
- **Google Cloud Function tool** — Serverless function integration
- **Chat assistant** — Structured chat with human input, MongoDB saver
- **Vector DB proxy** — Qdrant integration with proxy layer
- **Multi-modal** — Text + image + document support

**Merge Strategy:** Port CrewAI integration patterns for agent orchestration. Port RAG tool and retrievers for document-based research. Reference vector DB proxy patterns.

---

### Rank 10: nanggroe-iot — C2-SUPPORT
| Attribute | Value |
|-----------|-------|
| **Language** | Python (30,681 lines) + TypeScript (62,397 lines) |
| **Branches** | 13 (10 dependabot branches — dependency bumps only) |
| **Total LOC** | ~93,000+ |
| **What it is** | Modular IoT and Robotics platform + fork of mnemosyne skills |

**Unique Value for QNAI:**
- **Shares mnemosyne skill system** — Same 50+ AI skills including finance, stock-analysis, market-research
- **IoT/Robotics layer** — WebSocket-driven device control, sensor data streaming, hardware orchestration
- **Capacitor mobile app** — Android/iOS native app with TypeScript
- **Agent context files** — 9 developer context files for code agent tasks
- **Custom database** — db/custom.db with device/telemetry data

**Merge Strategy:** Treat as duplicate of mnemosyne for skills. Port IoT WebSocket patterns if hardware trading integration is needed. Low priority — mostly overlaps with mnemosyne.

---

### Rank 11: pase-fx — C2-SUPPORT
| Attribute | Value |
|-----------|-------|
| **Language** | TypeScript (18,068 lines) |
| **Branches** | 4 (1 remote with accessibility fixes) |
| **Total LOC** | ~18,200+ |
| **What it is** | Forex trading community platform with AI-enhanced market analysis |

**Unique Value for QNAI:**
- **Forex-specific** — Forex market data, currency pair analysis, AI market commentary
- **Backend API** — Express.js backend with routes, middleware, utils
- **Prisma ORM** — Database schema for forex data
- **Community features** — Discussion, education, signals
- **Investing.com integration** — UPGRADE_TO_INVESTING_COM.md indicates data source integration
- **Constants** — 20K+ line constants.ts with forex pairs, pip values, market hours

**Merge Strategy:** Port forex market data integration patterns. Port constants (currency pairs, pip values, market hours) as Python config. Reference investing.com scraping approach.

---

### Rank 12: bloomberg-terminal — C2-SUPPORT
| Attribute | Value |
|-----------|-------|
| **Language** | TypeScript (11,767 lines) |
| **Branches** | 3 (main only) |
| **Total LOC** | ~11,800+ |
| **What it is** | Bloomberg Terminal clone with real-time financial data visualization |

**Unique Value for QNAI:**
- **Alpha Vantage API integration** — lib/alpha-vantage.ts with stock quote, time series, technical indicators
- **Market data refresh system** — lib/market-data-refresh.ts with configurable refresh rates
- **Redis state management** — lib/redis.ts for Upstash Redis
- **Scheduler** — lib/scheduler.ts for periodic data updates
- **UI Components** — Professional terminal-style financial dashboard with market data views, news, movers, volatility
- **Jotai atoms** — Local state management for real-time data
- **Keyboard shortcuts** — Terminal-style keyboard navigation

**Merge Strategy:** Port Alpha Vantage integration as Python data source. Reference UI components for QNAI frontend dashboard. Port scheduler pattern for periodic data updates.

---

### Rank 13: rtk-reduce-tokenLLM — C2-SUPPORT
| Attribute | Value |
|-----------|-------|
| **Language** | Rust (62,028 lines) + TypeScript (1,027 lines) + Python (155 lines) |
| **Branches** | 3 (main only) |
| **Total LOC** | ~63,200+ |
| **What it is** | High-performance CLI proxy that reduces LLM token consumption by 60-90% |

**Unique Value for QNAI:**
- **Token optimization** — LLM prompt compression that reduces token usage by 60-90%
- **Rust performance** — Built for speed with native binary
- **Hook system** — Pre/post-processing hooks for LLM calls
- **Parser** — Code-aware parsing for intelligent compression
- **Filters** — Token filtering and reduction strategies
- **Learn module** — Adaptive compression learning
- **Analytics** — Token usage analytics and reporting

**Merge Strategy:** Use as external tool/binary for reducing QNAI's LLM API costs. Reference compression strategies for prompt optimization in agent tools. Not Python — would be called as subprocess.

---

### Rank 14: openhuman — C2-REFERENCE
| Attribute | Value |
|-----------|-------|
| **Language** | Rust (687,512 lines) + TypeScript (303,511 lines) |
| **Branches** | 3 (main only) |
| **Total LOC** | ~991,000+ |
| **What it is** | Personal AI superintelligence — local memory, managed services, MCP, Tauri app |

**Unique Value for QNAI:**
- **Massive Rust codebase** — 687K lines of Rust for core AI logic and RPC server
- **Memory tree system** — Hierarchical memory with tree-based storage
- **MCP support** — MCP stub for tool integration
- **Tauri desktop app** — Cross-platform native app
- **Multiple binaries** — openhuman-core, slack-backfill, gmail-backfill, memory-tree-init-smoke, inference-probe, test-mcp-stub
- **Local-first architecture** — Everything runs locally with optional cloud services

**Merge Strategy:** Too large and Rust-based for direct merge. Reference memory tree architecture and local-first design patterns. The Rust codebase is not Python-compatible.

---

### Rank 15: skales — C2-REFERENCE
| Attribute | Value |
|-----------|-------|
| **Language** | TypeScript (57,579 lines) + JavaScript (4,993 lines) |
| **Branches** | 3 (main only) |
| **Total LOC** | ~62,600+ |
| **What it is** | Private AI desktop app — 15+ AI providers, offline Ollama, WhatsApp/Telegram |

**Unique Value for QNAI:**
- **Multi-provider LLM** — 15+ AI provider integrations
- **Electron desktop app** — Cross-platform with auto-updater
- **WhatsApp/Telegram bots** — Messaging platform integration
- **Offline-first** — Ollama support for fully local inference
- **File management** — Local file processing without cloud upload

**Merge Strategy:** Reference multi-provider LLM integration patterns. Port WhatsApp/Telegram notification bot patterns. Not Python — reference only.

---

### Rank 16: aikit — C2-REFERENCE
| Attribute | Value |
|-----------|-------|
| **Language** | TypeScript (18,343 lines) + JavaScript (1,080 lines) |
| **Branches** | 3 (main only) |
| **Total LOC** | ~19,400+ |
| **What it is** | Open-source AI coding agent toolkit — Skills, Agents, Commands, Tools, Plugins |

**Unique Value for QNAI:**
- **Skill system** — Structured skills for debugging, design, development, documentation, figma, git, review, testing
- **Plugin architecture** — Extensible plugin system for adding capabilities
- **Agent commands** — Command system for agent interaction
- **TypeScript SDK** — tsup-built package for programmatic use

**Merge Strategy:** Reference skill definition format and plugin architecture. Not Python — patterns only.

---

### Rank 17: superpowers — C2-REFERENCE
| Attribute | Value |
|-----------|-------|
| **Language** | Markdown + TypeScript (168 lines) + JavaScript (1,210 lines) |
| **Branches** | 3 (main only) |
| **Total LOC** | ~1,400+ (code) |
| **What it is** | AI coding agent skill/prompt library — brainstorming, debugging, TDD, code review |

**Unique Value for QNAI:**
- **14 production-ready skills** — brainstorming, dispatching-parallel-agents, executing-plans, finishing-branch, receiving-code-review, requesting-code-review, subagent-driven-development, systematic-debugging, test-driven-development, using-git-worktrees, using-superpowers, verification-before-completion, writing-plans, writing-skills
- **Multi-agent coding patterns** — Parallel agent dispatch, subagent orchestration
- **Code review automation** — Automated review request/receive workflow
- **Git worktree patterns** — Parallel development with worktrees

**Merge Strategy:** Reference skill prompt templates for QNAI agent skill definitions. Port subagent-driven-development patterns. Very lightweight — patterns only.

---

### Rank 18: yolobox — C2-REFERENCE
| Attribute | Value |
|-----------|-------|
| **Language** | Go (1,847 lines) |
| **Branches** | 3 (main only) |
| **Total LOC** | ~1,850+ |
| **What it is** | Sandbox for running AI coding agents in "yolo mode" without nuking your home directory |

**Unique Value for QNAI:**
- **Container sandbox** — Go-based sandboxing for AI agent code execution
- **Permission model** — Project directory mounted at /workspace, home directory protected
- **Persistent volumes** — Tool/config persistence across sessions
- **Agent support** — Claude Code, OpenAI Codex, Gemini CLI

**Merge Strategy:** Reference sandbox design for QNAI's agent code execution. Not Python — but the container isolation pattern is valuable for safe tool execution.

---

### Rank 19: sled — C2-REFERENCE
| Attribute | Value |
|-----------|-------|
| **Language** | TypeScript (17,829 lines) + JavaScript (4,403 lines) |
| **Branches** | 3 (main only) |
| **Total LOC** | ~22,200+ |
| **What it is** | Mobile interface for desktop coding agents — use Claude Code/Codex from phone with voice |

**Unique Value for QNAI:**
- **Voice-to-agent** — Voice input for coding agent commands
- **Cloudflare Workers** — Server-client architecture with edge deployment
- **Mobile-first UI** — Responsive interface for phone-based agent interaction
- **Agent protocol** — Communication protocol for remote agent control

**Merge Strategy:** Reference voice interaction pattern for QNAI mobile trading alerts. Reference agent remote control protocol for mobile trading app.

---

## DISCARD Repos (12)

### awesome-quant — DISCARD
| Attribute | Value |
|-----------|-------|
| **Language** | Markdown + Python (1,507 lines — just scrapers) |
| **What it is** | Curated list of quant finance libraries and resources |

**Reason:** Awesome-list with no implementable code. The 1,507 lines of Python are just list scrapers (cranscrape.py, parse.py, topic.py, recommendation.ipynb). Zero trading/AI implementation.

---

### awesome-vibe-coding — DISCARD
| Attribute | Value |
|-----------|-------|
| **Language** | Markdown only (0 lines of code) |
| **What it is** | Curated list of vibe coding tools and resources |

**Reason:** Pure awesome-list. No code at all.

---

### developer-portfolios — DISCARD
| Attribute | Value |
|-----------|-------|
| **Language** | Python (1,511 lines — just test scraper) + JSON (179,973 lines — portfolio data) |
| **What it is** | List of 1,728 developer portfolio websites |

**Reason:** Portfolio directory. The Python code is just a link checker (run_tests.py). No useful code.

---

### founders-kit — DISCARD
| Attribute | Value |
|-----------|-------|
| **Language** | Markdown only (0 lines of code) |
| **What it is** | Curated startup resources directory |

**Reason:** Resource list only. No code whatsoever.

---

### free-AI-Project-Gallery — DISCARD
| Attribute | Value |
|-----------|-------|
| **Language** | Markdown only (0 lines of code) |
| **What it is** | Table of AI project links and repositories |

**Reason:** Link table only. No code.

---

### famlyzer-ai — DISCARD
| Attribute | Value |
|-----------|-------|
| **Language** | TypeScript (12,767 lines) |
| **What it is** | Family/life planning AI with 7 agents |

**Reason:** Life planning platform — no trading/finance/quant relevance. Generic Next.js + TypeScript app with life planning agents. The AI agent patterns are basic and already covered by better repos (suna, ai-manus).

---

### autonomous-organism — DISCARD
| Attribute | Value |
|-----------|-------|
| **Language** | TypeScript (7,570 lines) + JavaScript (1,168 lines) |
| **What it is** | Self-evolving digital entity simulation |

**Reason:** Experimental research project about digital adaptation/evolution. Each module is a single index.js file (decision, factory, immune, memory, scheduler, sense). Shallow implementation — more concept than code. No trading/finance relevance.

---

### cyber-shell-x-nexus — DISCARD
| Attribute | Value |
|-----------|-------|
| **Language** | TypeScript (16,909 lines) + JavaScript (566 lines) |
| **What it is** | AI-assisted cybersecurity platform with vulnerability scanning |

**Reason:** Cybersecurity tool — no trading/finance/quant relevance. Multi-agent security orchestration is interesting but not applicable. Already has Android app and CLI interface.

---

### project-nomad-offline — DISCARD
| Attribute | Value |
|-----------|-------|
| **Language** | TypeScript (37,251 lines) |
| **What it is** | Offline-first knowledge/education server |

**Reason:** Self-contained offline knowledge server. No AI/ML/trading code. AdonisJS backend with admin panel. Not relevant to QNAI.

---

### PromptForgeAI — DISCARD
| Attribute | Value |
|-----------|-------|
| **Language** | TypeScript (2,184 lines) + JavaScript (1,149 lines) |
| **What it is** | AI prompt marketplace/generator |

**Reason:** Prompt management tool. Small codebase with basic Next.js app. No trading/AI implementation value.

---

### sim — DISCARD (already partially merged)
| Attribute | Value |
|-----------|-------|
| **Language** | TypeScript (255,211 lines) + Python (1,554 lines) |
| **Branches** | 27 (Kalshi/Polymarket tools already ported in Task 4-c) |
| **What it is** | AI agent workflow builder (Sim.ai clone) |

**Reason:** Already merged in Task 4-c — Kalshi broker (1,272 lines Python) and Polymarket enhancements (+789 lines Python) ported to execution layer. Remaining code is TypeScript workflow builder UI — not Python-compatible. No additional value for QNAI.

---

## Detailed Audit Per Repo

### 1. agentcloud
- **Primary Language:** Python (backend) + TypeScript (frontend) + Rust (vector DB proxy)
- **LOC:** Python 5,236 | TS 66,195 | Rust 5,508
- **Branches:** 3 (main only)
- **Key Files:** agent-backend/src/crew/, agent-backend/src/tools/, agent-backend/src/chat/
- **Unique Implementations:** CrewAI integration, RAG tool, Docker notebook executor, Qdrant vector DB proxy
- **Classification:** C2-SUPPORT — CrewAI patterns and RAG retrievers useful

### 2. agenticSeek
- **Primary Language:** Python
- **LOC:** Python 7,183 | JS 856
- **Branches:** 3 (main only)
- **Key Files:** sources/agents/ (6 agents), sources/router.py, sources/tools/ (9 tools), sources/memory.py
- **Unique Implementations:** ML-based agent router (BART + AdaptiveClassifier), safety module, multi-language code interpreters
- **Classification:** C2-SUPPORT — Agent router and safety module valuable

### 3. ai-engineering-hub
- **Primary Language:** Python + TypeScript
- **LOC:** Python 40,928 | TS 45,512
- **Branches:** 3 (main only)
- **Key Files:** stock-portfolio-analysis-agent/, financial-analyst-deepseek/, autogen-stock-analyst/, agentic_rag/
- **Unique Implementations:** 93+ AI projects including 3 financial agents, RAG agents, MCP demos
- **Classification:** C2-SUPPORT — Financial agent implementations directly relevant

### 4. ai-financial-agent
- **Primary Language:** TypeScript (Next.js)
- **LOC:** TS 14,119 | JS 475
- **Branches:** 3 (main only)
- **Key Files:** lib/ai/tools/financial-tools.ts, lib/ai/prompts.ts, lib/api/stock-filters.ts
- **Unique Implementations:** 7 financial data tools (stock prices, income, balance sheet, cash flow, metrics, search, news), FinancialDatasets.ai API, tool deduplication
- **Classification:** C2-CORE — Financial data integration directly mergeable

### 5. ai-manus
- **Primary Language:** Python (backend) + TypeScript (frontend)
- **LOC:** Python 13,938 | TS 3,483
- **Branches:** 15 (3 with unique code, already partially merged)
- **Key Files:** backend/app/domain/ (14 models), backend/app/infrastructure/ (8 adapters), backend/app/interfaces/api/
- **Unique Implementations:** DDD architecture, agent task runner, sandbox, browser use, MCP support. Auth/file ops/MCP config already merged.
- **Classification:** C2-CORE — Remaining domain models and infrastructure valuable

### 6. aikit
- **Primary Language:** TypeScript
- **LOC:** TS 18,343 | JS 1,080
- **Branches:** 3 (main only)
- **Key Files:** skills/ (9 skill dirs), src/ (SDK), plugins/
- **Unique Implementations:** Skill/plugin architecture for AI coding agents
- **Classification:** C2-REFERENCE — Skill system pattern reference

### 7. autonomous-organism
- **Primary Language:** TypeScript + JavaScript
- **LOC:** TS 7,570 | JS 1,168
- **Branches:** 3 (main only)
- **Key Files:** decision/, factory/, immune/, memory/, scheduler/, sense/ — all single index.js files
- **Unique Implementations:** Self-modifying parameter system (shallow)
- **Classification:** DISCARD — Shallow implementation, no trading relevance

### 8. awesome-quant
- **Primary Language:** Markdown
- **LOC:** Python 1,507 (scrapers only)
- **Branches:** 3 (main only)
- **Key Files:** README.md (94KB), cranscrape.py, parse.py
- **Unique Implementations:** None — curated list
- **Classification:** DISCARD — Awesome-list

### 9. awesome-vibe-coding
- **Primary Language:** Markdown
- **LOC:** 0 lines of code
- **Branches:** 3 (main only)
- **Key Files:** README.md
- **Unique Implementations:** None — curated list
- **Classification:** DISCARD — Awesome-list

### 10. bloomberg-terminal
- **Primary Language:** TypeScript (Next.js)
- **LOC:** TS 11,767
- **Branches:** 3 (main only)
- **Key Files:** lib/alpha-vantage.ts, lib/market-data-refresh.ts, lib/redis.ts, lib/scheduler.ts, components/bloomberg/
- **Unique Implementations:** Alpha Vantage integration, real-time market data refresh, terminal-style UI
- **Classification:** C2-SUPPORT — Alpha Vantage data source and UI patterns

### 11. cyber-shell-x-nexus
- **Primary Language:** TypeScript + JavaScript
- **LOC:** TS 16,909 | JS 566
- **Branches:** 3 (main only)
- **Key Files:** client/src/, cybershell-commands/, android-assistant/, cli-interface.js
- **Unique Implementations:** Security vulnerability scanner, recon engine, CVSS v3.1 risk engine
- **Classification:** DISCARD — Cybersecurity, not trading

### 12. developer-portfolios
- **Primary Language:** Markdown + JSON
- **LOC:** Python 1,511 (link checker)
- **Branches:** 3 (main only)
- **Key Files:** README.md (114KB), feed.json (180KB)
- **Unique Implementations:** None — portfolio directory
- **Classification:** DISCARD — Directory listing

### 13. famlyzer-ai
- **Primary Language:** TypeScript (Next.js)
- **LOC:** TS 12,767
- **Branches:** 3 (main only)
- **Key Files:** src/ (7 AI agent pages, components, lib)
- **Unique Implementations:** 7 life-planning AI agents (financial, career, family, health)
- **Classification:** DISCARD — Life planning, not trading

### 14. founders-kit
- **Primary Language:** Markdown
- **LOC:** 0 lines of code
- **Branches:** 3 (main only)
- **Key Files:** README.md (42KB)
- **Unique Implementations:** None — resource directory
- **Classification:** DISCARD — Resource list

### 15. free-AI-Project-Gallery
- **Primary Language:** Markdown
- **LOC:** 0 lines of code
- **Branches:** 3 (main only)
- **Key Files:** README.md (link table)
- **Unique Implementations:** None — link table
- **Classification:** DISCARD — Link table

### 16. ghoststudio-ai
- **Primary Language:** Python (engine) + TypeScript (frontend)
- **LOC:** Python 27,563 | TS 35,522 | JS 676
- **Branches:** 3 (main only)
- **Key Files:** engine/core.py, engine/failsafe.py, engine/scheduler.py, engine/memory.py, engine/agents/ (8 agents), engine/publishers/ (20+)
- **Unique Implementations:** 8-layer failsafe system, SQLite scheduler, 8-agent content pipeline, 20+ publisher integrations
- **Classification:** C2-CORE — Failsafe system and scheduler directly mergeable

### 17. mnemosyne
- **Primary Language:** Python + TypeScript
- **LOC:** Python 30,681 | TS 45,941 | JS 4,684
- **Branches:** 4 (1 remote, already merged — 0 unique commits)
- **Key Files:** skills/finance/, skills/stock-analysis-skill/, skills/market-research-reports/, skills/ (50+ total), src/ (Next.js app)
- **Unique Implementations:** Finance skill, stock analysis skill, market research skill, 50+ AI skills, MCP server, multi-LLM hub
- **Classification:** C2-CORE — Finance skills and MCP integration directly mergeable

### 18. nanggroe-iot
- **Primary Language:** Python + TypeScript
- **LOC:** Python 30,681 | TS 62,397 | JS 2,722
- **Branches:** 13 (10 dependabot — dependency bumps only)
- **Key Files:** skills/ (same as mnemosyne), android/, db/, agent-ctx/
- **Unique Implementations:** IoT WebSocket device control, Capacitor mobile app, hardware sensor integration
- **Classification:** C2-SUPPORT — IoT layer unique, skills overlap with mnemosyne

### 19. openhuman
- **Primary Language:** Rust + TypeScript
- **LOC:** Rust 687,512 | TS 303,511 | JS 5,043
- **Branches:** 3 (main only)
- **Key Files:** Cargo.toml (6 binaries), app/src-tauri/ (Tauri desktop), app/src/ (React frontend)
- **Unique Implementations:** Memory tree system, local-first AI, Tauri native app, Slack/Gmail backfill, MCP
- **Classification:** C2-REFERENCE — Architecture patterns, too large/Rust for direct merge

### 20. pase-fx
- **Primary Language:** TypeScript (Next.js + Express)
- **LOC:** TS 18,068 | JS 171
- **Branches:** 4 (1 remote with accessibility fixes)
- **Key Files:** backend/src/ (Express API), constants.ts (20K+ lines of forex data), components/ (UI)
- **Unique Implementations:** Forex-specific market data, currency pair constants, investing.com integration
- **Classification:** C2-SUPPORT — Forex data constants and integration patterns

### 21. polymarket-cli
- **Primary Language:** Rust
- **LOC:** Rust 8,668
- **Branches:** 3 (main only)
- **Key Files:** src/commands/ (16 modules), src/auth.rs, src/config.rs, src/main.rs
- **Unique Implementations:** Complete Polymarket CLOB API coverage (markets, events, series, CLOB, CTF, bridge, wallet, sports, tags, comments)
- **Classification:** C2-CORE — Reference for Polymarket API completeness

### 22. project-nomad-offline
- **Primary Language:** TypeScript (AdonisJS)
- **LOC:** TS 37,251 | JS 30
- **Branches:** 3 (main only)
- **Key Files:** admin/ (AdonisJS app), install/, collections/
- **Unique Implementations:** Offline knowledge server, self-hosted education platform
- **Classification:** DISCARD — Not AI/trading relevant

### 23. rtk-reduce-tokenLLM
- **Primary Language:** Rust
- **LOC:** Rust 62,028 | TS 1,027 | Python 155
- **Branches:** 3 (main only)
- **Key Files:** src/main.rs (101K lines!), src/filters/, src/parser/, src/hooks/, src/learn/
- **Unique Implementations:** 60-90% LLM token reduction, code-aware compression, adaptive learning
- **Classification:** C2-SUPPORT — Cost optimization tool for LLM API calls

### 24. sim
- **Primary Language:** TypeScript (React/Bun) + Python
- **LOC:** TS 255,211 | Python 1,554
- **Branches:** 27 (already audited and partially merged in Task 4-c)
- **Key Files:** packages/ (workflow engine), apps/ (Sim.ai clone)
- **Unique Implementations:** Already merged — Kalshi + Polymarket brokers ported to Python
- **Classification:** DISCARD — Already merged, remaining is TS workflow UI

### 25. skales
- **Primary Language:** TypeScript (Electron) + JavaScript
- **LOC:** TS 57,579 | JS 4,993
- **Branches:** 3 (main only)
- **Key Files:** apps/web/ (Next.js), electron/ (desktop app)
- **Unique Implementations:** 15+ AI providers, WhatsApp/Telegram bots, offline Ollama
- **Classification:** C2-REFERENCE — Multi-provider LLM patterns and messaging bots

### 26. sled
- **Primary Language:** TypeScript + JavaScript
- **LOC:** TS 17,829 | JS 4,403
- **Branches:** 3 (main only)
- **Key Files:** app/ (Cloudflare Workers), server-client/ (WebSocket relay)
- **Unique Implementations:** Voice-to-agent control, mobile coding agent interface
- **Classification:** C2-REFERENCE — Voice interaction pattern

### 27. suna
- **Primary Language:** Python (backend) + TypeScript (frontend)
- **LOC:** Python 112,550 (backend 110K + sdk 2K) | TS 251,469
- **Branches:** 3 (main only)
- **Key Files:** backend/core/ (50+ modules), backend/core/agentpress/, backend/core/tools/ (30+ tools), backend/core/memory/, backend/core/sandbox/
- **Unique Implementations:** AgentPress framework, thread manager, tool registry, 30+ tools, MCP, memory, sandbox, agent builder
- **Classification:** C2-CORE — Complete agent platform for direct merge

### 28. superpowers
- **Primary Language:** Markdown + JavaScript
- **LOC:** TS 168 | JS 1,210 | Python 168
- **Branches:** 3 (main only)
- **Key Files:** skills/ (14 skill dirs with SKILL.md)
- **Unique Implementations:** 14 AI coding agent skills (debugging, TDD, code review, parallel agents)
- **Classification:** C2-REFERENCE — Skill prompt templates

### 29. yolobox
- **Primary Language:** Go
- **LOC:** Go 1,847
- **Branches:** 3 (main only)
- **Key Files:** cmd/ (yolobox binary), Makefile, Dockerfile
- **Unique Implementations:** Container sandbox for AI coding agents with home directory protection
- **Classification:** C2-REFERENCE — Sandbox isolation pattern

### 30. PromptForgeAI
- **Primary Language:** TypeScript (Next.js)
- **LOC:** TS 2,184 | JS 1,149
- **Branches:** 3 (main only)
- **Key Files:** src/ (agents, components, database, pages, utils)
- **Unique Implementations:** Prompt marketplace/generator
- **Classification:** DISCARD — Basic prompt tool, no trading value

---

## Merge Priority Recommendations

### Phase 1: Immediate Merge (C2-CORE)
1. **suna** — AgentPress framework + tool registry + memory system (~15,000 lines of core Python)
2. **ai-manus** — Remaining domain models + infrastructure adapters (~5,000 lines)
3. **ai-financial-agent** — Financial data tools ported to Python (~2,000 lines)
4. **polymarket-cli** — Reference for Polymarket API gaps (port missing endpoints ~1,000 lines)
5. **mnemosyne** — Finance + stock-analysis skills ported to Python (~5,000 lines)
6. **ghoststudio-ai** — Failsafe system + scheduler + agent patterns (~3,000 lines)

### Phase 2: Support Integration (C2-SUPPORT)
7. **ai-engineering-hub** — Financial agent implementations (~3,000 lines)
8. **agenticSeek** — Agent router + safety module (~2,000 lines)
9. **agentcloud** — CrewAI integration + RAG tools (~2,000 lines)
10. **nanggroe-iot** — IoT WebSocket patterns (if needed) (~1,000 lines)
11. **pase-fx** — Forex constants + integration patterns (~1,500 lines)
12. **bloomberg-terminal** — Alpha Vantage integration (~500 lines)
13. **rtk-reduce-tokenLLM** — External binary for LLM cost optimization (0 lines merge — call as subprocess)

### Phase 3: Reference Only (C2-REFERENCE)
14. **openhuman** — Memory tree architecture reference
15. **skales** — Multi-provider LLM + messaging bot patterns
16. **aikit** — Skill system architecture reference
17. **superpowers** — Skill prompt templates
18. **yolobox** — Sandbox isolation design reference
19. **sled** — Voice interaction pattern reference

### No Merge (DISCARD — 12 repos)
- awesome-quant, awesome-vibe-coding, developer-portfolios, founders-kit, free-AI-Project-Gallery — pure link lists
- famlyzer-ai — life planning, not trading
- autonomous-organism — shallow experimental concept
- cyber-shell-x-nexus — cybersecurity, not trading
- project-nomad-offline — offline education, not AI/trading
- PromptForgeAI — basic prompt tool
- sim — already merged (Kalshi + Polymarket)

---

## Estimated Merge Impact

| Phase | Repos | New Python LOC | Key Deliverables |
|-------|-------|----------------|------------------|
| Phase 1 | 6 C2-CORE | ~31,000 lines | AgentPress framework, financial tools, failsafe system, stock analysis, Polymarket API |
| Phase 2 | 7 C2-SUPPORT | ~10,000 lines | Agent router, CrewAI integration, forex data, Alpha Vantage, RAG tools |
| Phase 3 | 6 C2-REFERENCE | ~0 lines (reference only) | Architecture patterns, skill templates, sandbox design |
| **Total** | **19 repos** | **~41,000 lines** | **+41K Python lines to monorepo** |

---

## Key Risks and Considerations

1. **suna's AgentPress** is tightly coupled to Supabase, LiteLLM, and Langfuse — will need significant adapter work
2. **ai-financial-agent** is all TypeScript — needs full Python port of financial tools
3. **mnemosyne finance skills** are prompt-based skill definitions — the actual API calls are in the TypeScript app, not in the Python scripts
4. **ghoststudio-ai failsafe** uses SQLite — QNAI uses PostgreSQL + Redis, needs adapter
5. **polymarket-cli** is Rust — port endpoints by reading the source, not direct code merge
6. **nanggroe-iot** is 90% overlap with mnemosyne — only unique IoT features worth extracting
7. **ai-manus** already had auth/file ops/MCP merged — remaining merge is smaller than expected

---

*End of C2 Repository Deep Audit*
