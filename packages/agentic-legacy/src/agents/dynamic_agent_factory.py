"""
Dynamic Agent Factory - Creates new agents based on specific needs
"""

from typing import Dict, List, Any, Optional
import json
from datetime import datetime

from ..core.base_agent import BaseAgent

class DynamicAgentFactory(BaseAgent):
    """Creates and manages dynamic agents for specific tasks"""
    
    def __init__(self, config_path: str = "config/prompts.yaml"):
        super().__init__("dynamic_agent_factory", config_path)
        self.created_agents = {}
        self.agent_templates = {}
        self._load_agent_templates()
        
    def _load_agent_templates(self):
        """Load templates for creating new agents"""
        self.agent_templates = {
            'data_scientist': {
                'role': 'Data Analysis & Machine Learning',
                'skills': ['python', 'pandas', 'scikit-learn', 'statistics', 'visualization'],
                'prompt_template': """
                Anda adalah Data Scientist specialist. Anda ahli dalam:
                - Analisis data dan statistik
                - Machine learning dan modeling
                - Data visualization
                - Python ecosystem (pandas, numpy, scikit-learn)
                - Statistical analysis dan hypothesis testing
                """
            },
            'devops_engineer': {
                'role': 'DevOps & Infrastructure',
                'skills': ['docker', 'kubernetes', 'ci/cd', 'cloud', 'monitoring'],
                'prompt_template': """
                Anda adalah DevOps Engineer specialist. Anda ahli dalam:
                - Container orchestration (Docker, Kubernetes)
                - CI/CD pipelines
                - Cloud infrastructure (AWS, GCP, Azure)
                - Monitoring dan logging
                - Infrastructure as Code
                """
            },
            'frontend_developer': {
                'role': 'Frontend Development',
                'skills': ['javascript', 'react', 'vue', 'html', 'css', 'ui/ux'],
                'prompt_template': """
                Anda adalah Frontend Developer specialist. Anda ahli dalam:
                - Modern JavaScript frameworks (React, Vue, Angular)
                - HTML5, CSS3, responsive design
                - UI/UX best practices
                - Frontend build tools
                - Web performance optimization
                """
            },
            'backend_developer': {
                'role': 'Backend Development',
                'skills': ['python', 'node.js', 'databases', 'apis', 'microservices'],
                'prompt_template': """
                Anda adalah Backend Developer specialist. Anda ahli dalam:
                - Server-side programming (Python, Node.js, Java)
                - Database design dan optimization
                - REST API dan GraphQL development
                - Microservices architecture
                - System design dan scalability
                """
            },
            'content_writer': {
                'role': 'Content Creation & Writing',
                'skills': ['writing', 'copywriting', 'seo', 'content_strategy'],
                'prompt_template': """
                Anda adalah Content Writer specialist. Anda ahli dalam:
                - Technical writing dan documentation
                - Copywriting dan marketing content
                - SEO optimization
                - Content strategy
                - Multi-language content creation
                """
            },
            'product_manager': {
                'role': 'Product Management',
                'skills': ['product_strategy', 'requirements', 'roadmap', 'analytics'],
                'prompt_template': """
                Anda adalah Product Manager specialist. Anda ahli dalam:
                - Product strategy dan roadmap planning
                - Requirements gathering dan analysis
                - User experience research
                - Product analytics dan metrics
                - Cross-functional team coordination
                """
            }
        }
    
    def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Assess need for new agents and create them if necessary"""
        
        if not self.validate_input(task):
            return self.handle_error(
                Exception("Invalid task format"), task
            )
        
        try:
            self.update_status("assessing", task)
            
            # Assess if new agents are needed
            assessment = self._assess_agent_needs(task)
            
            # Create agents if needed
            created_agents = []
            if assessment['needs_new_agents']:
                created_agents = self._create_required_agents(assessment['required_agents'])
            
            self.update_status("ready")
            
            # Prepare response
            response_content = f"""
🏭 ASSESSMENT: {assessment['summary']}

⚙️ SPECIFICATION:
{self._format_agent_specs(assessment.get('required_agents', []))}

🚀 DEPLOYMENT:
{self._format_deployment_info(created_agents)}

