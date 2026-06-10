"""Base agent class for all trading and sub-agents."""

from __future__ import annotations

import logging
import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class PlanExecutionResult:
    """Result of executing a multi-step plan."""

    agent_name: str
    total_steps_executed: int
    successful_steps: int
    failed_steps: int
    skipped_steps: int
    execution_time_seconds: float
    success: bool
    phase_results: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class StepResult:
    """Result of a single step execution."""

    step_number: int
    step_name: str
    success: bool
    message: str
    data: Any = None
    error: Optional[str] = None


class BaseAgent(ABC):
    """Base class for all agents in the system."""

    def __init__(
        self,
        agent_name: str,
        db_path: Optional[str] = None,
        config_path: Optional[str] = None,
    ):
        self.agent_name = agent_name
        self.db_path = db_path or f"data/{agent_name.lower()}_agent.db"
        self.config_path = config_path or f"src/agents/config/{agent_name.lower()}_agent_config.yaml"
        self.logger = logging.getLogger(f"{__name__}.{agent_name}")

        self._initialize_database()
        self.logger.info(f"{agent_name} initialized with database at {self.db_path}")

    def _initialize_database(self):
        """Initialize the agent's database."""
        try:
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(self.db_path)
            self._create_tables(conn)
            conn.commit()
            conn.close()
            self.logger.info(f"Database initialized at {self.db_path}")
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            raise

    @abstractmethod
    def _create_tables(self, conn: sqlite3.Connection):
        """Create tables for this agent's specific data structures."""
        pass

    @abstractmethod
    def analyze(
        self,
        ticker: str,
        data: pd.DataFrame,
        mode: str = "analysis",
    ) -> Dict[str, Any]:
        """Analyze market data and generate signals.

        Args:
            ticker: Stock symbol to analyze
            data: Historical market data as DataFrame
            mode: Analysis mode (analysis, trading, etc.)

        Returns:
            Dictionary containing analysis results including signals
        """
        pass

    def get_signal(
        self,
        ticker: str,
        data: pd.DataFrame,
    ) -> Dict[str, Any]:
        """Get trading signal for given ticker.

        Args:
            ticker: Stock symbol
            data: Historical market data

        Returns:
            Dictionary with signal details (BUY/SELL/HOLD, confidence, reasoning)
        """
        result = self.analyze(ticker, data)
        return {
            "agent_name": self.agent_name,
            "ticker": ticker,
            "signal": result.get("signal", "HOLD"),
            "confidence": result.get("confidence", 0.5),
            "reasoning": result.get("reasoning", ""),
            "metadata": result.get("metadata", {}),
        }

    def execute_plan(
        self,
        max_steps: Optional[int] = None,
        skip_phases: Optional[List[str]] = None,
    ) -> PlanExecutionResult:
        """Execute the agent's full plan through all phases and steps.

        Args:
            max_steps: Maximum number of steps to execute (None = all)
            skip_phases: List of phase names to skip

        Returns:
            PlanExecutionResult with full execution details
        """
        start_time = datetime.now()
        total_steps = 0
        successful_steps = 0
        failed_steps = 0
        skipped_steps = 0
        errors = []
        warnings = []
        phase_results = {}

        self.logger.info(f"Starting plan execution for {self.agent_name}")

        if not hasattr(self, "phase_definition") or not self.phase_definition:
            self.logger.warning("No phase_definition found, using single-phase default")
            return self._execute_default_plan(max_steps)

        skip_phases_set = set(skip_phases or [])

        for phase_name, phase_description, step_range in self.phase_definition:
            if phase_name in skip_phases_set:
                self.logger.info(f"Skipping phase: {phase_name}")
                skipped_steps += len(step_range)
                continue

            self.logger.info(f"Executing phase: {phase_name} - {phase_description}")
            phase_results[phase_name] = []

            for step_num in step_range:
                if max_steps and total_steps >= max_steps:
                    self.logger.info(f"Reached max_steps limit: {max_steps}")
                    break

                step_name = f"step_{step_num}"
                try:
                    step_result = self._execute_step(step_num, phase_name)
                    phase_results[phase_name].append(step_result)

                    if step_result.success:
                        successful_steps += 1
                        self.logger.debug(f"Step {step_num} completed: {step_result.message}")
                    else:
                        failed_steps += 1
                        errors.append(f"Phase {phase_name}, Step {step_num}: {step_result.error}")
                        self.logger.warning(f"Step {step_num} failed: {step_result.error}")

                except Exception as e:
                    failed_steps += 1
                    error_msg = f"Phase {phase_name}, Step {step_num}: {str(e)}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
                    step_result = StepResult(
                        step_number=step_num,
                        step_name=step_name,
                        success=False,
                        message="Step failed with exception",
                        error=str(e),
                    )
                    phase_results[phase_name].append(step_result)

                total_steps += 1

        execution_time = (datetime.now() - start_time).total_seconds()
        success = failed_steps == 0

        result = PlanExecutionResult(
            agent_name=self.agent_name,
            total_steps_executed=total_steps,
            successful_steps=successful_steps,
            failed_steps=failed_steps,
            skipped_steps=skipped_steps,
            execution_time_seconds=execution_time,
            success=success,
            phase_results=phase_results,
            errors=errors,
            warnings=warnings,
        )

        self.logger.info(f"Plan execution completed: {total_steps} steps, " f"{successful_steps} success, {failed_steps} failed, " f"{skipped_steps} skipped, {execution_time:.2f}s")

        self._save_execution_result(result)
        return result

    def _execute_default_plan(self, max_steps: Optional[int]) -> PlanExecutionResult:
        """Execute a simple default plan when no phase_definition exists."""
        start_time = datetime.now()
        total_steps = 0
        successful_steps = 0
        failed_steps = 0
        skipped_steps = 0

        self.logger.info("Executing default single-phase plan")

        steps_to_execute = max_steps if max_steps else 10

        for step_num in range(1, steps_to_execute + 1):
            try:
                self._execute_step(step_num, "default")
                successful_steps += 1
            except Exception as e:
                failed_steps += 1
                self.logger.error(f"Default step {step_num} failed: {e}")
            total_steps += 1

        execution_time = (datetime.now() - start_time).total_seconds()

        return PlanExecutionResult(
            agent_name=self.agent_name,
            total_steps_executed=total_steps,
            successful_steps=successful_steps,
            failed_steps=failed_steps,
            skipped_steps=skipped_steps,
            execution_time_seconds=execution_time,
            success=failed_steps == 0,
        )

    @abstractmethod
    def _execute_step(self, step_num: int, phase_name: str) -> StepResult:
        """Execute a specific step within a phase.

        Args:
            step_num: Step number to execute
            phase_name: Name of the current phase

        Returns:
            StepResult with execution status
        """
        pass

    def _save_execution_result(self, result: PlanExecutionResult):
        """Save plan execution result to database.

        Args:
            result: PlanExecutionResult to save
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS execution_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    agent_name TEXT,
                    total_steps INTEGER,
                    successful_steps INTEGER,
                    failed_steps INTEGER,
                    skipped_steps INTEGER,
                    execution_time REAL,
                    success INTEGER
                )
            """
            )

            cursor.execute(
                """
                INSERT INTO execution_history
                (timestamp, agent_name, total_steps, successful_steps, failed_steps,
                 skipped_steps, execution_time, success)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    datetime.now().isoformat(),
                    result.agent_name,
                    result.total_steps_executed,
                    result.successful_steps,
                    result.failed_steps,
                    result.skipped_steps,
                    result.execution_time_seconds,
                    1 if result.success else 0,
                ),
            )

            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Failed to save execution result: {e}")

    def get_execution_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent execution history from database.

        Args:
            limit: Maximum number of records to retrieve

        Returns:
            List of execution records
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT timestamp, agent_name, total_steps, successful_steps,
                       failed_steps, skipped_steps, execution_time, success
                FROM execution_history
                ORDER BY id DESC
                LIMIT ?
            """,
                (limit,),
            )

            rows = cursor.fetchall()
            conn.close()

            return [
                {
                    "timestamp": row[0],
                    "agent_name": row[1],
                    "total_steps": row[2],
                    "successful_steps": row[3],
                    "failed_steps": row[4],
                    "skipped_steps": row[5],
                    "execution_time": row[6],
                    "success": bool(row[7]),
                }
                for row in rows
            ]
        except Exception as e:
            self.logger.error(f"Failed to get execution history: {e}")
            return []

    def cleanup_database(self):
        """Clean up old data from database if needed."""
        self.logger.info(f"Database cleanup not implemented for {self.agent_name}")
