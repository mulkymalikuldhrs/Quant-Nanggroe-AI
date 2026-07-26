"""
Pipeline Factory
================
Wires UnifiedPipeline with all its components.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

from quant_nanggroe.pipeline.data import UnifiedDataProvider
from quant_nanggroe.pipeline.signal import UnifiedSignalEngine
from quant_nanggroe.pipeline.execution import UnifiedExecutionRouter
from quant_nanggroe.pipeline.orchestrator import UnifiedPipeline, PipelineResult

log = logging.getLogger("QNA-Pipeline-Factory")


@dataclass
class PipelineComponents:
    data: UnifiedDataProvider
    signal: UnifiedSignalEngine
    execution: UnifiedExecutionRouter
    pipeline: UnifiedPipeline


def create_pipeline(
    allow_live: bool = False,
    cache_ttl: int = 60,
    mode_resolver=None,
) -> PipelineComponents:
    data_provider = UnifiedDataProvider(cache_ttl=cache_ttl)

    signal_engine = UnifiedSignalEngine()

    execution_router = UnifiedExecutionRouter(allow_live=allow_live)

    pipeline = UnifiedPipeline(
        data_provider=data_provider,
        signal_engine=signal_engine,
        execution_router=execution_router,
        mode_resolver=mode_resolver,
    )

    return PipelineComponents(
        data=data_provider,
        signal=signal_engine,
        execution=execution_router,
        pipeline=pipeline,
    )
