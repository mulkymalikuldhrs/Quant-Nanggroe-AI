"""Executor agent - from AI-Manus pattern.

Specializes in executing planned subtasks with verification,
error handling, and retry logic.
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional

from ai_multicolony.config.logging_config import get_logger
from ai_multicolony.core.base_agent import BaseAgent
from ai_multicolony.types.agent import AgentCapabilities, AgentConfig, AgentRole, AgentState
from ai_multicolony.types.memory import MemoryType
from ai_multicolony.types.messages import Message, MessageRole
from ai_multicolony.agents.executor.prompts import (
    EXECUTOR_SYSTEM_PROMPT,
    EXECUTOR_VERIFICATION_PROMPT,
    EXECUTOR_ERROR_HANDLING_PROMPT,
    EXECUTOR_STEP_EXECUTION_PROMPT,
)

logger = get_logger(__name__)


class ExecutorAgent(BaseAgent):
    """Executor agent for carrying out planned subtasks.

    From AI-Manus pattern. Receives specific subtasks and executes
    them using available tools, with built-in verification and retry.

    State-specific behavior:
    - IDLE: Ready for task assignment
    - RUNNING: Actively executing a subtask
    - THINKING: Analyzing execution results
    - WAITING: Awaiting verification or external input
    - PAUSED: Execution paused, resumable
    - ERROR: Error recovery with retry logic
    """

    # Track execution results
    _execution_log: list[dict[str, Any]]
    _max_retries: int = 2

    def __init__(self, config: Optional[AgentConfig] = None, **kwargs: Any) -> None:
        if config is None:
            config = AgentConfig(
                role=AgentRole.EXECUTOR,
                name="executor-agent",
                description="Subtask execution specialist with verification",
                tools=["shell", "file", "code", "docker"],
                system_prompt=EXECUTOR_SYSTEM_PROMPT,
                temperature=0.05,  # Very low for precise execution
                capabilities=AgentCapabilities(
                    code_execution=True,
                    file_operations=True,
                    shell_execution=True,
                    docker_management=True,
                ),
            )
        else:
            if not config.system_prompt:
                config.system_prompt = EXECUTOR_SYSTEM_PROMPT
            if not config.tools:
                config.tools = ["shell", "file", "code", "docker"]

        super().__init__(config=config, **kwargs)
        self._execution_log = []

    # ------------------------------------------------------------------
    # Required tools
    # ------------------------------------------------------------------

    @classmethod
    def get_required_tools(cls) -> list[str]:
        """Return the list of tool names ExecutorAgent requires.

        Returns:
            Tools needed for task execution.
        """
        return ["shell", "file", "code", "docker"]

    # ------------------------------------------------------------------
    # System prompt
    # ------------------------------------------------------------------

    def get_system_prompt(self) -> str:
        """Get the system prompt for the Executor agent."""
        return self.config.system_prompt or EXECUTOR_SYSTEM_PROMPT

    # ------------------------------------------------------------------
    # State-specific behavior
    # ------------------------------------------------------------------

    def _on_enter_running(self) -> None:
        """Hook called when entering RUNNING state."""
        logger.info(
            "executor_agent_running",
            agent_id=self.agent_id,
            executions=len(self._execution_log),
        )

    def _on_enter_error(self) -> None:
        """Hook called when entering ERROR state."""
        logger.warning(
            "executor_agent_error",
            agent_id=self.agent_id,
            error_count=self.error_count,
        )
        # Store error in execution log
        self._execution_log.append({
            "status": "error",
            "error_count": self.error_count,
            "iteration": self.iteration_count,
        })

    def _on_enter_waiting(self) -> None:
        """Hook called when entering WAITING state."""
        logger.info("executor_agent_waiting", agent_id=self.agent_id)

    # ------------------------------------------------------------------
    # Core execution methods
    # ------------------------------------------------------------------

    async def execute_subtask(self, task_description: str, verification: bool = True) -> str:
        """Execute a specific subtask with optional verification.

        Args:
            task_description: The subtask to execute.
            verification: Whether to verify the result after execution.

        Returns:
            The execution result.
        """
        result = await self.run(task_description)

        # Log execution
        self._execution_log.append({
            "task": task_description[:200],
            "result": result[:200],
            "verified": False,
            "status": "completed",
        })

        if verification:
            verified = await self._verify_result(task_description, result)
            if not verified:
                # Try once more with verification feedback
                retry_prompt = (
                    f"Previous attempt failed verification. Task: {task_description}\n"
                    f"Previous result: {result}\nPlease try again with corrections."
                )
                result = await self.run(retry_prompt)

                # Log retry
                self._execution_log.append({
                    "task": f"retry: {task_description[:100]}",
                    "result": result[:200],
                    "verified": True,
                    "status": "retry",
                })

        return result

    async def execute_step(
        self,
        subtask: str,
        context: str = "",
        verification_criteria: str = "Output matches expected format",
    ) -> str:
        """Execute a subtask step-by-step with detailed logging.

        Args:
            subtask: The subtask description.
            context: Additional context for the execution.
            verification_criteria: What to verify after execution.

        Returns:
            The execution result with detailed log.
        """
        prompt = EXECUTOR_STEP_EXECUTION_PROMPT.format(
            subtask=subtask,
            context=context or "No additional context",
            verification=verification_criteria,
        )
        return await self.run(prompt)

    async def execute_with_retry(
        self,
        task_description: str,
        max_retries: int = 2,
    ) -> str:
        """Execute a subtask with automatic retry on failure.

        Args:
            task_description: The subtask to execute.
            max_retries: Maximum number of retry attempts.

        Returns:
            The execution result (from last attempt).
        """
        last_error: Optional[str] = None
        for attempt in range(1, max_retries + 1):
            try:
                result = await self.run(task_description)

                # Verify result
                verified = await self._verify_result(task_description, result)
                if verified:
                    self._execution_log.append({
                        "task": task_description[:200],
                        "attempt": attempt,
                        "status": "success",
                    })
                    return result

                last_error = "Verification failed"

            except Exception as e:
                last_error = str(e)

            # Log failed attempt
            self._execution_log.append({
                "task": task_description[:200],
                "attempt": attempt,
                "status": "failed",
                "error": last_error,
            })

            # If not last attempt, inject error handling prompt
            if attempt < max_retries:
                error_prompt = EXECUTOR_ERROR_HANDLING_PROMPT.format(
                    task=task_description,
                    error=last_error or "Unknown error",
                    attempt=attempt,
                )
                self.messages.append(Message(
                    role=MessageRole.USER,
                    content=error_prompt,
                ))

        return f"Execution failed after {max_retries} attempts. Last error: {last_error}"

    # ------------------------------------------------------------------
    # Verification
    # ------------------------------------------------------------------

    async def _verify_result(self, task: str, result: str) -> bool:
        """Verify that the result accomplishes the task.

        Uses the LLM to check whether the execution result satisfies
        the task requirements.

        Args:
            task: The original task.
            result: The execution result.

        Returns:
            True if verification passes.
        """
        verification_prompt = EXECUTOR_VERIFICATION_PROMPT.format(task=task, result=result)

        provider = self._get_llm_provider()
        response = await provider.chat(
            messages=[
                {"role": "system", "content": "You are a task verification assistant."},
                {"role": "user", "content": verification_prompt},
            ],
            max_tokens=200,
            temperature=0.0,
        )

        is_pass = "PASS" in response.content.upper()

        # Update last execution log entry
        if self._execution_log:
            self._execution_log[-1]["verified"] = is_pass

        return is_pass

    # ------------------------------------------------------------------
    # Execution log
    # ------------------------------------------------------------------

    def get_execution_log(self) -> list[dict[str, Any]]:
        """Get the execution log for all tasks.

        Returns:
            List of execution log entries.
        """
        return list(self._execution_log)

    def clear_execution_log(self) -> None:
        """Clear the execution log."""
        self._execution_log.clear()
