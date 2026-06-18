"""Agent harness orchestration package for AI-MultiColony.

Provides LangGraph-style execution graphs, Markdown-based skill
definitions, sandbox execution, and persistent memory with
checkpointing.

Modules
-------
graph   – LangGraph-based execution graph with planning/execution/review
skills  – Markdown-based skill system with dynamic loading
sandbox – Sandbox execution adapter (Docker/subprocess)
memory  – Long-term memory with SQLite checkpointing
"""

from .graph import (
    HarnessGraph,
    HarnessNode,
    HarnessCheckpoint,
    HarnessNodeStatus,
    HarnessGraphStatus,
    NodeRole,
    ExecutionStep,
)
from .skills import (
    SkillRegistry,
    SkillDefinition,
    SkillParameter,
    SkillExecution,
    SkillParser,
)
from .sandbox import (
    SandboxManager,
    SandboxHandle,
    SandboxConfig,
    SandboxResult,
    SandboxType,
    SandboxStatus,
    NetworkPolicy,
)
from .memory import (
    HarnessMemory,
    SQLiteMemoryStore,
    MemoryEntry,
    CheckpointEntry,
    RecallResult,
)

__all__ = [
    # Graph
    "HarnessGraph",
    "HarnessNode",
    "HarnessCheckpoint",
    "HarnessNodeStatus",
    "HarnessGraphStatus",
    "NodeRole",
    "ExecutionStep",
    # Skills
    "SkillRegistry",
    "SkillDefinition",
    "SkillParameter",
    "SkillExecution",
    "SkillParser",
    # Sandbox
    "SandboxManager",
    "SandboxHandle",
    "SandboxConfig",
    "SandboxResult",
    "SandboxType",
    "SandboxStatus",
    "NetworkPolicy",
    # Memory
    "HarnessMemory",
    "SQLiteMemoryStore",
    "MemoryEntry",
    "CheckpointEntry",
    "RecallResult",
]
