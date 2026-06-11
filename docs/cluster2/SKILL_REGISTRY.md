# AI-MultiColony-Ecosystem — Skill Registry

> Cluster 2 Skill System Design Document
> Version: 0.1.0-draft | Status: Pre-Implementation | Classification: Internal

---

## 1. Overview

The Skill Registry defines the unified skill system for AI-MultiColony-Ecosystem.
Skills are reusable, composable, testable procedures that agents can activate to
perform complex multi-step tasks. This design unifies skill formats from openfang
(modular skills), oh-my-claudecode (28 agents, 30 skills), and superpowers
(platform-agnostic methodology, TDD-first).

**Core principle**: A skill is a tested, documented, versioned procedure that
combines tool calls, LLM reasoning, and conditional logic into a reusable unit.
Skills are to agents what libraries are to programs.

---

## 2. SKILL.md Format Specification

### 2.1 Canonical Skill Definition

Every skill is defined by a `SKILL.md` file plus optional implementation code.
The format unifies the best elements of:

- **superpowers**: SKILL.md format with TDD methodology
- **oh-my-claudecode**: Skill activation and routing patterns
- **openfang**: Modular skill composition and 40 channel adapters

```markdown
# Skill: {skill_name}

## Metadata
- **skill_id**: `{category}.{name}` (e.g., `coding.refactor_extract_method`)
- **version**: {semver} (e.g., `1.2.0`)
- **author**: {author_name_or_org}
- **license**: {license_identifier}
- **created**: {ISO8601_date}
- **updated**: {ISO8601_date}
- **status**: `draft` | `experimental` | `stable` | `deprecated`

## Description
{One-paragraph description of what this skill does and when to use it.}

## Activation Triggers
- **explicit**: Agent explicitly invokes this skill
- **pattern**: Task matches pattern `{regex_or_description}`
- **keyword**: Task contains keywords: `{keyword_list}`
- **context**: Agent is in context: `{context_description}`

## Prerequisites
- **required_tools**: [{list_of_mcp_tools}]
- **required_skills**: [{list_of_other_skills}]
- **required_capabilities**: [{list_of_agent_capabilities}]
- **required_memory**: {memory_requirements}
- **required_llm**: {model_requirements}

## Parameters
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| {name} | {type} | {yes/no} | {value} | {description} |

## Procedure
1. {step_1_description}
   - Tool: `{tool_name}` with `{args}`
   - Expected: {expected_outcome}
   - On failure: {failure_handling}
2. {step_2_description}
   ...

## Outputs
- **primary**: {description_of_main_output}
- **side_effects**: {description_of_side_effects}
- **artifacts**: {files_or_data_created}

## Testing
- **unit_tests**: `{test_file_path}`
- **integration_tests**: `{test_file_path}`
- **benchmark**: {performance_benchmark}

## Examples
### Example 1: {scenario_name}
```
Input: {input_description}
Steps: {executed_steps}
Output: {output_description}
```

## Composition
- **uses**: [{skills_this_one_uses}]
- **used_by**: [{skills_that_use_this_one}]
- **conflicts**: [{skills_that_conflict}]

## Changelog
- {version} ({date}): {change_description}
```

### 2.2 Skill Implementation File

Alongside `SKILL.md`, skills have an implementation file:

