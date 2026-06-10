"""
⚡ QUANTA AI - OpenHands Integration Core
==========================================
Core components from OpenHands adapted for Quanta AI.

Features:
- Task execution and management
- Tool discovery and creation
- Session management
- Code execution
- File operations
- System commands

Author: Quanta AI Team
Version: 3.0.0
Inspired by: OpenHands Project
"""

import os
import sys
import json
import time
import uuid
import hashlib
import subprocess
import threading
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable, Type
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from abc import ABC, abstractmethod
import copy


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    WAITING = "waiting"


class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Task:
    """A task for autonomous execution."""
    task_id: str = field(default_factory=lambda: f"task_{uuid.uuid4().hex[:12]}")
    name: str = ""
    description: str = ""
    task_type: str = "general"
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    input_data: Dict[str, Any] = field(default_factory=dict)
    output_data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3
    depends_on: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'task_id': self.task_id,
            'name': self.name,
            'description': self.description,
            'task_type': self.task_type,
            'status': self.status.value,
            'priority': self.priority.value,
            'input_data': self.input_data,
            'output_data': self.output_data,
            'error': self.error,
            'created_at': self.created_at,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'depends_on': self.depends_on,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        return cls(
            task_id=data.get('task_id', f"task_{uuid.uuid4().hex[:12]}"),
            name=data.get('name', ''),
            description=data.get('description', ''),
            task_type=data.get('task_type', 'general'),
            status=TaskStatus(data.get('status', 'pending')),
            priority=TaskPriority(data.get('priority', 2)),
            input_data=data.get('input_data', {}),
            output_data=data.get('output_data', {}),
            error=data.get('error'),
            created_at=data.get('created_at', time.time()),
            started_at=data.get('started_at'),
            completed_at=data.get('completed_at'),
            retry_count=data.get('retry_count', 0),
            max_retries=data.get('max_retries', 3),
            depends_on=data.get('depends_on', []),
            metadata=data.get('metadata', {})
        )
    
    def start(self) -> None:
        """Mark task as started."""
        self.status = TaskStatus.IN_PROGRESS
        self.started_at = time.time()
    
    def complete(self, output: Dict[str, Any]) -> None:
        """Mark task as completed."""
        self.status = TaskStatus.COMPLETED
        self.output_data = output
        self.completed_at = time.time()
    
    def fail(self, error: str) -> None:
        """Mark task as failed."""
        self.status = TaskStatus.FAILED
        self.error = error
        self.completed_at = time.time()
    
    def cancel(self) -> None:
        """Cancel the task."""
        self.status = TaskStatus.CANCELLED
        self.completed_at = time.time()
    
    def can_execute(self, completed_tasks: List[str]) -> bool:
        """Check if task can be executed."""
        if self.status != TaskStatus.PENDING:
            return False
        
        # Check dependencies
        for dep in self.depends_on:
            if dep not in completed_tasks:
                return False
        
        return True


class Tool:
    """A tool that can be executed by the system."""
    
    def __init__(self, name: str, description: str, func: Callable):
        self.name = name
        self.description = description
        self.func = func
        self.usage_count = 0
        self.last_used: Optional[float] = None
        self.success_count = 0
        self.failure_count = 0
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool."""
        self.usage_count += 1
        self.last_used = time.time()
        
        try:
            result = self.func(**kwargs)
            self.success_count += 1
            return {
                'status': 'success',
                'result': result
            }
        except Exception as e:
            self.failure_count += 1
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get tool statistics."""
        total = self.success_count + self.failure_count
        success_rate = self.success_count / total if total > 0 else 0
        
        return {
            'name': self.name,
            'usage_count': self.usage_count,
            'success_rate': f"{success_rate:.2%}",
            'last_used': self.last_used
        }


