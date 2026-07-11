#!/usr/bin/env python3
"""
🌐 Ultimate AGI Force - Daemon Manager
Service manager for autonomous agents that run as background daemons

Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

import os
import sys
import time
import signal
import subprocess
import json
import threading
from pathlib import Path
from datetime import datetime
import multiprocessing as mp
from typing import Dict, List, Any

class DaemonManager:
    """
    Manages all Ultimate AGI Force agents as background daemons
    """
    
    def __init__(self):
        self.daemon_dir = Path("data/daemons")
        self.daemon_dir.mkdir(parents=True, exist_ok=True)
        
        self.pid_file = self.daemon_dir / "agi_force.pid"
        self.log_dir = Path("data/logs")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.agents_config = {
            # Core System Agents
            "prompt_master": {
                "module": "core.prompt_master",
                "class": "PromptMasterAgent",
                "instance": "prompt_master",
                "priority": 1,
                "auto_start": True
            },
            "memory_bus": {
                "module": "core.memory_bus", 
                "class": "MemoryBusAgent",
                "instance": "memory_bus",
                "priority": 1,
                "auto_start": True
            },
            "scheduler": {
                "module": "core.scheduler",
                "class": "SchedulerAgent", 
                "instance": "agent_scheduler",
                "priority": 1,
                "auto_start": True
            },
            
            # Original Agents
            "cybershell": {
                "module": "agents.cybershell",
                "class": "CyberShellAgent",
                "instance": "cybershell_agent",
                "priority": 2,
                "auto_start": True
            },
            "agent_maker": {
                "module": "agents.agent_maker",
                "class": "AgentMakerAgent", 
                "instance": "agent_maker",
                "priority": 2,
                "auto_start": True
            },
            "ui_designer": {
                "module": "agents.ui_designer",
                "class": "UIDesignerAgent",
                "instance": "ui_designer_agent",
                "priority": 2,
                "auto_start": True
            },
            "dev_engine": {
                "module": "agents.dev_engine",
                "class": "DevEngineAgent",
                "instance": "dev_engine_agent", 
                "priority": 2,
                "auto_start": True
            },
            "fullstack_dev": {
                "module": "agents.fullstack_dev",
                "class": "FullStackDevAgent",
                "instance": "fullstack_dev_agent",
                "priority": 2,
                "auto_start": True
            },
            
            # Ultimate AGI Force v7.0.0 Agents
            "agi_colony_connector": {
                "module": "agents.agi_colony_connector",
                "class": "AGIColonyConnector", 
                "instance": "agi_colony_connector",
                "priority": 1,
                "auto_start": True,
                "description": "🌐 Super-powered inter-colony communication & port forwarding"
            },
            "deployment_specialist": {
                "module": "agents.deployment_specialist",
                "class": "DeploymentSpecialist",
                "instance": "deployment_specialist", 
                "priority": 1,
                "auto_start": True,
                "description": "🚀 Autonomous colony deployment & expansion specialist"
            },
            "commander_agi": {
                "module": "agents.commander_agi",
                "class": "CommanderAGI",
                "instance": "commander_agi",
                "priority": 3,
                "auto_start": True,
                "description": "Security monitoring & robotics coordination"
            },
            "bug_hunter": {
                "module": "agents.bug_hunter_bot", 
                "class": "BugHunterBot",
                "instance": "bug_hunter_bot",
                "priority": 3,
                "auto_start": True,
                "description": "Ethical hacking & vulnerability discovery"
            },
            "money_maker": {
                "module": "agents.money_making_agent",
                "class": "MoneyMakingAgent", 
                "instance": "money_making_agent",
                "priority": 3,
                "auto_start": True,
                "description": "Autonomous revenue generation"
            },
            "backup_colony": {
                "module": "agents.backup_colony_system",
                "class": "BackupColonySystem",
                "instance": "backup_colony_system", 
                "priority": 3,
                "auto_start": True,
                "description": "Distributed backup infrastructure"
            },
            "authentication": {
                "module": "agents.authentication_agent",
                "class": "AuthenticationAgent",
                "instance": "authentication_agent",
                "priority": 3,
                "auto_start": True,
                "description": "KYC verification & payment processing"
            },
            "knowledge_manager": {
                "module": "agents.knowledge_management_agent", 
                "class": "KnowledgeManagementAgent",
                "instance": "knowledge_management_agent",
                "priority": 3,
                "auto_start": True,
                "description": "Advanced memory & data storage"
            },
            "marketing": {
                "module": "agents.marketing_agent",
                "class": "MarketingAgent",
                "instance": "marketing_agent",
                "priority": 3, 
                "auto_start": True,
                "description": "Global promotion & outreach automation"
            },
            "quality_control": {
                "module": "agents.quality_control_specialist",
                "class": "QualityControlSpecialist",
                "instance": "quality_control_specialist",
                "priority": 3,
                "auto_start": True,
                "description": "Visual & analytical assessment"
            }
        }
        
        self.running_agents = {}
        self.agent_processes = {}
        
    def start_daemon(self):
        """Start the AGI Force daemon"""
        print("🛡️ Starting Ultimate AGI Force Daemon v7.0.0")
        print("🇮🇩 Made with ❤️ by Mulky Malikul Dhaher in Indonesia")
        
        # Check if already running
        if self.is_running():
            print("❌ AGI Force daemon is already running")
            return False
        
        # Create daemon
        self._daemonize()
        
        # Save PID
        with open(self.pid_file, 'w') as f:
            f.write(str(os.getpid()))
        
        # Start all agents
        self._start_all_agents()
        
        # Start web interface
        self._start_web_interface()
        
        # Keep daemon running
        self._daemon_loop()
        
        return True
    
    def stop_daemon(self):
        """Stop the AGI Force daemon"""
        if not self.is_running():
            print("❌ AGI Force daemon is not running")
            return False
        
        try:
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            # Stop all agent processes
            self._stop_all_agents()
            
            # Kill main daemon
            os.kill(pid, signal.SIGTERM)
            
            # Remove PID file
            if self.pid_file.exists():
                self.pid_file.unlink()
            
            print("✅ AGI Force daemon stopped")
            return True
            
        except Exception as e:
            print(f"❌ Failed to stop daemon: {e}")
            return False
    
    def status(self):
        """Get daemon status"""
        if not self.is_running():
            print("❌ AGI Force daemon is not running")
            return
        
        print("✅ AGI Force daemon is running")
        print(f"📊 PID: {self._get_pid()}")
        
        # Check agent status
        status_file = self.daemon_dir / "status.json"
        if status_file.exists():
            with open(status_file, 'r') as f:
                status = json.load(f)
            
            print(f"\n🤖 Agents Status:")
            for agent_id, agent_status in status.get('agents', {}).items():
                status_icon = "✅" if agent_status.get('status') == 'running' else "❌"
                print(f"  {status_icon} {agent_id}: {agent_status.get('status', 'unknown')}")
                
    def restart_daemon(self):
        """Restart the AGI Force daemon"""
        print("🔄 Restarting AGI Force daemon...")
        self.stop_daemon()
        time.sleep(2)
        self.start_daemon()
    
    def is_running(self):
        """Check if daemon is running"""
        if not self.pid_file.exists():
            return False
        
        try:
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            # Check if process exists
            os.kill(pid, 0)
            return True
            
        except (ValueError, OSError):
            return False
    
    def _get_pid(self):
        """Get daemon PID"""
        if self.pid_file.exists():
            with open(self.pid_file, 'r') as f:
                return int(f.read().strip())
        return None
    
    def _daemonize(self):
        """Create daemon process"""
        # Ensure directories exist first
        self.daemon_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # First fork
            pid = os.fork()
            if pid > 0:
                sys.exit(0)  # Parent exits
        except OSError as e:
            print(f"Fork #1 failed: {e}")
            sys.exit(1)
        
        # Decouple from parent environment
        # NOTE: Do NOT os.chdir("/") — it breaks all relative paths
        # (data dirs, config files, etc.). Keep project root as cwd.
        os.setsid()
        os.umask(0)
        
        try:
            # Second fork
            pid = os.fork()
            if pid > 0:
                sys.exit(0)  # Second parent exits
        except OSError as e:
            print(f"Fork #2 failed: {e}")
            sys.exit(1)
        
        # Redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        
        # Redirect to log files
        log_file = self.log_dir / f"agi_force_{datetime.now().strftime('%Y%m%d')}.log"
        
        with open(log_file, 'a+') as f:
            os.dup2(f.fileno(), sys.stdout.fileno())
            os.dup2(f.fileno(), sys.stderr.fileno())
    
    def _start_all_agents(self):
        """Start all configured agents"""
        print(f"🚀 Starting {len(self.agents_config)} agents...")
        
        # Sort by priority
        sorted_agents = sorted(
            self.agents_config.items(),
            key=lambda x: x[1]['priority']
        )
        
        for agent_id, config in sorted_agents:
            if config.get('auto_start', False):
                success = self._start_agent(agent_id, config)
                if success:
                    print(f"  ✅ {agent_id}: Started")
                else:
                    print(f"  ❌ {agent_id}: Failed to start")
                
                # Small delay between agent starts
                time.sleep(0.5)
    
    def _start_agent(self, agent_id, config):
        """Start individual agent"""
        try:
            # Import agent module
            module = __import__(config["module"], fromlist=[config["instance"]])
            agent_instance = getattr(module, config["instance"])
            
            # Set agent to running status
            if hasattr(agent_instance, 'status'):
                agent_instance.status = 'running'
            
            # Store agent reference
            self.running_agents[agent_id] = {
                'instance': agent_instance,
                'config': config,
                'start_time': datetime.now(),
                'status': 'running'
            }
            
            # Start agent monitoring thread
            monitor_thread = threading.Thread(
                target=self._monitor_agent, 
                args=(agent_id,),
                daemon=True
            )
            monitor_thread.start()
            
            return True
            
        except Exception as e:
            print(f"Failed to start {agent_id}: {e}")
            return False
    
    def _monitor_agent(self, agent_id):
        """Monitor agent health"""
        while agent_id in self.running_agents:
            try:
                agent_data = self.running_agents[agent_id]
                agent = agent_data['instance']
                
                # Check if agent is still responsive
                if hasattr(agent, 'health_check'):
                    health = agent.health_check()
                    if not health:
                        print(f"⚠️ Agent {agent_id} health check failed")
                        # Attempt restart
                        self._restart_agent(agent_id)
                
                # Update status
                self._update_agent_status(agent_id)
                
                # Sleep for monitoring interval
                time.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                print(f"Error monitoring {agent_id}: {e}")
                time.sleep(60)  # Longer sleep on error
    
    def _update_agent_status(self, agent_id):
        """Update agent status in status file"""
        status_file = self.daemon_dir / "status.json"
        
        try:
            # Load existing status
            if status_file.exists():
                with open(status_file, 'r') as f:
                    status = json.load(f)
            else:
                status = {'agents': {}}
            
            # Update agent status
            if agent_id in self.running_agents:
                agent_data = self.running_agents[agent_id]
                status['agents'][agent_id] = {
                    'status': 'running',
                    'start_time': agent_data['start_time'].isoformat(),
                    'description': agent_data['config'].get('description', ''),
                    'last_check': datetime.now().isoformat()
                }
            
            # Update system status
            status['system'] = {
                'total_agents': len(self.running_agents),
                'running_agents': len([a for a in self.running_agents.values() if a['status'] == 'running']),
                'last_update': datetime.now().isoformat(),
                'version': '7.0.0'
            }
            
            # Save status
            with open(status_file, 'w') as f:
                json.dump(status, f, indent=2)
                
        except Exception as e:
            print(f"Failed to update status: {e}")
    
    def _restart_agent(self, agent_id):
        """Restart a specific agent"""
        if agent_id in self.running_agents:
            config = self.running_agents[agent_id]['config']
            del self.running_agents[agent_id]
            time.sleep(1)
            self._start_agent(agent_id, config)
    
    def _stop_all_agents(self):
        """Stop all running agents"""
        print("🛑 Stopping all agents...")
        
        for agent_id in list(self.running_agents.keys()):
            try:
                agent_data = self.running_agents[agent_id]
                agent = agent_data['instance']
                
                if hasattr(agent, 'stop'):
                    agent.stop()
                elif hasattr(agent, 'status'):
                    agent.status = 'stopped'
                
                print(f"  ✅ {agent_id}: Stopped")
                
            except Exception as e:
                print(f"  ❌ {agent_id}: Failed to stop - {e}")
        
        self.running_agents.clear()
    
    def _start_web_interface(self):
        """Start web interface as background process"""
        try:
            # Start web interface
            import os
            project_root = str(Path(__file__).parent)
            web_process = subprocess.Popen([
                sys.executable, "-c",
                f"""
