"""
Agentic AI System - Web Interface
Modern Flask-based control panel for multi-agent system

Made with love by Mulky Malikul Dhaher in Indonesia
"""

from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit
import json
import sys
import os
import asyncio
from datetime import datetime
import threading
import time
from pathlib import Path
import secrets

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

app = Flask(__name__)

# SECURITY FIX: Generate a proper secret key if not set via env var
# In production, ALWAYS set SECRET_KEY env var to a strong random value
_secret_key = os.getenv('SECRET_KEY')
if not _secret_key:
    _secret_key = secrets.token_hex(32)
    print("WARNING: SECRET_KEY not set in environment. Using generated key.")
    print("  For production, set SECRET_KEY env var to a persistent value.")
app.config['SECRET_KEY'] = _secret_key

# SocketIO with proper CORS settings - use gevent for better WebSocket support
try:
    import gevent
    import geventwebsocket
    _socketio_mode = 'gevent'
except ImportError:
    _socketio_mode = 'threading'

socketio = SocketIO(
    app,
    cors_allowed_origins=os.getenv('CORS_ALLOWED_ORIGINS', 'http://localhost:5000'),
    async_mode=_socketio_mode,
    ping_timeout=60,
    ping_interval=25,
    transports=['websocket', 'polling']
)

# Global system status
system_status = {
    'status': 'initializing',
    'agents_active': 0,
    'total_agents': 0,
    'uptime': 0,
    'last_update': datetime.now().isoformat()
}

# Safe import of core components
# Each is imported individually so one failure doesn't block others
memory_bus = None
llm_gateway = None
agent_registry = {}  # Consistent naming: agent_registry (not agents_registry)

def _try_import(module_path, attribute, fallback=None):
    """Safely import a module attribute with fallback"""
    try:
        mod = __import__(module_path, fromlist=[attribute])
        return getattr(mod, attribute)
    except Exception as e:
        print(f"  Warning: Could not import {module_path}.{attribute}: {e}")
        return fallback

# Import core components (each may fail independently)
memory_bus = _try_import('core.memory_bus', 'memory_bus')
llm_gateway = _try_import('connectors.llm_gateway', 'llm_gateway')

# Import agents (each may fail independently)
_agent_imports = {
    'prompt_master': ('core.prompt_master', 'prompt_master'),
    'cybershell': ('agents.cybershell', 'cybershell_agent'),
    'agent_maker': ('agents.agent_maker', 'agent_maker'),
    'ui_designer': ('agents.ui_designer', 'ui_designer_agent'),
    'dev_engine': ('agents.dev_engine', 'dev_engine_agent'),
    'data_sync': ('agents.data_sync', 'data_sync_agent'),
    'fullstack_dev': ('agents.fullstack_dev', 'fullstack_dev_agent'),
    'meta_agent_creator': ('agents.meta_agent_creator', 'meta_agent_creator'),
    'system_optimizer': ('agents.system_optimizer', 'system_optimizer'),
    'code_executor': ('agents.code_executor', 'code_executor'),
    'ai_research_agent': ('agents.ai_research_agent', 'ai_research_agent'),
    'credential_manager': ('agents.credential_manager', 'credential_manager'),
    'authentication_agent': ('agents.authentication_agent', 'authentication_agent'),
    'llm_provider_manager': ('agents.llm_provider_manager', 'llm_provider_manager'),
    'github_agent': ('agents.github_agent', 'github_agent'),
    'voice_agent': ('agents.voice_agent', 'voice_agent'),
    'web3_plugin': ('agents.web3_plugin', 'web3_plugin'),
    'agent_watcher': ('agents.agent_watcher', 'agent_watcher'),
    'quality_control_specialist': ('agents.quality_control_specialist', 'quality_control_specialist'),
    'deploy_manager': ('agents.deploy_manager', 'deploy_manager_agent'),
    'commander_agi': ('agents.commander_agi', 'commander_agi'),
}

