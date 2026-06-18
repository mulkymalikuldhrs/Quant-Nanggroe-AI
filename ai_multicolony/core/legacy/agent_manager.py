"""
Agent Manager - Orchestrates all agents in the system
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

from .base_agent import BaseAgent

class AgentManager:
    """Manages and coordinates all agents in the system"""
    
    def __init__(self, config_path: str = "config/prompts.yaml"):
        self.config_path = config_path
        self.agents = {}
        self.active_workflows = {}
        self.communication_log = []
        
        # Initialize logging
        self.logger = logging.getLogger("agentic.manager")
        
        # Workflow management
        self.workflow_templates = {}
        self.load_workflow_templates()
        
    def register_agent(self, agent: BaseAgent):
        """Register an agent with the manager"""
        self.agents[agent.agent_id] = agent
        self.logger.info(f"Registered agent: {agent.name} ({agent.agent_id})")
    
    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Get agent by ID"""
        return self.agents.get(agent_id)
    
    def list_agents(self) -> List[Dict[str, Any]]:
        """List all registered agents"""
        return [
            {
                'id': agent.agent_id,
                'name': agent.name,
                'role': agent.role,
                'emoji': agent.emoji,
                'status': agent.status
            }
            for agent in self.agents.values()
        ]
    
    def load_workflow_templates(self):
        """Load workflow templates from config"""
        try:
            import yaml
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            self.workflow_templates = config.get('workflow', {})
            self.logger.info("Workflow templates loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to load workflow templates: {e}")
    
    async def execute_workflow(self, workflow_name: str, request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a predefined workflow"""
        workflow_id = f"{workflow_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if workflow_name not in self.workflow_templates:
            return self._error_response(f"Workflow '{workflow_name}' not found")
        
        workflow = self.workflow_templates[workflow_name]
        self.active_workflows[workflow_id] = {
            'name': workflow_name,
            'status': 'running',
            'started_at': datetime.now().isoformat(),
            'steps': [],
            'current_step': 0,
            'results': {}
        }
        
        try:
            results = await self._execute_workflow_steps(workflow_id, workflow, request)
            
            self.active_workflows[workflow_id]['status'] = 'completed'
            self.active_workflows[workflow_id]['completed_at'] = datetime.now().isoformat()
            
            return {
                'workflow_id': workflow_id,
                'status': 'completed',
                'results': results
            }
            
        except Exception as e:
            self.active_workflows[workflow_id]['status'] = 'failed'
            self.active_workflows[workflow_id]['error'] = str(e)
            
            return self._error_response(f"Workflow execution failed: {str(e)}")
    
    async def _execute_workflow_steps(self, workflow_id: str, workflow: List[Dict], request: Dict[str, Any]) -> Dict[str, Any]:
        """Execute individual workflow steps"""
        results = {}
        context = {'original_request': request}
        
        for i, step in enumerate(workflow):
            self.active_workflows[workflow_id]['current_step'] = i
            
            step_info = {
                'step': step.get('step', f'Step {i+1}'),
                'agent': step.get('agent'),
                'action': step.get('action'),
                'started_at': datetime.now().isoformat()
            }
            
            try:
                # Get the agent for this step
                agent_id = step.get('agent')
                agent = self.get_agent(agent_id)
                
                if not agent:
                    raise Exception(f"Agent '{agent_id}' not found")
                
                # Prepare task for agent
                task = {
                    'task_id': f"{workflow_id}_step_{i}",
                    'request': step.get('action'),
                    'context': context,
                    'workflow_id': workflow_id,
                    'step_number': i
                }
                
                # Execute task
                result = await self._execute_agent_task(agent, task)
                
                # Store result
                step_key = step.get('step', f'step_{i}')
                results[step_key] = result
                context[step_key] = result
                
                step_info['completed_at'] = datetime.now().isoformat()
                step_info['status'] = 'completed'
                step_info['result'] = result
                
            except Exception as e:
                step_info['status'] = 'failed'
                step_info['error'] = str(e)
                self.logger.error(f"Step {i} failed: {e}")
                
                # Decide whether to continue or stop
                if step.get('critical', True):
                    raise e
            
            self.active_workflows[workflow_id]['steps'].append(step_info)
        
        return results
    
    async def _execute_agent_task(self, agent: BaseAgent, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task on a specific agent"""
        try:
            # Update agent status
            agent.update_status("processing", task)
            
            # Process the task
            result = agent.process_task(task)
            
            # Log the communication
            self._log_communication(agent.agent_id, task, result)
            
            # Update agent status
            agent.update_status("ready")
            
            return result
            
        except Exception as e:
            agent.update_status("error")
            raise e
    
    def _log_communication(self, agent_id: str, task: Dict[str, Any], result: Dict[str, Any]):
        """Log communication between manager and agents"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'agent_id': agent_id,
            'task': task,
            'result': result
        }
        
        self.communication_log.append(log_entry)
        
        # Keep only recent entries to manage memory
        if len(self.communication_log) > 1000:
            self.communication_log = self.communication_log[-500:]
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        agent_stats = []
        for agent in self.agents.values():
            agent_stats.append(agent.get_performance_metrics())
        
        return {
            'timestamp': datetime.now().isoformat(),
            'total_agents': len(self.agents),
            'active_workflows': len([w for w in self.active_workflows.values() if w['status'] == 'running']),
            'agent_status': agent_stats,
            'recent_communications': self.communication_log[-10:] if self.communication_log else []
        }
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific workflow"""
        return self.active_workflows.get(workflow_id)
    
    def _error_response(self, message: str) -> Dict[str, Any]:
        """Generate error response"""
        return {
            'status': 'error',
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
    
    async def send_message_between_agents(self, from_agent_id: str, to_agent_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """Facilitate communication between agents"""
        from_agent = self.get_agent(from_agent_id)
        to_agent = self.get_agent(to_agent_id)
        
        if not from_agent or not to_agent:
            return self._error_response("One or both agents not found")
        
        # Format inter-agent communication
        communication_task = {
            'task_id': f"comm_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'request': message.get('request', ''),
            'context': {
                'from_agent': from_agent_id,
                'communication_type': 'inter_agent',
                'original_message': message
            }
        }
        
        try:
            result = await self._execute_agent_task(to_agent, communication_task)
            
            # Log the inter-agent communication
            self._log_communication(f"{from_agent_id}->{to_agent_id}", communication_task, result)
            
            return result
            
        except Exception as e:
            return self._error_response(f"Communication failed: {str(e)}")
