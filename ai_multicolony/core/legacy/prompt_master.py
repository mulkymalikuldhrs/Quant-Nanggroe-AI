"""
🧠 Prompt Master Agent - Central Command System
Mulky Command Core AI - Autonomous Agent Coordinator

Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .memory_bus import MemoryBus
from .ai_selector import AISelector
from .sync_engine import SyncEngine
from connectors.llm_gateway import LLMGateway

@dataclass
class Task:
    task_id: str
    prompt: str
    task_type: str
    priority: int
    assigned_agent: Optional[str] = None
    status: str = "pending"
    created_at: datetime = None
    completed_at: datetime = None
    result: Any = None

class PromptMasterAgent:
    """
    🧠 Prompt Master Agent - Mulky Command Core AI
    
    Central coordinator that:
    - Receives user prompts (text, voice, video)
    - Analyzes and breaks down complex tasks
    - Selects best agents for execution
    - Coordinates multi-agent workflows
    - Manages autonomous operations
    """
    
    def __init__(self):
        self.agent_id = "prompt_master"
        self.name = "Mulky Command Core AI"
        self.status = "active"
        self.memory = MemoryBus()
        self.ai_selector = AISelector()
        self.sync_engine = SyncEngine()
        self.llm = LLMGateway()
        
        self.active_tasks: Dict[str, Task] = {}
        self.agent_registry = {}
        self.workflow_templates = {}
        
        # Load configurations
        self._load_agent_registry()
        self._load_workflow_templates()
        
    def _load_agent_registry(self):
        """Load available agents and their capabilities"""
        try:
            with open('data/agents_registry.json', 'r') as f:
                self.agent_registry = json.load(f)
        except FileNotFoundError:
            self._create_default_registry()
    
    def _create_default_registry(self):
        """Create default agent registry"""
        self.agent_registry = {
            "cybershell": {
                "name": "CyberShell Agent",
                "capabilities": ["shell_execution", "cli_automation", "system_administration"],
                "status": "active",
                "priority": 8
            },
            "ui_designer": {
                "name": "UI Designer Agent", 
                "capabilities": ["ui_design", "react_components", "tailwind_css", "figma_design"],
                "status": "active",
                "priority": 7
            },
            "dev_engine": {
                "name": "Development Engine",
                "capabilities": ["project_setup", "architecture_design", "code_generation"],
                "status": "active", 
                "priority": 9
            },
            "agent_maker": {
                "name": "Agent Maker",
                "capabilities": ["agent_creation", "code_generation", "autonomous_development"],
                "status": "active",
                "priority": 9
            },
            "fullstack_dev": {
                "name": "Full Stack Developer",
                "capabilities": ["frontend", "backend", "database", "api_development"],
                "status": "active",
                "priority": 10
            },
            "data_sync": {
                "name": "Data Sync Agent",
                "capabilities": ["database_sync", "supabase", "redis", "json_storage"],
                "status": "active",
                "priority": 8
            },
            "voice_agent": {
                "name": "Voice Agent",
                "capabilities": ["speech_to_text", "voice_commands", "audio_processing"],
                "status": "active",
                "priority": 6
            },
            "github_agent": {
                "name": "GitHub Agent",
                "capabilities": ["git_operations", "repo_management", "ci_cd", "code_sync"],
                "status": "active",
                "priority": 7
            },
            "deploy_manager": {
                "name": "Deploy Manager",
                "capabilities": ["web_deployment", "apk_build", "docker", "cloud_deploy"],
                "status": "active",
                "priority": 8
            },
            "web3_plugin": {
                "name": "Web3 Agent",
                "capabilities": ["smart_contracts", "blockchain", "defi", "nft"],
                "status": "active",
                "priority": 6
            }
        }
        self._save_agent_registry()
    
    def _save_agent_registry(self):
        """Save agent registry to file"""
        with open('data/agents_registry.json', 'w') as f:
            json.dump(self.agent_registry, f, indent=2)
    
    def _load_workflow_templates(self):
        """Load workflow templates for common tasks"""
        self.workflow_templates = {
            "create_web_app": [
                {"agent": "dev_engine", "task": "setup_project_structure"},
                {"agent": "ui_designer", "task": "create_ui_components"},
                {"agent": "backend_dev", "task": "create_api_endpoints"},
                {"agent": "data_sync", "task": "setup_database"},
                {"agent": "deploy_manager", "task": "deploy_to_web"}
            ],
            "create_mobile_app": [
                {"agent": "dev_engine", "task": "setup_react_native"},
                {"agent": "ui_designer", "task": "mobile_ui_design"},
                {"agent": "fullstack_dev", "task": "mobile_development"},
                {"agent": "deploy_manager", "task": "build_apk"}
            ],
            "automate_workflow": [
                {"agent": "cybershell", "task": "analyze_requirements"},
                {"agent": "agent_maker", "task": "create_automation_agent"},
                {"agent": "github_agent", "task": "setup_ci_cd"}
            ],
            "data_analysis": [
                {"agent": "data_sync", "task": "collect_data"},
                {"agent": "fullstack_dev", "task": "create_analysis_tools"},
                {"agent": "ui_designer", "task": "create_dashboard"}
            ]
        }
    
    async def process_prompt(self, prompt: str, input_type: str = "text", metadata: Dict = None) -> Dict[str, Any]:
        """
        Main entry point for processing user prompts
        
        Args:
            prompt: User input (text, transcribed voice, etc.)
            input_type: Type of input (text, voice, video, drag_drop)
            metadata: Additional context (user_id, session, etc.)
        """
        try:
            # Generate unique task ID
            task_id = f"task_{int(time.time())}_{len(self.active_tasks)}"
            
            # Analyze prompt with AI
            analysis = await self._analyze_prompt(prompt, input_type, metadata)
            
            # Create task object
            task = Task(
                task_id=task_id,
                prompt=prompt,
                task_type=analysis["task_type"],
                priority=analysis["priority"],
                created_at=datetime.now()
            )
            
            # Store task
            self.active_tasks[task_id] = task
            self.memory.store_task(task)
            
            # Determine execution strategy
            if analysis["complexity"] == "simple":
                # Single agent execution
                result = await self._execute_single_agent_task(task, analysis)
            else:
                # Multi-agent workflow
                result = await self._execute_workflow(task, analysis)
            
            return {
                "success": True,
                "task_id": task_id,
                "result": result,
                "execution_time": (datetime.now() - task.created_at).total_seconds()
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "task_id": task_id if 'task_id' in locals() else None
            }
    
    async def _analyze_prompt(self, prompt: str, input_type: str, metadata: Dict) -> Dict[str, Any]:
        """Analyze prompt using LLM to determine task type and complexity"""
        
        system_prompt = """
        You are an AI task analyzer for the Agentic AI System. Analyze the user prompt and return a JSON response with:
        
        {
            "task_type": "web_app|mobile_app|automation|data_analysis|ui_design|backend|deployment|other",
            "complexity": "simple|medium|complex",
            "priority": 1-10,
            "required_agents": ["agent1", "agent2"],
            "estimated_time": "5min|30min|2hours|1day",
            "description": "Brief description of what needs to be done"
        }
        
        Available agents: cybershell, ui_designer, dev_engine, agent_maker, fullstack_dev, data_sync, voice_agent, github_agent, deploy_manager, web3_plugin
        """
        
        try:
            response = await self.llm.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Input type: {input_type}\nPrompt: {prompt}"}
                ],
                model="llm7"
            )
            
            analysis = json.loads(response["choices"][0]["message"]["content"])
            return analysis
            
        except Exception as e:
            # Fallback analysis
            return {
                "task_type": "other",
                "complexity": "medium", 
                "priority": 5,
                "required_agents": ["fullstack_dev"],
                "estimated_time": "30min",
                "description": "General task execution"
            }
    
    async def _execute_single_agent_task(self, task: Task, analysis: Dict) -> Dict[str, Any]:
        """Execute task with single best-fit agent"""
        
        # Select best agent
        selected_agent = self.ai_selector.select_best_agent(
            task_type=analysis["task_type"],
            required_capabilities=analysis.get("required_capabilities", []),
            agent_registry=self.agent_registry
        )
        
        task.assigned_agent = selected_agent
        task.status = "executing"
        
        # Execute with selected agent
        agent_module = self._get_agent_module(selected_agent)
        if agent_module:
            result = await agent_module.process_task({
                "task_id": task.task_id,
                "prompt": task.prompt,
                "analysis": analysis
            })
            
            task.status = "completed"
            task.completed_at = datetime.now()
            task.result = result
            
            return result
        else:
            raise Exception(f"Agent {selected_agent} not available")
    
    async def _execute_workflow(self, task: Task, analysis: Dict) -> Dict[str, Any]:
        """Execute complex multi-agent workflow"""
        
        # Get workflow template
        workflow = self._get_workflow_template(analysis["task_type"])
        
        if not workflow:
            # Generate custom workflow
            workflow = await self._generate_custom_workflow(task, analysis)
        
        task.status = "executing_workflow"
        results = []
        
        # Execute workflow steps
        for step in workflow:
            step_result = await self._execute_workflow_step(step, task, analysis)
            results.append(step_result)
            
            # Check if step failed
            if not step_result.get("success", True):
                task.status = "failed"
                break
        
        # Compile final result
        final_result = await self._compile_workflow_result(results, task)
        
        task.status = "completed"
        task.completed_at = datetime.now()
        task.result = final_result
        
        return final_result
    
    def _get_workflow_template(self, task_type: str) -> List[Dict]:
        """Get predefined workflow template"""
        return self.workflow_templates.get(task_type)
    
    async def _generate_custom_workflow(self, task: Task, analysis: Dict) -> List[Dict]:
        """Generate custom workflow using AI"""
        
        system_prompt = """
        Generate a workflow of agent tasks to complete the user request. Return JSON array:
        
        [
            {"agent": "agent_name", "task": "specific_task_description"},
            {"agent": "agent_name", "task": "specific_task_description"}
        ]
        
        Available agents: cybershell, ui_designer, dev_engine, agent_maker, fullstack_dev, data_sync, voice_agent, github_agent, deploy_manager, web3_plugin
        """
        
        try:
            response = await self.llm.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Task: {task.prompt}\nAnalysis: {json.dumps(analysis)}"}
                ],
                model="llm7"
            )
            
            workflow = json.loads(response["choices"][0]["message"]["content"])
            return workflow
            
        except Exception as e:
            # Fallback workflow
            return [{"agent": "fullstack_dev", "task": task.prompt}]
    
    async def _execute_workflow_step(self, step: Dict, task: Task, analysis: Dict) -> Dict[str, Any]:
        """Execute single workflow step"""
        
        agent_name = step["agent"] 
        step_task = step["task"]
        
        # Get agent module
        agent_module = self._get_agent_module(agent_name)
        
        if agent_module:
            step_result = await agent_module.process_task({
                "task_id": f"{task.task_id}_step_{agent_name}",
                "prompt": step_task,
                "original_prompt": task.prompt,
                "analysis": analysis,
                "workflow_context": True
            })
            
            # Store step result in memory
            self.memory.store_workflow_step(task.task_id, agent_name, step_result)
            
            return {
                "agent": agent_name,
                "task": step_task,
                "result": step_result,
                "success": True
            }
        else:
            return {
                "agent": agent_name,
                "task": step_task,
                "error": f"Agent {agent_name} not available",
                "success": False
            }
    
    async def _compile_workflow_result(self, results: List[Dict], task: Task) -> Dict[str, Any]:
        """Compile final result from workflow execution"""
        
        successful_steps = [r for r in results if r.get("success", False)]
        failed_steps = [r for r in results if not r.get("success", True)]
        
        # Generate summary using AI
        summary_prompt = f"""
        Summarize the results of this multi-agent workflow execution:
        
        Original Task: {task.prompt}
        Successful Steps: {len(successful_steps)}
        Failed Steps: {len(failed_steps)}
        
        Results: {json.dumps(results, default=str)}
        
        Provide a concise summary and any deliverables created.
        """
        
        try:
            response = await self.llm.chat_completion(
                messages=[{"role": "user", "content": summary_prompt}],
                model="llm7"
            )
            
            summary = response["choices"][0]["message"]["content"]
        except Exception:
            summary = f"Workflow completed with {len(successful_steps)} successful steps"
        
        return {
            "summary": summary,
            "total_steps": len(results),
            "successful_steps": len(successful_steps),
            "failed_steps": len(failed_steps),
            "results": results,
            "deliverables": self._extract_deliverables(results)
        }
    
    def _extract_deliverables(self, results: List[Dict]) -> List[str]:
        """Extract deliverables (files, URLs, etc.) from workflow results"""
        deliverables = []
        
        for result in results:
            if result.get("success") and "result" in result:
                result_data = result["result"]
                
                # Extract files
                if "files_created" in result_data:
                    deliverables.extend(result_data["files_created"])
                
                # Extract URLs
                if "deployed_url" in result_data:
                    deliverables.append(result_data["deployed_url"])
                
                # Extract repositories
                if "repository_url" in result_data:
                    deliverables.append(result_data["repository_url"])
        
        return deliverables
    
    def _get_agent_module(self, agent_name: str):
        """Get agent module by name"""
        try:
            if agent_name == "cybershell":
                from agents.cybershell import CyberShellAgent
                return CyberShellAgent()
            elif agent_name == "ui_designer":
                from agents.ui_designer import UIDesignerAgent
                return UIDesignerAgent()
            elif agent_name == "dev_engine":
                from agents.dev_engine import DevEngineAgent
                return DevEngineAgent()
            elif agent_name == "agent_maker":
                from agents.agent_maker import AgentMakerAgent
                return AgentMakerAgent()
            elif agent_name == "fullstack_dev":
                from agents.fullstack_dev import FullStackDevAgent
                return FullStackDevAgent()
            elif agent_name == "data_sync":
                from agents.data_sync import DataSyncAgent
                return DataSyncAgent()
            elif agent_name == "github_agent":
                from agents.github_agent import GitHubAgent
                return GitHubAgent()
            elif agent_name == "deploy_manager":
                from agents.deploy_manager import DeployManagerAgent
                return DeployManagerAgent()
            elif agent_name == "voice_agent":
                from agents.voice_agent import VoiceAgent
                return VoiceAgent()
            elif agent_name == "web3_plugin":
                from agents.web3_plugin import Web3Plugin
                return Web3Plugin()
            elif agent_name == "agent_watcher":
                from agents.agent_watcher import AgentWatcherAgent
                return AgentWatcherAgent()
            # Add other agents as needed
            else:
                return None
        except ImportError:
            return None
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "status": self.status,
            "active_tasks": len(self.active_tasks),
            "available_agents": len(self.agent_registry),
            "memory_usage": self.memory.get_usage_stats(),
            "uptime": time.time() - getattr(self, 'start_time', time.time())
        }
    
    def get_active_tasks(self) -> List[Dict]:
        """Get list of active tasks"""
        return [
            {
                "task_id": task.task_id,
                "prompt": task.prompt[:100],
                "status": task.status,
                "assigned_agent": task.assigned_agent,
                "created_at": task.created_at.isoformat() if task.created_at else None
            }
            for task in self.active_tasks.values()
        ]

# Global instance
prompt_master = PromptMasterAgent()