```python
# skills/builtin/coding/refactor_extract_method.py

from multicolony.skills import Skill, SkillContext, SkillResult

class RefactorExtractMethod(Skill):
    """
    Extract a code block into a separate method.
    Inspired by: superpowers TDD methodology, OpenHands refactoring
    """

    skill_id = "coding.refactor_extract_method"
    version = "1.0.0"

    # Parameters with type annotations and defaults
    class Params(SkillParams):
        file_path: str           # File to refactor
        start_line: int          # Start of code block
        end_line: int            # End of code block
        method_name: str         # Name for extracted method
        class_name: str | None = None  # If within a class

    async def execute(self, ctx: SkillContext, params: Params) -> SkillResult:
        """
        Execute the skill. Each step corresponds to the procedure in SKILL.md.
        """
        # Step 1: Read the target file
        file_content = await ctx.use_tool("data.file_read", path=params.file_path)

        # Step 2: Analyze the code block
        analysis = await ctx.reason(
            f"Analyze lines {params.start_line}-{params.end_line} of {params.file_path}. "
            f"Identify: variables used, variables modified, return values.",
            context=file_content
        )

        # Step 3: Generate extracted method
        extracted_method = await ctx.reason(
            f"Generate a method named '{params.method_name}' that encapsulates "
            f"the analyzed code block. Include proper parameter passing.",
            context=analysis
        )

        # Step 4: Generate replacement code
        replacement = await ctx.reason(
            f"Generate the call to '{params.method_name}' that replaces "
            f"the original code block.",
            context=analysis
        )

        # Step 5: Apply the refactoring
        new_content = self.apply_refactoring(
            original=file_content,
            start_line=params.start_line,
            end_line=params.end_line,
            extracted_method=extracted_method,
            replacement=replacement,
            class_name=params.class_name,
        )

        await ctx.use_tool("data.file_write", path=params.file_path, content=new_content)

        # Step 6: Verify with tests
        test_result = await ctx.use_tool("code.test_run", path=params.file_path)

        # Step 7: Revert on failure (TDD-first from superpowers)
        if not test_result.success:
            await ctx.use_tool("data.file_write", path=params.file_path, content=file_content)
            return SkillResult(
                success=False,
                output="Refactoring broke tests, reverted.",
                artifacts={"test_output": test_result.output}
            )

        return SkillResult(
            success=True,
            output=f"Extracted method '{params.method_name}' successfully.",
            artifacts={"diff": self.compute_diff(file_content, new_content)}
        )
```

---

## 3. Skill Taxonomy

### 3.1 Classification Hierarchy

```
SKILLS
├── CODING
│   ├── Generation
│   │   ├── code.generate_function
│   │   ├── code.generate_class
│   │   ├── code.generate_tests
│   │   ├── code.generate_docs
│   │   └── code.generate_config
│   ├── Refactoring
│   │   ├── code.refactor_extract_method
│   │   ├── code.refactor_rename
│   │   ├── code.refactor_inline
│   │   └── code.refactor_simplify
│   ├── Debugging
│   │   ├── code.debug_analyze_error
│   │   ├── code.debug_trace_execution
│   │   └── code.debug_fix_bug
│   ├── Review
│   │   ├── code.review_security
│   │   ├── code.review_performance
│   │   ├── code.review_style
│   │   └── code.review_completeness
│   └── DevOps
│       ├── code.docker_setup
│       ├── code.ci_configure
│       └── code.deploy_prepare
│
├── RESEARCH
│   ├── Search
│   │   ├── research.web_search
│   │   ├── research.academic_search
│   │   └── research.code_search
│   ├── Analysis
│   │   ├── research.summarize_paper
│   │   ├── research.compare_sources
│   │   ├── research.fact_check
│   │   └── research.extract_entities
│   └── Synthesis
│       ├── research.write_report
│       ├── research.create_bibliography
│       └── research.build_knowledge_graph
│
├── TRADING
│   ├── Analysis
│   │   ├── trading.technical_analysis
│   │   ├── trading.fundamental_analysis
│   │   ├── trading.sentiment_analysis
│   │   └── trading.risk_assessment
│   ├── Execution
│   │   ├── trading.place_order
│   │   ├── trading.set_stop_loss
│   │   └── trading.rebalance_portfolio
│   └── Monitoring
│       ├── trading.watch_price
│       ├── trading.alert_threshold
│       └── trading.performance_report
│
├── CREATIVE
│   ├── Content
│   │   ├── creative.write_article
│   │   ├── creative.write_email
│   │   ├── creative.write_social_post
│   │   └── creative.write_script
│   ├── Design
│   │   ├── creative.ui_mockup
│   │   ├── creative.design_system
│   │   └── creative.generate_image_prompt
│   └── Multimedia
│       ├── creative.video_script
│       ├── creative.audio_transcribe
│       └── creative.presentation_build
│
├── MANAGEMENT
│   ├── Planning
│   │   ├── mgmt.task_decompose
│   │   ├── mgmt.sprint_plan
│   │   ├── mgmt.resource_estimate
│   │   └── mgmt.risk_identify
│   ├── Coordination
│   │   ├── mgmt.assign_tasks
│   │   ├── mgmt.track_progress
│   │   ├── mgmt.escalate_issue
│   │   └── mgmt.sync_stakeholders
│   └── Reporting
│       ├── mgmt.status_report
│       ├── mgmt.metrics_dashboard
│       └── mgmt.retrospective
│
└── INFRASTRUCTURE
    ├── Deployment
    │   ├── infra.deploy_service
    │   ├── infra.scale_service
    │   ├── infra.rollback_service
    │   └── infra.health_check
    ├── Security
    │   ├── infra.vuln_scan
    │   ├── infra.config_audit
    │   └── infra.access_review
    └── Monitoring
        ├── infra.log_analyze
        ├── infra.alert_configure
        └── infra.capacity_plan
```

