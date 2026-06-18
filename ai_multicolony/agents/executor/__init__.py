"""Executor agent module."""

from ai_multicolony.agents.executor.agent import ExecutorAgent

# SandboxConfig and SandboxHandle may not exist in all versions;
# provide stubs so that ``from .executor import ...`` never breaks.
try:
    from ai_multicolony.agents.executor.agent import SandboxConfig, SandboxHandle
except ImportError:
    from pydantic import BaseModel

    class SandboxConfig(BaseModel):
        """Stub SandboxConfig – not implemented in this executor version."""
        pass

    class SandboxHandle(BaseModel):
        """Stub SandboxHandle – not implemented in this executor version."""
        pass

__all__ = ["ExecutorAgent", "SandboxConfig", "SandboxHandle"]
