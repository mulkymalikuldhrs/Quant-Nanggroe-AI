# RISK REGISTER — AI-MultiColony-Ecosystem (Cluster 2)

> Document Version: 1.0.0 | Date: 2026-06-10 | Status: Active

---

## Risk Scoring Framework

| Score | Probability | Impact |
|-------|-----------|--------|
| 1 | Very Unlikely (<5%) | Negligible |
| 2 | Unlikely (5-20%) | Minor |
| 3 | Possible (20-50%) | Moderate |
| 4 | Likely (50-80%) | Major |
| 5 | Almost Certain (>80%) | Catastrophic |

**Risk Score = Probability × Impact**

| Score Range | Level | Action |
|-------------|-------|--------|
| 1-4 | Low | Monitor |
| 5-9 | Medium | Mitigate |
| 10-15 | High | Active Mitigation Required |
| 16-25 | Critical | Immediate Action / Stop Work |

---

## Technical Risks

### R2-T01: Rust-Python FFI Instability
- **Description**: openfang's Rust core (14 crates, 137K LOC) requires stable FFI bindings to Python. PyO3 compatibility issues across Python versions could cause runtime crashes.
- **Probability**: 3 | **Impact**: 4 | **Score**: 12 (HIGH)
- **Mitigation**: Pin PyO3 version, create comprehensive FFI integration tests, maintain Python-only fallback for critical paths
- **Owner**: Platform Team
- **Status**: Open

### R2-T02: Agent Sandbox Escape
- **Description**: Docker sandbox from OpenHands/ai-manus/suna executes untrusted code. Container escape vulnerability could compromise host system.
- **Probability**: 2 | **Impact**: 5 | **Score**: 10 (HIGH)
- **Mitigation**: Use gVisor/runsc isolation, drop all capabilities, read-only filesystem, network isolation, regular security audits
- **Owner**: Security Team
- **Status**: Open

### R2-T03: WASM Runtime Memory Corruption
- **Description**: openfang's WASM sandbox with dual metering could have memory corruption bugs leading to undefined behavior.
- **Probability**: 2 | **Impact**: 4 | **Score**: 8 (MEDIUM)
- **Mitigation**: WASM sandbox tests, memory sanitizers, wasmtime runtime hardening
- **Owner**: Runtime Team
- **Status**: Open

### R2-T04: Multi-LLM Provider Failover Cascade
- **Description**: AI-MultiColony's 7-provider failover could cascade failures if multiple providers have simultaneous outages.
- **Probability**: 3 | **Impact**: 3 | **Score**: 9 (MEDIUM)
- **Mitigation**: Circuit breaker per provider, request queue with backpressure, local LLM fallback (Ollama via agenticSeek), provider health monitoring
- **Owner**: Infrastructure Team
- **Status**: Open

### R2-T05: Browser Automation Detection
- **Description**: CloakBrowser's stealth patches (58 C++ modifications) could become detectable as Chromium updates change browser fingerprints.
- **Probability**: 4 | **Impact**: 3 | **Score**: 12 (HIGH)
- **Mitigation**: Automated Chromium version tracking, CI pipeline for patch compatibility, fingerprint testing suite, community patch updates
- **Owner**: Browser Team
- **Status**: Open

### R2-T06: Skill Format Fragmentation
- **Description**: Four different skill formats exist across repos (openfang HAND.toml, oh-my-claudecode SKILL.md, superpowers SKILL.md, nanobot skills/). Consolidation could break existing skills.
- **Probability**: 3 | **Impact**: 3 | **Score**: 9 (MEDIUM)
- **Mitigation**: Define canonical SKILL.md v2 spec, write migration scripts from each format, backward compatibility layer
- **Owner**: Architecture Team
- **Status**: Open

### R2-T07: OpenHands Monorepo Complexity
- **Description**: OpenHands is the largest repo with 16+ CI workflows, enterprise features, and complex dependency tree. Integration could introduce instability.
- **Probability**: 3 | **Impact**: 3 | **Score**: 9 (MEDIUM)
- **Mitigation**: Extract only core agent framework (openhands/agenthub + openhands/runtime), leave enterprise features behind, thorough integration testing
- **Owner**: Integration Team
- **Status**: Open