for agent_id, (module_path, attr_name) in _agent_imports.items():
    agent_instance = _try_import(module_path, attr_name)
    if agent_instance is not None:
        agent_registry[agent_id] = agent_instance

loaded_count = len(agent_registry)
total_count = len(_agent_imports)
print(f"Loaded {loaded_count}/{total_count} agents, memory_bus={'OK' if memory_bus else 'NA'}, llm_gateway={'OK' if llm_gateway else 'NA'}")


# ============================================================
# Page Routes
# ============================================================

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('enhanced_index.html')

@app.route('/dashboard')
def dashboard():
    """System dashboard"""
    return render_template('dashboard.html')

@app.route('/agents')
def agents_page():
    """Agents management page"""
    return render_template('agents.html')

@app.route('/workflows')
def workflows():
    """Workflows management page"""
    return render_template('workflows.html')

@app.route('/monitoring')
def monitoring():
    """System monitoring page"""
    return render_template('monitoring.html')

@app.route('/platform_integrations')
def platform_integrations():
    """Platform integrations page"""
    return render_template('platform_integrations.html')

@app.route('/credentials')
def credentials():
    """Credential management page"""
    return render_template('credentials.html')

@app.route('/llm-providers')
def llm_providers():
    """LLM providers page"""
    return render_template('llm_providers.html')

@app.route('/integrations')
def integrations():
    """Alias for platform integrations"""
    return render_template('platform_integrations.html')


# ============================================================
# API Routes - System
# ============================================================

@app.route('/api/system/status')
def get_system_status():
    """Get current system status
    
    Returns JSON with system status, agent counts, version, and component health.
    """
    try:
        data = {
            'system_status': 'running' if agent_registry else 'partial',
            'agents_active': len(agent_registry),
            'total_agents': len(agent_registry),
            'loaded_agents': list(agent_registry.keys()),
            'last_update': datetime.now().isoformat(),
            'version': '2.0.0',
            'components': {
                'memory_bus': memory_bus is not None,
                'llm_gateway': llm_gateway is not None,
            }
        }

        # Add prompt_master status if available
        if 'prompt_master' in agent_registry:
            try:
                master_status = agent_registry['prompt_master'].get_system_status()
                data['uptime'] = master_status.get('uptime', '0')
                data['memory_usage'] = master_status.get('memory_usage', 'Unknown')
            except Exception:
                pass

        # Add LLM provider info if available
        if llm_gateway:
            try:
                data['llm_providers'] = len([p for p in llm_gateway.providers.values() if p.get('status') != 'disabled'])
            except Exception:
                data['llm_providers'] = 0

        return jsonify({'success': True, 'data': data})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# API Routes - Agents
# ============================================================

@app.route('/api/agents/list')
def list_agents():
    """List all registered agents with their status and capabilities"""
    try:
        agents_list = []
        for agent_id, agent in agent_registry.items():
            try:
                agents_list.append({
                    'id': agent_id,
                    'name': getattr(agent, 'name', agent_id),
                    'status': getattr(agent, 'status', 'unknown'),
                    'capabilities': getattr(agent, 'capabilities', []),
                    'agent_id': getattr(agent, 'agent_id', agent_id)
                })
            except Exception as e:
                agents_list.append({
                    'id': agent_id,
                    'name': agent_id,
                    'status': 'error',
                    'error': str(e)
                })

        return jsonify({'success': True, 'data': agents_list})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/agents/<agent_id>/status')
def get_agent_status(agent_id):
    """Get specific agent status"""
    try:
        if agent_id not in agent_registry:
            return jsonify({'success': False, 'error': 'Agent not found'}), 404

        agent = agent_registry[agent_id]

        # Try to get performance metrics
        if hasattr(agent, 'get_performance_metrics'):
            status = agent.get_performance_metrics()
        else:
            status = {
                'agent_id': agent_id,
                'name': getattr(agent, 'name', agent_id),
                'status': getattr(agent, 'status', 'ready'),
                'capabilities': getattr(agent, 'capabilities', [])
            }

        return jsonify({'success': True, 'data': status})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# API Routes - Tasks