📈 MONITORING: {len(self.created_agents)} total dynamic agents active
            """
            
            return self.format_response(response_content.strip(), "agent_creation")
            
        except Exception as e:
            return self.handle_error(e, task)
    
    def _assess_agent_needs(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Assess if new specialized agents are needed"""
        request = task.get('request', '')
        context = task.get('context', {})
        
        # Analyze request for specialized needs
        required_agents = []
        request_lower = request.lower()
        
        # Check for specific specializations
        specialization_mapping = {
            'data science': 'data_scientist',
            'machine learning': 'data_scientist',
            'ml': 'data_scientist',
            'analytics': 'data_scientist',
            'devops': 'devops_engineer',
            'deployment': 'devops_engineer',
            'infrastructure': 'devops_engineer',
            'ci/cd': 'devops_engineer',
            'frontend': 'frontend_developer',
            'react': 'frontend_developer',
            'vue': 'frontend_developer',
            'ui': 'frontend_developer',
            'backend': 'backend_developer',
            'api': 'backend_developer',
            'database': 'backend_developer',
            'server': 'backend_developer',
            'content': 'content_writer',
            'writing': 'content_writer',
            'documentation': 'content_writer',
            'product': 'product_manager',
            'roadmap': 'product_manager',
            'requirements': 'product_manager'
        }
        
        for keyword, agent_type in specialization_mapping.items():
            if keyword in request_lower and agent_type not in required_agents:
                required_agents.append(agent_type)
        
        # Check complexity indicators
        complexity_indicators = ['complex', 'enterprise', 'scalable', 'production', 'multiple']
        high_complexity = any(indicator in request_lower for indicator in complexity_indicators)
        
        # Determine if new agents are needed
        needs_new_agents = bool(required_agents) or high_complexity
        
        assessment = {
            'needs_new_agents': needs_new_agents,
            'required_agents': required_agents,
            'complexity': 'high' if high_complexity else 'medium',
            'summary': self._create_assessment_summary(needs_new_agents, required_agents, high_complexity),
            'justification': self._create_justification(request, required_agents)
        }
        
        return assessment
    
    def _create_assessment_summary(self, needs_new: bool, agents: List[str], high_complexity: bool) -> str:
        """Create assessment summary"""
        if not needs_new:
            return "Existing agents sufficient for this task"
        
        if high_complexity:
            return f"High complexity task requiring specialized agents: {', '.join(agents)}"
        
        return f"Specialized expertise needed: {', '.join(agents)}"
    
    def _create_justification(self, request: str, required_agents: List[str]) -> str:
        """Create justification for agent creation"""
        if not required_agents:
            return "No specialized agents required"
        
        justifications = []
        for agent_type in required_agents:
            template = self.agent_templates.get(agent_type, {})
            role = template.get('role', agent_type)
            justifications.append(f"- {role}: Required for specialized expertise in this domain")
        
        return "\n".join(justifications)
    
    def _create_required_agents(self, agent_types: List[str]) -> List[Dict[str, Any]]:
        """Create the required specialized agents"""
        created_agents = []
        
        for agent_type in agent_types:
            if agent_type in self.agent_templates:
                agent_spec = self._create_agent_spec(agent_type)
                created_agents.append(agent_spec)
                
                # Register the created agent
                agent_id = agent_spec['agent_id']
                self.created_agents[agent_id] = {
                    'spec': agent_spec,
                    'created_at': datetime.now().isoformat(),
                    'status': 'active',
                    'tasks_handled': 0
                }
        
        return created_agents
    
    def _create_agent_spec(self, agent_type: str) -> Dict[str, Any]:
        """Create specification for a new agent"""
        template = self.agent_templates[agent_type]
        agent_id = f"{agent_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return {
            'agent_id': agent_id,
            'agent_type': agent_type,
            'name': template['role'],
            'skills': template['skills'],
            'prompt': template['prompt_template'],
            'creation_timestamp': datetime.now().isoformat(),
            'status': 'ready'
        }
    
    def _format_agent_specs(self, required_agents: List[str]) -> str:
        """Format agent specifications for display"""
        if not required_agents:
            return "No new agents required"
        
        formatted = ""
        for agent_type in required_agents:
            if agent_type in self.agent_templates:
                template = self.agent_templates[agent_type]
                formatted += f"• Type: {agent_type}\n"
                formatted += f"  Role: {template['role']}\n"
                formatted += f"  Skills: {', '.join(template['skills'])}\n\n"
        
        return formatted
    
    def _format_deployment_info(self, created_agents: List[Dict[str, Any]]) -> str:
        """Format deployment information"""
        if not created_agents:
            return "No agents created in this session"
        
        formatted = ""
        for agent in created_agents:
            formatted += f"✅ Created: {agent['name']}\n"
            formatted += f"   ID: {agent['agent_id']}\n"
            formatted += f"   Status: {agent['status']}\n\n"
        
        return formatted
    
    def get_created_agents(self) -> Dict[str, Any]:
        """Get list of all created agents"""
        return self.created_agents
    
    def deactivate_agent(self, agent_id: str) -> bool:
        """Deactivate a created agent"""
        if agent_id in self.created_agents:
            self.created_agents[agent_id]['status'] = 'deactivated'
            self.created_agents[agent_id]['deactivated_at'] = datetime.now().isoformat()
            return True
        return False
    
    def get_agent_performance(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get performance metrics for a created agent"""
        if agent_id in self.created_agents:
            return self.created_agents[agent_id]
        return None