---

## 4. Skills from Each Repo Mapped

### 4.1 oh-my-claudecode Skills (30 skills)

| oh-my-claudecode Skill | Unified Skill ID | Category | Mapping Notes |
|---|---|---|---|
| code-review | `code.review_style` | Coding | Enhanced with security review |
| code-refactor | `code.refactor_extract_method` | Coding | Generalized refactoring |
| debug | `code.debug_analyze_error` | Coding | Combined with trace |
| test-write | `code.generate_tests` | Coding | Multi-framework support |
| doc-write | `code.generate_docs` | Coding | Multi-format (md, rst, docstring) |
| search-web | `research.web_search` | Research | Unified with agenticSeek |
| search-code | `research.code_search` | Research | Ripgrep-based |
| summarize | `research.summarize_paper` | Research | Generalized summarizer |
| fact-check | `research.fact_check` | Research | Enhanced with source verification |
| translate | `creative.translate` | Creative | Multi-language support |
| write-email | `creative.write_email` | Creative | Template-aware |
| write-article | `creative.write_article` | Creative | SEO-aware |
| deploy | `infra.deploy_service` | Infrastructure | Multi-cloud support |
| monitor | `infra.health_check` | Infrastructure | Enhanced metrics |
| security-scan | `infra.vuln_scan` | Infrastructure | openfang integration |
| task-plan | `mgmt.task_decompose` | Management | DSPy optimization |
| sprint-plan | `mgmt.sprint_plan` | Management | Added |
| *15 more specialized skills* | Various | Various | Mapped individually |

### 4.2 superpowers Skills (Methodology-as-skill)

| superpowers Concept | Unified Skill ID | Category | Mapping Notes |
|---|---|---|---|
| TDD cycle | `code.tdd_cycle` | Coding | Red-Green-Refactor as skill |
| incremental-build | `mgmt.incremental_build` | Management | Step-by-step delivery |
| error-driven-dev | `code.debug_error_driven` | Coding | Debug-first development |
| spec-first | `mgmt.spec_first` | Management | Specification before code |
| review-checklist | `code.review_checklist` | Coding | Systematic review process |
| documentation-driven | `code.generate_docs` | Coding | Docs-first approach |

### 4.3 openfang Skills (40 channel adapter patterns)

| openfang Adapter | Unified Skill ID | Category | Mapping Notes |
|---|---|---|---|
| HTTP adapter | `infra.http_request` | Infrastructure | Generic HTTP client |
| WebSocket adapter | `infra.websocket_connect` | Infrastructure | Persistent connections |
| gRPC adapter | `infra.grpc_call` | Infrastructure | Protocol buffer calls |
| MQTT adapter | `infra.mqtt_publish` | Infrastructure | IoT messaging |
| AMQP adapter | `infra.amqp_message` | Infrastructure | Queue messaging |
| Redis adapter | `infra.redis_command` | Infrastructure | Cache/queue operations |
| SMTP adapter | `creative.write_email` | Creative | Email sending |
| Slack adapter | `mgmt.notify_slack` | Management | Slack notifications |
| Discord adapter | `mgmt.notify_discord` | Management | Discord notifications |
| Telegram adapter | `mgmt.notify_telegram` | Management | Telegram notifications |
| *30 more adapters* | Various | Various | Channel-specific skills |

### 4.4 AI-MultiColony-Ecosystem Agent Skills

The original 36 agent modules each embody specialized skills:

| Agent Module | Unified Skill ID | Category |
|---|---|---|
| Market Data Agent | `trading.market_data_fetch` | Trading |
| Technical Analysis Agent | `trading.technical_analysis` | Trading |
| Risk Management Agent | `trading.risk_assessment` | Trading |
| Portfolio Agent | `trading.rebalance_portfolio` | Trading |
| News Analysis Agent | `trading.sentiment_analysis` | Trading |
| Compliance Agent | `trading.compliance_check` | Trading |
| *30 more agent skills* | Various | Various |