### R2-T08: Memory System Data Loss
- **Description**: openhuman Memory Tree and Letta/MemGPT both manage persistent agent state. Data corruption or migration errors could lose agent memories.
- **Probability**: 2 | **Impact**: 4 | **Score**: 8 (MEDIUM)
- **Mitigation**: Event sourcing with append-only log, automated backups, migration dry-run mode, checksum verification
- **Owner**: Data Team
- **Status**: Open

---

## Integration Risks

### R2-I01: License Incompatibility — AGPL (agentcloud)
- **Description**: agentcloud uses AGPL-3.0 which is a viral copyleft license. Merging AGPL code with MIT/Apache code would require the entire project to become AGPL.
- **Probability**: 4 | **Impact**: 5 | **Score**: 20 (CRITICAL)
- **Mitigation**: Option A: Exclude agentcloud entirely, use only Qdrant Rust proxy as reference. Option B: Isolate agentcloud as standalone service behind API boundary. Option C: Rewrite RAG functionality from scratch using Qdrant + LangChain.
- **Recommendation**: Option C — Rewrite RAG pipeline. agentcloud's RAG is thin wrapper around CrewAI + Qdrant. Not worth the license contamination.
- **Owner**: Legal + Architecture Team
- **Status**: Open — Decision Required

### R2-I02: License Incompatibility — KPSL (suna)
- **Description**: suna uses "KPSL" license which is non-standard and may restrict commercial use or derivative works.
- **Probability**: 3 | **Impact**: 4 | **Score**: 12 (HIGH)
- **Mitigation**: Legal review of KPSL terms. If restrictive, extract only architectural patterns (no code), reimplement Docker runtime SDK and agent orchestration from scratch.
- **Owner**: Legal Team
- **Status**: Open — Legal Review Required

### R2-I03: Database Schema Conflicts
- **Description**: Multiple repos use different databases (SQLite, PostgreSQL, MySQL, MongoDB, Supabase, Google Sheets). Merging requires unified schema.
- **Probability**: 3 | **Impact**: 3 | **Score**: 9 (MEDIUM)
- **Mitigation**: Standardize on PostgreSQL (primary) + Redis (cache) + Qdrant (vectors). Write migration scripts per repo. Use SQLAlchemy/Alembic for schema versioning.
- **Owner**: Data Team
- **Status**: Open

### R2-I04: API Contract Conflicts
- **Description**: OpenHands uses SSE streaming, ai-manus uses Socket.IO, sim uses WebSocket, AI-MultiColony uses REST. Need unified API layer.
- **Probability**: 3 | **Impact**: 3 | **Score**: 9 (MEDIUM)
- **Mitigation**: Standardize on FastAPI with SSE for streaming + WebSocket for real-time events. Write API adapter layer for each repo's existing endpoints.
- **Owner**: API Team
- **Status**: Open

### R2-I05: Duplicate Agent Implementations
- **Description**: OpenManus, agenticSeek, and ai-manus all implement "Manus-like" general agents. OpenHands and openfang implement different agent models. Need to choose one approach.
- **Probability**: 4 | **Impact**: 3 | **Score**: 12 (HIGH)
- **Mitigation**: Use openfang's Rust agent kernel for performance-critical paths. Use OpenManus's Python agent framework for general-purpose agents. Deprecate agenticSeek and ai-manus agent implementations, extract only unique features (voice from agenticSeek, sandbox from ai-manus).
- **Owner**: Architecture Team
- **Status**: Open

### R2-I06: Frontend Technology Fragmentation
- **Description**: React (suna, agentcloud, open-lovable), Vue.js (ai-manus, QuantDinger), Next.js (sim, bloomberg-terminal), Flutter (Trading-Plan-AI), Tauri (openfang, openhuman, FinceptTerminal). Too many frontend stacks.
- **Probability**: 4 | **Impact**: 3 | **Score**: 12 (HIGH)
- **Mitigation**: Standardize on React 19 + TypeScript for web UI, Tauri for desktop. Vue.js and Flutter code preserved as reference only. Next.js apps migrated to Vite+React.
- **Owner**: Frontend Team
- **Status**: Open

---

## Operational Risks

### R2-O01: Docker Dependency for Sandboxing
- **Description**: Multiple repos require Docker for agent sandboxing. Docker daemon failures or resource exhaustion could halt all agent execution.
- **Probability**: 3 | **Impact**: 4 | **Score**: 12 (HIGH)
- **Mitigation**: Support alternative runtimes (Podman, E2B cloud, gVisor), Docker health monitoring, resource limits per container, pre-pulled images
- **Owner**: DevOps Team
- **Status**: Open