import sys
sys.path.insert(0, {repr(project_root)})
from web_interface.app import app, socketio
socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
"""
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=project_root)
            
            self.agent_processes['web_interface'] = web_process
            print("  ✅ Web Interface: Started on port 5000")
            
        except Exception as e:
            print(f"  ❌ Web Interface: Failed to start - {e}")
    
    def _daemon_loop(self):
        """Main daemon loop"""
        print("🔄 AGI Force daemon is now running autonomously...")
        
        while True:
            try:
                # Update system status
                self._update_system_status()
                
                # Check for agent failures and restart if needed
                self._check_agent_health()
                
                # Sleep for main loop interval
                time.sleep(60)  # Main loop every minute
                
            except KeyboardInterrupt:
                print("🛑 Received interrupt signal")
                break
            except Exception as e:
                print(f"❌ Daemon loop error: {e}")
                time.sleep(30)
        
        # Cleanup on exit
        self._stop_all_agents()
    
    def _update_system_status(self):
        """Update overall system status"""
        status_file = self.daemon_dir / "status.json"
        
        try:
            if status_file.exists():
                with open(status_file, 'r') as f:
                    status = json.load(f)
            else:
                status = {'agents': {}}
            
            # Update system metrics
            status['system'] = {
                'status': 'running',
                'total_agents': len(self.agents_config),
                'running_agents': len(self.running_agents),
                'uptime': str(datetime.now() - datetime.fromtimestamp(os.path.getctime(self.pid_file))),
                'version': '7.0.0',
                'last_update': datetime.now().isoformat(),
                'web_interface': 'http://localhost:5000'
            }
            
            with open(status_file, 'w') as f:
                json.dump(status, f, indent=2)
                
        except Exception as e:
            print(f"Failed to update system status: {e}")
    
    def _check_agent_health(self):
        """Check all agent health and restart if needed"""
        for agent_id in list(self.running_agents.keys()):
            try:
                agent_data = self.running_agents[agent_id]
                agent = agent_data['instance']
                
                # Simple health check
                if hasattr(agent, 'status') and agent.status in ['error', 'crashed']:
                    print(f"⚠️ Restarting unhealthy agent: {agent_id}")
                    self._restart_agent(agent_id)
                    
            except Exception as e:
                print(f"Health check failed for {agent_id}: {e}")

def main():
    """Main CLI interface"""
    daemon = DaemonManager()
    
    if len(sys.argv) < 2:
        print("Usage: python daemon_manager.py {start|stop|restart|status}")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == 'start':
        daemon.start_daemon()
    elif command == 'stop':
        daemon.stop_daemon()
    elif command == 'restart':
        daemon.restart_daemon()
    elif command == 'status':
        daemon.status()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