### 4.5 Additional Skill Sources

| Source | Skills | Unified Skill IDs | Category |
|---|---|---|---|
| OpenHands | SWE-bench solving | `code.debug_fix_bug`, `code.review_completeness` | Coding |
| OpenManus | ReAct loop, browser automation | `research.web_search`, `code.debug_analyze_error` | Research/Coding |
| agentcloud | CrewAI crew orchestration | `mgmt.crew_orchestrate` | Management |
| agenticSeek | Voice input processing | `research.voice_query` | Research |
| nanobot | Chat interface patterns | `mgmt.chat_interface` | Management |
| suna | Desktop/mobile runtime | `infra.runtime_manage` | Infrastructure |
| CloakBrowser | Stealth browsing | `research.stealth_browse` | Research |
| open-computer-use | GUI automation | `infra.gui_automate` | Infrastructure |

---

## 5. Skill Activation Triggers

### 5.1 Trigger Types

```python
class SkillTrigger(BaseModel):
    """Defines when and how a skill is activated"""
    trigger_type: Literal["explicit", "pattern", "keyword", "context", "event"]
    pattern: Optional[str] = None     # Regex pattern for task matching
    keywords: Optional[list[str]] = None
    context: Optional[str] = None     # Agent context description
    event: Optional[str] = None       # System event name

    # Activation conditions
    confidence_threshold: float = 0.8  # Minimum confidence to auto-activate
    requires_confirmation: bool = False  # Ask user before activating
    priority: int = 0                  # Higher = preferred when multiple match
```

### 5.2 Trigger Matching Engine

```python
class SkillTriggerEngine:
    """
    Matches incoming tasks to appropriate skills.
    Uses a combination of keyword matching, pattern matching,
    and semantic similarity.
    """

    async def match(self, task: Task, agent: BaseAgent) -> list[SkillMatch]:
        """
        Find skills that match the current task context.

        Matching strategy (in order of precedence):
        1. Explicit invocation (skill_name in task metadata)
        2. Pattern match (regex against task description)
        3. Keyword match (task contains skill keywords)
        4. Context match (agent state matches skill context)
        5. Semantic similarity (embedding-based matching)
        """
        matches = []

        # 1. Explicit
        if task.skill_name:
            skill = await self.registry.get(task.skill_name)
            matches.append(SkillMatch(skill=skill, confidence=1.0, trigger="explicit"))

        # 2. Pattern
        for skill in await self.registry.list_skills():
            for trigger in skill.triggers:
                if trigger.trigger_type == "pattern":
                    if re.search(trigger.pattern, task.description):
                        matches.append(SkillMatch(
                            skill=skill, confidence=0.9, trigger="pattern"
                        ))

        # 3. Keyword
        task_words = set(task.description.lower().split())
        for skill in await self.registry.list_skills():
            for trigger in skill.triggers:
                if trigger.trigger_type == "keyword":
                    overlap = len(set(kw.lower() for kw in trigger.keywords) & task_words)
                    if overlap > 0:
                        confidence = overlap / len(trigger.keywords)
                        if confidence >= trigger.confidence_threshold:
                            matches.append(SkillMatch(
                                skill=skill, confidence=confidence, trigger="keyword"
                            ))

        # 4. Semantic similarity (fallback)
        if not matches:
            task_embedding = await self.embed(task.description)
            skill_embeddings = await self.registry.get_all_embeddings()
            similarities = cosine_similarity(task_embedding, skill_embeddings)
            for skill_id, sim in similarities.items():
                if sim >= 0.7:
                    skill = await self.registry.get(skill_id)
                    matches.append(SkillMatch(
                        skill=skill, confidence=sim, trigger="semantic"
                    ))

        return sorted(matches, key=lambda m: m.confidence, reverse=True)
```

### 5.3 Example Triggers

| Skill | Trigger Type | Pattern/Keywords | Confidence |
|---|---|---|---|
| `code.refactor_extract_method` | keyword | refactor, extract, method | 0.85 |
| `code.generate_tests` | pattern | `write tests? (for|of) \w+` | 0.90 |
| `code.debug_analyze_error` | keyword | error, bug, crash, traceback | 0.80 |
| `research.web_search` | keyword | search, find, look up | 0.75 |
| `research.fact_check` | keyword | verify, fact check, is it true | 0.85 |
| `trading.technical_analysis` | pattern | `(RSI|MACD|Bollinger|moving average)` | 0.95 |
| `trading.risk_assessment` | keyword | risk, exposure, drawdown | 0.85 |
| `creative.write_article` | keyword | write, article, blog post | 0.80 |
| `mgmt.task_decompose` | keyword | plan, break down, decompose | 0.75 |
| `infra.deploy_service` | keyword | deploy, release, ship | 0.85 |

