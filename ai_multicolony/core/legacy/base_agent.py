"""
Base Agent Class for Agentic AI System
Provides common functionality for all agents
"""

import abc
import yaml
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
import logging

class BaseAgent(abc.ABC):
    """Base class for all agents in the system"""
    
    def __init__(self, agent_id: str, config_path: str = "config/prompts.yaml"):
        self.agent_id = agent_id
        self.config = self._load_config(config_path)
        self.agent_config = self.config.get('agents', {}).get(agent_id, {})
        self.name = self.agent_config.get('name', agent_id)
        self.role = self.agent_config.get('role', 'Unknown')
        self.emoji = self.agent_config.get('emoji', '🤖')
        self.prompt = self.agent_config.get('prompt', '')
        
        # Initialize logging
        self.logger = logging.getLogger(f"agentic.{agent_id}")
        
        # State management
        self.status = "initialized"
        self.current_task = None
        self.task_history = []
        self.performance_metrics = {
            'tasks_completed': 0,
            'success_rate': 1.0,
            'avg_response_time': 0.0,
            'errors': 0
        }
        
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logging.error(f"Failed to load config: {e}")
            return {}
    
    @abc.abstractmethod
    def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process a task - must be implemented by each agent"""
        pass
    
    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent"""
        return f"""
        {self.prompt}
        
        AGENT INFO:
        - Name: {self.name}
        - Role: {self.role}
        - ID: {self.agent_id}
        
        Always respond in the format specified in your prompt.
        Include your emoji ({self.emoji}) in status updates.
        """
    
    def update_status(self, status: str, task_info: Optional[Dict] = None):
        """Update agent status"""
        self.status = status
        self.current_task = task_info
        self.logger.info(f"{self.emoji} {self.name} status: {status}")
    
    def log_task_completion(self, task: Dict, result: Dict, success: bool = True):
        """Log completed task for performance tracking"""
        task_log = {
            'timestamp': datetime.now().isoformat(),
            'task': task,
            'result': result,
            'success': success,
            'response_time': getattr(self, '_task_start_time', 0)
        }
        
        self.task_history.append(task_log)
        self.performance_metrics['tasks_completed'] += 1
        
        if not success:
            self.performance_metrics['errors'] += 1
        
        # Update success rate
        total_tasks = self.performance_metrics['tasks_completed']
        successful_tasks = total_tasks - self.performance_metrics['errors']
        self.performance_metrics['success_rate'] = successful_tasks / total_tasks if total_tasks > 0 else 1.0
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        return {
            'agent_id': self.agent_id,
            'name': self.name,
            'status': self.status,
            'metrics': self.performance_metrics,
            'current_task': self.current_task
        }
    
    def format_response(self, content: str, response_type: str = "standard") -> Dict[str, Any]:
        """Format agent response consistently"""
        return {
            'agent_id': self.agent_id,
            'agent_name': self.name,
            'emoji': self.emoji,
            'response_type': response_type,
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'status': self.status
        }
    
    def validate_input(self, task: Dict[str, Any]) -> bool:
        """Validate input task format"""
        required_fields = ['task_id', 'request', 'context']
        return all(field in task for field in required_fields)
    
    def handle_error(self, error: Exception, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle errors gracefully"""
        error_msg = f"Error in {self.name}: {str(error)}"
        self.logger.error(error_msg)
        
        return self.format_response(
            f"❌ {error_msg}\n\nTask: {task.get('request', 'Unknown')}\nPlease retry or contact system administrator.",
            "error"
        )