### R2-O02: LLM API Cost Explosion
- **Description**: Multi-agent systems with 20+ agents making LLM calls per task could generate massive API costs.
- **Probability**: 4 | **Impact**: 4 | **Score**: 16 (CRITICAL)
- **Mitigation**: Token budgeting per colony/task, local LLM routing for routine tasks (Ollama), token compression (openhuman TokenJuice - 80% reduction), cost monitoring dashboards, per-agent cost limits
- **Owner**: Platform Team
- **Status**: Open

### R2-O03: OpenHot Dependency (Chromium Binary)
- **Description**: CloakBrowser depends on a custom-built Chromium binary (~200MB). Binary distribution and auto-updates could fail.
- **Probability**: 3 | **Impact**: 3 | **Score**: 9 (MEDIUM)
- **Mitigation**: CDN distribution with checksums, fallback to standard Playwright when stealth not needed, version pinning
- **Owner**: Browser Team
- **Status**: Open

### R2-O04: Monitoring and Observability Gap
- **Description**: No unified monitoring across 19+ merged repos. Agent failures could go undetected.
- **Probability**: 3 | **Impact**: 3 | **Score**: 9 (MEDIUM)
- **Mitigation**: Structured logging (structlog/OpenTelemetry), agent health heartbeat system, centralized metrics (Prometheus + Grafana), distributed tracing (Jaeger)
- **Owner**: SRE Team
- **Status**: Open

---

## Business Risks

### R2-B01: Contributor Onboarding Complexity
- **Description**: The merged codebase spans Rust, Python, TypeScript, Swift, Go, and multiple frameworks. New contributors face steep learning curve.
- **Probability**: 4 | **Impact**: 3 | **Score**: 12 (HIGH)
- **Mitigation**: Clear architecture documentation, modular repo structure, contribution guides per module, "good first issue" labels, dev container setup
- **Owner**: Community Team
- **Status**: Open

### R2-B02: OpenHands Upstream Divergence
- **Description**: OpenHands is an actively maintained upstream project. Forking it for MultiColony could create maintenance burden for rebasing.
- **Probability**: 3 | **Impact**: 3 | **Score**: 9 (MEDIUM)
- **Mitigation**: Contribute changes upstream where possible, extract only needed components (not full fork), maintain compatibility layer
- **Owner**: Integration Team
- **Status**: Open

### R2-B03: Market Positioning Confusion
- **Description**: "Autonomous Agent OS" is a crowded space (Manus, Devin, Cursor, Claude Code). Unclear differentiation could limit adoption.
- **Probability**: 3 | **Impact**: 3 | **Score**: 9 (MEDIUM)
- **Mitigation**: Focus on unique differentiators: colony model, Rust performance, 40+ messaging channels, open-source-first, self-hostable, skill marketplace
- **Owner**: Product Team
- **Status**: Open

### R2-B04: Key Person Risk
- **Description**: Several repos (nanobot, nanocode, open-lovable) are single-maintainer projects. Bus factor of 1.
- **Probability**: 3 | **Impact**: 2 | **Score**: 6 (MEDIUM)
- **Mitigation**: Code review and knowledge sharing for all merged modules, documentation of design decisions, pair programming on critical paths
- **Owner**: Engineering Manager
- **Status**: Open

---

## Compliance Risks

### R2-C01: Computer Use Legal Liability
- **Description**: open-computer-use automates GUI interactions which may violate terms of service of some applications or be considered unauthorized access.
- **Probability**: 3 | **Impact**: 4 | **Score**: 12 (HIGH)
- **Mitigation**: Clear user responsibility disclaimer, opt-in consent for each automated action, audit logging of all GUI interactions, terms-of-service compliance checker
- **Owner**: Legal Team
- **Status**: Open

### R2-C02: Data Privacy (Agent Memory)
- **Description**: Agent memory systems store conversation history, credentials, and potentially PII. GDPR/CCPA compliance required.
- **Probability**: 3 | **Impact**: 4 | **Score**: 12 (HIGH)
- **Mitigation**: Data minimization in memory, user data deletion API, encryption at rest (AES-256 from AI-MultiColony), access logging, privacy-by-design
- **Owner**: Legal + Security Team
- **Status**: Open

