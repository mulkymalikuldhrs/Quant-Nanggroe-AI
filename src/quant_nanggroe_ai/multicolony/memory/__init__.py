"""Memory subpackage for the Multi-Colony Ecosystem.

This subpackage provides the four-layer memory system:
    L1: Working memory (immediate context)
    L2: Episodic memory (event sequences with compression)
    L3: Semantic memory (facts with vector search)
    L4: Procedural memory (skills with optimization)
"""

from quant_nanggroe_ai.multicolony.memory.episodic import (
    CompressionResult,
    Episode,
    EpisodeImportance,
    EpisodeNotFoundError,
    EpisodeType,
    EpisodicMemory,
)
from quant_nanggroe_ai.multicolony.memory.procedural import (
    ExtractionResult,
    OptimizationResult,
    Procedure,
    ProcedureNotFoundError,
    ProcedureStatus,
    ProceduralMemory,
)
from quant_nanggroe_ai.multicolony.memory.semantic import (
    Fact,
    FactNotFoundError,
    FactType,
    SearchResult,
    SemanticMemory,
)

__all__ = [
    "CompressionResult",
    "Episode",
    "EpisodeImportance",
    "EpisodeNotFoundError",
    "EpisodeType",
    "EpisodicMemory",
    "ExtractionResult",
    "Fact",
    "FactNotFoundError",
    "FactType",
    "OptimizationResult",
    "Procedure",
    "ProcedureNotFoundError",
    "ProcedureStatus",
    "ProceduralMemory",
    "SearchResult",
    "SemanticMemory",
]
