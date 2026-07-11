# HERMES QUANT OPERATING SYSTEM - PULL REQUEST GUIDE

## PR Template

### Title Format
```
[<scope>] <type>: <short description>
```

**Scopes:** `agent`, `tools`, `risk`, `infra`, `docs`, `config`, `testing`, `execution`

**Types:** `feat`, `fix`, `refactor`, `docs`, `chore`, `perf`, `test`, `breaking`

**Examples:**
- `[tools] feat: add correlation monitor to portfolio tool`
- `[risk] fix: hardcoded daily limit check bypass in edge case`
- `[infra] refactor: consolidate watchdog and keeper into unified monitor`
- `[docs] docs: add architecture diagram for 5-layer agent system`

---

### Pull Request Template

```markdown
## Description
<!-- Clear description of what this PR does and why -->

## Type of Change
- [ ] feat: New feature (adds agent/tool/capability)
- [ ] fix: Bug fix (corrects existing behavior)
- [ ] refactor: Code restructure (no behavior change)
- [ ] breaking: Breaking change (modifies existing API/behavior)
- [ ] docs: Documentation update
- [ ] chore: Maintenance/dependencies
- [ ] perf: Performance improvement
- [ ] test: Test coverage

## AGENTS.md Compliance
<!-- All PRs MUST comply with AGENTS.md -->
- [ ] Risk rules remain HARDCODED (0.5%/1%/3%)
- [ ] Risk Officer FULL VETO is preserved
- [ ] Kill Switch auto-trigger logic is intact
- [ ] No override mechanism added for safety rules
- [ ] Deployment stage gate is respected (no stage skipping)

## Affected Agent Layer
- [ ] L1 - Data Layer (Market Data, Chart Vision)
- [ ] L2 - Analysis Layer (Technical, Macro, Sentiment)
- [ ] L3 - Decision Layer (Strategy, Risk Officer, Portfolio)
- [ ] L4 - Execution Layer (Execution, Kill Switch)
- [ ] L5 - Learning Layer (Journal, Auditor, Research)
- [ ] Infrastructure (Watchdog, Keeper, On-Boot)
- [ ] Configuration (config/, requirements.txt)
- [ ] Documentation (*.md, docs/)

## Testing
- [ ] Python compilation passes (`python3 -m py_compile <file>`)
- [ ] Tool initialization works without errors
- [ ] Risk Officer veto still functions correctly
- [ ] Kill switch triggers on daily/weekly limit breach
- [ ] No hardcoded API keys or credentials added

## Checklist
- [ ] Code follows AGENTS.md principles
- [ ] No subjective trading logic added (all decisions must be data-grounded)
- [ ] Logging added for all new operations
- [ ] Backward compatible (or breaking change is documented)
- [ ] Changelog updated (CHANGELOG.md)

## Related Issues
<!-- Link any related issues -->
Closes #
Related to #
```

---

## PR Review Criteria

### Mandatory Checks (Auto-Reject if Failed)

1. **Risk Rule Integrity**: Any PR that introduces the ability to override, bypass, or dynamically modify the hardcoded risk rules (0.5% per trade, 1% daily, 3% weekly) MUST be rejected. These values are constants, not configuration variables.

2. **Risk Officer VETO**: The Risk Officer tool must maintain FULL VETO authority. No PR may introduce a mechanism for other agents or user commands to circumvent a Risk Officer rejection.

3. **Kill Switch Independence**: The Kill Switch must remain independently triggerable. No PR may add a dependency that could prevent the Kill Switch from activating when risk limits are breached.

4. **Deployment Stage Gate**: No PR may skip deployment stages. The progression from Research Lab through Full Autonomous must require explicit user approval with documented performance metrics.

5. **No Subjective Trading Logic**: All trading decisions must be grounded in numerical data. PRs that introduce "vibes-based" analysis, subjective opinions, or ungrounded LLM outputs as trade signals must be rejected.

### Quality Checks

1. **Tool Interface Consistency**: New tools must follow the existing tool interface pattern (class-based with standard methods).

2. **Error Handling**: All new code must have try/except blocks with proper logging via the standard logger.

3. **Memory Management**: New tools must not create unbounded data structures. Use rolling windows or capped lists.

4. **Import Safety**: Tool imports in `hermes_quant.py` must be wrapped in try/except with `TOOLS_AVAILABLE` flag.

5. **Configuration**: New configurable parameters must have sensible defaults and be documented in `hermes-quant.yaml`.

---

## PR Categories

### Feature PRs (feat)
New agents, tools, or capabilities. Must include:
- Tool class with standard interface methods
- Integration in `hermes_quant.py` tool initialization
- System prompt update (if new tool is user-facing)
- Telegram command addition (if applicable)
- Testing evidence

### Bug Fix PRs (fix)
Corrections to existing behavior. Must include:
- Description of the bug and its impact
- Root cause analysis
- Fix explanation
- Verification that fix doesn't break other tools

