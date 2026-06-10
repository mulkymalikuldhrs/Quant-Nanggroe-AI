"""
Autonomous Development Workflow System for AI Quant Hedge Fund
Tracks progress, auto-commits changes, and maintains documentation
"""

import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Callable
from enum import Enum

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    """Development task for tracking."""
    id: str
    title: str
    description: str
    priority: str
    status: str = TaskStatus.PENDING.value
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    commits: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


class AutonomousDeveloper:
    """
    Autonomous development system that:
    - Tracks tasks and progress
    - Auto-commits changes
    - Maintains documentation
    - Reports status
    """
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root or os.getcwd())
        self.tasks_file = self.project_root / ".autonomous_tasks.json"
        self.session_file = self.project_root / ".dev_session.json"
        self.session_start = datetime.now()
        self.changes_made: List[Dict] = []
        
        self.load_tasks()
    
    def load_tasks(self) -> Dict[str, Task]:
        """Load tasks from file."""
        if self.tasks_file.exists():
            with open(self.tasks_file, 'r') as f:
                data = json.load(f)
                return {k: Task(**v) for k, v in data.items()}
        return {}
    
    def save_tasks(self) -> None:
        """Save tasks to file."""
        tasks_dict = {k: asdict(v) for k, v in self.tasks.items()}
        with open(self.tasks_file, 'w') as f:
            json.dump(tasks_dict, f, indent=2)
    
    def create_task(
        self,
        task_id: str,
        title: str,
        description: str,
        priority: str = "medium"
    ) -> Task:
        """Create a new task."""
        task = Task(
            id=task_id,
            title=title,
            description=description,
            priority=priority
        )
        self.tasks[task_id] = task
        self.save_tasks()
        self._log_change("task_created", f"Task created: {task_id} - {title}")
        return task
    
    def start_task(self, task_id: str) -> Task:
        """Start working on a task."""
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")
        
        task = self.tasks[task_id]
        task.status = TaskStatus.IN_PROGRESS.value
        task.notes.append(f"Started at {datetime.now().isoformat()}")
        self.save_tasks()
        
        self._log_change("task_started", f"Task started: {task_id}")
        return task
    
    def complete_task(self, task_id: str, commit_message: str = None) -> Task:
        """Mark task as completed and commit."""
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")
        
        task = self.tasks[task_id]
        task.status = TaskStatus.COMPLETED.value
        task.completed_at = datetime.now().isoformat()
        
        if commit_message:
            task.notes.append(f"Committed: {commit_message}")
            commit_hash = self.auto_commit(commit_message)
            task.commits.append(commit_hash)
        
        self.save_tasks()
        self._log_change("task_completed", f"Task completed: {task_id}")
        return task
    
    def add_note(self, task_id: str, note: str) -> None:
        """Add note to task."""
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")
        
        self.tasks[task_id].notes.append(f"[{datetime.now().isoformat()}] {note}")
        self.save_tasks()
    
    def auto_commit(self, message: str) -> str:
        """Auto-commit all changes."""
        try:
            subprocess.run(['git', 'add', '-A'], cwd=self.project_root, check=True)
            result = subprocess.run(
                ['git', 'commit', '-m', message],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                commit_hash = result.stdout.split('\n')[0][:8]
                self._log_change("auto_commit", f"Committed: {message[:50]}...")
                return commit_hash
        except Exception as e:
            self._log_change("commit_failed", str(e))
        return ""
    
    def _log_change(self, change_type: str, description: str) -> None:
        """Log a change."""
        self.changes_made.append({
            "type": change_type,
            "description": description,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_status(self) -> Dict:
        """Get development status."""
        completed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED.value)
        in_progress = sum(1 for t in self.tasks.values() if t.status == TaskStatus.IN_PROGRESS.value)
        pending = sum(1 for t in self.tasks.values() if t.status == TaskStatus.PENDING.value)
        
        return {
            "session_start": self.session_start.isoformat(),
            "session_duration": (datetime.now() - self.session_start).total_seconds(),
            "tasks": {
                "total": len(self.tasks),
                "completed": completed,
                "in_progress": in_progress,
                "pending": pending
            },
            "changes_made": len(self.changes_made),
            "recent_changes": self.changes_made[-10:]
        }
    
    def generate_report(self) -> str:
        """Generate development report."""
        status = self.get_status()
        
        report = f"""
================================================================================
                    AI QUANT HEDGE FUND - DEVELOPMENT REPORT
================================================================================

Session Started: {status['session_start']}
Duration: {status['session_duration']:.0f} seconds

TASKS SUMMARY
-------------
Total Tasks: {status['tasks']['total']}
Completed:   {status['tasks']['completed']}
In Progress: {status['tasks']['in_progress']}
Pending:     {status['tasks']['pending']}

CHANGES MADE: {status['changes_made']}

================================================================================
"""
        return report
    
    def run_autonomous_session(self, tasks_to_run: List[str]) -> None:
        """
        Run an autonomous development session.
        
        Args:
            tasks_to_run: List of task IDs to complete
        """
        print(f"\n{'='*60}")
        print("AUTONOMOUS DEVELOPMENT SESSION STARTED")
        print(f"{'='*60}\n")
        
        for task_id in tasks_to_run:
            if task_id not in self.tasks:
                print(f"Task {task_id} not found, skipping...")
                continue
            
            task = self.tasks[task_id]
            print(f"Working on: [{task_id}] {task.title}")
            
            self.start_task(task_id)
            
            try:
                self.execute_task(task)
                self.complete_task(task_id, f"feat({task_id}): {task.title}")
                print(f"✓ Completed: {task.title}\n")
            except Exception as e:
                print(f"✗ Failed: {task.title} - {e}\n")
                self.tasks[task_id].status = TaskStatus.FAILED.value
                self.tasks[task_id].notes.append(f"Failed: {str(e)}")
        
        print(f"\n{'='*60}")
        print("AUTONOMOUS SESSION COMPLETED")
        print(f"{'='*60}")
        print(self.generate_report())
        
        self.save_tasks()
    
    def execute_task(self, task: Task) -> None:
        """Execute a task. Override in subclasses for specific implementations."""
        raise NotImplementedError("Subclasses must implement execute_task")


class DevelopmentSession:
    """Context manager for development sessions."""
    
    def __init__(self, developer: AutonomousDeveloper, task_id: str):
        self.developer = developer
        self.task_id = task_id
        self.started = False
    
    def __enter__(self):
        self.developer.start_task(self.task_id)
        self.started = True
        print(f"Starting task: {self.task_id}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self.developer.complete_task(self.task_id)
            print(f"Completed task: {self.task_id}")
        else:
            print(f"Task failed: {exc_val}")
        return False


def create_developer(project_root: str = None) -> AutonomousDeveloper:
    """Factory function to create developer instance."""
    return AutonomousDeveloper(project_root)


def init_autonomous_development() -> AutonomousDeveloper:
    """Initialize autonomous development system."""
    developer = create_developer()
    
    print("Initializing Autonomous Development System...")
    print(f"Project: {developer.project_root}")
    print(f"Tasks file: {developer.tasks_file}")
    
    return developer


if __name__ == "__main__":
    dev = init_autonomous_development()
    print(dev.generate_report())