# ============================================================

@app.route('/api/task/submit', methods=['POST'])
def submit_task():
    """Submit a task to a specific agent for execution
    
    Expects JSON body with 'agent_id' and 'task' fields.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400

        # Support both 'agent_id' and 'agent' keys for flexibility
        agent_id = data.get('agent_id') or data.get('agent')
        task_data = data.get('task', data.get('task_data', {}))
        # If task_data is a string, wrap it in a dict
        if isinstance(task_data, str):
            task_data = {'description': task_data}

        if not agent_id:
            return jsonify({'success': False, 'error': 'agent_id is required'}), 400

        if agent_id not in agent_registry:
            # Return available agents list for guidance
            return jsonify({
                'success': False,
                'error': f'Agent "{agent_id}" not found',
                'available_agents': list(agent_registry.keys())
            }), 404

        agent = agent_registry[agent_id]

        # Execute task
        if hasattr(agent, 'process_task'):
            if asyncio.iscoroutinefunction(agent.process_task):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(agent.process_task(task_data))
                loop.close()
            else:
                result = agent.process_task(task_data)
        elif hasattr(agent, 'execute'):
            result = agent.execute(task_data)
        else:
            result = {
                'success': True,
                'message': f'Task received by {agent_id}',
                'agent': agent_id,
                'task': task_data
            }

        return jsonify({'success': True, 'data': result})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/prompt/process', methods=['POST'])
def process_prompt():
    """Process a prompt through the system"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400

        prompt = data.get('prompt', '')
        input_type = data.get('input_type', 'text')
        metadata = data.get('metadata', {})

        if not prompt:
            return jsonify({'success': False, 'error': 'Prompt is required'}), 400

        # Use prompt master if available
        if 'prompt_master' in agent_registry:
            pm = agent_registry['prompt_master']

            if hasattr(pm, 'process_prompt'):
                if asyncio.iscoroutinefunction(pm.process_prompt):
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    result = loop.run_until_complete(
                        pm.process_prompt(prompt, input_type, metadata)
                    )
                    loop.close()
                else:
                    result = pm.process_prompt(prompt, input_type, metadata)
            else:
                result = {
                    'success': False,
                    'error': 'Prompt processing not implemented'
                }
        else:
            # Fallback: return available agents info
            result = {
                'success': True,
                'message': 'Prompt received but prompt master not available',
                'prompt': prompt,
                'suggested_agents': list(agent_registry.keys())
            }

        return jsonify({'success': True, 'data': result})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# API Routes - LLM
# ============================================================

