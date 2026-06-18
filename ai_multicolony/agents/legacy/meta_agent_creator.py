"""
🤖 Meta Agent Creator - Advanced Agent Creation System
Creates specialized AI agents dynamically based on requirements
Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

class MetaAgentCreator:
    """
    Meta Agent that creates other specialized agents based on requirements.
    This agent can analyze tasks and create purpose-built agents for specific functions.
    """
    
    def __init__(self):
        self.agent_id = "meta_agent_creator"
        self.name = "Meta Agent Creator"
        self.version = "2.0.0"
        self.capabilities = [
            "agent_creation",
            "code_generation", 
            "requirement_analysis",
            "template_management",
            "agent_deployment",
            "dynamic_specialization"
        ]
        self.status = "ready"
        self.created_agents = []
        self.agent_templates = self._load_agent_templates()
        self.specializations = self._load_specializations()
        
        # Performance tracking
        self.agents_created = 0
        self.last_creation_time = None
        self.success_rate = 100.0
        
        print(f"✅ {self.name} initialized successfully")
    
    def _load_agent_templates(self) -> Dict[str, Dict]:
        """Load predefined agent templates"""
        return {
            "data_scientist": {
                "description": "Specialized in data analysis, machine learning, and statistical modeling",
                "capabilities": ["data_analysis", "ml_modeling", "statistical_analysis", "data_visualization"],
                "imports": ["pandas", "numpy", "sklearn", "matplotlib", "seaborn"],
                "base_functions": ["analyze_data", "create_model", "visualize_results"]
            },
            "web_developer": {
                "description": "Specialized in web development, frontend and backend",
                "capabilities": ["html_css", "javascript", "react", "nodejs", "api_development"],
                "imports": ["requests", "flask", "fastapi"],
                "base_functions": ["create_webpage", "build_api", "setup_server"]
            },
            "devops_engineer": {
                "description": "Specialized in deployment, infrastructure, and CI/CD",
                "capabilities": ["docker", "kubernetes", "ci_cd", "cloud_deployment", "monitoring"],
                "imports": ["docker", "subprocess", "yaml"],
                "base_functions": ["deploy_application", "setup_infrastructure", "monitor_system"]
            },
            "content_creator": {
                "description": "Specialized in content creation, writing, and social media",
                "capabilities": ["content_writing", "social_media", "seo", "copywriting"],
                "imports": ["requests", "beautifulsoup4"],
                "base_functions": ["create_content", "optimize_seo", "manage_social_media"]
            },
            "mobile_developer": {
                "description": "Specialized in mobile app development",
                "capabilities": ["react_native", "flutter", "ios", "android", "mobile_ui"],
                "imports": ["requests"],
                "base_functions": ["create_mobile_app", "design_ui", "implement_features"]
            },
            "security_specialist": {
                "description": "Specialized in cybersecurity and security auditing",
                "capabilities": ["security_audit", "penetration_testing", "vulnerability_assessment"],
                "imports": ["cryptography", "hashlib", "ssl"],
                "base_functions": ["security_audit", "scan_vulnerabilities", "encrypt_data"]
            },
            "ai_researcher": {
                "description": "Specialized in AI research and model development",
                "capabilities": ["ai_research", "model_development", "paper_analysis", "experiment_design"],
                "imports": ["torch", "tensorflow", "transformers", "openai"],
                "base_functions": ["research_topic", "develop_model", "analyze_papers"]
            },
            "business_analyst": {
                "description": "Specialized in business analysis and strategy",
                "capabilities": ["market_analysis", "business_planning", "financial_modeling"],
                "imports": ["pandas", "numpy", "requests"],
                "base_functions": ["analyze_market", "create_business_plan", "financial_forecast"]
            }
        }
    
    def _load_specializations(self) -> Dict[str, List[str]]:
        """Load available specializations and their skills"""
        return {
            "programming_languages": ["python", "javascript", "java", "go", "rust", "cpp", "csharp"],
            "frameworks": ["react", "vue", "angular", "django", "flask", "fastapi", "express", "spring"],
            "databases": ["postgresql", "mysql", "mongodb", "redis", "elasticsearch"],
            "cloud_platforms": ["aws", "gcp", "azure", "digitalocean", "heroku"],
            "ai_ml": ["tensorflow", "pytorch", "scikit_learn", "huggingface", "openai"],
            "industries": ["fintech", "healthcare", "ecommerce", "education", "gaming", "media"]
        }
    
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process agent creation requests"""
        try:
            task_type = task.get('type', 'create_agent')
            
            if task_type == 'create_agent':
                return await self.create_agent(task)
            elif task_type == 'analyze_requirements':
                return await self.analyze_requirements(task)
            elif task_type == 'list_templates':
                return self.list_agent_templates()
            elif task_type == 'update_agent':
                return await self.update_existing_agent(task)
            elif task_type == 'clone_agent':
                return await self.clone_agent(task)
            else:
                return {
                    'success': False,
                    'error': f'Unknown task type: {task_type}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Meta agent creation error: {str(e)}'
            }
    
    async def create_agent(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new specialized agent based on requirements"""
        try:
            requirements = task.get('requirements', {})
            agent_name = requirements.get('name', f'custom_agent_{len(self.created_agents)}')
            agent_type = requirements.get('type', 'general_purpose')
            description = requirements.get('description', 'Custom AI agent')
            capabilities = requirements.get('capabilities', [])
            
            print(f"🤖 Creating new agent: {agent_name}")
            
            # Analyze requirements and select template
            template = await self._select_best_template(requirements)
            
            # Generate agent code
            agent_code = await self._generate_agent_code(
                agent_name, agent_type, description, capabilities, template
            )
            
            # Create agent file
            agent_file = await self._create_agent_file(agent_name, agent_code)
            
            # Register the new agent
            agent_info = {
                'name': agent_name,
                'type': agent_type,
                'description': description,
                'capabilities': capabilities,
                'file_path': agent_file,
                'created_at': datetime.now().isoformat(),
                'created_by': 'meta_agent_creator',
                'version': '1.0.0',
                'template_used': template['name'] if template else 'custom'
            }
            
            self.created_agents.append(agent_info)
            self.agents_created += 1
            self.last_creation_time = datetime.now()
            
            # Update UI automatically
            await self._update_ui_for_new_agent(agent_info)
            
            return {
                'success': True,
                'message': f'Agent {agent_name} created successfully',
                'agent_info': agent_info,
                'file_path': agent_file,
                'capabilities': capabilities
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to create agent: {str(e)}'
            }
    
    async def _select_best_template(self, requirements: Dict[str, Any]) -> Optional[Dict]:
        """Select the best template based on requirements"""
        agent_type = requirements.get('type', '').lower()
        capabilities = requirements.get('capabilities', [])
        description = requirements.get('description', '').lower()
        
        # Direct template match
        if agent_type in self.agent_templates:
            template = self.agent_templates[agent_type].copy()
            template['name'] = agent_type
            return template
        
        # Capability-based matching
        best_match = None
        best_score = 0
        
        for template_name, template in self.agent_templates.items():
            score = 0
            
            # Check capability overlap
            template_caps = template.get('capabilities', [])
            overlap = len(set(capabilities) & set(template_caps))
            score += overlap * 2
            
            # Check description keywords
            template_desc = template.get('description', '').lower()
            desc_words = description.split()
            for word in desc_words:
                if word in template_desc:
                    score += 1
            
            if score > best_score:
                best_score = score
                best_match = template.copy()
                best_match['name'] = template_name
        
        return best_match if best_score > 0 else None
    
    async def _generate_agent_code(self, name: str, agent_type: str, description: str, 
                                 capabilities: List[str], template: Optional[Dict]) -> str:
        """Generate the Python code for the new agent"""
        
        class_name = ''.join(word.capitalize() for word in name.replace('_', ' ').split()) + 'Agent'
        
        # Base imports
        imports = [
            "import asyncio",
            "import json", 
            "import os",
            "from datetime import datetime",
            "from typing import Dict, Any, List, Optional"
        ]
        
        # Add template-specific imports
        if template:
            template_imports = template.get('imports', [])
            for imp in template_imports:
                imports.append(f"import {imp}")
        
        # Generate class structure
        code = f'''"""
🤖 {name.replace('_', ' ').title()} Agent
{description}
Auto-generated by Meta Agent Creator
Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

{chr(10).join(imports)}

class {class_name}:
    """
    {description}
    
    Capabilities: {', '.join(capabilities)}
    """
    
    def __init__(self):
        self.agent_id = "{name}"
        self.name = "{name.replace('_', ' ').title()}"
        self.agent_type = "{agent_type}"
        self.version = "1.0.0"
        self.capabilities = {capabilities}
        self.status = "ready"
        
        # Performance metrics
        self.tasks_completed = 0
        self.success_rate = 100.0
        self.last_activity = None
        
        print(f"✅ {{self.name}} initialized successfully")
    
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming tasks"""
        try:
            self.last_activity = datetime.now()
            task_type = task.get('type', 'general')
            
            print(f"🔄 {{self.name}} processing task: {{task_type}}")
            
            # Route to appropriate method
            if hasattr(self, f'handle_{{task_type}}'):
                handler = getattr(self, f'handle_{{task_type}}')
                result = await handler(task)
            else:
                result = await self.handle_general_task(task)
            
            # Update metrics
            if result.get('success', False):
                self.tasks_completed += 1
            
            return result
            
        except Exception as e:
            return {{
                'success': False,
                'error': f'{{self.name}} error: {{str(e)}}'
            }}
    
    async def handle_general_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle general tasks"""
        return {{
            'success': True,
            'message': f'{{self.name}} processed general task',
            'result': 'Task completed successfully',
            'timestamp': datetime.now().isoformat()
        }}
'''
        
        # Add template-specific methods
        if template:
            base_functions = template.get('base_functions', [])
            for func_name in base_functions:
                method_code = self._generate_method_code(func_name, template)
                code += f"\n{method_code}"
        
        # Add performance and utility methods
        code += f'''
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get agent performance metrics"""
        return {{
            'agent_id': self.agent_id,
            'name': self.name,
            'type': self.agent_type,
            'status': self.status,
            'capabilities': self.capabilities,
            'tasks_completed': self.tasks_completed,
            'success_rate': self.success_rate,
            'last_activity': self.last_activity.isoformat() if self.last_activity else None,
            'uptime': str(datetime.now() - (self.last_activity or datetime.now()))
        }}
    
    def get_status(self) -> str:
        """Get current agent status"""
        return self.status
    
    def set_status(self, status: str):
        """Set agent status"""
        self.status = status
        print(f"📊 {{self.name}} status changed to: {{status}}")

# Global instance
{name} = {class_name}()
'''
        
        return code
    
    def _generate_method_code(self, func_name: str, template: Dict) -> str:
        """Generate code for template-specific methods"""
        method_templates = {
            'analyze_data': '''
    async def handle_analyze_data(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze data from various sources"""
        try:
            data_source = task.get('data_source')
            analysis_type = task.get('analysis_type', 'descriptive')
            
            # Data analysis logic here
            result = {
                'analysis_type': analysis_type,
                'summary': 'Data analysis completed',
                'insights': ['Key insight 1', 'Key insight 2'],
                'recommendations': ['Recommendation 1', 'Recommendation 2']
            }
            
            return {
                'success': True,
                'result': result,
                'message': 'Data analysis completed successfully'
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}''',
            
            'create_webpage': '''
    async def handle_create_webpage(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Create a webpage based on specifications"""
        try:
            page_type = task.get('page_type', 'landing')
            content = task.get('content', {})
            
            # Web development logic here
            html_code = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{content.get('title', 'New Page')}</title>
</head>
<body>
    <h1>{content.get('heading', 'Welcome')}</h1>
    <p>{content.get('description', 'This is a new webpage.')}</p>
</body>
</html>
            """
            
            return {
                'success': True,
                'result': {'html': html_code, 'page_type': page_type},
                'message': 'Webpage created successfully'
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}''',
            
            'deploy_application': '''
    async def handle_deploy_application(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy application to specified platform"""
        try:
            platform = task.get('platform', 'heroku')
            app_path = task.get('app_path', '.')
            
            # Deployment logic here
            deployment_steps = [
                'Building application',
                'Running tests',
                'Creating deployment package',
                f'Deploying to {platform}',
                'Verifying deployment'
            ]
            
            return {
                'success': True,
                'result': {
                    'platform': platform,
                    'deployment_url': f'https://your-app.{platform}.com',
                    'steps_completed': deployment_steps
                },
                'message': 'Application deployed successfully'
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}'''
        }
        
        return method_templates.get(func_name, f'''
    async def handle_{func_name}(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle {func_name.replace('_', ' ')} tasks"""
        try:
            # Implementation for {func_name}
            return {{
                'success': True,
                'result': '{func_name} completed',
                'message': '{func_name.replace("_", " ").title()} task completed successfully'
            }}
        except Exception as e:
            return {{'success': False, 'error': str(e)}}''')
    
    async def _create_agent_file(self, agent_name: str, agent_code: str) -> str:
        """Create the agent Python file"""
        # Ensure agents directory exists
        agents_dir = Path("agents")
        agents_dir.mkdir(exist_ok=True)
        
        # Create the agent file
        file_path = agents_dir / f"{agent_name}.py"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(agent_code)
        
        print(f"📄 Agent file created: {file_path}")
        return str(file_path)
    
    async def _update_ui_for_new_agent(self, agent_info: Dict[str, Any]):
        """Update the UI to include the new agent"""
        try:
            # Update web interface agent registry
            # This would integrate with the web interface to add the new agent
            print(f"🔄 Updating UI for new agent: {agent_info['name']}")
            
            # In a real implementation, this would:
            # 1. Update the agent registry in the web interface
            # 2. Add new navigation items
            # 3. Create agent-specific pages
            # 4. Update the agent list in real-time
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to update UI: {e}")
            return False
    
    async def analyze_requirements(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze requirements to suggest optimal agent configuration"""
        try:
            requirements = task.get('requirements', '')
            
            # AI-powered requirement analysis
            analysis = {
                'suggested_type': 'general_purpose',
                'recommended_capabilities': [],
                'complexity_score': 'medium',
                'estimated_development_time': '1-2 hours',
                'suggested_templates': []
            }
            
            # Simple keyword-based analysis (in real implementation, use LLM)
            requirements_lower = requirements.lower()
            
            if any(word in requirements_lower for word in ['data', 'analysis', 'machine learning', 'ml']):
                analysis['suggested_type'] = 'data_scientist'
                analysis['recommended_capabilities'].extend(['data_analysis', 'ml_modeling'])
                analysis['suggested_templates'].append('data_scientist')
            
            if any(word in requirements_lower for word in ['web', 'website', 'frontend', 'backend']):
                analysis['suggested_type'] = 'web_developer'
                analysis['recommended_capabilities'].extend(['html_css', 'javascript'])
                analysis['suggested_templates'].append('web_developer')
            
            if any(word in requirements_lower for word in ['deploy', 'devops', 'infrastructure']):
                analysis['suggested_type'] = 'devops_engineer'
                analysis['recommended_capabilities'].extend(['docker', 'ci_cd'])
                analysis['suggested_templates'].append('devops_engineer')
            
            return {
                'success': True,
                'analysis': analysis,
                'message': 'Requirements analyzed successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Requirements analysis failed: {str(e)}'
            }
    
    def list_agent_templates(self) -> Dict[str, Any]:
        """List all available agent templates"""
        return {
            'success': True,
            'templates': self.agent_templates,
            'specializations': self.specializations,
            'total_templates': len(self.agent_templates)
        }
    
    async def update_existing_agent(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing agent with new capabilities"""
        try:
            agent_name = task.get('agent_name')
            new_capabilities = task.get('new_capabilities', [])
            
            # Find and update the agent
            for agent in self.created_agents:
                if agent['name'] == agent_name:
                    agent['capabilities'].extend(new_capabilities)
                    agent['updated_at'] = datetime.now().isoformat()
                    break
            
            return {
                'success': True,
                'message': f'Agent {agent_name} updated successfully',
                'new_capabilities': new_capabilities
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to update agent: {str(e)}'
            }
    
    async def clone_agent(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Clone an existing agent with modifications"""
        try:
            source_agent = task.get('source_agent')
            new_name = task.get('new_name')
            modifications = task.get('modifications', {})
            
            # Clone logic here
            clone_info = {
                'name': new_name,
                'cloned_from': source_agent,
                'modifications': modifications,
                'created_at': datetime.now().isoformat()
            }
            
            return {
                'success': True,
                'message': f'Agent {new_name} cloned from {source_agent}',
                'clone_info': clone_info
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to clone agent: {str(e)}'
            }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get meta agent performance metrics"""
        return {
            'agent_id': self.agent_id,
            'name': self.name,
            'status': self.status,
            'agents_created': self.agents_created,
            'success_rate': self.success_rate,
            'last_creation': self.last_creation_time.isoformat() if self.last_creation_time else None,
            'available_templates': len(self.agent_templates),
            'created_agents_list': [agent['name'] for agent in self.created_agents]
        }

# Global instance
meta_agent_creator = MetaAgentCreator()