---

## 6. Skill Composition Patterns

### 6.1 Composition Types

```
SEQUENTIAL: Skill A → Skill B → Skill C
  Use when: Output of one skill feeds the next
  Example: research.web_search → research.summarize_paper → creative.write_article

PARALLEL: Skill A ─┬─→ Merge
        Skill B ─┤
        Skill C ─┘
  Use when: Skills are independent, can run concurrently
  Example: trading.technical_analysis + trading.sentiment_analysis → trading.risk_assessment

CONDITIONAL: Skill A → [condition]? → Skill B : Skill C
  Use when: Next skill depends on intermediate result
  Example: code.debug_analyze_error → (fixable)? code.debug_fix_bug : mgmt.escalate_issue

ITERATIVE: Skill A → [loop condition]? → Skill A
  Use when: Skill needs multiple passes
  Example: code.tdd_cycle (red → green → refactor → next test)

PIPELINE: Input → Skill A → Transform → Skill B → Output
  Use when: Data transformation between skills
  Example: research.web_search → extract_entities → build_knowledge_graph
```

### 6.2 Composition Definition

```python
class SkillComposition(BaseModel):
    """Defines a composition of multiple skills"""
    composition_id: str
    name: str
    description: str

    # Composition graph
    nodes: dict[str, SkillRef]          # node_id → skill reference
    edges: list[CompositionEdge]         # Data flow between skills
    entry_point: str                     # Starting node_id
    exit_points: list[str]               # Ending node_ids

    # Execution strategy
    strategy: Literal["sequential", "parallel", "conditional", "iterative"]

    # Error handling
    on_skill_failure: Literal["abort", "skip", "retry", "fallback"]
    max_retries: int = 1

class SkillRef(BaseModel):
    skill_id: str
    params: dict[str, Any] = {}          # Default params (can be overridden)
    timeout_seconds: int = 300

class CompositionEdge(BaseModel):
    from_node: str
    to_node: str
    condition: Optional[str] = None      # Python expression for conditional edges
    transform: Optional[str] = None      # Transform function for data mapping
```

### 6.3 Example: Research & Report Composition

```python
research_report_composition = SkillComposition(
    composition_id="composition.research_report",
    name="Research and Report",
    description="Research a topic and produce a comprehensive report",
    strategy="sequential",
    nodes={
        "search": SkillRef(skill_id="research.web_search", timeout_seconds=120),
        "academic": SkillRef(skill_id="research.academic_search", timeout_seconds=120),
        "summarize": SkillRef(skill_id="research.summarize_paper", timeout_seconds=60),
        "fact_check": SkillRef(skill_id="research.fact_check", timeout_seconds=60),
        "write": SkillRef(skill_id="creative.write_article", timeout_seconds=180),
    },
    edges=[
        CompositionEdge(from_node="search", to_node="summarize"),
        CompositionEdge(from_node="academic", to_node="summarize"),
        CompositionEdge(from_node="summarize", to_node="fact_check"),
        CompositionEdge(from_node="fact_check", to_node="write"),
    ],
    entry_point="search",
    exit_points=["write"],
    on_skill_failure="skip",
)
```

---

## 7. Skill Testing Framework

### 7.1 Test Types (Following superpowers TDD-First Methodology)

```python
class SkillTestSuite:
    """
    Three-level testing for skills, following superpowers TDD methodology.
    Every skill MUST have at minimum unit tests before activation.
    """

    # Level 1: Unit Tests (required for all skills)
    # - Test each step of the procedure in isolation
    # - Mock all tool calls and LLM responses
    # - Verify correct logic and error handling

    # Level 2: Integration Tests (required for stable skills)
    # - Test skill with real tools but mocked LLM
    # - Verify tool interaction patterns
    # - Test with various parameter combinations

    # Level 3: E2E Tests (required for production skills)
    # - Test with real LLM and real tools
    # - Verify end-to-end correctness
    # - Measure performance and cost
```