class OpenHandsCore:
    """
    Core OpenHands functionality adapted for Quanta AI.
    
    Provides:
    - Task management
    - Tool registry
    - Code execution
    - File operations
    - System commands
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger("Quanta.OpenHands")
        
        # Task management
        self.tasks: Dict[str, Task] = {}
        self.task_queue: List[Task] = []
        self.completed_tasks: List[str] = []
        
        # Tool registry
        self.tools: Dict[str, Tool] = {}
        
        # Session management
        self.current_session_id: Optional[str] = None
        
        # Working directory
        self.working_dir = self.config.get('working_dir', '/tmp/quanta_work')
        Path(self.working_dir).mkdir(parents=True, exist_ok=True)
        
        # Register built-in tools
        self._register_builtin_tools()
        
        self.logger.info("OpenHands Core initialized")
    
    # ==================== TASK MANAGEMENT ====================
    
    def create_task(self, name: str, description: str = "",
                   task_type: str = "general",
                   priority: TaskPriority = TaskPriority.NORMAL,
                   input_data: Dict[str, Any] = None,
                   depends_on: List[str] = None) -> Task:
        """Create a new task."""
        task = Task(
            name=name,
            description=description,
            task_type=task_type,
            priority=priority,
            input_data=input_data or {},
            depends_on=depends_on or []
        )
        
        self.tasks[task.task_id] = task
        self.task_queue.append(task)
        
        self.logger.debug(f"Created task: {task.task_id} - {name}")
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return self.tasks.get(task_id)
    
    def list_tasks(self, status: TaskStatus = None) -> List[Task]:
        """List tasks, optionally filtered by status."""
        tasks = list(self.tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        return sorted(tasks, key=lambda t: (t.priority.value, t.created_at), reverse=True)
    
    def execute_task(self, task_id: str) -> Dict[str, Any]:
        """Execute a single task."""
        task = self.tasks.get(task_id)
        if not task:
            return {'status': 'error', 'error': f'Task {task_id} not found'}
        
        if task.status != TaskStatus.PENDING:
            return {'status': 'error', 'error': f'Task {task_id} is not pending'}
        
        # Check dependencies
        for dep_id in task.depends_on:
            dep_task = self.tasks.get(dep_id)
            if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                return {'status': 'error', 'error': f'Dependency {dep_id} not completed'}
        
        task.start()
        
        try:
            # Execute based on task type
            if task.task_type == 'analysis':
                result = self._execute_analysis_task(task)
            elif task.task_type == 'trading':
                result = self._execute_trading_task(task)
            elif task.task_type == 'code':
                result = self._execute_code_task(task)
            elif task.task_type == 'file':
                result = self._execute_file_task(task)
            elif task.task_type == 'command':
                result = self._execute_command_task(task)
            else:
                result = self._execute_general_task(task)
            
            task.complete(result)
            self.completed_tasks.append(task_id)
            
            return {
                'status': 'success',
                'task_id': task_id,
                'result': result
            }
            
        except Exception as e:
            task.retry_count += 1
            
            if task.retry_count >= task.max_retries:
                task.fail(str(e))
                return {'status': 'failed', 'task_id': task_id, 'error': str(e)}
            else:
                return {'status': 'retry', 'task_id': task_id, 'retry_count': task.retry_count}
    
    def _execute_analysis_task(self, task: Task) -> Dict[str, Any]:
        """Execute an analysis task."""
        from .agents.analyst_agent import AnalystAgent
        from .core.orchestrator import QuantaOrchestrator
        
        orchestrator = QuantaOrchestrator()
        if not orchestrator.initialize():
            return {'status': 'error', 'message': 'Failed to initialize orchestrator'}
        
        result = orchestrator.run_once(task.input_data.get('symbols', ['AAPL']))
        return result
    
    def _execute_trading_task(self, task: Task) -> Dict[str, Any]:
        """Execute a trading task."""
        # Trading logic would go here
        return {
            'status': 'executed',
            'task': task.name,
            'signal': task.input_data.get('signal', 'hold')
        }
    
    def _execute_code_task(self, task: Task) -> Dict[str, Any]:
        """Execute a code task."""
        code = task.input_data.get('code', '')
        language = task.input_data.get('language', 'python')
        
        if language == 'python':
            return self._run_python_code(code)
        elif language == 'bash':
            return self._run_bash_command(code)
        else:
            return {'status': 'error', 'error': f'Unsupported language: {language}'}
    
    def _execute_file_task(self, task: Task) -> Dict[str, Any]:
        """Execute a file operation task."""
        operation = task.input_data.get('operation', 'read')
        filepath = task.input_data.get('filepath', '')
        
        if operation == 'read':
            return self._read_file(filepath)
        elif operation == 'write':
            content = task.input_data.get('content', '')
            return self._write_file(filepath, content)
        elif operation == 'list':
            directory = task.input_data.get('directory', '.')
            return self._list_directory(directory)
        else:
            return {'status': 'error', 'error': f'Unknown operation: {operation}'}
    
    def _execute_command_task(self, task: Task) -> Dict[str, Any]:
        """Execute a system command."""
        command = task.input_data.get('command', '')
        return self._run_bash_command(command)
    
    def _execute_general_task(self, task: Task) -> Dict[str, Any]:
        """Execute a general task."""
        return {
            'status': 'executed',
            'task': task.name,
            'input': task.input_data
        }
    
    def execute_all_tasks(self) -> Dict[str, Any]:
        """Execute all pending tasks in dependency order."""
        results = {}
        
        while True:
            executed = False
            
            for task in list(self.task_queue):
                if task.can_execute(self.completed_tasks):
                    result = self.execute_task(task.task_id)
                    results[task.task_id] = result
                    self.task_queue.remove(task)
                    executed = True
                    break
            
            if not executed:
                break
        
        return results
    
    # ==================== TOOL REGISTRY ====================
    
    def register_tool(self, name: str, description: str, func: Callable) -> Tool:
        """Register a new tool."""
        tool = Tool(name, description, func)
        self.tools[name] = tool
        self.logger.debug(f"Registered tool: {name}")
        return tool
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self.tools.get(name)
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """List all registered tools."""
        return [tool.get_stats() for tool in self.tools.values()]
    
    def call_tool(self, name: str, **kwargs) -> Dict[str, Any]:
        """Call a tool by name."""
        tool = self.get_tool(name)
        if not tool:
            return {'status': 'error', 'error': f'Tool {name} not found'}
        return tool.execute(**kwargs)
    
    def _register_builtin_tools(self) -> None:
        """Register built-in tools."""
        # File tools
        self.register_tool(
            'read_file',
            'Read a file and return its contents',
            self._read_file
        )
        
        self.register_tool(
            'write_file',
            'Write content to a file',
            self._write_file
        )
        
        self.register_tool(
            'list_directory',
            'List contents of a directory',
            self._list_directory
        )
        
        self.register_tool(
            'file_exists',
            'Check if a file exists',
            lambda filepath: {'exists': Path(filepath).exists()}
        )
        
        # Code execution tools
        self.register_tool(
            'run_python',
            'Execute Python code',
            self._run_python_code
        )
        
        self.register_tool(
            'run_bash',
            'Execute a bash command',
            self._run_bash_command
        )
        
        # Analysis tools
        self.register_tool(
            'analyze_symbol',
            'Analyze a stock symbol',
            self._analyze_symbol
        )
        
        self.register_tool(
            'get_market_data',
            'Get market data for a symbol',
            self._get_market_data
        )
        
        # Utility tools
        self.register_tool(
            'get_time',
            'Get current timestamp',
            lambda: {'timestamp': time.time(), 'datetime': datetime.now().isoformat()}
        )
        
        self.register_tool(
            'sleep',
            'Sleep for specified seconds',
            lambda seconds: time.sleep(seconds) or {'slept': seconds}
        )
        
        self.register_tool(
            'generate_id',
            'Generate a unique ID',
            lambda: {'id': str(uuid.uuid4())}
        )
        
        self.register_tool(
            'calculate',
            'Perform a calculation',
            lambda expression: {'result': eval(expression)}
        )
    
    # ==================== FILE OPERATIONS ====================
    
    def _read_file(self, filepath: str) -> Dict[str, Any]:
        """Read a file."""
        try:
            path = Path(filepath).expanduser()
            if path.exists() and path.is_file():
                with open(path, 'r') as f:
                    content = f.read()
                return {
                    'status': 'success',
                    'content': content,
                    'size': len(content),
                    'path': str(path)
                }
            else:
                return {
                    'status': 'error',
                    'error': f'File not found: {filepath}'
                }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _write_file(self, filepath: str, content: str) -> Dict[str, Any]:
        """Write to a file."""
        try:
            path = Path(filepath).expanduser()
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w') as f:
                f.write(content)
            
            return {
                'status': 'success',
                'path': str(path),
                'size': len(content)
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _list_directory(self, directory: str = '.') -> Dict[str, Any]:
        """List directory contents."""
        try:
            path = Path(directory).expanduser()
            if path.exists() and path.is_dir():
                items = []
                for item in path.iterdir():
                    items.append({
                        'name': item.name,
                        'type': 'directory' if item.is_dir() else 'file',
                        'size': item.stat().st_size if item.is_file() else 0
                    })
                return {
                    'status': 'success',
                    'directory': str(path),
                    'items': items,
                    'count': len(items)
                }
            else:
                return {
                    'status': 'error',
                    'error': f'Directory not found: {directory}'
                }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    # ==================== CODE EXECUTION ====================
    
    def _run_python_code(self, code: str) -> Dict[str, Any]:
        """Execute Python code."""
        try:
            local_vars = {}
            exec(code, {}, local_vars)
            
            # Get the last expression result if any
            result = local_vars.get('_result', {'status': 'executed'})
            
            return {
                'status': 'success',
                'result': result,
                'output': str(result)
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _run_bash_command(self, command: str) -> Dict[str, Any]:
        """Execute a bash command."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                'status': 'success' if result.returncode == 0 else 'warning',
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                'status': 'error',
                'error': 'Command timed out'
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    # ==================== ANALYSIS TOOLS ====================
    
    def _analyze_symbol(self, symbol: str) -> Dict[str, Any]:
        """Analyze a stock symbol."""
        try:
            from .core.orchestrator import QuantaOrchestrator
            
            orchestrator = QuantaOrchestrator()
            if orchestrator.initialize():
                result = orchestrator.run_once([symbol])
                return result
            
            return {
                'status': 'error',
                'message': 'Failed to initialize analysis'
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def _get_market_data(self, symbol: str, period: str = '1mo') -> Dict[str, Any]:
        """Get market data for a symbol."""
        try:
            import yfinance as yf
            
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period)
            
            if df.empty:
                return {
                    'status': 'warning',
                    'message': f'No data for {symbol}'
                }
            
            return {
                'status': 'success',
                'symbol': symbol,
                'data_points': len(df),
                'latest_close': float(df['Close'].iloc[-1]),
                'high': float(df['High'].max()),
                'low': float(df['Low'].min()),
                'volume': int(df['Volume'].sum())
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    # ==================== SESSION MANAGEMENT ====================
    
    def start_session(self, session_id: str = None) -> str:
        """Start a new session."""
        if session_id is None:
            session_id = f"session_{uuid.uuid4().hex[:12]}"
        self.current_session_id = session_id
        return session_id
    
    def get_session_id(self) -> Optional[str]:
        """Get current session ID."""
        return self.current_session_id
    
    # ==================== STATS ====================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get system statistics."""
        return {
            'tasks': {
                'total': len(self.tasks),
                'pending': len([t for t in self.tasks.values() if t.status == TaskStatus.PENDING]),
                'completed': len([t for t in self.tasks.values() if t.status == TaskStatus.COMPLETED]),
                'failed': len([t for t in self.tasks.values() if t.status == TaskStatus.FAILED])
            },
            'tools': {
                'registered': len(self.tools),
                'total_uses': sum(t.usage_count for t in self.tools.values())
            },
            'working_dir': self.working_dir,
            'current_session': self.current_session_id
        }
