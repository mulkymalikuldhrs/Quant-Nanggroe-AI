"""
Agent Base - Master Controller & Task Coordinator
"""

from typing import Dict, List, Any
import json
from datetime import datetime

from ..core.base_agent import BaseAgent

class AgentBase(BaseAgent):
    """Master controller and task coordinator"""
    
    def __init__(self, config_path: str = "config/prompts.yaml"):
        super().__init__("agent_base", config_path)
        self.delegation_history = []
        self.active_delegations = {}
        
    def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming requests and coordinate other agents"""
        
        if not self.validate_input(task):
            return self.handle_error(
                Exception("Invalid task format"), task
            )
        
        try:
            self.update_status("analyzing", task)
            
            # Analyze the request
            analysis = self._analyze_request(task)
            
            # Create execution plan
            execution_plan = self._create_execution_plan(analysis)
            
            # Determine agent assignments
            assignments = self._determine_agent_assignments(execution_plan)
            
            self.update_status("coordinating")
            
            # Prepare response
            response_content = f"""
📋 ANALISIS TUGAS: {analysis['summary']}

🎯 RENCANA EKSEKUSI:
{self._format_execution_plan(execution_plan)}

👥 ASSIGNMENT AGENT:
{self._format_assignments(assignments)}

📊 STATUS: Ready for execution
✅ HASIL: Coordination plan created, ready to delegate tasks
            """
            
            # Log the delegation
            self._log_delegation(task, analysis, execution_plan, assignments)
            
            return self.format_response(response_content.strip(), "coordination_plan")
            
        except Exception as e:
            return self.handle_error(e, task)
    
    def _analyze_request(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze incoming request to understand requirements"""
        request = task.get('request', '')
        context = task.get('context', {})
        
        # Basic analysis - in production, this would use LLM
        analysis = {
            'summary': request[:200] + "..." if len(request) > 200 else request,
            'complexity': self._assess_complexity(request),
            'required_skills': self._identify_required_skills(request),
            'estimated_time': self._estimate_time(request),
            'priority': context.get('priority', 'medium'),
            'dependencies': self._identify_dependencies(request)
        }
        
        return analysis
    
    def _assess_complexity(self, request: str) -> str:
        """Assess task complexity"""
        # Simple heuristics - in production, use LLM
        if len(request) > 500 or any(word in request.lower() for word in ['complex', 'multiple', 'integrate', 'system']):
            return 'high'
        elif len(request) > 200 or any(word in request.lower() for word in ['create', 'design', 'analyze']):
            return 'medium'
        else:
            return 'low'
    
    def _identify_required_skills(self, request: str) -> List[str]:
        """Identify what skills/agents are needed"""
        skills = []
        request_lower = request.lower()
        
        # Map keywords to required agents
        skill_mapping = {
            'plan': 'planning',
            'execute': 'execution', 
            'code': 'execution',
            'script': 'execution',
            'design': 'design',
            'visual': 'design',
            'ui': 'design',
            'security': 'specialist',
            'legal': 'specialist',
            'compliance': 'specialist',
            'analysis': 'specialist',
            'data': 'execution',
            'api': 'execution',
            'report': 'output_handling'
        }
        
        for keyword, skill in skill_mapping.items():
            if keyword in request_lower and skill not in skills:
                skills.append(skill)
        
        # Always include planning for complex tasks
        if not skills or len(skills) > 2:
            skills.insert(0, 'planning')
        
        # Always include output handling for final compilation
        if 'output_handling' not in skills:
            skills.append('output_handling')
            
        return skills
    
    def _estimate_time(self, request: str) -> str:
        """Estimate time required"""
        complexity = self._assess_complexity(request)
        if complexity == 'high':
            return '2-4 hours'
        elif complexity == 'medium':
            return '30-60 minutes'
        else:
            return '10-30 minutes'
    
    def _identify_dependencies(self, request: str) -> List[str]:
        """Identify task dependencies"""
        dependencies = []
        request_lower = request.lower()
        
        if 'data' in request_lower or 'information' in request_lower:
            dependencies.append('knowledge_retrieval')
        
        if 'api' in request_lower or 'integration' in request_lower:
            dependencies.append('external_services')
            
        return dependencies
    
    def _create_execution_plan(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Create detailed execution plan"""
        skills = analysis['required_skills']
        
        # Standard workflow steps
        steps = []
        
        # Always start with planning for complex tasks
        if 'planning' in skills:
            steps.append({
                'step': 'Planning',
                'agent': 'agent_03_planner',
                'description': 'Break down goals into actionable tasks',
                'estimated_time': '10-15 minutes'
            })
        
        # Add knowledge retrieval if needed
        if 'knowledge_retrieval' in analysis.get('dependencies', []):
            steps.append({
                'step': 'Knowledge Retrieval',
                'agent': 'knowledge_base_rag',
                'description': 'Gather relevant context and information',
                'estimated_time': '5-10 minutes'
            })
        
        # Add execution step
        if 'execution' in skills:
            steps.append({
                'step': 'Execution',
                'agent': 'agent_04_executor',
                'description': 'Execute scripts, API calls, and automation',
                'estimated_time': '20-45 minutes'
            })
        
        # Add design step
        if 'design' in skills:
            steps.append({
                'step': 'Design Creation',
                'agent': 'agent_05_designer', 
                'description': 'Create visual assets and UI components',
                'estimated_time': '30-60 minutes'
            })
        
        # Add specialist review
        if 'specialist' in skills:
            steps.append({
                'step': 'Specialist Review',
                'agent': 'agent_06_specialist',
                'description': 'Domain expertise and validation',
                'estimated_time': '15-30 minutes'
            })
        
        # Always end with output handling
        if 'output_handling' in skills:
            steps.append({
                'step': 'Final Compilation',
                'agent': 'output_handler',
                'description': 'Compile and format final deliverable',
                'estimated_time': '10-20 minutes'
            })
        
        return {
            'total_steps': len(steps),
            'estimated_duration': analysis['estimated_time'],
            'complexity': analysis['complexity'],
            'steps': steps
        }
    
    def _determine_agent_assignments(self, execution_plan: Dict[str, Any]) -> Dict[str, Any]:
        """Determine specific agent assignments"""
        assignments = {}
        
        for i, step in enumerate(execution_plan['steps']):
            agent_id = step['agent']
            assignments[f"step_{i+1}"] = {
                'agent_id': agent_id,
                'agent_name': self._get_agent_name(agent_id),
                'task': step['description'],
                'estimated_time': step['estimated_time'],
                'priority': 'high' if i == 0 else 'medium',
                'dependencies': [f"step_{i}"] if i > 0 else []
            }
        
        return assignments
    
    def _get_agent_name(self, agent_id: str) -> str:
        """Get agent display name"""
        agent_names = {
            'agent_03_planner': 'Agent 03 (Planner)',
            'knowledge_base_rag': 'Knowledge Base (RAG)',
            'agent_04_executor': 'Agent 04 (Executor)', 
            'agent_05_designer': 'Agent 05 (Designer)',
            'agent_06_specialist': 'Agent 06 (Specialist)',
            'output_handler': 'Output Handler'
        }
        return agent_names.get(agent_id, agent_id)
    
    def _format_execution_plan(self, plan: Dict[str, Any]) -> str:
        """Format execution plan for display"""
        formatted = f"Complexity: {plan['complexity'].upper()}\n"
        formatted += f"Total Steps: {plan['total_steps']}\n"
        formatted += f"Estimated Duration: {plan['estimated_duration']}\n\n"
        
        for i, step in enumerate(plan['steps'], 1):
            formatted += f"{i}. {step['step']}\n"
            formatted += f"   → Agent: {step['agent']}\n"
            formatted += f"   → Task: {step['description']}\n"
            formatted += f"   → Time: {step['estimated_time']}\n\n"
        
        return formatted
    
    def _format_assignments(self, assignments: Dict[str, Any]) -> str:
        """Format agent assignments for display"""
        formatted = ""
        
        for step_id, assignment in assignments.items():
            formatted += f"• {assignment['agent_name']}\n"
            formatted += f"  Task: {assignment['task']}\n"
            formatted += f"  Priority: {assignment['priority']}\n"
            formatted += f"  Time: {assignment['estimated_time']}\n\n"
        
        return formatted
    
    def _log_delegation(self, task: Dict[str, Any], analysis: Dict[str, Any], 
                       execution_plan: Dict[str, Any], assignments: Dict[str, Any]):
        """Log delegation for tracking"""
        delegation_log = {
            'timestamp': datetime.now().isoformat(),
            'task_id': task.get('task_id'),
            'request_summary': analysis['summary'],
            'execution_plan': execution_plan,
            'assignments': assignments,
            'status': 'delegated'
        }
        
        self.delegation_history.append(delegation_log)
        self.active_delegations[task.get('task_id')] = delegation_log
    
    def get_delegation_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of a delegated task"""
        return self.active_delegations.get(task_id, {})
    
    def update_delegation_status(self, task_id: str, status: str, results: Dict[str, Any] = None):
        """Update delegation status"""
        if task_id in self.active_delegations:
            self.active_delegations[task_id]['status'] = status
            self.active_delegations[task_id]['updated_at'] = datetime.now().isoformat()
            
            if results:
                self.active_delegations[task_id]['results'] = results