### 7.2 Unit Test Template

```python
# tests/skills/coding/test_refactor_extract_method.py

import pytest
from unittest.mock import AsyncMock, patch
from skills.builtin.coding.refactor_extract_method import RefactorExtractMethod, RefactorParams

class TestRefactorExtractMethod:
    """Unit tests for code.refactor_extract_method skill"""

    @pytest.fixture
    def skill(self):
        return RefactorExtractMethod()

    @pytest.fixture
    def mock_context(self):
        ctx = AsyncMock()
        ctx.use_tool = AsyncMock()
        ctx.reason = AsyncMock()
        return ctx

    async def test_simple_extraction(self, skill, mock_context):
        """Test extracting a simple block into a method"""
        # Arrange
        params = RefactorParams(
            file_path="test.py",
            start_line=5,
            end_line=10,
            method_name="process_data"
        )

        mock_context.use_tool.side_effect = [
            "def main():\n    x = 1\n    y = x * 2\n    z = y + 3\n    return z",  # read
            None,  # write
            {"success": True},  # test_run
        ]

        # Act
        result = await skill.execute(mock_context, params)

        # Assert
        assert result.success
        mock_context.use_tool.assert_called()

    async def test_tests_fail_revert(self, skill, mock_context):
        """Test that failed tests trigger revert"""
        # Arrange
        params = RefactorParams(
            file_path="test.py",
            start_line=5,
            end_line=10,
            method_name="process_data"
        )

        original_content = "def main():\n    x = 1\n    y = x * 2"
        mock_context.use_tool.side_effect = [
            original_content,  # read
            None,  # write (refactored)
            {"success": False, "output": "1 test failed"},  # test_run fails
            None,  # write (revert)
        ]

        # Act
        result = await skill.execute(mock_context, params)

        # Assert
        assert not result.success
        assert "reverted" in result.output.lower()

    async def test_missing_file(self, skill, mock_context):
        """Test handling of missing file"""
        params = RefactorParams(
            file_path="nonexistent.py",
            start_line=1,
            end_line=5,
            method_name="foo"
        )

        mock_context.use_tool.side_effect = FileNotFoundError()

        # Act
        result = await skill.execute(mock_context, params)

        # Assert
        assert not result.success
```

### 7.3 Skill Quality Gates

```python
SKILL_QUALITY_GATES = {
    "draft": {
        "min_unit_tests": 0,
        "min_test_coverage": 0,
        "requires_integration_test": False,
        "requires_e2e_test": False,
        "requires_peer_review": False,
    },
    "experimental": {
        "min_unit_tests": 3,
        "min_test_coverage": 0.6,
        "requires_integration_test": False,
        "requires_e2e_test": False,
        "requires_peer_review": True,
    },
    "stable": {
        "min_unit_tests": 5,
        "min_test_coverage": 0.8,
        "requires_integration_test": True,
        "requires_e2e_test": False,
        "requires_peer_review": True,
    },
    "production": {
        "min_unit_tests": 10,
        "min_test_coverage": 0.9,
        "requires_integration_test": True,
        "requires_e2e_test": True,
        "requires_peer_review": True,
    },
}
```

---

## 8. Community Skill Marketplace Design

### 8.1 Marketplace Architecture

