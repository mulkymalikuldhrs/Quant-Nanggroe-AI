"""
AutoGen Integration for Agentic AI System
Provides seamless integration with Microsoft AutoGen framework
"""

from typing import Dict, List, Any, Optional
import asyncio
from datetime import datetime

try:
    import autogen
    from autogen import ConversableAgent, GroupChat, GroupChatManager
    AUTOGEN_AVAILABLE = True
except ImportError:
    AUTOGEN_AVAILABLE = False
    ConversableAgent = None
    GroupChat = None
    GroupChatManager = None

from ..core.agent_manager import AgentManager

class AutoGenAdapter:
    """Adapter for integrating Agentic AI System with AutoGen"""
    
    def __init__(self, agent_manager: AgentManager):
        if not AUTOGEN_AVAILABLE:
            raise ImportError("AutoGen is not installed. Install with: pip install pyautogen")
        
        self.agent_manager = agent_manager
        self.autogen_agents = {}
        self.group_chats = {}
        
        # Default LLM configuration
        self.llm_config = {
            "model": "gpt-3.5-turbo",
            "api_key": None,  # Set this from environment or config
            "temperature": 0.7
        }
    
    def create_autogen_agent(self, agent_id: str, agent_config: Optional[Dict[str, Any]] = None) -> ConversableAgent:
        """Create an AutoGen agent from an Agentic AI agent"""
        
        # Get the original agent
        original_agent = self.agent_manager.get_agent(agent_id)
        if not original_agent:
            raise ValueError(f"Agent '{agent_id}' not found in agent manager")
        
        # Prepare agent configuration
        config = agent_config or {}
        agent_name = config.get('name', original_agent.name)
        system_message = config.get('system_message', original_agent.get_system_prompt())
        
        # Create AutoGen agent
        autogen_agent = ConversableAgent(
            name=agent_name,
            system_message=system_message,
            llm_config=self.llm_config,
            human_input_mode="NEVER",
            max_consecutive_auto_reply=config.get('max_auto_reply', 3)
        )
        
        # Override the generate_reply method to use our agent
        original_generate_reply = autogen_agent.generate_reply
        
        def custom_generate_reply(messages, sender, config):
            """Custom reply generation using Agentic AI agent"""
            
            # Extract the last message
            last_message = messages[-1] if messages else {"content": ""}
            
            # Prepare task for our agent
            task = {
                'task_id': f'autogen_{agent_id}_{int(datetime.now().timestamp())}',
                'request': last_message.get('content', ''),
                'context': {
                    'integration': 'autogen',
                    'sender': sender.name if sender else 'unknown',
                    'conversation_history': messages,
                    'timestamp': datetime.now().isoformat()
                }
            }
            
            # Process with our agent
            try:
                result = original_agent.process_task(task)
                return True, result.get('content', str(result))
            except Exception as e:
                return True, f"Error: {str(e)}"
        
        autogen_agent.generate_reply = custom_generate_reply
        
        # Store the mapping
        self.autogen_agents[agent_id] = autogen_agent
        
        return autogen_agent
    
    def create_group_chat(self, agent_ids: List[str], admin_name: str = "Admin") -> GroupChatManager:
        """Create an AutoGen group chat with specified agents"""
        
        # Create AutoGen agents for each ID
        agents = []
        for agent_id in agent_ids:
            if agent_id not in self.autogen_agents:
                self.create_autogen_agent(agent_id)
            agents.append(self.autogen_agents[agent_id])
        
        # Create admin agent
        admin_agent = ConversableAgent(
            name=admin_name,
            system_message="You are an admin managing a group conversation between AI agents.",
            llm_config=self.llm_config,
            human_input_mode="NEVER"
        )
        
        agents.append(admin_agent)
        
        # Create group chat
        group_chat = GroupChat(
            agents=agents,
            messages=[],
            max_round=10,
            speaker_selection_method="auto"
        )
        
        # Create group chat manager
        manager = GroupChatManager(
            groupchat=group_chat,
            llm_config=self.llm_config
        )
        
        # Store the group chat
        chat_id = f"group_chat_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.group_chats[chat_id] = {
            'manager': manager,
            'group_chat': group_chat,
            'agents': agents,
            'created_at': datetime.now().isoformat()
        }
        
        return manager
    
    def start_conversation(self, agent_ids: List[str], initial_message: str) -> Dict[str, Any]:
        """Start a conversation between specified agents"""
        
        # Create group chat
        manager = self.create_group_chat(agent_ids)
        
        # Get the first agent to start the conversation
        first_agent = self.autogen_agents[agent_ids[0]]
        
        try:
            # Start the conversation
            result = first_agent.initiate_chat(
                manager,
                message=initial_message
            )
            
            return {
                'status': 'completed',
                'conversation_result': result,
                'participants': agent_ids,
                'started_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'failed',
                'error': str(e),
                'participants': agent_ids,
                'started_at': datetime.now().isoformat()
            }
    
    def create_specialized_workflows(self) -> Dict[str, Any]:
        """Create specialized AutoGen workflows"""
        
        workflows = {}
        
        # Software Development Team
        workflows['software_development'] = {
            'agents': ['agent_base', 'agent_03_planner', 'agent_04_executor', 'agent_06_specialist'],
            'roles': {
                'agent_base': 'Product Manager',
                'agent_03_planner': 'Software Architect', 
                'agent_04_executor': 'Senior Developer',
                'agent_06_specialist': 'Quality Assurance Engineer'
            },
            'workflow_type': 'collaborative_development'
        }
        
        # Design Team
        workflows['design_team'] = {
            'agents': ['agent_base', 'agent_05_designer', 'agent_06_specialist'],
            'roles': {
                'agent_base': 'Creative Director',
                'agent_05_designer': 'UI/UX Designer',
                'agent_06_specialist': 'Design Reviewer'
            },
            'workflow_type': 'design_collaboration'
        }
        
        # Analysis Team
        workflows['analysis_team'] = {
            'agents': ['agent_base', 'agent_06_specialist', 'agent_04_executor', 'output_handler'],
            'roles': {
                'agent_base': 'Research Director',
                'agent_06_specialist': 'Domain Expert',
                'agent_04_executor': 'Data Analyst',
                'output_handler': 'Report Writer'
            },
            'workflow_type': 'analytical_research'
        }
        
        return workflows
    
    def execute_workflow(self, workflow_name: str, task_description: str) -> Dict[str, Any]:
        """Execute a predefined workflow"""
        
        workflows = self.create_specialized_workflows()
        
        if workflow_name not in workflows:
            raise ValueError(f"Workflow '{workflow_name}' not found")
        
        workflow = workflows[workflow_name]
        agent_ids = workflow['agents']
        
        # Create custom system messages based on roles
        for agent_id in agent_ids:
            if agent_id not in self.autogen_agents:
                role = workflow['roles'].get(agent_id, 'Team Member')
                system_message = f"You are a {role} working on: {task_description}"
                
                self.create_autogen_agent(agent_id, {
                    'name': role,
                    'system_message': system_message
                })
        
        # Start the collaborative conversation
        initial_message = f"""
        Team, we have a new project: {task_description}
        
        Let's collaborate to deliver the best solution. Each team member should contribute based on their expertise.
        
        {workflow['roles'][agent_ids[0]]}, please start by outlining the approach.
        """
        
        return self.start_conversation(agent_ids, initial_message)
    
    def create_sequential_workflow(self, agent_sequence: List[str], task: str) -> Dict[str, Any]:
        """Create a sequential workflow where agents work one after another"""
        
        results = []
        current_message = task
        
        for i, agent_id in enumerate(agent_sequence):
            # Get or create AutoGen agent
            if agent_id not in self.autogen_agents:
                self.create_autogen_agent(agent_id)
            
            current_agent = self.autogen_agents[agent_id]
            
            # If not the first agent, get next agent
            if i < len(agent_sequence) - 1:
                next_agent_id = agent_sequence[i + 1]
                if next_agent_id not in self.autogen_agents:
                    self.create_autogen_agent(next_agent_id)
                next_agent = self.autogen_agents[next_agent_id]
                
                # Create conversation between current and next agent
                try:
                    result = current_agent.initiate_chat(
                        next_agent,
                        message=current_message
                    )
                    
                    results.append({
                        'agent': agent_id,
                        'result': result,
                        'success': True
                    })
                    
                    # Use the result as input for next agent
                    current_message = str(result)
                    
                except Exception as e:
                    results.append({
                        'agent': agent_id,
                        'error': str(e),
                        'success': False
                    })
                    break
        
        return {
            'workflow_type': 'sequential',
            'agents': agent_sequence,
            'results': results,
            'final_result': current_message,
            'completed_at': datetime.now().isoformat()
        }
    
    def get_conversation_history(self, chat_id: str) -> Optional[List[Dict[str, Any]]]:
        """Get conversation history for a group chat"""
        
        if chat_id in self.group_chats:
            group_chat = self.group_chats[chat_id]['group_chat']
            return group_chat.messages
        
        return None
    
    def list_active_chats(self) -> List[Dict[str, Any]]:
        """List all active group chats"""
        
        return [
            {
                'chat_id': chat_id,
                'participants': [agent.name for agent in chat_data['agents']],
                'created_at': chat_data['created_at'],
                'message_count': len(chat_data['group_chat'].messages)
            }
            for chat_id, chat_data in self.group_chats.items()
        ]

