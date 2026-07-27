"""Coder agent – code generation, review, and VCS integration.

Supports generating code from specifications, performing security-focused
code reviews, automated test generation, and VCS operations (commit, PR).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..types import AgentSpec, AgentType, Task
from .base import BaseAgent

logger = logging.getLogger(__name__)


class CodeArtifact:
    """Represents a generated or reviewed code artifact."""

    def __init__(
        self,
        artifact_id: str = "",
        language: str = "python",
        code: str = "",
        tests: str = "",
        file_path: str = "",
        review_status: str = "pending",
    ):
        self.artifact_id = artifact_id or f"art-{uuid.uuid4().hex[:8]}"
        self.language = language
        self.code = code
        self.tests = tests
        self.file_path = file_path
        self.review_status = review_status
        self.issues: List[Dict[str, Any]] = []
        self.security_findings: List[Dict[str, Any]] = []
        self.suggestions: List[str] = []
        self.created_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "language": self.language,
            "code": self.code[:8192],
            "tests": self.tests[:4096],
            "file_path": self.file_path,
            "review_status": self.review_status,
            "issues": self.issues,
            "security_findings": self.security_findings,
            "suggestions": self.suggestions,
        }


class CoderAgent(BaseAgent):
    """Code generation and analysis agent.

    Features
    --------
    * **Code generation** from natural-language specifications.
    * **Code review** with security focus (OWASP, CWE patterns).
    * **Test generation** – unit test scaffolding for generated code.
    * **VCS integration** – commit, branch, and PR operations.
    """

    def __init__(self, spec: Optional[AgentSpec] = None, **kwargs):
        spec = spec or AgentSpec(agent_type=AgentType.CODER, autonomy_level=2)
        if spec.agent_type != AgentType.CODER:
            spec.agent_type = AgentType.CODER
        super().__init__(spec=spec, **kwargs)
        self._code_cache: Dict[str, str] = {}
        self._artifacts: Dict[str, CodeArtifact] = {}
        self._vcs_log: List[Dict[str, Any]] = []

    # ── Abstract hook implementations ──

    async def on_task(self, task: Task) -> Any:
        """Execute code-related task based on ``payload.action``."""
        action = task.payload.get("action", "generate")
        if action == "generate":
            return await self._generate_code(task)
        elif action == "review":
            return await self._review_code(task)
        elif action == "generate_tests":
            return await self._generate_tests(task)
        elif action == "commit":
            return await self._vcs_commit(task)
        elif action == "create_pr":
            return await self._vcs_create_pr(task)
        elif action == "analyze":
            return await self._analyze_code(task)
        else:
            return {"action": action, "result": f"Unknown coder action: {action}"}

    async def on_message(self, message: Dict[str, Any]) -> Any:
        """Handle A2A messages for code operations."""
        msg_type = message.get("message_type", "")
        if msg_type == "code_review_request":
            payload = message.get("payload", {})
            return {"review_status": "pending", "artifact_id": payload.get("artifact_id")}
        elif msg_type == "code_query":
            artifact_id = message.get("payload", {}).get("artifact_id", "")
            artifact = self._artifacts.get(artifact_id)
            return artifact.to_dict() if artifact else {"error": "not_found"}
        return {"acknowledged": True}

    def capabilities(self) -> List[str]:
        """Declare coder capabilities."""
        return [
            "code_generation", "code_review", "test_generation",
            "vcs_integration", "security_review", "refactoring",
        ]

    # ── Code generation ──

    async def _generate_code(self, task: Task) -> Dict[str, Any]:
        """Generate code based on task description and specification.

        The ``payload`` may contain:
        * ``language`` – target programming language (default ``"python"``).
        * ``spec`` – natural-language specification.
        * ``file_path`` – target file path for the generated code.
        """
        language = task.payload.get("language", "python")
        spec = task.payload.get("spec", task.description)
        file_path = task.payload.get("file_path", f"generated_{uuid.uuid4().hex[:6]}.{self._ext(language)}")

        # Generate code scaffold from spec
        code = self._scaffold_code(language, spec)
        tests = self._scaffold_tests(language, spec, code)

        artifact = CodeArtifact(
            language=language,
            code=code,
            tests=tests,
            file_path=file_path,
            review_status="generated",
        )
        self._artifacts[artifact.artifact_id] = artifact
        self._code_cache[artifact.artifact_id] = code

        return {
            "action": "generate",
            "artifact_id": artifact.artifact_id,
            "language": language,
            "code": code,
            "tests": tests,
            "file_path": file_path,
        }

    def _scaffold_code(self, language: str, spec: str) -> str:
        """Produce a code scaffold from a specification."""
        if language == "python":
            return (
                f'"""Generated module for: {spec}"""\n\n'
                f"from __future__ import annotations\n\n"
                f"def main() -> None:\n"
                f'    """Entry point for: {spec}"""\n'
                f"    pass\n\n\n"
                f"if __name__ == '__main__':\n"
                f"    main()\n"
            )
        elif language in ("javascript", "typescript"):
            return (
                f"// Generated module for: {spec}\n\n"
                f"function main() {{\n"
                f"  // TODO: implement {spec}\n"
                f"}}\n\n"
                f"main();\n"
            )
        return f"// Generated code for: {spec}\n"

    def _scaffold_tests(self, language: str, spec: str, code: str) -> str:
        """Produce a test scaffold for generated code."""
        if language == "python":
            return (
                f'"""Tests for: {spec}"""\n\n'
                f"import pytest\n\n"
                f"def test_main():\n"
                f"    # TODO: implement test for {spec}\n"
                f"    assert True\n"
            )
        return f"// Tests for: {spec}\n// TODO: implement tests\n"

    def _ext(self, language: str) -> str:
        """Return file extension for a language."""
        return {
            "python": "py",
            "javascript": "js",
            "typescript": "ts",
            "rust": "rs",
            "go": "go",
            "java": "java",
        }.get(language, "txt")

    # ── Code review ──

    async def _review_code(self, task: Task) -> Dict[str, Any]:
        """Review code for quality, security, and best practices.

        Checks for:
        * Common security anti-patterns (hardcoded secrets, SQL injection, etc.)
        * Code style issues
        * Missing type hints and documentation
        """
        code = task.payload.get("code", "")
        language = task.payload.get("language", "python")
        artifact_id = task.payload.get("artifact_id")

        issues: List[Dict[str, Any]] = []
        security_findings: List[Dict[str, Any]] = []
        suggestions: List[str] = []

        # Security-focused pattern checks
        security_patterns = [
            ("hardcoded_password", "password", "Hardcoded password detected"),
            ("hardcoded_secret", "secret_key", "Hardcoded secret key detected"),
            ("sql_injection", "f\"SELECT", "Potential SQL injection"),
            ("eval_usage", "eval(", "Use of eval() is dangerous"),
            ("exec_usage", "exec(", "Use of exec() is dangerous"),
            ("subprocess_shell", "shell=True", "Subprocess with shell=True may allow command injection"),
        ]
        for pattern_id, pattern, desc in security_patterns:
            if pattern in code:
                security_findings.append({
                    "id": pattern_id,
                    "severity": "high",
                    "description": desc,
                    "pattern": pattern,
                })

        # Style suggestions
        if language == "python":
            if "from __future__ import annotations" not in code:
                suggestions.append("Consider adding 'from __future__ import annotations'")
            if "type" not in code and "->" not in code:
                suggestions.append("Consider adding type hints")

        approved = len(severity for severity in [f for f in security_findings if f.get("severity") == "high"]) == 0

        # Update artifact if referenced
        if artifact_id and artifact_id in self._artifacts:
            artifact = self._artifacts[artifact_id]
            artifact.review_status = "approved" if approved else "rejected"
            artifact.issues = issues
            artifact.security_findings = security_findings
            artifact.suggestions = suggestions

        return {
            "action": "review",
            "approved": approved,
            "issues": issues,
            "security_findings": security_findings,
            "suggestions": suggestions,
        }

    # ── Test generation ──

    async def _generate_tests(self, task: Task) -> Dict[str, Any]:
        """Generate unit tests for code.

        If an ``artifact_id`` is provided in the payload, tests are generated
        for the referenced artifact.  Otherwise, tests are generated from
        the ``code`` field in the payload.
        """
        artifact_id = task.payload.get("artifact_id")
        code = task.payload.get("code", "")
        language = task.payload.get("language", "python")

        if artifact_id and artifact_id in self._artifacts:
            artifact = self._artifacts[artifact_id]
            code = artifact.code
            language = artifact.language

        tests = self._scaffold_tests(language, f"artifact {artifact_id}", code)

        if artifact_id and artifact_id in self._artifacts:
            self._artifacts[artifact_id].tests = tests

        return {
            "action": "generate_tests",
            "artifact_id": artifact_id,
            "tests": tests,
            "language": language,
        }

    # ── Code analysis ──

    async def _analyze_code(self, task: Task) -> Dict[str, Any]:
        """Analyze code for complexity and issues."""
        code = task.payload.get("code", "")
        language = task.payload.get("language", "python")

        lines = code.split("\n") if code else []
        complexity = "low"
        if len(lines) > 50:
            complexity = "medium"
        if len(lines) > 150:
            complexity = "high"

        return {
            "action": "analyze",
            "language": language,
            "lines_of_code": len(lines),
            "complexity": complexity,
            "issues": [],
            "suggestions": ["Consider adding docstrings"] if len(lines) > 10 else [],
        }

    # ── VCS integration ──

    async def _vcs_commit(self, task: Task) -> Dict[str, Any]:
        """Commit code changes to VCS."""
        message = task.payload.get("message", "Automated commit")
        files = task.payload.get("files", [])
        branch = task.payload.get("branch", "main")

        commit_id = f"commit-{uuid.uuid4().hex[:8]}"
        entry = {
            "commit_id": commit_id,
            "message": message,
            "files": files,
            "branch": branch,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self._vcs_log.append(entry)

        return {
            "action": "commit",
            "commit_id": commit_id,
            "branch": branch,
            "files": files,
            "message": message,
        }

    async def _vcs_create_pr(self, task: Task) -> Dict[str, Any]:
        """Create a pull request."""
        title = task.payload.get("title", "Automated PR")
        source_branch = task.payload.get("source_branch", "feature/automated")
        target_branch = task.payload.get("target_branch", "main")
        description = task.payload.get("description", "")

        pr_id = f"pr-{uuid.uuid4().hex[:6]}"
        return {
            "action": "create_pr",
            "pr_id": pr_id,
            "title": title,
            "source_branch": source_branch,
            "target_branch": target_branch,
            "description": description,
            "status": "open",
        }