### R2-C03: Credential Storage Security
- **Description**: AI-MultiColony stores encrypted credentials. Key management must be production-grade.
- **Probability**: 2 | **Impact**: 5 | **Score**: 10 (HIGH)
- **Mitigation**: Use HashiCorp Vault for key management, rotate encryption keys regularly, audit credential access, hardware security module (HSM) for production
- **Owner**: Security Team
- **Status**: Open

---

## Risk Heat Map

```
IMPACT →    1-Negligible  2-Minor  3-Moderate  4-Major  5-Catastrophic
PROB ↓
5-Certain  |              |         |           |         |
4-Likely   |              |         | R2-I05    | R2-T05  | R2-I01
           |              |         | R2-I06    | R2-B01  | R2-O02
           |              |         | R2-O02    | R2-C01  |
3-Possible |              |         | R2-T01    | R2-T02  | R2-I02
           |              |         | R2-T04    | R2-I05* | R2-C02
           |              |         | R2-T06    | R2-I06* | R2-C03
           |              |         | R2-I03    |         |
           |              |         | R2-I04    |         |
           |              |         | R2-O01    |         |
           |              |         | R2-O04    |         |
           |              |         | R2-B02    |         |
           |              |         | R2-B03    |         |
2-Unlikely |              |         | R2-T03    | R2-T08  |
           |              |         | R2-O03    |         |
1-V.Unlikely|             |         |           |         |
```

---

## Top 10 Risks by Score

| Rank | ID | Description | Score | Level |
|------|----|-------------|-------|-------|
| 1 | R2-I01 | AGPL License (agentcloud) | 20 | CRITICAL |
| 2 | R2-O02 | LLM API Cost Explosion | 16 | CRITICAL |
| 3 | R2-I02 | KPSL License (suna) | 12 | HIGH |
| 4 | R2-T01 | Rust-Python FFI Instability | 12 | HIGH |
| 5 | R2-T05 | Browser Automation Detection | 12 | HIGH |
| 6 | R2-I05 | Duplicate Agent Implementations | 12 | HIGH |
| 7 | R2-I06 | Frontend Fragmentation | 12 | HIGH |
| 8 | R2-O01 | Docker Dependency | 12 | HIGH |
| 9 | R2-B01 | Contributor Onboarding | 12 | HIGH |
| 10 | R2-C01 | Computer Use Legal Liability | 12 | HIGH |

---

## Risk Acceptance Criteria

Risks with score ≤ 4 may be accepted without active mitigation. All risks ≥ 5 must have documented mitigation plans. Critical risks (≥ 16) require executive approval before proceeding.

---

## Escalation Procedures

| Trigger | Action | Owner |
|---------|--------|-------|
| Any risk reaches CRITICAL (≥16) | Stop affected work stream, convene risk review within 24h | CTO |
| 3+ HIGH risks become realized simultaneously | Pause merge, full risk reassessment | Engineering Manager |
| License incompatibility confirmed | Stop code integration, legal review within 48h | Legal Team |
| Security vulnerability in sandbox | Disable sandbox, switch to API-only mode | Security Team |

---

## Phase-Specific Risk Summary

| Phase | Top Risks | Mitigation Priority |
|-------|-----------|-------------------|
| Phase 1: Foundation | R2-I01 (AGPL), R2-I02 (KPSL), R2-T01 (FFI) | License review, Rust-Python binding tests |
| Phase 2: Runtime | R2-O01 (Docker), R2-T02 (Sandbox Escape), R2-T03 (WASM) | Security hardening, alternative runtimes |
| Phase 3: Agents | R2-I05 (Duplicate Agents), R2-O02 (LLM Costs), R2-T04 (Failover) | Agent consolidation, cost controls |
| Phase 4: Tools | R2-T05 (Browser Detection), R2-C01 (Computer Use Legal) | Browser patch pipeline, legal review |
| Phase 5: Intelligence | R2-T08 (Memory Loss), R2-C02 (Privacy), R2-C03 (Credentials) | Data protection, key management |
| Phase 6: Production | R2-B01 (Onboarding), R2-B02 (Upstream), R2-O04 (Monitoring) | Documentation, observability stack |