# Example usage and testing utilities
class AutoGenWorkflowTester:
    """Testing utilities for AutoGen integration"""
    
    def __init__(self, adapter: AutoGenAdapter):
        self.adapter = adapter
        
    def test_agent_conversation(self, agent1_id: str, agent2_id: str, test_message: str) -> Dict[str, Any]:
        """Test conversation between two agents"""
        
        # Create agents if they don't exist
        if agent1_id not in self.adapter.autogen_agents:
            self.adapter.create_autogen_agent(agent1_id)
        if agent2_id not in self.adapter.autogen_agents:
            self.adapter.create_autogen_agent(agent2_id)
        
        agent1 = self.adapter.autogen_agents[agent1_id]
        agent2 = self.adapter.autogen_agents[agent2_id]
        
        try:
            result = agent1.initiate_chat(agent2, message=test_message)
            
            return {
                'status': 'success',
                'agent1': agent1_id,
                'agent2': agent2_id,
                'test_message': test_message,
                'result': result,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'failed',
                'agent1': agent1_id,
                'agent2': agent2_id,
                'test_message': test_message,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def test_workflow_performance(self, workflow_name: str, test_cases: List[str]) -> Dict[str, Any]:
        """Test workflow performance with multiple test cases"""
        
        results = []
        
        for i, test_case in enumerate(test_cases):
            print(f"Testing case {i+1}/{len(test_cases)}: {test_case[:50]}...")
            
            start_time = datetime.now()
            result = self.adapter.execute_workflow(workflow_name, test_case)
            end_time = datetime.now()
            
            duration = (end_time - start_time).total_seconds()
            
            results.append({
                'test_case': test_case,
                'result': result,
                'duration': duration,
                'success': result['status'] == 'completed'
            })
        
        success_rate = sum(1 for r in results if r['success']) / len(results)
        avg_duration = sum(r['duration'] for r in results) / len(results)
        
        return {
            'workflow_name': workflow_name,
            'total_tests': len(test_cases),
            'successful_tests': sum(1 for r in results if r['success']),
            'success_rate': success_rate,
            'average_duration': avg_duration,
            'detailed_results': results
        }

# Helper class for custom agent behaviors
class AutoGenAgentCustomizer:
    """Utilities for customizing AutoGen agent behaviors"""
    
    @staticmethod
    def create_code_execution_agent(agent_manager: AgentManager) -> ConversableAgent:
        """Create a specialized code execution agent"""
        
        executor_agent = agent_manager.get_agent('agent_04_executor')
        
        code_agent = ConversableAgent(
            name="CodeExecutor",
            system_message="""
            You are a code execution specialist. You can execute Python code, run scripts, 
            and handle API calls. Always provide clear explanations of what the code does 
            and what the results mean.
            """,
            llm_config={
                "model": "gpt-3.5-turbo",
                "temperature": 0.1  # Lower temperature for code tasks
            },
            code_execution_config={
                "work_dir": "temp",
                "use_docker": False  # Set to True if Docker is available
            }
        )
        
        return code_agent
    
    @staticmethod
    def create_review_agent(agent_manager: AgentManager) -> ConversableAgent:
        """Create a specialized review agent"""
        
        specialist_agent = agent_manager.get_agent('agent_06_specialist')
        
        review_agent = ConversableAgent(
            name="ReviewSpecialist",
            system_message="""
            You are a review specialist. Your role is to critically evaluate work products,
            identify potential issues, suggest improvements, and ensure quality standards are met.
            Provide constructive feedback and actionable recommendations.
            """,
            llm_config={
                "model": "gpt-3.5-turbo",
                "temperature": 0.3
            },
            human_input_mode="NEVER"
        )
        
        return review_agent
