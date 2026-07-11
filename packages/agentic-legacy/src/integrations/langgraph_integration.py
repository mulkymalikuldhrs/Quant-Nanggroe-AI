"""
LangGraph Integration for Agentic AI System
Provides seamless integration with LangGraph framework
"""

from typing import Dict, List, Any, Optional
import asyncio
from datetime import datetime

try:
    from langgraph.graph import Graph, START, END
    from langgraph.prebuilt import ToolExecutor
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    Graph = None
    START = None
    END = None

from ..core.agent_manager import AgentManager

class LangGraphAdapter:
    """Adapter for integrating Agentic AI System with LangGraph"""
    
    def __init__(self, agent_manager: AgentManager):
        if not LANGGRAPH_AVAILABLE:
            raise ImportError("LangGraph is not installed. Install with: pip install langgraph")
        
        self.agent_manager = agent_manager
        self.workflows = {}
        
    def create_workflow_graph(self, workflow_config: Dict[str, Any]) -> Graph:
        """Create a LangGraph workflow from agent configuration"""
        
        workflow = Graph()
        
        # Add nodes for each agent
        for agent_id in workflow_config.get('nodes', []):
            agent = self.agent_manager.get_agent(agent_id)
            if agent:
                workflow.add_node(agent_id, self._create_agent_node(agent))
        
        # Add edges based on configuration
        for edge in workflow_config.get('edges', []):
            if len(edge) == 2:
                from_node, to_node = edge
                workflow.add_edge(from_node, to_node)
        
        # Add start and end connections
        start_nodes = workflow_config.get('start_nodes', ['agent_base'])
        end_nodes = workflow_config.get('end_nodes', ['output_handler'])
        
        for start_node in start_nodes:
            workflow.add_edge(START, start_node)
        
        for end_node in end_nodes:
            workflow.add_edge(end_node, END)
        
        # Compile the workflow
        compiled_workflow = workflow.compile()
        
        # Store for later reference
        workflow_id = f"langgraph_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.workflows[workflow_id] = compiled_workflow
        
        return compiled_workflow
    
    def _create_agent_node(self, agent):
        """Create a LangGraph node from an Agentic AI agent"""
        
        async def agent_node(state: Dict[str, Any]) -> Dict[str, Any]:
            """Node function that wraps agent execution"""
            
            # Prepare task for agent
            task = {
                'task_id': state.get('task_id', f'langgraph_{int(datetime.now().timestamp())}'),
                'request': state.get('input', state.get('messages', [''])[-1] if state.get('messages') else ''),
                'context': {
                    'workflow_type': 'langgraph',
                    'state': state,
                    'timestamp': datetime.now().isoformat()
                }
            }
            
            # Execute agent task
            try:
                result = agent.process_task(task)
                
                # Update state with agent result
                state['last_agent'] = agent.agent_id
                state['last_result'] = result
                
                # Add to messages if they exist
                if 'messages' in state:
                    state['messages'].append({
                        'role': agent.agent_id,
                        'content': result.get('content', str(result))
                    })
                else:
                    state['output'] = result.get('content', str(result))
                
                return state
                
            except Exception as e:
                state['error'] = str(e)
                state['failed_agent'] = agent.agent_id
                return state
        
        return agent_node
    
    def create_standard_workflows(self) -> Dict[str, Any]:
        """Create standard workflow templates for LangGraph"""
        
        workflows = {}
        
        # Standard multi-agent workflow
        workflows['standard_process'] = {
            'nodes': ['agent_base', 'agent_03_planner', 'agent_04_executor', 'output_handler'],
            'edges': [
                ('agent_base', 'agent_03_planner'),
                ('agent_03_planner', 'agent_04_executor'),
                ('agent_04_executor', 'output_handler')
            ],
            'start_nodes': ['agent_base'],
            'end_nodes': ['output_handler']
        }
        
        # Design workflow
        workflows['design_process'] = {
            'nodes': ['agent_base', 'agent_03_planner', 'agent_05_designer', 'agent_06_specialist', 'output_handler'],
            'edges': [
                ('agent_base', 'agent_03_planner'),
                ('agent_03_planner', 'agent_05_designer'),
                ('agent_05_designer', 'agent_06_specialist'),
                ('agent_06_specialist', 'output_handler')
            ],
            'start_nodes': ['agent_base'],
            'end_nodes': ['output_handler']
        }
        
        # Analysis workflow
        workflows['analysis_process'] = {
            'nodes': ['agent_base', 'agent_06_specialist', 'agent_04_executor', 'output_handler'],
            'edges': [
                ('agent_base', 'agent_06_specialist'),
                ('agent_06_specialist', 'agent_04_executor'),
                ('agent_04_executor', 'output_handler')
            ],
            'start_nodes': ['agent_base'],
            'end_nodes': ['output_handler']
        }
        
        return workflows
    
    async def execute_workflow(self, workflow_name: str, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a named workflow with input data"""
        
        workflows = self.create_standard_workflows()
        
        if workflow_name not in workflows:
            raise ValueError(f"Workflow '{workflow_name}' not found")
        
        # Create workflow graph
        workflow_graph = self.create_workflow_graph(workflows[workflow_name])
        
        # Prepare initial state
        initial_state = {
            'task_id': f'langgraph_{workflow_name}_{int(datetime.now().timestamp())}',
            'input': input_data.get('input', input_data.get('request', '')),
            'workflow_name': workflow_name,
            'started_at': datetime.now().isoformat(),
            'messages': []
        }
        
        # Execute workflow
        try:
            result = await workflow_graph.ainvoke(initial_state)
            
            return {
                'status': 'completed',
                'workflow_name': workflow_name,
                'result': result,
                'completed_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'failed',
                'workflow_name': workflow_name,
                'error': str(e),
                'failed_at': datetime.now().isoformat()
            }
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific workflow"""
        
        if workflow_id in self.workflows:
            return {
                'workflow_id': workflow_id,
                'status': 'available',
                'created_at': datetime.now().isoformat()
            }
        
        return None
    
    def list_available_workflows(self) -> List[str]:
        """List all available workflow templates"""
        return list(self.create_standard_workflows().keys())

# Example usage and helper functions
class LangGraphWorkflowBuilder:
    """Helper class for building complex LangGraph workflows"""
    
    def __init__(self, adapter: LangGraphAdapter):
        self.adapter = adapter
        
    def build_conditional_workflow(self, conditions: Dict[str, Any]) -> Graph:
        """Build a workflow with conditional logic"""
        
        workflow = Graph()
        
        # Add decision node
        def decision_node(state: Dict[str, Any]) -> str:
            # Simple decision logic based on input
            input_text = state.get('input', '').lower()
            
            if any(word in input_text for word in ['design', 'visual', 'ui']):
                return 'design_path'
            elif any(word in input_text for word in ['analyze', 'data', 'report']):
                return 'analysis_path'
            else:
                return 'standard_path'
        
        workflow.add_node('decision', decision_node)
        
        # Add conditional edges
        workflow.add_conditional_edges(
            'decision',
            decision_node,
            {
                'design_path': 'agent_05_designer',
                'analysis_path': 'agent_06_specialist',
                'standard_path': 'agent_04_executor'
            }
        )
        
        return workflow
    
    def build_parallel_workflow(self, parallel_agents: List[str]) -> Graph:
        """Build a workflow with parallel agent execution"""
        
        workflow = Graph()
        
        # Add parallel nodes
        for agent_id in parallel_agents:
            agent = self.adapter.agent_manager.get_agent(agent_id)
            if agent:
                workflow.add_node(agent_id, self.adapter._create_agent_node(agent))
        
        # Add aggregation node
        def aggregate_results(state: Dict[str, Any]) -> Dict[str, Any]:
            # Combine results from parallel agents
            results = []
            for agent_id in parallel_agents:
                if f'{agent_id}_result' in state:
                    results.append(state[f'{agent_id}_result'])
            
            state['aggregated_results'] = results
            return state
        
        workflow.add_node('aggregator', aggregate_results)
        
        # Connect all parallel agents to aggregator
        for agent_id in parallel_agents:
            workflow.add_edge(agent_id, 'aggregator')
        
        return workflow

# Integration testing utilities
class LangGraphTester:
    """Testing utilities for LangGraph integration"""
    
    def __init__(self, adapter: LangGraphAdapter):
        self.adapter = adapter
        
    async def test_workflow(self, workflow_name: str, test_inputs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test a workflow with multiple inputs"""
        
        results = []
        
        for i, input_data in enumerate(test_inputs):
            print(f"Testing input {i+1}/{len(test_inputs)}")
            
            result = await self.adapter.execute_workflow(workflow_name, input_data)
            results.append({
                'input': input_data,
                'result': result,
                'success': result['status'] == 'completed'
            })
        
        success_rate = sum(1 for r in results if r['success']) / len(results)
        
        return {
            'workflow_name': workflow_name,
            'total_tests': len(test_inputs),
            'successful_tests': sum(1 for r in results if r['success']),
            'success_rate': success_rate,
            'detailed_results': results
        }
