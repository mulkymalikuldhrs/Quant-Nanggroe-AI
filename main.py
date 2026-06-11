"""
🧠 Agentic AI System - Main Entry Point
Autonomous Multi-Agent Intelligence System

Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩

DEPRECATED: Legacy Flask interface is deprecated. Use quant_nanggroe CLI instead.
"""

import warnings
warnings.warn(
    "Legacy Flask interface is deprecated. Use quant_nanggroe CLI instead.",
    DeprecationWarning,
    stacklevel=2,
)

import asyncio
import sys
import os
import signal
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Add src to path for imports
sys.path.append(str(Path(__file__).parent))

def print_banner():
    """Print system banner"""
    banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                        🧠 AGENTIC AI SYSTEM 🧠                               ║
║                                                                              ║
║                    Autonomous Multi-Agent Intelligence                       ║
║                                                                              ║
║               🤖 20+ Specialized Agents | 🔄 Auto-Schedule                   ║
║               🌐 Multi-Platform | 🚀 Self-Expanding                         ║
║               📊 Real-time Sync | 🎯 Intelligent Selection                  ║
║                                                                              ║
║                Made with ❤️ by Mulky Malikul Dhaher 🇮🇩                     ║
╚══════════════════════════════════════════════════════════════════════════════╝
    """
    print(banner)

class AgenticAISystem:
    """
    Main Agentic AI System orchestrator that:
    - Initializes all core components
    - Manages agent lifecycle
    - Handles system coordination
    - Provides unified interface
    - Manages autonomous operations
    """
    
    def __init__(self):
        self.system_id = "agentic_ai_system"
        self.version = "2.1.0"
        self.status = "initializing"
        self.start_time = datetime.now()
        
        # Core components
        self.prompt_master = None
        self.memory_bus = None
        self.sync_engine = None
        self.scheduler = None
        self.ai_selector = None
        
        # Agents registry
        self.agents = {}
        self.active_agents = {}
        
        # System configuration
        self.config = self._load_system_config()
        
        # Shutdown flag
        self.shutdown_requested = False
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _load_system_config(self) -> Dict[str, Any]:
        """Load system configuration"""
        default_config = {
            "auto_start_agents": [
                "prompt_master",
                "cybershell", 
                "agent_maker",
                "ui_designer",
                "dev_engine",
                "data_sync",
                "fullstack_dev"
            ],
            "enable_scheduler": True,
            "enable_sync_engine": True,
            "enable_web_interface": True,
            "web_interface_port": 5000,
            "log_level": "INFO",
            "max_concurrent_tasks": 10,
            "auto_backup_interval": 3600,  # 1 hour
            "health_check_interval": 300   # 5 minutes
        }
        
        config_file = Path("data/system_config.json")
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    user_config = json.load(f)
                    default_config.update(user_config)
            except Exception as e:
                print(f"⚠️ Failed to load config: {e}")
        
        return default_config
    
    async def initialize(self):
        """Initialize the system"""
        print("🚀 Initializing Agentic AI System...")
        
        try:
            # Ensure data directories exist
            self._ensure_directories()
            
            # Initialize core components
            await self._initialize_core_components()
            
            # Initialize agents
            await self._initialize_agents()
            
            # Start scheduler if enabled
            if self.config["enable_scheduler"]:
                await self._start_scheduler()
            
            # Start sync engine if enabled
            if self.config["enable_sync_engine"]:
                await self._start_sync_engine()
            
            # Start web interface if enabled
            if self.config["enable_web_interface"]:
                await self._start_web_interface()
            
            self.status = "running"
            print("✅ Agentic AI System initialized successfully!")
            
            # Print system status
            await self._print_system_status()
            
        except Exception as e:
            print(f"❌ System initialization failed: {e}")
            self.status = "failed"
            raise
    
    def _ensure_directories(self):
        """Ensure required directories exist"""
        directories = [
            "data", "data/backups", "data/logs", "data/cache",
            "projects", "ui/generated", "reports"
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    async def _initialize_core_components(self):
        """Initialize core system components"""
        print("🔧 Initializing core components...")
        
        # Initialize Memory Bus
        try:
            from core.memory_bus import memory_bus
            self.memory_bus = memory_bus
            print("  ✅ Memory Bus")
        except ImportError:
            print("  ⚠️  Memory Bus: legacy module not available (deprecated)")
        except Exception as e:
            print(f"  ❌ Memory Bus: {e}")
        
        # Initialize AI Selector
        try:
            from core.ai_selector import ai_selector
            self.ai_selector = ai_selector
            print("  ✅ AI Selector")
        except ImportError:
            print("  ⚠️  AI Selector: legacy module not available (deprecated)")
        except Exception as e:
            print(f"  ❌ AI Selector: {e}")
        
        # Initialize Prompt Master
        try:
            from core.prompt_master import prompt_master
            self.prompt_master = prompt_master
            self.prompt_master.start_time = self.start_time.timestamp()
            print("  ✅ Prompt Master")
        except ImportError:
            print("  ⚠️  Prompt Master: legacy module not available (deprecated)")
        except Exception as e:
            print(f"  ❌ Prompt Master: {e}")
    
    async def _initialize_agents(self):
        """Initialize and register all agents"""
        print("🤖 Initializing agents...")
        
        # Agent configurations
        agent_configs = {
            "cybershell": {
                "module": "agents.cybershell",
                "class": "CyberShellAgent",
                "instance": "cybershell_agent"
            },
            "agent_maker": {
                "module": "agents.agent_maker", 
                "class": "AgentMakerAgent",
                "instance": "agent_maker"
            },
            "ui_designer": {
                "module": "agents.ui_designer",
                "class": "UIDesignerAgent", 
                "instance": "ui_designer_agent"
            },
            "dev_engine": {
                "module": "agents.dev_engine",
                "class": "DevEngineAgent",
                "instance": "dev_engine_agent"
            },
            "data_sync": {
                "module": "agents.data_sync",
                "class": "DataSyncAgent",
                "instance": "data_sync_agent"
            },
            "fullstack_dev": {
                "module": "agents.fullstack_dev",
                "class": "FullStackDevAgent",
                "instance": "fullstack_dev_agent"
            }
        }
        
        # Initialize each agent
        for agent_id, config in agent_configs.items():
            try:
                # Import agent module
                module = __import__(config["module"], fromlist=[config["instance"]])
                agent_instance = getattr(module, config["instance"])
                
                # Register agent
                self.agents[agent_id] = agent_instance
                
                # Auto-start if configured
                if agent_id in self.config["auto_start_agents"]:
                    self.active_agents[agent_id] = agent_instance
                
                print(f"  ✅ {agent_id}")
                
            except ImportError:
                print(f"  ⚠️  {agent_id}: legacy module not available (deprecated)")
            except Exception as e:
                print(f"  ❌ {agent_id}: {e}")
        
        print(f"🤖 Initialized {len(self.agents)} agents, {len(self.active_agents)} active")
    
    async def _start_scheduler(self):
        """Start the agent scheduler"""
        try:
            from core.scheduler import agent_scheduler
            self.scheduler = agent_scheduler
            self.scheduler.start()
            print("  ✅ Agent Scheduler started")
        except ImportError:
            print("  ⚠️  Scheduler: legacy module not available (deprecated)")
        except Exception as e:
            print(f"  ❌ Scheduler failed: {e}")
    
    async def _start_sync_engine(self):
        """Start the sync engine"""
        try:
            from core.sync_engine import sync_engine
            self.sync_engine = sync_engine
            await self.sync_engine.start()
            print("  ✅ Sync Engine started")
        except ImportError:
            print("  ⚠️  Sync Engine: legacy module not available (deprecated)")
        except Exception as e:
            print(f"  ❌ Sync Engine failed: {e}")
    
    async def _start_web_interface(self):
        """Start the web interface"""
        try:
            # Start web interface in background
            asyncio.create_task(self._run_web_interface())
            print(f"  ✅ Web Interface starting on port {self.config['web_interface_port']}")
        except Exception as e:
            print(f"  ❌ Web Interface failed: {e}")
    
    async def _run_web_interface(self) -> None:
        """Run the web interface server"""
        try:
            import subprocess
            import sys
            
            # Start Flask app
            subprocess.Popen([
                sys.executable, "-m", "flask", "--app", "web_interface.app", "run",
                "--host", "0.0.0.0", "--port", str(self.config["web_interface_port"])
            ])
            
        except Exception as e:
            print(f"Web interface error: {e}")
    
    async def _print_system_status(self):
        """Print current system status"""
        status_info = f"""