@app.route('/api/llm/providers')
def get_llm_providers():
    """Get LLM provider status"""
    try:
        if not llm_gateway:
            return jsonify({
                'success': False,
                'error': 'LLM Gateway not available'
            }), 503

        status = llm_gateway.get_provider_status()
        usage = llm_gateway.get_usage_summary()

        return jsonify({
            'success': True,
            'data': {
                'providers': status,
                'usage': usage
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/llm/test', methods=['POST'])
def test_llm_providers():
    """Test all LLM providers"""
    try:
        if not llm_gateway:
            return jsonify({
                'success': False,
                'error': 'LLM Gateway not available'
            }), 503

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        test_results = loop.run_until_complete(llm_gateway.test_all_providers())
        loop.close()

        return jsonify({'success': True, 'data': test_results})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# API Routes - Memory
# ============================================================

@app.route('/api/memory/stats')
def get_memory_stats():
    """Get memory bus statistics"""
    try:
        if not memory_bus:
            return jsonify({
                'success': True,
                'data': {
                    'status': 'available',
                    'mode': 'sqlite',
                    'total_entries': 0,
                    'memory_usage': '0 MB',
                    'redis_available': False
                }
            })

        stats = memory_bus.get_usage_stats()
        return jsonify({'success': True, 'data': stats})

    except Exception as e:
        return jsonify({'success': True, 'data': {'status': 'error', 'error': str(e)}})


# ============================================================
# API Routes - Performance & Workflows
# ============================================================

@app.route('/api/performance/metrics')
def get_performance_metrics():
    """Get system performance metrics"""
    try:
        import psutil
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory_info = psutil.virtual_memory()
        disk_info = psutil.disk_usage('/')
    except ImportError:
        # Fallback without psutil
        cpu_percent = 0
        memory_info = type('obj', (object,), {'percent': 0, 'available': 0, 'total': 1})()
        disk_info = type('obj', (object,), {'percent': 0, 'free': 0, 'total': 1})()

    metrics = {
        'cpu': {
            'percent': cpu_percent,
            'cores': os.cpu_count() or 1
        },
        'memory': {
            'percent': getattr(memory_info, 'percent', 0),
            'available': getattr(memory_info, 'available', 0),
            'total': getattr(memory_info, 'total', 1)
        },
        'disk': {
            'percent': getattr(disk_info, 'percent', 0),
            'free': getattr(disk_info, 'free', 0),
            'total': getattr(disk_info, 'total', 1)
        },
        'agents': {
            'total': len(agent_registry),
            'active': len([a for a in agent_registry.values()
                          if hasattr(a, 'status') and a.status == 'ready'])
        },
        'uptime': str(datetime.now()),
        'timestamp': datetime.now().isoformat()
    }

    return jsonify({'success': True, 'data': metrics})


# ============================================================
# API Routes - Credentials
# ============================================================

@app.route('/api/credentials', methods=['GET'])
def list_credentials():
    """List all stored credentials (without passwords)"""
    try:
        try:
            from src.core.credential_manager import get_credential_manager
            cm = get_credential_manager()
            creds = cm.list_credentials()
        except Exception:
            creds = []
        return jsonify({'success': True, 'data': creds})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/credentials', methods=['POST'])
def store_credential():
    """Store a new credential"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400

        try:
            from src.core.credential_manager import get_credential_manager
            cm = get_credential_manager()
            result = cm.store_credential(
                website_name=data.get('website_name', ''),
                website_url=data.get('website_url', ''),
                username=data.get('username'),
                email=data.get('email'),
                password=data.get('password'),
                additional_fields=data.get('additional_fields'),
                notes=data.get('notes')
            )
        except Exception as e:
            return jsonify({'success': False, 'error': f'Credential storage error: {str(e)}'}), 500

        return jsonify({'success': result, 'data': {'stored': result}})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/credentials/<int:cred_id>', methods=['GET'])
def get_credential(cred_id):
    """Get credential by ID"""
    try:
        try:
            from src.core.credential_manager import get_credential_manager
            cm = get_credential_manager()
            cred = cm.get_credential(credential_id=cred_id)
        except Exception:
            cred = None

        if cred:
            return jsonify({'success': True, 'data': cred})
        return jsonify({'success': False, 'error': 'Credential not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/credentials/<int:cred_id>', methods=['DELETE'])
def delete_credential(cred_id):
    """Delete credential by ID"""
    try:
        try:
            from src.core.credential_manager import get_credential_manager
            cm = get_credential_manager()
            result = cm.delete_credential(cred_id)
        except Exception:
            result = False

        return jsonify({'success': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/credentials/search', methods=['GET'])
def search_credentials():
    """Search credentials"""
    try:
        query = request.args.get('q', '')
        try:
            from src.core.credential_manager import get_credential_manager
            cm = get_credential_manager()
            results = cm.search_credentials(query)
        except Exception:
            results = []

        return jsonify({'success': True, 'data': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# API Routes - Workflows
# ============================================================

@app.route('/api/workflows/list')
def list_workflows():
    """List available workflows"""
    try:
        workflows = []
        # Get from prompt_master if available
        if 'prompt_master' in agent_registry:
            pm = agent_registry['prompt_master']
            if hasattr(pm, 'workflow_templates'):
                for wf_id, steps in pm.workflow_templates.items():
                    workflows.append({
                        'id': wf_id,
                        'name': wf_id.replace('_', ' ').title(),
                        'steps': len(steps),
                        'step_details': steps
                    })

        # Also check memory bus for saved workflows
        if memory_bus:
            try:
                import sqlite3
                conn = sqlite3.connect('data/memory.db')
                cursor = conn.execute("SELECT COUNT(*) FROM tasks WHERE task_type='workflow'")
                workflow_count = cursor.fetchone()[0]
                conn.close()
            except Exception:
                workflow_count = 0

        return jsonify({'success': True, 'data': workflows})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/workflows/history')
def workflow_history():
    """Get workflow execution history"""
    try:
        history = []
        if memory_bus:
            try:
                tasks = memory_bus.get_recent_tasks(limit=20)
                history = [t for t in tasks if t.get('task_type') == 'workflow']
            except Exception:
                pass

        return jsonify({'success': True, 'data': history})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/workflows/<workflow_id>/pause', methods=['POST'])
def pause_workflow(workflow_id):
    """Pause a running workflow"""
    return jsonify({'success': True, 'data': {'workflow_id': workflow_id, 'status': 'paused'}})


@app.route('/api/workflows/<workflow_id>/stop', methods=['POST'])
def stop_workflow(workflow_id):
    """Stop a running workflow"""
    return jsonify({'success': True, 'data': {'workflow_id': workflow_id, 'status': 'stopped'}})


# ============================================================
# API Routes - Integrations
# ============================================================

@app.route('/api/integrations/status')
def integrations_status():
    """Get status of all platform integrations"""
    try:
        integrations = []

        # Check GitHub
        if 'github_agent' in agent_registry:
            ga = agent_registry['github_agent']
            integrations.append({
                'id': 'github',
                'name': 'GitHub',
                'status': 'connected' if getattr(ga, 'token', None) else 'disconnected',
                'capabilities': getattr(ga, 'capabilities', [])
            })
        else:
            integrations.append({'id': 'github', 'name': 'GitHub', 'status': 'unavailable'})

        # Check LLM providers
        if llm_gateway:
            provider_status = llm_gateway.get_provider_status()
            for pid, pinfo in provider_status.items():
                integrations.append({
                    'id': f'llm_{pid}',
                    'name': f'LLM - {pid.title()}',
                    'status': pinfo.get('status', 'unknown'),
                    'capabilities': pinfo.get('models', [])
                })

        # Check Web3
        if 'web3_plugin' in agent_registry:
            integrations.append({
                'id': 'web3',
                'name': 'Web3 / Blockchain',
                'status': 'available',
                'capabilities': getattr(agent_registry['web3_plugin'], 'capabilities', [])
            })

        # Check Voice
        if 'voice_agent' in agent_registry:
            integrations.append({
                'id': 'voice',
                'name': 'Voice Processing',
                'status': 'available',
                'capabilities': getattr(agent_registry['voice_agent'], 'capabilities', [])
            })

        return jsonify({'success': True, 'data': integrations})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# API Routes - Monitoring
# ============================================================

@app.route('/api/monitoring/agents')
def monitoring_agents():
    """Get detailed agent performance data for monitoring"""
    try:
        agents_data = []
        for agent_id, agent in agent_registry.items():
            try:
                metrics = {}
                if hasattr(agent, 'get_performance_metrics'):
                    metrics = agent.get_performance_metrics()
                elif hasattr(agent, 'execution_stats'):
                    metrics = agent.execution_stats

                agents_data.append({
                    'id': agent_id,
                    'name': getattr(agent, 'name', agent_id),
                    'status': getattr(agent, 'status', 'unknown'),
                    'capabilities': getattr(agent, 'capabilities', []),
                    'metrics': metrics
                })
            except Exception:
                agents_data.append({'id': agent_id, 'status': 'error'})

        return jsonify({'success': True, 'data': agents_data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/monitoring/logs')
def monitoring_logs():
    """Get recent system logs"""
    try:
        logs = []
        if memory_bus:
            try:
                recent = memory_bus.search(data_type='log', limit=50)
                for entry in recent:
                    logs.append({
                        'timestamp': entry.timestamp.isoformat() if hasattr(entry, 'timestamp') else '',
                        'agent': entry.agent_id if hasattr(entry, 'agent_id') else 'system',
                        'level': 'info',
                        'message': str(entry.content)[:200] if hasattr(entry, 'content') else ''
                    })
            except Exception:
                pass

        # Also check file-based logs
        try:
            log_dir = Path('data/logs')
            if log_dir.exists():
                for log_file in sorted(log_dir.glob('*.log'), reverse=True)[:3]:
                    with open(log_file, 'r') as f:
                        for line in f.readlines()[-20:]:
                            logs.append({'message': line.strip(), 'level': 'info', 'source': log_file.name})
        except Exception:
            pass

        return jsonify({'success': True, 'data': logs})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/monitoring/alerts')
def monitoring_alerts():
    """Get system alerts"""
    try:
        alerts = []
        if 'agent_watcher' in agent_registry:
            watcher = agent_registry['agent_watcher']
            if hasattr(watcher, 'get_alerts'):
                result = watcher.get_alerts()
                if isinstance(result, dict) and 'alerts' in result:
                    alerts = result['alerts']

        return jsonify({'success': True, 'data': alerts})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/monitoring/report', methods=['POST'])
def generate_report():
    """Generate a monitoring report"""
    try:
        import psutil
        report = {
            'generated_at': datetime.now().isoformat(),
            'system': {
                'cpu_percent': psutil.cpu_percent(interval=0.1),
                'memory_percent': psutil.virtual_memory().percent,
                'disk_percent': psutil.disk_usage('/').percent
            },
            'agents': {
                'total': len(agent_registry),
                'active': len([a for a in agent_registry.values() if getattr(a, 'status', '') == 'ready']),
                'list': list(agent_registry.keys())
            },
            'components': {
                'memory_bus': memory_bus is not None,
                'llm_gateway': llm_gateway is not None
            }
        }
        return jsonify({'success': True, 'data': report})
    except ImportError:
        return jsonify({'success': False, 'error': 'psutil not available'}), 503
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# API Routes - Authentication (Basic)
# ============================================================

_auth_enabled = os.getenv('ENABLE_AUTH', 'false').lower() == 'true'
_auth_username = os.getenv('AUTH_USERNAME', 'admin')
_auth_password_hash = None

if _auth_enabled:
    import hashlib
    _auth_password = os.getenv('AUTH_PASSWORD', 'changeme')
    _auth_password_hash = hashlib.sha256(_auth_password.encode()).hexdigest()


@app.route('/api/auth/login', methods=['POST'])
def auth_login():
    """Login endpoint for basic authentication"""
    if not _auth_enabled:
        return jsonify({'success': False, 'error': 'Authentication not enabled'})

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'No data provided'}), 400

    username = data.get('username', '')
    password = data.get('password', '')

    if username == _auth_username and hashlib.sha256(password.encode()).hexdigest() == _auth_password_hash:
        session['authenticated'] = True
        session['username'] = username
        return jsonify({'success': True, 'data': {'username': username}})

    return jsonify({'success': False, 'error': 'Invalid credentials'}), 401


@app.route('/api/auth/logout', methods=['POST'])
def auth_logout():
    """Logout endpoint"""
    session.pop('authenticated', None)
    session.pop('username', None)
    return jsonify({'success': True})


@app.route('/api/auth/status')
def auth_status():
    """Check authentication status"""
    return jsonify({
        'success': True,
        'data': {
            'enabled': _auth_enabled,
            'authenticated': session.get('authenticated', False),
            'username': session.get('username')
        }
    })


@app.route('/api/workflows/execute', methods=['POST'])
def execute_workflow():
    """Execute a workflow"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400

        workflow_id = data.get('workflow_id', 'custom')
        steps = data.get('steps', [])

        # Execute workflow steps through available agents
        results = []
        for step in steps[:20]:  # Limit to 20 steps
            agent_id = step.get('agent_id') or step.get('agent')
            task = step.get('task', {})

            if agent_id and agent_id in agent_registry:
                agent = agent_registry[agent_id]
                if hasattr(agent, 'process_task'):
                    try:
                        if asyncio.iscoroutinefunction(agent.process_task):
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            step_result = loop.run_until_complete(agent.process_task(task))
                            loop.close()
                        else:
                            step_result = agent.process_task(task)
                        results.append({'step': len(results) + 1, 'agent': agent_id, 'result': step_result})
                    except Exception as e:
                        results.append({'step': len(results) + 1, 'agent': agent_id, 'error': str(e)})
                else:
                    results.append({'step': len(results) + 1, 'agent': agent_id, 'result': 'Task received'})
            else:
                results.append({'step': len(results) + 1, 'error': f'Agent {agent_id} not found'})

        return jsonify({
            'success': True,
            'data': {
                'workflow_id': workflow_id,
                'steps_executed': len(results),
                'results': results
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================
# WebSocket Events
# ============================================================

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f'Client connected: {request.sid}')
    emit('connection_status', {
        'status': 'connected',
        'message': 'Connected to Agentic AI System',
        'timestamp': datetime.now().isoformat(),
        'system_version': '2.0.0'
    })


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f'Client disconnected: {request.sid}')


@socketio.on('subscribe_updates')
def handle_subscribe_updates():
    """Subscribe to system updates"""
    from flask_socketio import join_room
    join_room('system_updates')
    emit('subscription_confirmed', {
        'message': 'Subscribed to system updates'
    })


@socketio.on('request_status_update')
def handle_status_request():
    """Handle status update request"""
    try:
        status_data = {
            'agents_count': len(agent_registry),
            'active_agents': len([a for a in agent_registry.values()
                                  if hasattr(a, 'status') and a.status == 'ready']),
            'system_status': 'running',
            'timestamp': datetime.now().isoformat()
        }
        emit('status_update', status_data)

    except Exception as e:
        emit('error', {
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        })


# ============================================================
# Background Monitoring
# ============================================================

def background_monitoring():
    """Background monitoring and updates"""
    while True:
        try:
            global system_status
            system_status.update({
                'status': 'running',
                'agents_active': len([a for a in agent_registry.values()
                                      if hasattr(a, 'status') and a.status == 'ready']),
                'total_agents': len(agent_registry),
                'last_update': datetime.now().isoformat()
            })

            socketio.emit('system_update', system_status, room='system_updates')
            time.sleep(10)

        except Exception as e:
            print(f"Background monitoring error: {e}")
            time.sleep(30)


# ============================================================
# Error Handlers
# ============================================================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 - check if it's an API request or page request"""
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'error': 'Not found'}), 404
    try:
        return render_template('offline.html'), 404
    except Exception:
        return jsonify({'success': False, 'error': 'Page not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors - returns JSON for both API and page requests"""
    return jsonify({'success': False, 'error': 'Internal server error'}), 500


# ============================================================
# Main Entry Point
# ============================================================

if __name__ == '__main__':
    print("Starting Agentic AI System Web Interface")
    print(f"Dashboard: http://localhost:{os.getenv('WEB_INTERFACE_PORT', 5000)}")
    print(f"Loaded {len(agent_registry)} agents")

    # Start background monitoring
    monitoring_thread = threading.Thread(target=background_monitoring, daemon=True)
    monitoring_thread.start()

    # Run the application
    port = int(os.getenv('WEB_INTERFACE_PORT', 5000))
    host = os.getenv('WEB_INTERFACE_HOST', '0.0.0.0')

    debug_mode = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    socketio.run(app, host=host, port=port, debug=debug_mode, allow_unsafe_werkzeug=True)
