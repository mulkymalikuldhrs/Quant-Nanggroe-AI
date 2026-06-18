#!/usr/bin/env python3
"""
⚡ Agentic AI System - Command Line Interface
Powerful CLI for managing the multi-agent system

Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

import asyncio
import click
import json
import sys
import os
from pathlib import Path
from datetime import datetime
import yaml

# Add current directory to Python path
sys.path.append(str(Path(__file__).parent))

# Color constants for output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    """Print colored header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}🧠 {text}{Colors.ENDC}")
    print(f"{Colors.CYAN}{'=' * (len(text) + 3)}{Colors.ENDC}")

def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✅ {text}{Colors.ENDC}")

def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}❌ {text}{Colors.ENDC}")

def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.ENDC}")

def print_info(text: str):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.ENDC}")

@click.group()
@click.version_option(version="2.0.0", prog_name="Agentic AI System")
def cli():
    """
    🧠 Agentic AI System - Autonomous Multi-Agent Intelligence
    
    🇮🇩 Made with ❤️ by Mulky Malikul Dhaher in Indonesia
    
    A powerful command-line interface for managing your AI agent ecosystem.
    """
    pass

@cli.group()
def system():
    """System management commands"""
    pass

@cli.group()
def agents():
    """Agent management commands"""
    pass

@cli.group()
def database():
    """Database management commands"""
    pass

@cli.group()
def deploy():
    """Deployment management commands"""
    pass

# System Commands
@system.command()
@click.option('--config', default='config/system_config.yaml', help='Configuration file path')
@click.option('--debug', is_flag=True, help='Enable debug mode')
def start(config, debug):
    """Start the Agentic AI System"""
    print_header("Starting Agentic AI System")
    
    try:
        # Import main system
        from main import main as start_system
        
        print_info(f"Loading configuration from: {config}")
        print_info(f"Debug mode: {'enabled' if debug else 'disabled'}")
        
        # Set environment variables
        if debug:
            os.environ['FLASK_ENV'] = 'development'
            os.environ['LOG_LEVEL'] = 'DEBUG'
        
        print_success("System starting...")
        
        # Start the system
        asyncio.run(start_system())
        
    except KeyboardInterrupt:
        print_warning("System shutdown requested")
    except Exception as e:
        print_error(f"Failed to start system: {e}")
        sys.exit(1)