┌─ SYSTEM STATUS ─────────────────────────────────────────────────────────────┐
│ Status: {self.status.upper()}                                               
│ Version: {self.version}                                                     
│ Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}                    
│                                                                             
│ 🧠 Core Components:                                                         
│   • Prompt Master: {'✅' if self.prompt_master else '❌'}                    
│   • Memory Bus: {'✅' if self.memory_bus else '❌'}                         
│   • AI Selector: {'✅' if self.ai_selector else '❌'}                       
│   • Sync Engine: {'✅' if self.sync_engine else '❌'}                       
│   • Scheduler: {'✅' if self.scheduler else '❌'}                           
│                                                                             
│ 🤖 Active Agents: {len(self.active_agents)}                                 
{self._format_agents_status()}                                               
│                                                                             
│ 🌐 Interfaces:                                                              
│   • Web UI: http://localhost:{self.config['web_interface_port']}            
│   • API: http://localhost:{self.config['web_interface_port']}/api           
│                                                                             
│ 🇮🇩 Made with ❤️ by Mulky Malikul Dhaher in Indonesia                      
└─────────────────────────────────────────────────────────────────────────────┘
        """
        print(status_info)
    
    def _format_agents_status(self) -> str:
        """Format agents status for display"""
        lines = []
        for agent_id, agent in self.active_agents.items():
            status = getattr(agent, 'status', 'unknown')
            name = getattr(agent, 'name', agent_id)
            lines.append(f"│   • {name}: {status}")
        
        return '\n'.join(lines) if lines else "│   • No active agents"
    
    async def process_user_input(self, user_input: str, input_type: str = "text", 
                                metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process user input through the system
        
        Args:
            user_input: The user's text or command input
            input_type: Type of input ('text', 'voice', 'code')
            metadata: Optional additional metadata for processing
            
        Returns:
            Dict with 'success' bool and 'result' or 'error'
        """
        if not self.prompt_master:
            return {"success": False, "error": "Prompt Master not available"}
        
        try:
            # Use Prompt Master to process the input
            result = await self.prompt_master.process_prompt(
                prompt=user_input,
                input_type=input_type,
                metadata=metadata or {}
            )
            
            return result
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status
        
        Returns:
            Dict containing system_id, version, status, uptime, components, agents, and config
        """
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        status = {
            "system_id": self.system_id,
            "version": self.version,
            "status": self.status,
            "uptime_seconds": uptime,
            "started_at": self.start_time.isoformat(),
            "core_components": {
                "prompt_master": self.prompt_master is not None,
                "memory_bus": self.memory_bus is not None,
                "ai_selector": self.ai_selector is not None,
                "sync_engine": self.sync_engine is not None,
                "scheduler": self.scheduler is not None
            },
            "agents": {
                "total": len(self.agents),
                "active": len(self.active_agents),
                "list": list(self.active_agents.keys())
            },
            "config": self.config
        }
        
        # Add component-specific status
        if self.prompt_master:
            status["prompt_master_status"] = self.prompt_master.get_system_status()
        
        if self.scheduler:
            status["scheduler_status"] = self.scheduler.get_scheduler_status()
        
        if self.sync_engine:
            status["sync_engine_status"] = self.sync_engine.get_engine_status()
        
        if self.memory_bus:
            status["memory_usage"] = self.memory_bus.get_usage_stats()
        
        return status
    
    async def run_interactive_mode(self) -> None:
        """Run in interactive mode - accepts text commands from stdin"""
        print("\n🎯 Entering interactive mode. Type 'help' for commands, 'exit' to quit.")
        
        while not self.shutdown_requested:
            try:
                # Get user input
                user_input = input("\n🧠 Agentic AI > ").strip()
                
                if not user_input:
                    continue
                
                # Handle special commands
                if user_input.lower() in ['exit', 'quit']:
                    break
                elif user_input.lower() == 'help':
                    self._print_help()
                    continue
                elif user_input.lower() == 'status':
                    status = await self.get_system_status()
                    print(json.dumps(status, indent=2))
                    continue
                elif user_input.lower() == 'agents':
                    print(f"Active agents: {', '.join(self.active_agents.keys())}")
                    continue
                
                # Process as regular prompt
                print("🔄 Processing...")
                result = await self.process_user_input(user_input)
                
                if result.get("success"):
                    print("✅ Task completed successfully!")
                    if "result" in result:
                        print(f"📊 Result: {result['result']}")
                else:
                    print(f"❌ Error: {result.get('error', 'Unknown error')}")
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
    
    def _print_help(self):
        """Print help information"""
        help_text = """
