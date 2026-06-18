"""Coder agent module."""

from ai_multicolony.agents.coder.agent import CoderAgent

try:
    from ai_multicolony.agents.coder.agent import CodeArtifact
except ImportError:
    from pydantic import BaseModel

    class CodeArtifact(BaseModel):
        """Stub CodeArtifact – not implemented in this coder version."""
        pass

__all__ = ["CoderAgent", "CodeArtifact"]
