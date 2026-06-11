"""AI-MultiColony-Ecosystem: A multi-agent operating system.

This module provides the core components for the Multi-Colony Ecosystem,
where autonomous agent colonies collaborate on complex tasks.

Architecture:
    Colony: A group of specialized agents with shared resources.
    Runtime: Agent pool management and health monitoring.
    Skills: Reusable capabilities that agents can invoke.
    Tools: MCP (Model Context Protocol) tool integration.
    Memory: Four-layer memory system (working, episodic, semantic, procedural).
    Knowledge: Document ingestion and RAG retrieval.

Example::

    from quant_nanggroe_ai.multicolony import (
        ColonyConfig,
        ColonyType,
        ColonyLifecycle,
        ColonyRouter,
        AgentPool,
        SkillRegistry,
        ToolRegistry,
    )

    # Create a colony configuration
    config = ColonyConfig(
        name="coding-colony",
        colony_type=ColonyType.CODING,
        max_agents=5,
    )

    # Initialize the lifecycle
    lifecycle = ColonyLifecycle(config)
    await lifecycle.initialize()
    await lifecycle.mark_running()

    # Manage agents
    pool = AgentPool(config)
    agent_id = await pool.spawn()

    # Register skills and tools
    skills = SkillRegistry()
    tools = ToolRegistry()
"""

__version__ = "0.1.0"

from quant_nanggroe_ai.multicolony.colony import (
    AgentConfig,
    ColonyConfig,
    ColonyInfo,
    ColonyLifecycle,
    ColonyRouter,
    ColonyState,
    ColonyStatus,
    ColonyType,
    InvalidStateTransition,
    NoAvailableColonyError,
    RoutingDecision,
    SecurityLevel,
    TaskPriority,
    TaskRequest,
)
from quant_nanggroe_ai.multicolony.knowledge import (
    ChunkStrategy,
    DocumentChunk,
    DocumentType,
    IngestedDocument,
    IngestionStatus,
    KnowledgeIngest,
    RAGConfig,
    RAGRetriever,
    RetrievalResponse,
    RetrievalResult,
    SearchMode,
)
from quant_nanggroe_ai.multicolony.memory import (
    CompressionResult,
    Episode,
    EpisodeImportance,
    EpisodeType,
    EpisodicMemory,
    ExtractionResult,
    Fact,
    FactType,
    OptimizationResult,
    Procedure,
    ProcedureStatus,
    ProceduralMemory,
    SearchResult,
    SemanticMemory,
)
from quant_nanggroe_ai.multicolony.runtime import (
    AgentInfo,
    AgentPool,
    AgentState,
    HealthCheckResult,
    HealthMonitor,
    HealthStatus,
    ResourceSnapshot,
    ResourceTracker,
)
from quant_nanggroe_ai.multicolony.skills import (
    SkillDefinition,
    SkillExecution,
    SkillLoader,
    SkillMetadata,
    SkillRegistry,
    SkillStatus,
)
from quant_nanggroe_ai.multicolony.tools import (
    BrowserAction,
    BrowserConfig,
    BrowserResult,
    BrowserSession,
    BrowserState,
    BrowserTool,
    CodeExecTool,
    CodeLanguage,
    ExecConfig,
    ExecutionResult,
    ExecutionStatus,
    ToolMetadata,
    ToolParameter,
    ToolRegistry,
    ToolType,
)

__all__ = [
    "__version__",
    # Colony
    "AgentConfig",
    "ColonyConfig",
    "ColonyInfo",
    "ColonyLifecycle",
    "ColonyRouter",
    "ColonyState",
    "ColonyStatus",
    "ColonyType",
    "InvalidStateTransition",
    "NoAvailableColonyError",
    "RoutingDecision",
    "SecurityLevel",
    "TaskPriority",
    "TaskRequest",
    # Knowledge
    "ChunkStrategy",
    "DocumentChunk",
    "DocumentType",
    "IngestedDocument",
    "IngestionStatus",
    "KnowledgeIngest",
    "RAGConfig",
    "RAGRetriever",
    "RetrievalResponse",
    "RetrievalResult",
    "SearchMode",
    # Memory
    "CompressionResult",
    "Episode",
    "EpisodeImportance",
    "EpisodeType",
    "EpisodicMemory",
    "ExtractionResult",
    "Fact",
    "FactType",
    "OptimizationResult",
    "Procedure",
    "ProcedureStatus",
    "ProceduralMemory",
    "SearchResult",
    "SemanticMemory",
    # Runtime
    "AgentInfo",
    "AgentPool",
    "AgentState",
    "HealthCheckResult",
    "HealthMonitor",
    "HealthStatus",
    "ResourceSnapshot",
    "ResourceTracker",
    # Skills
    "SkillDefinition",
    "SkillExecution",
    "SkillLoader",
    "SkillMetadata",
    "SkillRegistry",
    "SkillStatus",
    # Tools
    "BrowserAction",
    "BrowserConfig",
    "BrowserResult",
    "BrowserSession",
    "BrowserState",
    "BrowserTool",
    "CodeExecTool",
    "CodeLanguage",
    "ExecConfig",
    "ExecutionResult",
    "ExecutionStatus",
    "ToolMetadata",
    "ToolParameter",
    "ToolRegistry",
    "ToolType",
]
