"""
⏰ Agent Scheduler - Autonomous Task Scheduling System
Auto-run, auto-schedule, and event-driven agent execution

Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

import asyncio
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
try:
    import croniter
except ImportError:
    croniter = None
import uuid

class ScheduleType(Enum):
    ONE_TIME = "one_time"
    RECURRING = "recurring" 
    CRON = "cron"
    EVENT_DRIVEN = "event_driven"
    CONTINUOUS = "continuous"

class ScheduleStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"

@dataclass
class ScheduledTask:
    task_id: str
    agent_id: str
    task_type: ScheduleType
    schedule_expression: str  # cron, interval, or event pattern
    task_data: Dict[str, Any]
    priority: int = 5
    max_retries: int = 3
    retry_count: int = 0
    status: ScheduleStatus = ScheduleStatus.PENDING
    created_at: datetime = None
    next_run: datetime = None
    last_run: datetime = None
    last_result: Any = None
    enabled: bool = True

class AgentScheduler:
    """
    Autonomous scheduling system that manages:
    - Time-based scheduling (cron, intervals)
    - Event-driven execution
    - Continuous monitoring tasks
    - Auto-restart and recovery
    - Load balancing and optimization
    """
    
    def __init__(self):
        self.scheduler_id = "agent_scheduler"
        self.status = "initializing"
        
        # Scheduled tasks
        self.scheduled_tasks: Dict[str, ScheduledTask] = {}
        self.running_tasks: Dict[str, Dict] = {}
        
        # Event handlers
        self.event_handlers: Dict[str, List[str]] = {}  # event -> task_ids
        self.condition_evaluators: Dict[str, Callable] = {}
        
        # Auto-restart configurations
        self.auto_restart_agents: Dict[str, Dict] = {}
        self.agent_health_checks: Dict[str, Dict] = {}
        
        # Performance tracking
        self.execution_stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "avg_execution_time": 0,
            "last_execution": None
        }
        
        # Load configuration
        self._load_schedule_config()
        
        # Background tasks
        self.scheduler_thread = None
        self.is_running = False
        
        self.status = "ready"
    
    def _load_schedule_config(self):
        """Load schedule configuration from file"""
        try:
            with open('data/schedule.json', 'r') as f:
                config = json.load(f)
                
                # Load scheduled tasks
                for task_data in config.get("scheduled_tasks", []):
                    task = ScheduledTask(**task_data)
                    self.scheduled_tasks[task.task_id] = task
                
                # Load auto-restart configs
                self.auto_restart_agents = config.get("auto_restart", {})
                
                print(f"✅ Loaded {len(self.scheduled_tasks)} scheduled tasks")
                
        except FileNotFoundError:
            self._create_default_schedule()
        except Exception as e:
            print(f"Error loading schedule config: {e}")
            self._create_default_schedule()
    
    def _create_default_schedule(self):
        """Create default schedule configuration"""
        default_tasks = [
            {
                "task_id": "health_check",
                "agent_id": "agent_watcher",
                "task_type": "recurring",
                "schedule_expression": "*/5 * * * *",  # Every 5 minutes
                "task_data": {"action": "health_check"},
                "priority": 8
            },
            {
                "task_id": "memory_cleanup",
                "agent_id": "data_sync",
                "task_type": "recurring", 
                "schedule_expression": "0 2 * * *",  # Daily at 2 AM
                "task_data": {"action": "cleanup_memory"},
                "priority": 6
            },
            {
                "task_id": "performance_report",
                "agent_id": "prompt_master",
                "task_type": "recurring",
                "schedule_expression": "0 9 * * 1",  # Weekly on Monday at 9 AM
                "task_data": {"action": "generate_performance_report"},
                "priority": 4
            },
            {
                "task_id": "auto_backup",
                "agent_id": "data_sync",
                "task_type": "recurring",
                "schedule_expression": "0 0 * * 0",  # Weekly on Sunday at midnight
                "task_data": {"action": "backup_data"},
                "priority": 7
            }
        ]
        
        for task_data in default_tasks:
            task = ScheduledTask(
                task_id=task_data["task_id"],
                agent_id=task_data["agent_id"],
                task_type=ScheduleType(task_data["task_type"]),
                schedule_expression=task_data["schedule_expression"],
                task_data=task_data["task_data"],
                priority=task_data["priority"],
                created_at=datetime.now()
            )
            self.scheduled_tasks[task.task_id] = task
        
        # Default auto-restart configurations
        self.auto_restart_agents = {
            "prompt_master": {
                "enabled": True,
                "max_failures": 3,
                "restart_delay": 30,
                "health_check_interval": 60
            },
            "sync_engine": {
                "enabled": True,
                "max_failures": 2,
                "restart_delay": 10,
                "health_check_interval": 30
            }
        }
        
        self._save_schedule_config()
    
    def _save_schedule_config(self):
        """Save schedule configuration to file"""
        try:
            config = {
                "scheduled_tasks": [
                    asdict(task) for task in self.scheduled_tasks.values()
                ],
                "auto_restart": self.auto_restart_agents,
                "last_updated": datetime.now().isoformat()
            }
            
            with open('data/schedule.json', 'w') as f:
                json.dump(config, f, indent=2, default=str)
                
        except Exception as e:
            print(f"Error saving schedule config: {e}")
    
    def start(self):
        """Start the scheduler"""
        if self.is_running:
            return
        
        self.is_running = True
        self.status = "running"
        
        # Start scheduler thread
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        
        # Start health monitoring
        health_thread = threading.Thread(target=self._health_monitor_loop, daemon=True)
        health_thread.start()
        
        print("⏰ Agent Scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        self.is_running = False
        self.status = "stopped"
        print("⏰ Agent Scheduler stopped")
    
    def _scheduler_loop(self):
        """Main scheduler loop"""
        while self.is_running:
            try:
                current_time = datetime.now()
                
                # Check for tasks that need to run
                for task_id, task in self.scheduled_tasks.items():
                    if not task.enabled or task.status == ScheduleStatus.RUNNING:
                        continue
                    
                    # Check if task should run
                    should_run = self._should_task_run(task, current_time)
                    
                    if should_run:
                        self._run_task_async(self._execute_task(task))
                
                # Sleep for a short interval
                time.sleep(1)
                
            except Exception as e:
                print(f"Scheduler loop error: {e}")
                time.sleep(5)
    
    def _should_task_run(self, task: ScheduledTask, current_time: datetime) -> bool:
        """Check if a task should run based on its schedule"""
        
        if task.task_type == ScheduleType.ONE_TIME:
            return task.next_run and current_time >= task.next_run
        
        elif task.task_type == ScheduleType.RECURRING:
            # Parse cron expression
            return self._check_cron_schedule(task.schedule_expression, current_time, task.last_run)
        
        elif task.task_type == ScheduleType.CONTINUOUS:
            # Continuous tasks should always run if not currently running
            return task.status != ScheduleStatus.RUNNING
        
        elif task.task_type == ScheduleType.EVENT_DRIVEN:
            # Event-driven tasks are handled separately
            return False
        
        return False
    
    def _check_cron_schedule(self, cron_expr: str, current_time: datetime, last_run: datetime) -> bool:
        """Check if cron schedule should trigger"""
        try:
            # Check if enough time has passed since last run
            if last_run:
                min_interval = 60  # Minimum 1 minute between runs
                if (current_time - last_run).total_seconds() < min_interval:
                    return False

            # Use croniter for accurate cron parsing if available
            if croniter is not None:
                try:
                    cron = croniter.croniter(cron_expr, current_time)
                    prev_run = cron.get_prev(datetime)
                    # If the previous scheduled time is within the last 60 seconds, trigger
                    diff = (current_time - prev_run).total_seconds()
                    return 0 <= diff < 60
                except (ValueError, KeyError):
                    pass  # Fall through to simple parsing

            # Simple cron parsing fallback for common patterns
            parts = cron_expr.split()
            if len(parts) != 5:
                return False
            
            minute, hour, day, month, weekday = parts
            
            # Simple pattern matching
            if minute == "*/5":  # Every 5 minutes
                return current_time.minute % 5 == 0 and current_time.second < 5
            elif minute == "*/10":  # Every 10 minutes
                return current_time.minute % 10 == 0 and current_time.second < 5
            elif minute == "0" and hour == "*":  # Every hour
                return current_time.minute == 0 and current_time.second < 5
            elif minute == "0" and hour != "*":  # Specific hour
                return current_time.hour == int(hour) and current_time.minute == 0 and current_time.second < 5
            
            # Default: run once per minute for unrecognized patterns
            return current_time.second < 5
            
        except Exception as e:
            print(f"Error parsing cron expression {cron_expr}: {e}")
            return False
    
    async def _execute_task(self, task: ScheduledTask):
        """Execute a scheduled task"""
        execution_id = str(uuid.uuid4())
        
        try:
            # Update task status
            task.status = ScheduleStatus.RUNNING
            task.last_run = datetime.now()
            
            # Track running task
            self.running_tasks[execution_id] = {
                "task_id": task.task_id,
                "agent_id": task.agent_id,
                "started_at": datetime.now(),
                "status": "running"
            }
            
            print(f"⏰ Executing scheduled task: {task.task_id} on agent {task.agent_id}")
            
            # Get agent and execute task
            agent = self._get_agent_instance(task.agent_id)
            
            if agent:
                start_time = time.time()
                
                # Execute the task
                if hasattr(agent, 'process_scheduled_task'):
                    result = await agent.process_scheduled_task(task.task_data)
                else:
                    result = await agent.process_task(task.task_data)
                
                execution_time = time.time() - start_time
                
                # Update task with success
                task.status = ScheduleStatus.COMPLETED
                task.last_result = result
                task.retry_count = 0
                
                # Update stats
                self._update_execution_stats(True, execution_time)
                
                print(f"✅ Task {task.task_id} completed successfully in {execution_time:.2f}s")
                
            else:
                raise Exception(f"Agent {task.agent_id} not available")
                
        except Exception as e:
            # Handle task failure
            print(f"❌ Task {task.task_id} failed: {e}")
            
            task.retry_count += 1
            
            if task.retry_count < task.max_retries:
                task.status = ScheduleStatus.PENDING
                # Schedule retry with exponential backoff
                retry_delay = 2 ** task.retry_count * 60  # 2, 4, 8 minutes
                task.next_run = datetime.now() + timedelta(seconds=retry_delay)
                print(f"🔄 Retrying task {task.task_id} in {retry_delay/60:.1f} minutes (attempt {task.retry_count + 1})")
            else:
                task.status = ScheduleStatus.FAILED
                task.last_result = {"error": str(e)}
                print(f"💀 Task {task.task_id} failed permanently after {task.max_retries} retries")
            
            self._update_execution_stats(False, 0)
            
        finally:
            # Clean up running task tracking
            if execution_id in self.running_tasks:
                del self.running_tasks[execution_id]
            
            # Update next run time for recurring tasks
            if task.task_type == ScheduleType.RECURRING and task.status == ScheduleStatus.COMPLETED:
                task.next_run = self._calculate_next_run(task)
            
            # Save updated configuration
            self._save_schedule_config()
    
    def _get_agent_instance(self, agent_id: str):
        """Get agent instance for execution"""
        try:
            if agent_id == "prompt_master":
                from core.prompt_master import prompt_master
                return prompt_master
            elif agent_id == "agent_watcher":
                from agents.agent_watcher import AgentWatcherAgent
                return AgentWatcherAgent()
            elif agent_id == "data_sync":
                from agents.data_sync import DataSyncAgent
                return DataSyncAgent()
            elif agent_id == "cybershell":
                from agents.cybershell import CyberShellAgent
                return CyberShellAgent()
            # Add other agents as needed
            else:
                print(f"Unknown agent: {agent_id}")
                return None
        except ImportError as e:
            print(f"Failed to import agent {agent_id}: {e}")
            return None
    
    def _calculate_next_run(self, task: ScheduledTask) -> datetime:
        """Calculate next run time for recurring tasks"""
        current_time = datetime.now()
        
        if task.task_type == ScheduleType.RECURRING:
            # Simple interval calculation based on cron expression
            expr = task.schedule_expression
            
            if "*/5" in expr:  # Every 5 minutes
                return current_time + timedelta(minutes=5)
            elif "*/10" in expr:  # Every 10 minutes
                return current_time + timedelta(minutes=10)
            elif "0 2 * * *" in expr:  # Daily at 2 AM
                next_run = current_time.replace(hour=2, minute=0, second=0, microsecond=0)
                if next_run <= current_time:
                    next_run += timedelta(days=1)
                return next_run
            elif "0 9 * * 1" in expr:  # Weekly Monday at 9 AM
                days_ahead = 0 - current_time.weekday()
                if days_ahead <= 0:
                    days_ahead += 7
                next_run = current_time + timedelta(days=days_ahead)
                return next_run.replace(hour=9, minute=0, second=0, microsecond=0)
        
        # Default: run again in 1 hour
        return current_time + timedelta(hours=1)
    
    def _update_execution_stats(self, success: bool, execution_time: float):
        """Update execution statistics"""
        self.execution_stats["total_executions"] += 1
        self.execution_stats["last_execution"] = datetime.now().isoformat()
        
        if success:
            self.execution_stats["successful_executions"] += 1
        else:
            self.execution_stats["failed_executions"] += 1
        
        # Update average execution time
        if execution_time > 0:
            current_avg = self.execution_stats["avg_execution_time"]
            total = self.execution_stats["total_executions"]
            self.execution_stats["avg_execution_time"] = (current_avg * (total - 1) + execution_time) / total
    
    def _health_monitor_loop(self):
        """Monitor agent health and auto-restart if needed"""
        while self.is_running:
            try:
                for agent_id, config in self.auto_restart_agents.items():
                    if not config.get("enabled", False):
                        continue
                    
                    # Check agent health
                    is_healthy = self._check_agent_health(agent_id)
                    
                    if not is_healthy:
                        self._handle_agent_failure(agent_id, config)
                
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                print(f"Health monitor error: {e}")
                time.sleep(60)
    
    def _check_agent_health(self, agent_id: str) -> bool:
        """Check if an agent is healthy"""
        try:
            # Simple health check - can be enhanced
            agent = self._get_agent_instance(agent_id)
            
            if agent and hasattr(agent, 'get_system_status'):
                status = agent.get_system_status()
                return status.get("status") in ["active", "ready", "running"]
            
            return agent is not None
            
        except Exception as e:
            print(f"Health check failed for {agent_id}: {e}")
            return False
    
    def _handle_agent_failure(self, agent_id: str, config: Dict):
        """Handle agent failure and restart if configured"""
        current_time = datetime.now()
        
        # Track failure
        if agent_id not in self.agent_health_checks:
            self.agent_health_checks[agent_id] = {
                "failure_count": 0,
                "last_failure": current_time,
                "last_restart": None
            }
        
        health_data = self.agent_health_checks[agent_id]
        health_data["failure_count"] += 1
        health_data["last_failure"] = current_time
        
        max_failures = config.get("max_failures", 3)
        restart_delay = config.get("restart_delay", 30)
        
        # Check if we should restart
        if health_data["failure_count"] >= max_failures:
            # Check if enough time has passed since last restart
            if (health_data["last_restart"] is None or 
                (current_time - health_data["last_restart"]).total_seconds() > restart_delay):
                
                print(f"🔄 Auto-restarting agent {agent_id} after {health_data['failure_count']} failures")
                
                # Schedule restart task
                restart_task = ScheduledTask(
                    task_id=f"restart_{agent_id}_{int(time.time())}",
                    agent_id="agent_watcher",
                    task_type=ScheduleType.ONE_TIME,
                    schedule_expression="immediate",
                    task_data={
                        "action": "restart_agent",
                        "target_agent": agent_id
                    },
                    priority=10,
                    next_run=datetime.now()
                )
                
                self.scheduled_tasks[restart_task.task_id] = restart_task
                
                # Reset failure count and update restart time
                health_data["failure_count"] = 0
                health_data["last_restart"] = current_time
    
    def schedule_task(self, task: ScheduledTask) -> str:
        """Schedule a new task"""
        if not task.task_id:
            task.task_id = str(uuid.uuid4())
        
        if not task.created_at:
            task.created_at = datetime.now()
        
        # Calculate initial next run time
        if task.task_type == ScheduleType.RECURRING:
            task.next_run = self._calculate_next_run(task)
        elif task.task_type == ScheduleType.ONE_TIME and not task.next_run:
            task.next_run = datetime.now()
        
        self.scheduled_tasks[task.task_id] = task
        self._save_schedule_config()
        
        print(f"⏰ Scheduled task {task.task_id} for agent {task.agent_id}")
        return task.task_id
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a scheduled task"""
        if task_id in self.scheduled_tasks:
            self.scheduled_tasks[task_id].status = ScheduleStatus.CANCELLED
            self.scheduled_tasks[task_id].enabled = False
            self._save_schedule_config()
            print(f"⏰ Cancelled task {task_id}")
            return True
        return False
    
    def pause_task(self, task_id: str) -> bool:
        """Pause a scheduled task"""
        if task_id in self.scheduled_tasks:
            self.scheduled_tasks[task_id].status = ScheduleStatus.PAUSED
            self.scheduled_tasks[task_id].enabled = False
            self._save_schedule_config()
            return True
        return False
    
    def resume_task(self, task_id: str) -> bool:
        """Resume a paused task"""
        if task_id in self.scheduled_tasks:
            self.scheduled_tasks[task_id].status = ScheduleStatus.PENDING
            self.scheduled_tasks[task_id].enabled = True
            self._save_schedule_config()
            return True
        return False
    
    def _run_task_async(self, coro):
        """Safely run an async coroutine from a synchronous/thread context"""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            asyncio.run_coroutine_threadsafe(coro, loop)
        else:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.run_coroutine_threadsafe(coro, loop)
                else:
                    loop.run_until_complete(coro)
            except RuntimeError:
                new_loop = asyncio.new_event_loop()
                new_loop.run_until_complete(coro)
                new_loop.close()

    def trigger_event(self, event_name: str, event_data: Any = None):
        """Trigger event-driven tasks"""
        if event_name in self.event_handlers:
            for task_id in self.event_handlers[event_name]:
                if task_id in self.scheduled_tasks:
                    task = self.scheduled_tasks[task_id]
                    if task.enabled and task.task_type == ScheduleType.EVENT_DRIVEN:
                        # Update task data with event information
                        task.task_data["event_name"] = event_name
                        task.task_data["event_data"] = event_data
                        task.next_run = datetime.now()
                        self._run_task_async(self._execute_task(task))
    
    def get_scheduler_status(self) -> Dict[str, Any]:
        """Get scheduler status and statistics"""
        return {
            "scheduler_id": self.scheduler_id,
            "status": self.status,
            "is_running": self.is_running,
            "total_scheduled_tasks": len(self.scheduled_tasks),
            "running_tasks": len(self.running_tasks),
            "execution_stats": self.execution_stats,
            "auto_restart_agents": len(self.auto_restart_agents),
            "uptime_seconds": time.time() - getattr(self, 'start_time', time.time())
        }
    
    def get_scheduled_tasks(self) -> List[Dict]:
        """Get list of scheduled tasks"""
        return [
            {
                "task_id": task.task_id,
                "agent_id": task.agent_id,
                "task_type": task.task_type.value,
                "schedule_expression": task.schedule_expression,
                "status": task.status.value,
                "enabled": task.enabled,
                "next_run": task.next_run.isoformat() if task.next_run else None,
                "last_run": task.last_run.isoformat() if task.last_run else None,
                "retry_count": task.retry_count,
                "priority": task.priority
            }
            for task in self.scheduled_tasks.values()
        ]

# Global instance
agent_scheduler = AgentScheduler()
