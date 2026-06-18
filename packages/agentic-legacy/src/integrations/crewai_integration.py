"""
CrewAI Integration for Agentic AI System
Provides seamless integration with CrewAI framework
"""

from typing import Dict, List, Any, Optional
import asyncio
from datetime import datetime

try:
    from crewai import Agent, Task, Crew, Process
    from crewai.tools import BaseTool
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    Agent = None
    Task = None
    Crew = None
    Process = None

from ..core.agent_manager import AgentManager

class CrewAIAdapter:
    """Adapter for integrating Agentic AI System with CrewAI"""
    
    def __init__(self, agent_manager: AgentManager):
        if not CREWAI_AVAILABLE:
            raise ImportError("CrewAI is not installed. Install with: pip install crewai")
        
        self.agent_manager = agent_manager
        self.crews = {}
        self.crewai_agents = {}
        
        # Default LLM configuration
        self.llm_config = {
            "model": "gpt-3.5-turbo",
            "temperature": 0.7
        }
    
    def create_crewai_agent(self, agent_id: str, role_config: Optional[Dict[str, Any]] = None) -> Agent:
        """Create a CrewAI agent from an Agentic AI agent"""
        
        # Get the original agent
        original_agent = self.agent_manager.get_agent(agent_id)
        if not original_agent:
            raise ValueError(f"Agent '{agent_id}' not found in agent manager")
        
        # Prepare agent configuration
        config = role_config or {}
        
        # Create CrewAI agent
        crewai_agent = Agent(
            role=config.get('role', original_agent.role),
            goal=config.get('goal', f"Complete tasks using {original_agent.name} capabilities"),
            backstory=config.get('backstory', f"""
                You are {original_agent.name}, a specialized AI agent with expertise in {original_agent.role}.
                You work as part of a coordinated team to accomplish complex objectives.
                Your unique capabilities allow you to handle specific aspects of projects efficiently.
            """),
            verbose=config.get('verbose', True),
            allow_delegation=config.get('allow_delegation', False),
            tools=config.get('tools', []),
            llm=None  # Use default LLM
        )
        
        # Create custom execution method
        original_execute = crewai_agent.execute_task
        
        def custom_execute_task(task):
            """Custom task execution using Agentic AI agent"""
            
            # Prepare task for our agent
            agentic_task = {
                'task_id': f'crewai_{agent_id}_{int(datetime.now().timestamp())}',
                'request': task.description if hasattr(task, 'description') else str(task),
                'context': {
                    'integration': 'crewai',
                    'task_type': type(task).__name__,
                    'crew_context': getattr(task, 'context', {}),
                    'timestamp': datetime.now().isoformat()
                }
            }
            
            # Process with our agent
            try:
                result = original_agent.process_task(agentic_task)
                return result.get('content', str(result))
            except Exception as e:
                return f"Error executing task: {str(e)}"
        
        crewai_agent.execute_task = custom_execute_task
        
        # Store the mapping
        self.crewai_agents[agent_id] = crewai_agent
        
        return crewai_agent
    
    def create_crew(self, crew_config: Dict[str, Any]) -> Crew:
        """Create a CrewAI crew with specified configuration"""
        
        agents = []
        tasks = []
        
        # Create agents
        for agent_config in crew_config.get('agents', []):
            if isinstance(agent_config, str):
                # Simple agent ID
                agent_id = agent_config
                role_config = {}
            else:
                # Detailed agent configuration
                agent_id = agent_config['agent_id']
                role_config = agent_config.get('role_config', {})
            
            if agent_id not in self.crewai_agents:
                self.create_crewai_agent(agent_id, role_config)
            
            agents.append(self.crewai_agents[agent_id])
        
        # Create tasks
        for task_config in crew_config.get('tasks', []):
            task = Task(
                description=task_config.get('description', 'Complete assigned task'),
                agent=agents[task_config.get('agent_index', 0)],
                expected_output=task_config.get('expected_output', 'Task completion report')
            )
            tasks.append(task)
        
        # Create crew
        crew = Crew(
            agents=agents,
            tasks=tasks,
            process=Process.sequential,  # Default to sequential
            verbose=crew_config.get('verbose', True)
        )
        
        # Store the crew
        crew_id = f"crew_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.crews[crew_id] = {
            'crew': crew,
            'config': crew_config,
            'created_at': datetime.now().isoformat()
        }
        
        return crew
    
    def create_specialized_crews(self) -> Dict[str, Any]:
        """Create specialized crew templates"""
        
        crews = {}
        
        # Software Development Crew
        crews['software_development'] = {
            'agents': [
                {
                    'agent_id': 'agent_base',
                    'role_config': {
                        'role': 'Product Manager',
                        'goal': 'Coordinate development team and ensure project success',
                        'backstory': 'Experienced product manager with expertise in software development lifecycle'
                    }
                },
                {
                    'agent_id': 'agent_03_planner',
                    'role_config': {
                        'role': 'Software Architect',
                        'goal': 'Design system architecture and create development plans',
                        'backstory': 'Senior software architect with deep knowledge of system design'
                    }
                },
                {
                    'agent_id': 'agent_04_executor',
                    'role_config': {
                        'role': 'Senior Developer',
                        'goal': 'Implement features and execute development tasks',
                        'backstory': 'Experienced developer skilled in multiple programming languages'
                    }
                },
                {
                    'agent_id': 'agent_06_specialist',
                    'role_config': {
                        'role': 'Quality Assurance Engineer',
                        'goal': 'Ensure code quality and system reliability',
                        'backstory': 'QA specialist with expertise in testing and quality assurance'
                    }
                }
            ],
            'tasks': [
                {
                    'description': 'Create comprehensive project plan with timeline and milestones',
                    'agent_index': 1,  # Planner
                    'expected_output': 'Detailed project plan with timelines'
                },
                {
                    'description': 'Implement core features according to specifications',
                    'agent_index': 2,  # Executor
                    'expected_output': 'Working implementation of core features'
                },
                {
                    'description': 'Conduct thorough testing and quality review',
                    'agent_index': 3,  # Specialist
                    'expected_output': 'Quality assurance report with recommendations'
                }
            ]
        }
        
        # Content Creation Crew
        crews['content_creation'] = {
            'agents': [
                {
                    'agent_id': 'agent_base',
                    'role_config': {
                        'role': 'Content Director',
                        'goal': 'Oversee content strategy and execution',
                        'backstory': 'Experienced content strategist with marketing expertise'
                    }
                },
                {
                    'agent_id': 'agent_03_planner',
                    'role_config': {
                        'role': 'Content Strategist',
                        'goal': 'Plan content calendar and strategy',
                        'backstory': 'Strategic content planner with audience insight expertise'
                    }
                },
                {
                    'agent_id': 'agent_05_designer',
                    'role_config': {
                        'role': 'Creative Designer',
                        'goal': 'Create visual content and design assets',
                        'backstory': 'Creative designer specialized in digital content and visual storytelling'
                    }
                }
            ],
            'tasks': [
                {
                    'description': 'Develop content strategy and editorial calendar',
                    'agent_index': 1,
                    'expected_output': 'Content strategy document with calendar'
                },
                {
                    'description': 'Create visual assets and design elements',
                    'agent_index': 2,
                    'expected_output': 'Visual content package with design assets'
                }
            ]
        }
        
        # Data Analysis Crew
        crews['data_analysis'] = {
            'agents': [
                {
                    'agent_id': 'agent_base',
                    'role_config': {
                        'role': 'Research Director',
                        'goal': 'Guide analysis strategy and ensure insights quality',
                        'backstory': 'Senior researcher with expertise in data-driven decision making'
                    }
                },
                {
                    'agent_id': 'agent_06_specialist',
                    'role_config': {
                        'role': 'Data Scientist',
                        'goal': 'Conduct advanced data analysis and modeling',
                        'backstory': 'Data scientist with expertise in statistical analysis and machine learning'
                    }
                },
                {
                    'agent_id': 'agent_04_executor',
                    'role_config': {
                        'role': 'Data Engineer',
                        'goal': 'Process data and implement analysis pipelines',
                        'backstory': 'Data engineer skilled in data processing and pipeline development'
                    }
                },
                {
                    'agent_id': 'output_handler',
                    'role_config': {
                        'role': 'Report Writer',
                        'goal': 'Create comprehensive analysis reports',
                        'backstory': 'Technical writer specialized in data analysis reporting'
                    }
                }
            ],
            'tasks': [
                {
                    'description': 'Analyze data patterns and extract insights',
                    'agent_index': 1,
                    'expected_output': 'Statistical analysis with key findings'
                },
                {
                    'description': 'Process and clean data for analysis',
                    'agent_index': 2,
                    'expected_output': 'Clean, processed dataset ready for analysis'
                },
                {
                    'description': 'Create comprehensive analysis report',
                    'agent_index': 3,
                    'expected_output': 'Professional analysis report with visualizations'
                }
            ]
        }
        
        return crews
    
    def execute_crew_mission(self, crew_name: str, mission_description: str) -> Dict[str, Any]:
        """Execute a specialized crew mission"""
        
        crews = self.create_specialized_crews()
        
        if crew_name not in crews:
            raise ValueError(f"Crew '{crew_name}' not found")
        
        crew_config = crews[crew_name]
        
        # Update task descriptions with mission context
        for task in crew_config['tasks']:
            task['description'] = f"{mission_description}: {task['description']}"
        
        # Create and execute crew
        crew = self.create_crew(crew_config)
        
        try:
            start_time = datetime.now()
            result = crew.kickoff()
            end_time = datetime.now()
            
            return {
                'status': 'completed',
                'crew_name': crew_name,
                'mission': mission_description,
                'result': result,
                'duration': (end_time - start_time).total_seconds(),
                'started_at': start_time.isoformat(),
                'completed_at': end_time.isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'failed',
                'crew_name': crew_name,
                'mission': mission_description,
                'error': str(e),
                'failed_at': datetime.now().isoformat()
            }
    
    def create_custom_tool(self, tool_name: str, agent_id: str) -> BaseTool:
        """Create a custom tool that wraps an Agentic AI agent"""
        
        original_agent = self.agent_manager.get_agent(agent_id)
        if not original_agent:
            raise ValueError(f"Agent '{agent_id}' not found")
        
        class AgenticTool(BaseTool):
            name: str = tool_name
            description: str = f"Tool that uses {original_agent.name} capabilities"
            
            def _run(self, query: str) -> str:
                """Execute the tool"""
                task = {
                    'task_id': f'tool_{agent_id}_{int(datetime.now().timestamp())}',
                    'request': query,
                    'context': {
                        'integration': 'crewai_tool',
                        'tool_name': tool_name,
                        'timestamp': datetime.now().isoformat()
                    }
                }
                
                try:
                    result = original_agent.process_task(task)
                    return result.get('content', str(result))
                except Exception as e:
                    return f"Tool execution error: {str(e)}"
        
        return AgenticTool()
    
    def get_crew_status(self, crew_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific crew"""
        return self.crews.get(crew_id)
    
    def list_available_crews(self) -> List[str]:
        """List all available crew templates"""
        return list(self.create_specialized_crews().keys())
    
    def create_hierarchical_crew(self, hierarchy_config: Dict[str, Any]) -> Crew:
        """Create a crew with hierarchical structure"""
        
        # Create manager agent
        manager_config = hierarchy_config.get('manager', {})
        manager_id = manager_config.get('agent_id', 'agent_base')
        
        if manager_id not in self.crewai_agents:
            self.create_crewai_agent(manager_id, {
                'role': 'Team Manager',
                'goal': 'Coordinate team efforts and ensure project success',
                'backstory': 'Experienced manager with team coordination expertise',
                'allow_delegation': True
            })
        
        manager = self.crewai_agents[manager_id]
        
        # Create worker agents
        workers = []
        for worker_config in hierarchy_config.get('workers', []):
            worker_id = worker_config['agent_id']
            
            if worker_id not in self.crewai_agents:
                self.create_crewai_agent(worker_id, worker_config.get('role_config', {}))
            
            workers.append(self.crewai_agents[worker_id])
        
        # Create hierarchical tasks
        tasks = []
        
        # Manager task
        manager_task = Task(
            description=hierarchy_config.get('manager_task', 'Coordinate team and ensure project completion'),
            agent=manager,
            expected_output='Project coordination and final deliverable'
        )
        tasks.append(manager_task)
        
        # Worker tasks
        for i, worker_task_config in enumerate(hierarchy_config.get('worker_tasks', [])):
            worker_task = Task(
                description=worker_task_config.get('description', f'Complete specialized task {i+1}'),
                agent=workers[i % len(workers)],
                expected_output=worker_task_config.get('expected_output', 'Task completion')
            )
            tasks.append(worker_task)
        
        # Create crew with hierarchical process
        crew = Crew(
            agents=[manager] + workers,
            tasks=tasks,
            process=Process.hierarchical,
            manager_llm=None,  # Use default LLM
            verbose=hierarchy_config.get('verbose', True)
        )
        
        return crew

# Example usage and testing utilities
class CrewAIWorkflowBuilder:
    """Helper class for building complex CrewAI workflows"""
    
    def __init__(self, adapter: CrewAIAdapter):
        self.adapter = adapter
        
    def build_agile_development_crew(self, project_description: str) -> Crew:
        """Build an agile development crew"""
        
        crew_config = {
            'agents': [
                {
                    'agent_id': 'agent_base',
                    'role_config': {
                        'role': 'Scrum Master',
                        'goal': 'Facilitate agile development process',
                        'backstory': 'Certified Scrum Master with agile methodology expertise'
                    }
                },
                {
                    'agent_id': 'agent_03_planner',
                    'role_config': {
                        'role': 'Product Owner',
                        'goal': 'Define requirements and prioritize backlog',
                        'backstory': 'Product owner with user story creation expertise'
                    }
                },
                {
                    'agent_id': 'agent_04_executor',
                    'role_config': {
                        'role': 'Development Team',
                        'goal': 'Implement features in iterative sprints',
                        'backstory': 'Cross-functional development team'
                    }
                }
            ],
            'tasks': [
                {
                    'description': f'Create product backlog for: {project_description}',
                    'agent_index': 1,
                    'expected_output': 'Prioritized product backlog with user stories'
                },
                {
                    'description': 'Plan and execute development sprint',
                    'agent_index': 2,
                    'expected_output': 'Working software increment'
                }
            ]
        }
        
        return self.adapter.create_crew(crew_config)
    
    def build_research_crew(self, research_topic: str) -> Crew:
        """Build a research crew for comprehensive analysis"""
        
        crew_config = {
            'agents': [
                {
                    'agent_id': 'agent_06_specialist',
                    'role_config': {
                        'role': 'Research Lead',
                        'goal': 'Guide research methodology and analysis',
                        'backstory': 'Senior researcher with academic and industry experience'
                    }
                },
                {
                    'agent_id': 'agent_04_executor',
                    'role_config': {
                        'role': 'Data Collector',
                        'goal': 'Gather and process research data',
                        'backstory': 'Research assistant specialized in data collection'
                    }
                },
                {
                    'agent_id': 'output_handler',
                    'role_config': {
                        'role': 'Research Writer',
                        'goal': 'Synthesize findings into comprehensive report',
                        'backstory': 'Academic writer with research publication experience'
                    }
                }
            ],
            'tasks': [
                {
                    'description': f'Collect comprehensive data on: {research_topic}',
                    'agent_index': 1,
                    'expected_output': 'Structured research dataset'
                },
                {
                    'description': f'Analyze findings and create research report on: {research_topic}',
                    'agent_index': 2,
                    'expected_output': 'Academic-quality research report'
                }
            ]
        }
        
        return self.adapter.create_crew(crew_config)

# Testing utilities
class CrewAITester:
    """Testing utilities for CrewAI integration"""
    
    def __init__(self, adapter: CrewAIAdapter):
        self.adapter = adapter
        
    def test_crew_performance(self, crew_name: str, test_missions: List[str]) -> Dict[str, Any]:
        """Test crew performance with multiple missions"""
        
        results = []
        
        for i, mission in enumerate(test_missions):
            print(f"Testing mission {i+1}/{len(test_missions)}: {mission[:50]}...")
            
            result = self.adapter.execute_crew_mission(crew_name, mission)
            results.append(result)
        
        success_rate = sum(1 for r in results if r['status'] == 'completed') / len(results)
        avg_duration = sum(r.get('duration', 0) for r in results if r['status'] == 'completed') / len(results)
        
        return {
            'crew_name': crew_name,
            'total_tests': len(test_missions),
            'successful_tests': sum(1 for r in results if r['status'] == 'completed'),
            'success_rate': success_rate,
            'average_duration': avg_duration,
            'detailed_results': results
        }
    
    def test_agent_collaboration(self, agent_ids: List[str], collaboration_task: str) -> Dict[str, Any]:
        """Test collaboration between specific agents"""
        
        crew_config = {
            'agents': [{'agent_id': agent_id} for agent_id in agent_ids],
            'tasks': [
                {
                    'description': collaboration_task,
                    'agent_index': 0,
                    'expected_output': 'Collaborative task completion'
                }
            ]
        }
        
        crew = self.adapter.create_crew(crew_config)
        
        try:
            start_time = datetime.now()
            result = crew.kickoff()
            end_time = datetime.now()
            
            return {
                'status': 'success',
                'agents': agent_ids,
                'task': collaboration_task,
                'result': result,
                'duration': (end_time - start_time).total_seconds(),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'failed',
                'agents': agent_ids,
                'task': collaboration_task,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