```
┌────────────────────────────────────────────────────────┐
│                  SKILL MARKETPLACE                      │
│                                                        │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │
│  │  Discovery   │  │  Validation  │  │  Distribution│  │
│  │  - Search    │  │  - Lint      │  │  - Registry  │  │
│  │  - Browse    │  │  - Test      │  │  - Versioning│  │
│  │  - Recommend │  │  - Security  │  │  - Signing   │  │
│  │              │  │  - Review    │  │  - CDN       │  │
│  └──────────────┘  └──────────────┘  └─────────────┘  │
│                                                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Skill Package Format                            │  │
│  │  skill-package/                                  │  │
│  │  ├── SKILL.md          (metadata + procedure)    │  │
│  │  ├── skill.py          (implementation)          │  │
│  │  ├── tests/            (test suite)              │  │
│  │  │   ├── test_unit.py                             │  │
│  │  │   └── test_integration.py                      │  │
│  │  ├── examples/         (usage examples)          │  │
│  │  └── pyproject.toml    (dependencies)             │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

### 8.2 Skill Registry API

```python
class SkillRegistryAPI:
    """
    API for the skill marketplace.
    Supports publishing, discovering, installing, and rating skills.
    """

    # Publishing
    async def publish_skill(self, package: SkillPackage, author: str) -> str:
        """
        Publish a skill to the marketplace.
        Returns: skill_id
        Validation:
        - SKILL.md must be valid
        - Must pass all quality gate tests
        - Must not contain malicious code (sandbox check)
        - Dependencies must be declared
        """
        ...

    # Discovery
    async def search_skills(self, query: str, category: str = None) -> list[SkillSummary]:
        """Search for skills by description, category, or capability"""
        ...

    async def get_skill(self, skill_id: str) -> SkillPackage:
        """Download a skill package"""
        ...

    async def get_recommended(self, agent_type: str) -> list[SkillSummary]:
        """Get recommended skills for an agent type"""
        ...

    # Installation
    async def install_skill(self, skill_id: str, colony_id: str) -> None:
        """Install a skill for use by a colony"""
        ...

    async def uninstall_skill(self, skill_id: str, colony_id: str) -> None:
        """Uninstall a skill from a colony"""
        ...

    async def list_installed(self, colony_id: str) -> list[SkillSummary]:
        """List skills installed for a colony"""
        ...

    # Rating and Reviews
    async def rate_skill(self, skill_id: str, rating: int, review: str) -> None:
        """Rate and review a skill (1-5 stars)"""
        ...

    async def get_reviews(self, skill_id: str) -> list[SkillReview]:
        """Get reviews for a skill"""
        ...
```

### 8.3 Skill Security Scanning

```python
class SkillSecurityScanner:
    """
    Scans skill packages for security issues before marketplace publication.
    """

    CHECKS = [
        "no_eval_usage",           # No use of eval() or exec()
        "no_subprocess_shell",     # No shell=True in subprocess
        "no_file_system_escape",   # No path traversal (../)
        "no_network_unauthorized", # No hardcoded URLs (except declared APIs)
        "no_secret_hardcoded",     # No API keys or passwords
        "no_obfuscated_code",      # No base64-encoded executable code
        "declared_dependencies",   # All imports declared in pyproject.toml
        "no_dynamic_imports",      # No __import__() or importlib tricks
        "bounded_recursion",       # No unbounded recursion
        "sandbox_compatible",      # Works within sandbox constraints
    ]

    async def scan(self, package: SkillPackage) -> SecurityScanResult:
        """Run all security checks on a skill package"""
        ...
```

---

## 9. Skill Performance Metrics

### 9.1 Per-Skill Metrics

```python
class SkillMetrics(BaseModel):
    """Metrics tracked for each skill"""
    skill_id: str

    # Usage
    total_invocations: int
    success_rate: float          # successful / total
    avg_duration_seconds: float
    avg_llm_tokens: int
    avg_tool_calls: int
    avg_cost_usd: float

    # Quality
    test_coverage: float
    test_pass_rate: float
    user_rating: float           # 1-5 stars
    review_count: int

    # Performance
    p50_duration_seconds: float
    p95_duration_seconds: float
    p99_duration_seconds: float

    # Reliability
    error_rate: float
    timeout_rate: float
    last_failure: Optional[datetime]
    mtbf_hours: float           # Mean time between failures
