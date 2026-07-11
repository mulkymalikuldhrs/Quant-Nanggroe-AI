"""
Agentic AI System - Web Interface
Control Panel untuk monitoring dan operasi sistem multi-agent

Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit
import json
import sys
import os
from datetime import datetime
import threading
import time

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.agent_manager import AgentManager
from src.agents.agent_base import AgentBase
from src.agents.dynamic_agent_factory import DynamicAgentFactory
from src.agents.agent_02_meta_spawner import Agent02MetaSpawner
from src.agents.agent_03_planner import Agent03Planner
from src.agents.agent_04_executor import Agent04Executor
from src.agents.agent_05_designer import Agent05Designer
from src.agents.agent_06_specialist import Agent06Specialist
from src.agents.output_handler import OutputHandler

app = Flask(__name__)
app.config['SECRET_KEY'] = 'agentic_ai_system_secret_key_indonesia'
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize Agent Manager and Agents
agent_manager = AgentManager()

# Initialize all agents including launcher
agents = {
    'agent_base': AgentBase(),
    'dynamic_agent_factory': DynamicAgentFactory(),
    'agent_02_meta_spawner': Agent02MetaSpawner(),
    'agent_03_planner': Agent03Planner(),
    'agent_04_executor': Agent04Executor(),
    'agent_05_designer': Agent05Designer(),
    'agent_06_specialist': Agent06Specialist(),
    'output_handler': OutputHandler()
}

# Import and add launcher agent
try:
    from src.agents.launcher_agent import LauncherAgent
    agents['launcher_agent'] = LauncherAgent()
    print("🚀 Launcher Agent loaded successfully")
except ImportError as e:
    print(f"⚠️  Launcher Agent not available: {e}")

# Import and add web automation agent
try:
    from src.agents.web_automation_agent import WebAutomationAgent
    agents['web_automation_agent'] = WebAutomationAgent()
    print("🌐 Web Automation Agent loaded successfully")
except ImportError as e:
    print(f"⚠️  Web Automation Agent not available: {e}")

# Initialize platform integrator
try:
    from src.core.platform_integrator import platform_integrator
    asyncio.run(platform_integrator.initialize_all())
    print("🔌 Platform integrations initialized")
except ImportError as e:
    print(f"⚠️  Platform integrator not available: {e}")

# Register agents with manager
for agent in agents.values():
    agent_manager.register_agent(agent)

# Global variables for monitoring
system_status = {
    'status': 'idle',
    'active_workflows': {},
    'performance_metrics': {},
    'last_update': datetime.now().isoformat()
}

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('index.html')

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

@app.route('/integrations')
def integrations():
    """Platform integrations page"""
    return render_template('platform_integrations.html')

@app.route('/credentials')
def credentials():
    """Credential management page"""
    return render_template('credentials.html')

@app.route('/api/system/status')
def get_system_status():
    """Get current system status"""
    try:
        status = agent_manager.get_system_status()
        return jsonify({
            'success': True,
            'data': status
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/agents/list')
def list_agents():
    """List all agents"""
    try:
        agents_list = agent_manager.list_agents()
        return jsonify({
            'success': True,
            'data': agents_list
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/agents/<agent_id>/status')
def get_agent_status(agent_id):
    """Get specific agent status"""
    try:
        agent = agent_manager.get_agent(agent_id)
        if not agent:
            return jsonify({
                'success': False,
                'error': 'Agent not found'
            }), 404
        
        status = agent.get_performance_metrics()
        return jsonify({
            'success': True,
            'data': status
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/workflows/execute', methods=['POST'])
def execute_workflow():
    """Execute a workflow"""
    try:
        data = request.get_json()
        workflow_name = data.get('workflow_name', 'standard_process')
        request_data = data.get('request', {})
        
        # Start workflow execution in background
        def run_workflow():
            try:
                result = asyncio.run(agent_manager.execute_workflow(workflow_name, request_data))
                
                # Emit result to all connected clients
                socketio.emit('workflow_completed', {
                    'workflow_name': workflow_name,
                    'result': result,
                    'timestamp': datetime.now().isoformat()
                })
                
            except Exception as e:
                socketio.emit('workflow_error', {
                    'workflow_name': workflow_name,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
        
        # Start workflow in background thread
        workflow_thread = threading.Thread(target=run_workflow)
        workflow_thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Workflow started',
            'workflow_name': workflow_name
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/task/submit', methods=['POST'])
def submit_task():
    """Submit a task to specific agent"""
    try:
        data = request.get_json()
        agent_id = data.get('agent_id')
        task_data = data.get('task', {})
        
        agent = agent_manager.get_agent(agent_id)
        if not agent:
            return jsonify({
                'success': False,
                'error': 'Agent not found'
            }), 404
        
        # Execute task
        result = agent.process_task(task_data)
        
        return jsonify({
            'success': True,
            'data': result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/performance/metrics')
def get_performance_metrics():
    """Get performance metrics"""
    try:
        # Get metrics from meta-spawner
        meta_spawner = agent_manager.get_agent('agent_02_meta_spawner')
        if meta_spawner:
            # Simulate a monitoring task
            monitoring_task = {
                'task_id': f'monitor_{int(time.time())}',
                'request': 'System performance monitoring',
                'context': {
                    'monitoring_type': 'performance',
                    'active_workflows': len(system_status['active_workflows'])
                }
            }
            
            metrics_result = meta_spawner.process_task(monitoring_task)
            
            return jsonify({
                'success': True,
                'data': metrics_result
            })
        
        return jsonify({
            'success': False,
            'error': 'Meta-spawner agent not available'
        }), 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# WebSocket Events
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f'Client connected: {request.sid}')
    emit('connection_status', {
        'status': 'connected',
        'message': 'Connected to Agentic AI System',
        'timestamp': datetime.now().isoformat()
    })

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f'Client disconnected: {request.sid}')

@socketio.on('subscribe_agent')
def handle_subscribe_agent(data):
    """Subscribe to agent updates"""
    agent_id = data.get('agent_id')
    print(f'Client {request.sid} subscribed to agent {agent_id}')
    
    # Join room for agent-specific updates
    from flask_socketio import join_room
    join_room(f'agent_{agent_id}')
    
    emit('subscription_confirmed', {
        'agent_id': agent_id,
        'message': f'Subscribed to {agent_id} updates'
    })

@socketio.on('request_status_update')
def handle_status_request():
    """Handle status update request"""
    try:
        status = agent_manager.get_system_status()
        emit('status_update', {
            'status': status,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        emit('error', {
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        })

# Background monitoring
def background_monitoring():
    """Background monitoring and updates"""
    while True:
        try:
            # Update system status
            system_status['last_update'] = datetime.now().isoformat()
            system_status['performance_metrics'] = {
                'agents_active': len([a for a in agents.values() if a.status == 'ready']),
                'total_agents': len(agents),
                'uptime': 'Running',
                'memory_usage': '45%',  # Simulated
                'cpu_usage': '23%'      # Simulated
            }
            
            # Emit updates to all connected clients
            socketio.emit('system_update', system_status)
            
            time.sleep(5)  # Update every 5 seconds
            
        except Exception as e:
            print(f"Monitoring error: {e}")
            time.sleep(10)

if __name__ == '__main__':
    # Start background monitoring
    import asyncio
    monitoring_thread = threading.Thread(target=background_monitoring, daemon=True)
    monitoring_thread.start()
    
    print("🚀 Starting Agentic AI System Web Interface")
    print("🇮🇩 Made with ❤️ by Mulky Malikul Dhaher in Indonesia")
    print("📊 Dashboard available at: http://localhost:5000")
    
    # Run the application
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
