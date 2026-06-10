"""
⚡ QUANTA AI - Autonomous Engine
=================================
The brain of the system that combines OpenHands and Quanta AI
for truly autonomous operation.

Features:
- Goal pursuit and planning
- Self-improvement loop
- Cross-domain learning
- Adaptive behavior
- System self-monitoring

Author: Quanta AI Team
Version: 3.0.0
"""

import time
import threading
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import json
import hashlib


class GoalStatus(Enum):
    """Status of a goal."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


@dataclass
class Goal:
    """A goal for autonomous pursuit."""
    goal_id: str
    description: str
    target: Dict[str, Any]
    status: GoalStatus = GoalStatus.PENDING
    priority: int = 1
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    progress: float = 0.0
    subtasks: List[str] = field(default_factory=list)
    completed_subtasks: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'goal_id': self.goal_id,
            'description': self.description,
            'target': self.target,
            'status': self.status.value,
            'priority': self.priority,
            'created_at': self.created_at,
            'completed_at': self.completed_at,
            'progress': self.progress,
            'subtasks': self.subtasks,
            'completed_subtasks': self.completed_subtasks,
            'metadata': self.metadata
        }


class AutonomousEngine:
    """
    The autonomous engine that drives the entire system.
    
    Responsibilities:
    - Goal setting and pursuit
    - Task planning and execution
    - Self-improvement and learning
    - System monitoring and adaptation
    - Cross-domain coordination
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = logging.getLogger("Quanta.Autonomous")
        
        # Core components
        self.memory = None  # Will be set during initialization
        self.openhands = None
        self.orchestrator = None
        
        # Goals and tasks
        self.goals: Dict[str, Goal] = {}
        self.current_goal: Optional[Goal] = None
        
        # Learning and adaptation
        self.learning_enabled = self.config.get('learning_enabled', True)
        self.adaptation_enabled = self.config.get('adaptation_enabled', True)
        self.self_improvement_enabled = self.config.get('self_improvement_enabled', True)
        
        # Monitoring
        self.performance_metrics: Dict[str, Any] = {}
        self.health_status: Dict[str, Any] = {}
        self.alert_thresholds: Dict[str, float] = {
            'cpu_usage': 80.0,
            'memory_usage': 85.0,
            'error_rate': 0.1,
            'latency_threshold': 5.0
        }
        
        # Loop control
        self.running = False
        self.loops: Dict[str, threading.Thread] = {}
        
        # Callbacks
        self.on_goal_complete: List[Callable] = []
        self.on_alert: List[Callable] = []
        self.on_improve: List[Callable] = []
        
        self.logger.info("Autonomous Engine initialized")
    
    def initialize(self, memory, openhands, orchestrator) -> None:
        """Initialize the autonomous engine with core components."""
        self.memory = memory
        self.openhands = openhands
        self.orchestrator = orchestrator
        
        # Load previous goals
        self._load_goals()
        
        self.logger.info("Autonomous Engine ready")
    
    def start(self) -> None:
        """Start all autonomous loops."""
        if self.running:
            self.logger.warning("Already running")
            return
        
        self.running = True
        
        # Start monitoring loop
        self.loops['monitoring'] = threading.Thread(
            target=self._monitoring_loop, daemon=True
        )
        self.loops['monitoring'].start()
        
        # Start learning loop
        if self.learning_enabled:
            self.loops['learning'] = threading.Thread(
                target=self._learning_loop, daemon=True
            )
            self.loops['learning'].start()
        
        # Start adaptation loop
        if self.adaptation_enabled:
            self.loops['adaptation'] = threading.Thread(
                target=self._adaptation_loop, daemon=True
            )
            self.loops['adaptation'].start()
        
        # Start goal pursuit loop
        self.loops['goals'] = threading.Thread(
            target=self._goal_loop, daemon=True
        )
        self.loops['goals'].start()
        
        self.logger.info("Autonomous Engine started")
    
    def stop(self) -> None:
        """Stop all autonomous loops."""
        self.running = False
        
        for name, loop in self.loops.items():
            if loop.is_alive():
                loop.join(timeout=1.0)
        
        # Save state
        self._save_goals()
        
        self.logger.info("Autonomous Engine stopped")
    
    # ==================== GOAL MANAGEMENT ====================
    
    def set_goal(self, description: str, target: Dict[str, Any],
                priority: int = 1, metadata: Dict[str, Any] = None) -> str:
        """Set a new goal."""
        import uuid
        goal_id = f"goal_{uuid.uuid4().hex[:12]}"
        
        goal = Goal(
            goal_id=goal_id,
            description=description,
            target=target,
            priority=priority,
            metadata=metadata or {}
        )
        
        self.goals[goal_id] = goal
        
        # If no current goal, set this as current
        if not self.current_goal:
            self.current_goal = goal
            goal.status = GoalStatus.IN_PROGRESS
        
        self.logger.info(f"Goal set: {goal_id} - {description}")
        return goal_id
    
    def get_goals(self, status: GoalStatus = None) -> List[Goal]:
        """Get goals, optionally filtered by status."""
        goals = list(self.goals.values())
        if status:
            goals = [g for g in goals if g.status == status]
        return sorted(goals, key=lambda g: (g.priority, g.created_at), reverse=True)
    
    def pursue_goal(self, goal_id: str) -> Dict[str, Any]:
        """Pursue a specific goal."""
        goal = self.goals.get(goal_id)
        if not goal:
            return {'status': 'error', 'error': f'Goal {goal_id} not found'}
        
        self.current_goal = goal
        goal.status = GoalStatus.IN_PROGRESS
        
        # Break goal into tasks
        tasks = self._break_into_tasks(goal)
        goal.subtasks = [t.task_id for t in tasks]
        
        # Execute tasks
        for task in tasks:
            if not self.running:
                break
            
            result = self.openhands.execute_task(task.task_id)
            
            if result.get('status') == 'success':
                goal.completed_subtasks.append(task.task_id)
                progress = len(goal.completed_subtasks) / len(goal.subtasks) if goal.subtasks else 1.0
                goal.progress = progress
                
                # Update memory
                if self.memory:
                    self.memory.remember(
                        self.memory.memory_type.EPISODIC if hasattr(self.memory, 'memory_type') else 'episodic',
                        {
                            'type': 'goal_progress',
                            'goal_id': goal_id,
                            'task': task.name,
                            'progress': progress
                        },
                        tags=['goal', goal_id]
                    )
            
            if result.get('status') == 'failed':
                goal.status = GoalStatus.FAILED
                return result
        
        # Check if goal is complete
        if set(goal.completed_subtasks) == set(goal.subtasks):
            goal.status = GoalStatus.COMPLETED
            goal.completed_at = time.time()
            goal.progress = 1.0
            
            # Notify callbacks
            for callback in self.on_goal_complete:
                try:
                    callback(goal)
                except Exception as e:
                    self.logger.error(f"Goal complete callback error: {e}")
        
        return {
            'status': goal.status.value,
            'goal_id': goal_id,
            'progress': goal.progress
        }
    
    def _break_into_tasks(self, goal: Goal) -> List:
        """Break a goal into executable tasks."""
        tasks = []
        
        target = goal.target
        
        if 'analysis' in target:
            symbols = target.get('symbols', ['AAPL'])
            for symbol in symbols:
                task = self.openhands.create_task(
                    name=f"Analyze {symbol}",
                    description=f"Perform market analysis for {symbol}",
                    task_type='analysis',
                    priority=goal.priority,
                    input_data={'symbols': [symbol]}
                )
                tasks.append(task)
        
        if 'trading' in target:
            signals = target.get('signals', [])
            for signal in signals:
                task = self.openhands.create_task(
                    name=f"Execute {signal.get('action', 'trade')} for {signal.get('symbol')}",
                    description=f"Execute trading signal",
                    task_type='trading',
                    priority=goal.priority,
                    input_data=signal
                )
                tasks.append(task)
        
        if 'research' in target:
            topics = target.get('topics', [])
            for topic in topics:
                task = self.openhands.create_task(
                    name=f"Research {topic}",
                    description=f"Research information about {topic}",
                    task_type='general',
                    priority=goal.priority,
                    input_data={'topic': topic}
                )
                tasks.append(task)
        
        if 'code' in target:
            tasks.append(
                self.openhands.create_task(
                    name=target.get('task_name', 'Code Task'),
                    description=target.get('description', ''),
                    task_type='code',
                    priority=goal.priority,
                    input_data={
                        'code': target.get('code', ''),
                        'language': target.get('language', 'python')
                    }
                )
            )
        
        # Default task if no specific target
        if not tasks:
            tasks.append(
                self.openhands.create_task(
                    name=goal.description,
                    description=goal.description,
                    task_type='general',
                    priority=goal.priority,
                    input_data=goal.target
                )
            )
        
        return tasks
    
    # ==================== SELF-IMPROVEMENT ====================
    
    def _learning_loop(self) -> None:
        """Continuous learning loop."""
        while self.running:
            try:
                # Learn from completed goals
                completed_goals = [g for g in self.goals.values() 
                                 if g.status == GoalStatus.COMPLETED]
                
                for goal in completed_goals[-10:]:  # Last 10 goals
                    self._learn_from_goal(goal)
                
                # Learn from trades
                if self.memory:
                    insights = self.memory.get_strategy_insights()
                    if insights:
                        self._apply_strategy_insights(insights)
                
                time.sleep(300)  # Learn every 5 minutes
                
            except Exception as e:
                self.logger.error(f"Learning loop error: {e}")
                time.sleep(60)
    
    def _learn_from_goal(self, goal: Goal) -> None:
        """Learn from a completed goal."""
        if not self.memory:
            return
        
        # Extract lessons
        lesson = {
            'goal_type': goal.target.get('type', 'unknown'),
            'success': goal.status == GoalStatus.COMPLETED,
            'duration': goal.completed_at - goal.created_at,
            'subtasks': len(goal.subtasks),
            'completed_subtasks': len(goal.completed_subtasks)
        }
        
        # Store as knowledge
        self.memory.learn_fact(
            subject=f"goal_{goal.goal_id[:8]}",
            predicate="completed_in",
            object=f"{lesson['duration']:.0f}s",
            confidence=1.0,
            source="experience"
        )
        
        # Notify callbacks
        for callback in self.on_improve:
            try:
                callback('goal_completed', lesson)
            except Exception as e:
                self.logger.error(f"Improve callback error: {e}")
    
    def _apply_strategy_insights(self, insights: Dict[str, Any]) -> None:
        """Apply learned strategy insights."""
        if not self.openhands or not self.openhands.active_strategies:
            return
        
        best_strategy = insights.get('best_strategy')
        if best_strategy:
            # Increase weight of best performing strategy
            if best_strategy in self.openhands.active_strategies:
                self.openhands.active_strategies[best_strategy]['weight'] = min(
                    self.openhands.active_strategies[best_strategy]['weight'] * 1.1,
                    0.5
                )
                self.logger.info(f"Increased weight of {best_strategy} based on performance")
    
    # ==================== ADAPTATION ====================
    
    def _adaptation_loop(self) -> None:
        """Continuous adaptation loop."""
        while self.running:
            try:
                # Get performance metrics
                metrics = self._collect_performance_metrics()
                
                # Detect issues
                issues = self._detect_issues(metrics)
                
                if issues:
                    self._adapt_to_issues(issues)
                
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                self.logger.error(f"Adaptation loop error: {e}")
                time.sleep(30)
    
    def _collect_performance_metrics(self) -> Dict[str, Any]:
        """Collect performance metrics."""
        metrics = {
            'timestamp': time.time()
        }
        
        # Get task performance
        if self.openhands:
            stats = self.openhands.get_stats()
            metrics['tasks'] = stats.get('tasks', {})
        
        # Get memory stats
        if self.memory:
            metrics['memory'] = self.memory.get_stats()
        
        # Get orchestrator status
        if self.orchestrator:
            try:
                metrics['orchestrator'] = self.orchestrator.get_status()
            except:
                pass
        
        return metrics
    
    def _detect_issues(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect performance issues."""
        issues = []
        
        # Check task failures
        tasks = metrics.get('tasks', {})
        failed = tasks.get('failed', 0)
        total = tasks.get('total', 1)
        error_rate = failed / total if total > 0 else 0
        
        if error_rate > self.alert_thresholds.get('error_rate', 0.1):
            issues.append({
                'type': 'high_error_rate',
                'severity': 'warning' if error_rate < 0.3 else 'critical',
                'message': f"Error rate: {error_rate:.2%}",
                'metric': error_rate,
                'threshold': self.alert_thresholds['error_rate']
            })
        
        # Check task completion time
        pending = tasks.get('pending', 0)
        if pending > 20:
            issues.append({
                'type': 'task_backlog',
                'severity': 'warning',
                'message': f"Task backlog: {pending} pending",
                'metric': pending,
                'threshold': 20
            })
        
        return issues
    
    def _adapt_to_issues(self, issues: List[Dict[str, Any]]) -> None:
        """Adapt to detected issues."""
        for issue in issues:
            self.logger.warning(f"Adapting to: {issue['message']}")
            
            # Generate alert
            alert = {
                'type': issue['type'],
                'severity': issue['severity'],
                'message': issue['message'],
                'timestamp': time.time()
            }
            
            for callback in self.on_alert:
                try:
                    callback(alert)
                except Exception as e:
                    self.logger.error(f"Alert callback error: {e}")
            
            # Take adaptive action
            if issue['type'] == 'high_error_rate':
                # Reduce task priority
                if self.openhands:
                    for task in self.openhands.task_queue[:5]:
                        task.priority = max(task.priority.value - 1, 1)
            
            elif issue['type'] == 'task_backlog':
                # Increase workers (simplified)
                pass
    
    # ==================== MONITORING ====================
    
    def _monitoring_loop(self) -> None:
        """Continuous monitoring loop."""
        while self.running:
            try:
                # Update health status
                self._update_health_status()
                
                # Log metrics
                self._log_metrics()
                
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
                time.sleep(30)
    
    def _update_health_status(self) -> None:
        """Update system health status."""
        self.health_status = {
            'status': 'healthy',
            'timestamp': time.time(),
            'components': {}
        }
        
        # Check memory
        if self.memory:
            try:
                stats = self.memory.get_stats()
                self.health_status['components']['memory'] = 'healthy' if stats else 'warning'
            except:
                self.health_status['components']['memory'] = 'unknown'
        
        # Check openhands
        if self.openhands:
            try:
                stats = self.openhands.get_stats()
                self.health_status['components']['openhands'] = 'healthy'
            except:
                self.health_status['components']['openhands'] = 'error'
        
        # Check orchestrator
        if self.orchestrator:
            try:
                status = self.orchestrator.get_status()
                self.health_status['components']['orchestrator'] = 'healthy' if status.get('running') else 'stopped'
            except:
                self.health_status['components']['orchestrator'] = 'unknown'
        
        # Overall status
        errors = [c for c in self.health_status['components'].values() if c == 'error']
        if errors:
            self.health_status['status'] = 'degraded'
        if len(errors) > len(self.health_status['components']) / 2:
            self.health_status['status'] = 'critical'
    
    def _log_metrics(self) -> None:
        """Log performance metrics."""
        if self.openhands:
            stats = self.openhands.get_stats()
            self.performance_metrics = stats
    
    # ==================== PERSISTENCE ====================
    
    def _save_goals(self) -> None:
        """Save goals to disk."""
        try:
            goals_data = {
                goal_id: goal.to_dict() 
                for goal_id, goal in self.goals.items()
            }
            
            path = Path('~/.quanta_ai/autonomous_goals.json')
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w') as f:
                json.dump(goals_data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save goals: {e}")
    
    def _load_goals(self) -> None:
        """Load goals from disk."""
        try:
            path = Path('~/.quanta_ai/autonomous_goals.json')
            if path.exists():
                with open(path, 'r') as f:
                    goals_data = json.load(f)
                
                for goal_id, goal_data in goals_data.items():
                    goal = Goal(**goal_data)
                    self.goals[goal_id] = goal
        except Exception as e:
            self.logger.error(f"Failed to load goals: {e}")
    
    # ==================== PUBLIC API ====================
    
    def get_status(self) -> Dict[str, Any]:
        """Get autonomous engine status."""
        return {
            'running': self.running,
            'current_goal': self.current_goal.goal_id if self.current_goal else None,
            'goals_count': len(self.goals),
            'health': self.health_status,
            'features': {
                'learning': self.learning_enabled,
                'adaptation': self.adaptation_enabled,
                'self_improvement': self.self_improvement_enabled
            }
        }
    
    def set_alert_threshold(self, metric: str, threshold: float) -> None:
        """Set alert threshold for a metric."""
        self.alert_thresholds[metric] = threshold
    
    def add_goal_callback(self, callback: Callable) -> None:
        """Add callback for goal completion."""
        self.on_goal_complete.append(callback)
    
    def add_alert_callback(self, callback: Callable) -> None:
        """Add callback for alerts."""
        self.on_alert.append(callback)
    
    def add_improve_callback(self, callback: Callable) -> None:
        """Add callback for improvements."""
        self.on_improve.append(callback)
    
    def run_goal(self, description: str, target: Dict[str, Any],
                priority: int = 1) -> Dict[str, Any]:
        """Set and pursue a goal."""
        goal_id = self.set_goal(description, target, priority)
        return self.pursue_goal(goal_id)