```

### 9.2 Skill Leaderboard Criteria

| Rank Factor | Weight | Measurement |
|---|---|---|
| Success rate | 30% | successful_invocations / total_invocations |
| User rating | 25% | Average star rating |
| Test coverage | 15% | Line coverage percentage |
| Performance | 15% | Normalized avg_duration vs category average |
| Cost efficiency | 10% | avg_cost_usd / successful_invocations |
| Freshness | 5% | Days since last update (lower = better) |

---

## 10. Built-in Skills Inventory

### 10.1 Phase 1 Built-in Skills (Foundation)

| Skill ID | Category | Source | Priority | Test Coverage |
|---|---|---|---|---|
| `code.generate_function` | Coding | OpenHands | P1 | 85% |
| `code.generate_tests` | Coding | oh-my-claudecode | P1 | 90% |
| `code.generate_docs` | Coding | oh-my-claudecode | P1 | 80% |
| `code.debug_analyze_error` | Coding | OpenHands | P1 | 85% |
| `code.review_style` | Coding | oh-my-claudecode | P1 | 80% |
| `code.tdd_cycle` | Coding | superpowers | P1 | 95% |
| `research.web_search` | Research | agenticSeek | P1 | 75% |
| `research.summarize` | Research | oh-my-claudecode | P1 | 80% |
| `mgmt.task_decompose` | Management | OpenHands | P1 | 80% |
| `infra.health_check` | Infrastructure | openfang | P1 | 85% |

### 10.2 Phase 2 Built-in Skills (Core)

| Skill ID | Category | Source | Priority |
|---|---|---|---|
| `code.refactor_extract_method` | Coding | superpowers | P2 |
| `code.refactor_rename` | Coding | New | P2 |
| `code.review_security` | Coding | openfang | P2 |
| `code.docker_setup` | Coding | ai-manus | P2 |
| `research.academic_search` | Research | New | P2 |
| `research.fact_check` | Research | oh-my-claudecode | P2 |
| `research.stealth_browse` | Research | CloakBrowser | P2 |
| `trading.technical_analysis` | Trading | AI-MultiColony | P1 |
| `trading.risk_assessment` | Trading | AI-MultiColony | P1 |
| `creative.write_article` | Creative | oh-my-claudecode | P2 |
| `creative.write_email` | Creative | oh-my-claudecode | P2 |
| `mgmt.crew_orchestrate` | Management | agentcloud | P2 |
| `infra.deploy_service` | Infrastructure | openfang | P2 |
| `infra.vuln_scan` | Infrastructure | openfang | P2 |

### 10.3 Phase 3 Built-in Skills (Extended)

| Skill ID | Category | Source | Priority |
|---|---|---|---|
| `code.ci_configure` | Coding | New | P3 |
| `code.review_performance` | Coding | New | P3 |
| `research.voice_query` | Research | agenticSeek | P3 |
| `research.code_search` | Research | oh-my-claudecode | P3 |
| `trading.sentiment_analysis` | Trading | AI-MultiColony | P2 |
| `trading.place_order` | Trading | AI-MultiColony | P2 |
| `creative.ui_mockup` | Creative | open-lovable | P2 |
| `creative.design_system` | Creative | New | P3 |
| `mgmt.sprint_plan` | Management | New | P3 |
| `mgmt.status_report` | Management | New | P3 |
| `infra.gui_automate` | Infrastructure | open-computer-use | P3 |
| `infra.log_analyze` | Infrastructure | openfang | P3 |

---

## Appendix A: Skill Execution Context

```python
class SkillContext:
    """
    Context provided to a skill during execution.
    Contains all the interfaces a skill needs.
    """

    # Identity
    agent_id: str
    colony_id: str
    task_id: str

    # Tool access
    async def use_tool(self, tool_name: str, **kwargs) -> Any:
        """Call an MCP tool. Goes through permission checks."""
        ...

    # LLM access
    async def reason(self, prompt: str, context: str = None, **kwargs) -> str:
        """Use the agent's LLM for reasoning. Goes through token budget."""
        ...

    # Memory access
    async def recall(self, query: str, top_k: int = 5) -> list[MemoryItem]:
        """Retrieve relevant memories"""
        ...

    async def remember(self, content: str, metadata: dict = None) -> str:
        """Store a new memory"""
        ...

    # Skill composition
    async def use_skill(self, skill_id: str, **params) -> SkillResult:
        """Invoke another skill (composition)"""
        ...

    # Logging
    def log(self, level: str, message: str, **metadata):
        """Log a message"""
        ...

    # Progress
    async def report_progress(self, step: int, total: int, message: str):
        """Report execution progress"""
        ...
```

## Appendix B: Skill Versioning Strategy

```
Version Format: MAJOR.MINOR.PATCH

MAJOR: Breaking changes to procedure or output format
MINOR: New parameters, new steps, backward compatible
PATCH: Bug fixes, documentation updates

Examples:
  coding.refactor_extract_method 1.0.0 → Initial stable release
  coding.refactor_extract_method 1.1.0 → Added class_name parameter
  coding.refactor_extract_method 1.1.1 → Fixed edge case with nested functions
  coding.refactor_extract_method 2.0.0 → Changed output format (breaking)

Version Resolution:
  - Skills specify required versions of other skills: ">=1.0.0,<2.0.0"
  - The registry resolves compatible versions at install time
  - Multiple major versions can coexist in the registry
  - Colonies pin to specific major versions
```