### Breaking Change PRs (breaking)
Modifications to existing API or behavior. Must include:
- Migration guide
- Backward compatibility notes
- Approval from Owner (Mulky Malikul Dhaher)

### Infrastructure PRs (infra)
Watchdog, keeper, on-boot, deployment. Must include:
- Testing on both Termux (Android) and Linux
- Restart behavior verification
- Logging verification

---

## PR Workflow

```
1. Fork / Branch
   git checkout -b feat/my-feature

2. Develop
   - Follow AGENTS.md principles
   - Write code with proper error handling
   - Add logging

3. Test
   python3 -m py_compile src/tools/new_tool.py
   python3 src/hermes_quant.py --dry-run  # if available

4. Document
   - Update CHANGELOG.md
   - Update STRUCTURE.md (if new files)
   - Update ARCHITECTURE.md (if new layer/component)

5. Submit
   - Create PR using template above
   - Fill all checklist items
   - Tag reviewers

6. Review
   - Mandatory AGENTS.md compliance check
   - Risk rule integrity verification
   - Code quality review
   - Testing verification

7. Merge
   - Squash merge preferred
   - Delete branch after merge
```

---

## Current Open PRs & Proposed Changes

### PR-001: Autonomous Decision Loop Enhancement
**Status:** Proposed
**Scope:** `[agent]`
**Type:** `feat`
**Description:** Enhance the main agent loop to support autonomous market scanning at configurable intervals. Currently, the agent only responds to Telegram messages. This PR would add a scheduled analysis cycle where the agent proactively scans configured markets, generates scenarios, and reports findings without user prompting.

**Key Changes:**
- Add `autonomous_loop` method to `HermesQuantOS`
- Configurable scan intervals per market (e.g., XAUUSD every 15min, SHIB every 5min)
- Auto-generate 3-scenario analysis when confluence score >= 3/5
- Telegram notification for high-confluence setups only
- Risk Officer auto-check before any notification

**AGENTS.md Compliance:** Passive monitoring with user notification only. No auto-execution at Research Lab stage.

---

### PR-002: Correlation Monitor Integration
**Status:** Proposed
**Scope:** `[tools]`
**Type:** `feat`
**Source:** Quant-Nanggroe-AI architecture
**Description:** Port the Correlation Monitor from Quant-Nanggroe-AI to block execution when correlation between active assets exceeds 0.70. This prevents over-concentration in correlated positions.

**Key Changes:**
- New `correlation_monitor.py` tool
- Integration with Portfolio Tool for position tracking
- Risk Officer checkpoint addition (correlation check)
- Block execution if correlation > 0.70 between any open positions

**AGENTS.md Compliance:** Strengthens risk management. No override possible.

---

### PR-003: Darwinian Strategy Evolution
**Status:** Proposed
**Scope:** `[tools]`
**Type:** `feat`
**Source:** Quant-Nanggroe-AI v15.2.0
**Description:** Implement strategy lifecycle management where strategies with negative expectancy over a statistically significant sample are automatically KILLED and resources shifted to higher-performing variants.

**Key Changes:**
- Extend `strategy_lifecycle.py` with auto-KILL on negative expectancy over 20 trades
- Strategy performance tracking in SQLite
- Automatic resource reallocation
- Audit trail for all strategy lifecycle events

---

### PR-004: Vibe-Trading Alpha Zoo Integration
**Status:** Proposed
**Scope:** `[tools]`
**Type:** `feat`
**Source:** Vibe-Trading v0.1.8 (450+ alphas)
**Description:** Integrate the Alpha Zoo from Vibe-Trading (qlib158, alpha101, gtja191, academic) as an additional analysis layer. Use the 452 pre-built quant alphas for confluence scoring alongside existing SMC analysis.

**Key Changes:**
- Port alpha factor registry and computation engine
- Add alpha-based confluence signals to Strategy Tool
- Alpha purity enforcement (AST allowlist scan)
- Lookahead bias prevention (sentinel future-row injection)

---

### PR-005: AutoHedge Swarm Pipeline
**Status:** Proposed
**Scope:** `[execution]`
**Type:** `feat`
**Source:** AutoHedge by The Swarm Corporation
**Description:** Adapt the AutoHedge multi-agent pipeline (Director -> Quant -> Risk -> Execution) as an alternative execution mode for crypto markets. Focus on Solana venue support initially.

**Key Changes:**
- New swarm execution mode in Execution Tool
- Director Agent for thesis generation
- Quant Agent for statistical validation
- Risk Manager Agent for position sizing (subordinate to Hermes Risk Officer)
- Execution Agent for order generation
- Solana venue integration via Jupiter API

---

**Document maintained by Mulky Malikul Dhaher**
**Repository: github.com/mulkymalikuldhrs/hermes-quant-os**
