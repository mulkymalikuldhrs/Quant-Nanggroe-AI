"""
Deployment Agent for Agentic AI System
Manages deployment to various platforms including Netlify and Supabase

Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

# Import integrations
try:
    from src.integrations.netlify_integration import netlify_integration
    NETLIFY_AVAILABLE = True
except ImportError:
    NETLIFY_AVAILABLE = False
    print("⚠️  Netlify integration not available")

try:
    from src.integrations.supabase_integration import supabase_integration
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("⚠️  Supabase integration not available")

from src.core.base_agent import BaseAgent

class DeploymentAgent(BaseAgent):
    """Agent specialized in deployment operations"""
    
    def __init__(self):
        super().__init__()
        self.agent_id = "deployment_agent"
        self.name = "Deployment Agent"
        self.description = "Specialized agent for deployment and infrastructure management"
        self.capabilities = [
            "netlify_deployment",
            "supabase_database_setup",
            "static_site_generation",
            "environment_configuration",
            "deployment_monitoring",
            "rollback_management"
        ]
        
        self.deployment_history = []
        self.active_deployments = {}
    
    def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process deployment tasks"""
        try:
            task_type = task.get('task_type', 'deploy')
            platform = task.get('platform', 'netlify')
            
            if task_type == 'deploy':
                return self._handle_deployment(task)
            elif task_type == 'status':
                return self._get_deployment_status(task)
            elif task_type == 'rollback':
                return self._handle_rollback(task)
            elif task_type == 'setup_database':
                return self._setup_database(task)
            elif task_type == 'test_connections':
                return self._test_all_connections()
            else:
                return self._create_error_response(f"Unknown task type: {task_type}")
                
        except Exception as e:
            return self._create_error_response(str(e))
    
    def _handle_deployment(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle deployment to specified platform"""
        platform = task.get('platform', 'netlify').lower()
        
        try:
            if platform == 'netlify' and NETLIFY_AVAILABLE:
                return self._deploy_to_netlify(task)
            elif platform == 'supabase' and SUPABASE_AVAILABLE:
                return self._deploy_to_supabase(task)
            else:
                return self._create_error_response(f"Platform {platform} not available or supported")
                
        except Exception as e:
            return self._create_error_response(f"Deployment failed: {str(e)}")
    
    def _deploy_to_netlify(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy to Netlify"""
        try:
            site_name = task.get('site_name', 'agentic-ai-system')
            build_dir = task.get('build_dir', 'web_interface')
            
            # Generate static files first
            self._generate_static_files()
            
            # Get or create site
            sites = netlify_integration.get_sites()
            site = None
            
            for s in sites:
                if s.get('name') == site_name:
                    site = s
                    break
            
            if not site:
                # Create new site
                site = netlify_integration.create_site(site_name)
                if not site:
                    return self._create_error_response("Failed to create Netlify site")
            
            # Deploy the site
            deploy_result = netlify_integration.deploy_site(site['id'], build_dir)
            
            if deploy_result:
                deployment_info = {
                    'platform': 'netlify',
                    'site_id': site['id'],
                    'site_name': site_name,
                    'deploy_id': deploy_result['id'],
                    'url': site.get('ssl_url') or site.get('url'),
                    'status': deploy_result['state'],
                    'timestamp': datetime.now().isoformat()
                }
                
                self.deployment_history.append(deployment_info)
                self.active_deployments[site['id']] = deployment_info
                
                return {
                    'success': True,
                    'message': 'Deployment to Netlify initiated',
                    'deployment': deployment_info,
                    'next_steps': [
                        'Monitor deployment status',
                        'Test deployed application',
                        'Update DNS if needed'
                    ]
                }
            else:
                return self._create_error_response("Failed to deploy to Netlify")
                
        except Exception as e:
            return self._create_error_response(f"Netlify deployment error: {str(e)}")
    
    def _deploy_to_supabase(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy/setup Supabase database"""
        try:
            # Test connection first
            connection_test = supabase_integration.test_connection()
            
            if not connection_test['connected']:
                return self._create_error_response(f"Supabase connection failed: {connection_test.get('error')}")
            
            # Initialize agent tables
            table_setup = supabase_integration.initialize_agent_tables()
            
            if table_setup:
                deployment_info = {
                    'platform': 'supabase',
                    'url': supabase_integration.url,
                    'status': 'ready',
                    'timestamp': datetime.now().isoformat(),
                    'tables_initialized': True
                }
                
                self.deployment_history.append(deployment_info)
                
                return {
                    'success': True,
                    'message': 'Supabase database setup completed',
                    'deployment': deployment_info,
                    'next_steps': [
                        'Create RLS policies if needed',
                        'Set up database functions',
                        'Configure real-time subscriptions'
                    ]
                }
            else:
                return self._create_error_response("Failed to initialize Supabase tables")
                
        except Exception as e:
            return self._create_error_response(f"Supabase deployment error: {str(e)}")
    
    def _generate_static_files(self):
        """Generate static files for deployment"""
        try:
            # Create build directory
            build_dir = Path("web_interface/static")
            build_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate index.html for static deployment
            index_content = """<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agentic AI System - Multi-Agent Intelligence Platform</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header { text-align: center; margin-bottom: 30px; }
        .header h1 { color: #2c3e50; margin-bottom: 10px; }
        .header p { color: #7f8c8d; font-size: 18px; }
        .feature-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 30px 0; }
        .feature-card { background: #ecf0f1; padding: 20px; border-radius: 8px; border-left: 4px solid #3498db; }
        .feature-card h3 { color: #2c3e50; margin-top: 0; }
        .agent-list { background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }
        .agent-item { background: white; padding: 15px; margin: 10px 0; border-radius: 5px; border-left: 3px solid #e74c3c; }
        .footer { text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #bdc3c7; color: #7f8c8d; }
        .status { background: #d5f4e6; color: #27ae60; padding: 10px; border-radius: 5px; text-align: center; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 Agentic AI System</h1>
            <p>Advanced Multi-Agent Intelligence Platform</p>
            <div class="status">✅ System Deployed Successfully on Netlify</div>
        </div>
        
        <div class="feature-grid">
            <div class="feature-card">
                <h3>🎯 Master Controller</h3>
                <p>Koordinasi dan manajemen tugas untuk semua agent dalam sistem.</p>
            </div>
            <div class="feature-card">
                <h3>🏭 Dynamic Agent Factory</h3>
                <p>Membuat agent baru secara dinamis sesuai kebutuhan tugas.</p>
            </div>
            <div class="feature-card">
                <h3>📊 Performance Monitor</h3>
                <p>Pemantauan performa dan analisis bottleneck sistem.</p>
            </div>
            <div class="feature-card">
                <h3>🔒 Secure Credentials</h3>
                <p>Manajemen kredensial dengan enkripsi tingkat militer.</p>
            </div>
        </div>
        
        <div class="agent-list">
            <h2>🤖 Available Agents</h2>
            <div class="agent-item">
                <strong>Agent Base:</strong> Master Controller & Task Coordinator
            </div>
            <div class="agent-item">
                <strong>Agent 02 (Meta-Spawner):</strong> Performance Monitor & Bottleneck Analysis
            </div>
            <div class="agent-item">
                <strong>Agent 03 (Planner):</strong> Goal Breakdown & Step-by-Step Planning
            </div>
            <div class="agent-item">
                <strong>Agent 04 (Executor):</strong> Script, API & Automation Pipeline Runner
            </div>
            <div class="agent-item">
                <strong>Agent 05 (Designer):</strong> Visual Asset Creation - UI, Diagrams, Infographics
            </div>
            <div class="agent-item">
                <strong>Agent 06 (Specialist):</strong> Domain Expertise - Security, Legal, AI Tuning
            </div>
        </div>
        
        <div class="footer">
            <p>🇮🇩 Made with ❤️ by Mulky Malikul Dhaher in Indonesia</p>
            <p>Version 1.0.0 - Production Ready</p>
        </div>
    </div>
</body>
</html>"""
            
            with open(build_dir / "index.html", "w", encoding="utf-8") as f:
                f.write(index_content)
            
            print("✅ Static files generated successfully")
            
        except Exception as e:
            print(f"Error generating static files: {e}")
    
    def _get_deployment_status(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Get deployment status"""
        try:
            platform = task.get('platform', 'netlify')
            deploy_id = task.get('deploy_id')
            site_id = task.get('site_id')
            
            if platform == 'netlify' and NETLIFY_AVAILABLE:
                if site_id and deploy_id:
                    status = netlify_integration.get_deploy_status(site_id, deploy_id)
                    return {
                        'success': True,
                        'deployment_status': status,
                        'platform': 'netlify'
                    }
                elif site_id:
                    deploys = netlify_integration.get_deploys(site_id)
                    return {
                        'success': True,
                        'recent_deployments': deploys[:5],  # Last 5 deployments
                        'platform': 'netlify'
                    }
                else:
                    sites = netlify_integration.get_sites()
                    return {
                        'success': True,
                        'all_sites': sites,
                        'platform': 'netlify'
                    }
            
            elif platform == 'supabase' and SUPABASE_AVAILABLE:
                connection_status = supabase_integration.test_connection()
                return {
                    'success': True,
                    'connection_status': connection_status,
                    'platform': 'supabase'
                }
            
            else:
                return self._create_error_response(f"Platform {platform} not available")
                
        except Exception as e:
            return self._create_error_response(f"Status check failed: {str(e)}")
    
    def _test_all_connections(self) -> Dict[str, Any]:
        """Test all platform connections"""
        try:
            results = {}
            
            if NETLIFY_AVAILABLE:
                results['netlify'] = netlify_integration.test_connection()
            else:
                results['netlify'] = {'connected': False, 'error': 'Integration not available'}
            
            if SUPABASE_AVAILABLE:
                results['supabase'] = supabase_integration.test_connection()
            else:
                results['supabase'] = {'connected': False, 'error': 'Integration not available'}
            
            return {
                'success': True,
                'connections': results,
                'overall_status': all(r.get('connected', False) for r in results.values())
            }
            
        except Exception as e:
            return self._create_error_response(f"Connection test failed: {str(e)}")
    
    def _setup_database(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Setup database schema and initial data"""
        try:
            if not SUPABASE_AVAILABLE:
                return self._create_error_response("Supabase integration not available")
            
            # Initialize tables
            table_result = supabase_integration.initialize_agent_tables()
            
            # Insert initial agents data
            initial_agents = [
                {
                    'name': 'Agent Base',
                    'type': 'controller',
                    'status': 'ready',
                    'configuration': {
                        'role': 'Master Controller & Task Coordinator',
                        'capabilities': ['task_coordination', 'workflow_orchestration']
                    }
                },
                {
                    'name': 'Dynamic Agent Factory',
                    'type': 'factory',
                    'status': 'ready',
                    'configuration': {
                        'role': 'Agent Creation & Role Assignment',
                        'capabilities': ['agent_creation', 'role_assignment']
                    }
                }
            ]
            
            agents_inserted = supabase_integration.insert_data('agents', initial_agents)
            
            return {
                'success': True,
                'message': 'Database setup completed',
                'tables_initialized': table_result,
                'initial_data_inserted': agents_inserted is not None,
                'agents_count': len(agents_inserted) if agents_inserted else 0
            }
            
        except Exception as e:
            return self._create_error_response(f"Database setup failed: {str(e)}")
    
    def _handle_rollback(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle deployment rollback"""
        try:
            platform = task.get('platform', 'netlify')
            site_id = task.get('site_id')
            
            if platform == 'netlify' and NETLIFY_AVAILABLE:
                # Get deployment history
                deploys = netlify_integration.get_deploys(site_id)
                
                if len(deploys) < 2:
                    return self._create_error_response("No previous deployment available for rollback")
                
                # Find last successful deployment (not current)
                previous_deploy = None
                for deploy in deploys[1:]:  # Skip current deployment
                    if deploy.get('state') == 'ready':
                        previous_deploy = deploy
                        break
                
                if not previous_deploy:
                    return self._create_error_response("No successful previous deployment found")
                
                return {
                    'success': True,
                    'message': 'Rollback information retrieved',
                    'current_deploy': deploys[0],
                    'rollback_target': previous_deploy,
                    'note': 'Manual rollback required through Netlify dashboard'
                }
            
            else:
                return self._create_error_response(f"Rollback not supported for platform: {platform}")
                
        except Exception as e:
            return self._create_error_response(f"Rollback failed: {str(e)}")
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create standardized error response"""
        return {
            'success': False,
            'error': error_message,
            'timestamp': datetime.now().isoformat(),
            'agent': self.agent_id
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get deployment agent performance metrics"""
        return {
            'agent_id': self.agent_id,
            'status': self.status,
            'deployments_completed': len(self.deployment_history),
            'active_deployments': len(self.active_deployments),
            'platforms_supported': ['netlify', 'supabase'],
            'integrations_available': {
                'netlify': NETLIFY_AVAILABLE,
                'supabase': SUPABASE_AVAILABLE
            },
            'last_deployment': self.deployment_history[-1] if self.deployment_history else None
        }

# Create global instance
deployment_agent = DeploymentAgent()