@system.command()
def status():
    """Check system status"""
    print_header("System Status")
    
    try:
        # Check if system is running
        import requests
        response = requests.get('http://localhost:5000/api/system/status', timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                status_info = data.get('data', {})
                print_success("System is running")
                print(f"  Status: {status_info.get('system_status', 'unknown')}")
                print(f"  Agents: {status_info.get('agents_active', 0)}/{status_info.get('total_agents', 0)}")
                print(f"  Version: {status_info.get('version', '2.0.0')}")
                print(f"  Uptime: {status_info.get('uptime', 'unknown')}")
            else:
                print_error("System error detected")
        else:
            print_error("System not responding")
            
    except requests.exceptions.ConnectionError:
        print_warning("System not running or not accessible")
    except Exception as e:
        print_error(f"Status check failed: {e}")

@system.command()
def stop():
    """Stop the Agentic AI System"""
    print_header("Stopping System")
    
    try:
        # Try graceful shutdown via API
        import requests
        response = requests.post('http://localhost:5000/api/system/shutdown', timeout=5)
        
        if response.status_code == 200:
            print_success("System shutdown initiated")
        else:
            print_warning("Graceful shutdown failed, checking processes...")
            
    except:
        print_warning("Could not connect to system API")
    
    # Check for running processes
    try:
        import psutil
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                if 'main.py' in cmdline or 'agentic' in cmdline.lower():
                    print_info(f"Found process: {proc.info['name']} (PID: {proc.info['pid']})")
                    proc.terminate()
                    print_success(f"Terminated process {proc.info['pid']}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
                
    except ImportError:
        print_warning("psutil not available for process management")

@system.command()
@click.option('--output', default='system_health.json', help='Output file for health report')
def health(output):
    """Generate system health report"""
    print_header("System Health Check")
    
    health_report = {
        'timestamp': datetime.now().isoformat(),
        'system': {},
        'agents': {},
        'services': {},
        'recommendations': []
    }
    
    # Check system status
    try:
        import requests
        response = requests.get('http://localhost:5000/api/system/status', timeout=5)
        if response.status_code == 200:
            health_report['system'] = response.json().get('data', {})
            print_success("System status: OK")
        else:
            health_report['system']['status'] = 'error'
            print_error("System status: ERROR")
    except:
        health_report['system']['status'] = 'offline'
        print_warning("System status: OFFLINE")
    
    # Check agents
    try:
        response = requests.get('http://localhost:5000/api/agents/list', timeout=5)
        if response.status_code == 200:
            agents_data = response.json().get('data', [])
            health_report['agents'] = {agent['id']: agent['status'] for agent in agents_data}
            active_agents = len([a for a in agents_data if a.get('status') == 'ready'])
            print_info(f"Agents: {active_agents}/{len(agents_data)} active")
        else:
            print_warning("Could not retrieve agent status")
    except:
        print_warning("Agent status check failed")
    
    # Check services
    services_to_check = [
        ('Database', 'sqlite:///data/agentic.db'),
        ('Redis', 'redis://localhost:6379'),
        ('Web Interface', 'http://localhost:5000')
    ]
    
    for service_name, service_url in services_to_check:
        try:
            if service_name == 'Web Interface':
                import requests
                response = requests.get(service_url, timeout=3)
                status = 'ok' if response.status_code == 200 else 'error'
            elif service_name == 'Database':
                # Check if database file exists
                db_path = service_url.replace('sqlite:///', '')
                status = 'ok' if Path(db_path).exists() else 'missing'
            elif service_name == 'Redis':
                try:
                    import redis
                    r = redis.Redis(host='localhost', port=6379, db=0)
                    r.ping()
                    status = 'ok'
                except:
                    status = 'offline'
            
            health_report['services'][service_name] = status
            
            if status == 'ok':
                print_success(f"{service_name}: OK")
            else:
                print_warning(f"{service_name}: {status.upper()}")
                
        except Exception as e:
            health_report['services'][service_name] = 'error'
            print_error(f"{service_name}: ERROR - {e}")
    
    # Generate recommendations
    if health_report['system'].get('status') == 'offline':
        health_report['recommendations'].append("Start the system with: agentic system start")
    
    if health_report['services'].get('Redis') == 'offline':
        health_report['recommendations'].append("Start Redis server: redis-server")
    
    # Save report
    with open(output, 'w') as f:
        json.dump(health_report, f, indent=2)
    
    print_success(f"Health report saved to: {output}")

# Agent Commands
@agents.command()
def list():
    """List all agents"""
    print_header("Agent List")
    
    try:
        import requests
        response = requests.get('http://localhost:5000/api/agents/list', timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                agents_list = data.get('data', [])
                
                print(f"Found {len(agents_list)} agents:\n")
                
                for agent in agents_list:
                    status_icon = "🟢" if agent.get('status') == 'ready' else "🔴"
                    print(f"{status_icon} {agent.get('name', 'Unknown')} ({agent.get('id', 'unknown')})")
                    print(f"   Status: {agent.get('status', 'unknown')}")
                    capabilities = agent.get('capabilities', [])
                    if capabilities:
                        print(f"   Capabilities: {', '.join(capabilities[:3])}{'...' if len(capabilities) > 3 else ''}")
                    print()
            else:
                print_error("Failed to retrieve agent list")
        else:
            print_error("Could not connect to system")
            
    except Exception as e:
        print_error(f"Failed to list agents: {e}")

@agents.command()
@click.argument('agent_id')
def status(agent_id):
    """Get status of specific agent"""
    print_header(f"Agent Status: {agent_id}")
    
    try:
        import requests
        response = requests.get(f'http://localhost:5000/api/agents/{agent_id}/status', timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                agent_info = data.get('data', {})
                
                print(f"Agent ID: {agent_info.get('agent_id', agent_id)}")
                print(f"Name: {agent_info.get('name', 'Unknown')}")
                print(f"Status: {agent_info.get('status', 'unknown')}")
                
                capabilities = agent_info.get('capabilities', [])
                if capabilities:
                    print(f"Capabilities: {', '.join(capabilities)}")
                
                metrics = agent_info.get('metrics', {})
                if metrics:
                    print(f"\nMetrics:")
                    for key, value in metrics.items():
                        print(f"  {key}: {value}")
            else:
                print_error("Failed to get agent status")
        else:
            print_error("Agent not found or system not accessible")
            
    except Exception as e:
        print_error(f"Failed to get agent status: {e}")

@agents.command()
@click.argument('agent_type')
@click.option('--specialization', help='Agent specialization')
@click.option('--experience', default='senior', help='Experience level')
def create(agent_type, specialization, experience):
    """Create a new agent"""
    print_header(f"Creating Agent: {agent_type}")
    
    try:
        import requests
        
        task_data = {
            'agent_id': 'agent_maker',
            'task': {
                'action': 'create_agent',
                'agent_type': agent_type,
                'requirements': {
                    'specialization': specialization,
                    'experience_level': experience
                }
            }
        }
        
        response = requests.post('http://localhost:5000/api/task/submit', 
                               json=task_data, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print_success("Agent creation initiated")
                print(f"Agent Type: {agent_type}")
                if specialization:
                    print(f"Specialization: {specialization}")
                print(f"Experience: {experience}")
            else:
                print_error(f"Agent creation failed: {data.get('error')}")
        else:
            print_error("Could not submit agent creation request")
            
    except Exception as e:
        print_error(f"Failed to create agent: {e}")

# Database Commands
@database.command()
@click.option('--force', is_flag=True, help='Force initialization (will reset existing data)')
def init(force):
    """Initialize the database"""
    print_header("Database Initialization")
    
    try:
        from database.init_db import initialize_database, reset_database
        
        if force:
            print_warning("Force reset requested - this will delete all existing data!")
            if click.confirm("Are you sure you want to continue?"):
                reset_database()
                print_success("Database reset completed")
            else:
                print_info("Operation cancelled")
                return
        
        success = initialize_database()
        
        if success:
            print_success("Database initialized successfully")
        else:
            print_error("Database initialization failed")
            
    except Exception as e:
        print_error(f"Database initialization failed: {e}")

@database.command()
def migrate():
    """Run database migrations"""
    print_header("Database Migration")
    
    try:
        from database.migrations import run_migrations
        
        success = run_migrations()
        
        if success:
            print_success("Database migrations completed")
        else:
            print_error("Database migrations failed")
            
    except Exception as e:
        print_error(f"Migration failed: {e}")

@database.command()
@click.option('--output', default='backup.sql', help='Backup file name')
def backup(output):
    """Create database backup"""
    print_header("Database Backup")
    
    try:
        import requests
        
        backup_data = {
            'agent_id': 'data_sync',
            'task': {
                'action': 'create_backup',
                'backup_path': f'./backups/{output}',
                'compression': True
            }
        }
        
        response = requests.post('http://localhost:5000/api/task/submit',
                               json=backup_data, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print_success(f"Backup created: {output}")
            else:
                print_error(f"Backup failed: {data.get('error')}")
        else:
            print_error("Could not submit backup request")
            
    except Exception as e:
        print_error(f"Backup failed: {e}")

# Deployment Commands
@deploy.command()
@click.argument('platform')
@click.argument('app_name')
@click.option('--project-path', default='.', help='Project directory path')
@click.option('--config', help='Deployment configuration file')
def app(platform, app_name, project_path, config):
    """Deploy application to platform"""
    print_header(f"Deploying to {platform}")
    
    try:
        import requests
        
        deploy_config = {}
        if config and Path(config).exists():
            with open(config, 'r') as f:
                if config.endswith('.yaml') or config.endswith('.yml'):
                    import yaml
                    deploy_config = yaml.safe_load(f)
                else:
                    deploy_config = json.load(f)
        
        deploy_data = {
            'agent_id': 'deploy_manager',
            'task': {
                'action': 'deploy',
                'platform': platform,
                'app_name': app_name,
                'project_path': project_path,
                'config': deploy_config
            }
        }
        
        print_info(f"Deploying {app_name} to {platform}...")
        
        response = requests.post('http://localhost:5000/api/task/submit',
                               json=deploy_data, timeout=300)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print_success("Deployment completed!")
                if 'url' in data.get('data', {}):
                    print(f"App URL: {data['data']['url']}")
            else:
                print_error(f"Deployment failed: {data.get('error')}")
        else:
            print_error("Could not submit deployment request")
            
    except Exception as e:
        print_error(f"Deployment failed: {e}")

@deploy.command()
def platforms():
    """List supported deployment platforms"""
    print_header("Supported Platforms")
    
    platforms_info = {
        'netlify': 'Static sites and JAMstack applications',
        'vercel': 'Frontend applications with serverless functions',
        'railway': 'Full-stack applications with databases',
        'heroku': 'Traditional PaaS deployment',
        'aws': 'Amazon Web Services (Lambda, EC2, S3)',
        'gcp': 'Google Cloud Platform',
        'docker': 'Local containerization'
    }
    
    for platform, description in platforms_info.items():
        print(f"🚀 {platform:<10} - {description}")

# Utility Commands
@cli.command()
@click.option('--examples', is_flag=True, help='Run usage examples')
@click.option('--test', is_flag=True, help='Run system tests')
def demo(examples, test):
    """Run demo and examples"""
    print_header("Agentic AI System Demo")
    
    if examples:
        print_info("Running usage examples...")
        try:
            import subprocess
            result = subprocess.run([sys.executable, 'examples/basic_usage.py'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(result.stdout)
                print_success("Examples completed successfully")
            else:
                print_error(f"Examples failed: {result.stderr}")
        except Exception as e:
            print_error(f"Failed to run examples: {e}")
    
    if test:
        print_info("Running system tests...")
        try:
            import subprocess
            result = subprocess.run([sys.executable, '-m', 'pytest', 'tests/', '-v'],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(result.stdout)
                print_success("Tests completed successfully")
            else:
                print_warning("Some tests failed:")
                print(result.stdout)
        except Exception as e:
            print_error(f"Failed to run tests: {e}")

@cli.command()
@click.option('--config', default='config/system_config.yaml', help='Configuration file')
def validate(config):
    """Validate system configuration"""
    print_header("Configuration Validation")
    
    try:
        config_path = Path(config)
        if not config_path.exists():
            print_error(f"Configuration file not found: {config}")
            return
        
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        
        # Basic validation
        required_sections = ['system', 'agents', 'llm', 'database', 'web_interface']
        missing_sections = [section for section in required_sections 
                          if section not in config_data]
        
        if missing_sections:
            print_error(f"Missing configuration sections: {', '.join(missing_sections)}")
        else:
            print_success("All required configuration sections present")
        
        # Validate agent configuration
        agents_config = config_data.get('agents', {})
        if 'defaults' in agents_config:
            print_success("Agent defaults configured")
        
        # Validate LLM configuration
        llm_config = config_data.get('llm', {})
        if 'primary_provider' in llm_config:
            primary = llm_config['primary_provider']
            providers = llm_config.get('providers', {})
            if primary in providers:
                print_success(f"Primary LLM provider configured: {primary}")
            else:
                print_warning(f"Primary provider '{primary}' not found in providers")
        
        print_success("Configuration validation completed")
        
    except Exception as e:
        print_error(f"Configuration validation failed: {e}")

if __name__ == '__main__':
    cli()