🆘 AGENTIC AI SYSTEM HELP

Commands:
  help                    - Show this help
  status                  - Show system status
  agents                  - List active agents
  exit/quit               - Exit the system

Natural Language Commands:
  "Create a web app called TaskManager"
  "Build a React component for user login"
  "Set up a FastAPI backend with authentication"
  "Generate a landing page for my startup"
  "Deploy my app to production"
  "Create an agent that monitors system health"

Features:
  🤖 Multi-agent collaboration
  🔄 Auto-scheduling and execution
  🌐 Multi-platform deployment
  📊 Real-time monitoring
  🎨 UI/UX generation
  ⚙️ DevOps automation

For detailed documentation: http://localhost:5000/docs
        """
        print(help_text)
    
    def _signal_handler(self, signum: int, frame) -> None:
        """Handle shutdown signals gracefully
        
        Args:
            signum: Signal number received
            frame: Current stack frame (unused)
        """
        print(f"\n🛑 Received signal {signum}, initiating shutdown...")
        self.shutdown_requested = True
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the system, stopping all components"""
        print("🛑 Shutting down Agentic AI System...")
        
        try:
            # Stop scheduler
            if self.scheduler:
                self.scheduler.stop()
                print("  ✅ Scheduler stopped")
            
            # Close database connections
            if self.memory_bus:
                self.memory_bus.cleanup_expired()
                print("  ✅ Memory cleanup completed")
            
            # Save system state
            await self._save_system_state()
            
            self.status = "stopped"
            print("✅ System shutdown complete")
            
        except Exception as e:
            print(f"❌ Shutdown error: {e}")
    
    async def _save_system_state(self):
        """Save current system state"""
        try:
            state = {
                "shutdown_time": datetime.now().isoformat(),
                "uptime_seconds": (datetime.now() - self.start_time).total_seconds(),
                "active_agents": list(self.active_agents.keys()),
                "status": self.status,
                "version": self.version
            }
            
            with open("data/last_session.json", "w") as f:
                json.dump(state, f, indent=2)
                
        except Exception as e:
            print(f"Failed to save system state: {e}")

async def main():
    """Main entry point"""
    print_banner()
    
    # Create and initialize system
    system = AgenticAISystem()
    
    try:
        # Initialize the system
        await system.initialize()
        
        # Check command line arguments
        if len(sys.argv) > 1:
            command = " ".join(sys.argv[1:])
            print(f"🎯 Executing command: {command}")
            
            result = await system.process_user_input(command)
            
            if result.get("success"):
                print("✅ Command executed successfully!")
                if "result" in result:
                    print(json.dumps(result["result"], indent=2))
            else:
                print(f"❌ Command failed: {result.get('error')}")
        else:
            # Run in interactive mode
            await system.run_interactive_mode()
    
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    
    except Exception as e:
        print(f"❌ System error: {e}")
    
    finally:
        # Shutdown gracefully
        await system.shutdown()

if __name__ == "__main__":
    # Run the system
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 System interrupted")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
