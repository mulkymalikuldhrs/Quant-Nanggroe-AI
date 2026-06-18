"""
Test Suite for Agentic AI System Agents
Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, patch

from src.core.agent_manager import AgentManager
from src.agents.agent_base import AgentBase
from src.agents.dynamic_agent_factory import DynamicAgentFactory
from src.agents.agent_02_meta_spawner import Agent02MetaSpawner
from src.agents.agent_03_planner import Agent03Planner
from src.agents.agent_04_executor import Agent04Executor
from src.agents.agent_05_designer import Agent05Designer
from src.agents.agent_06_specialist import Agent06Specialist
from src.agents.output_handler import OutputHandler

class TestAgentBase:
    """Test cases for Agent Base"""
    
    def setup_method(self):
        """Setup test environment"""
        self.agent = AgentBase()
        
    def test_agent_initialization(self):
        """Test agent initialization"""
        assert self.agent.agent_id == "agent_base"
        assert self.agent.name == "Agent Base"
        assert self.agent.status == "initialized"
        
    def test_task_processing(self):
        """Test basic task processing"""
        task = {
            'task_id': 'test_001',
            'request': 'Create a simple project plan',
            'context': {'priority': 'high'}
        }
        
        result = self.agent.process_task(task)
        
        assert result['agent_id'] == 'agent_base'
        assert result['response_type'] == 'coordination_plan'
        assert 'content' in result
        
    def test_invalid_task_handling(self):
        """Test handling of invalid tasks"""
        invalid_task = {'invalid': 'task'}
        
        result = self.agent.process_task(invalid_task)
        
        assert result['response_type'] == 'error'
        assert 'error' in result['content']
        
    def test_performance_metrics(self):
        """Test performance metrics tracking"""
        metrics = self.agent.get_performance_metrics()
        
        assert 'agent_id' in metrics
        assert 'metrics' in metrics
        assert metrics['metrics']['tasks_completed'] == 0

class TestDynamicAgentFactory:
    """Test cases for Dynamic Agent Factory"""
    
    def setup_method(self):
        """Setup test environment"""
        self.factory = DynamicAgentFactory()
        
    def test_agent_creation_assessment(self):
        """Test agent creation needs assessment"""
        task = {
            'task_id': 'test_002',
            'request': 'Create a data science agent for machine learning project',
            'context': {}
        }
        
        result = self.factory.process_task(task)
        
        assert result['agent_id'] == 'dynamic_agent_factory'
        assert result['response_type'] == 'agent_creation'
        assert 'ASSESSMENT' in result['content']
        
    def test_specialization_detection(self):
        """Test specialization detection"""
        assessment = self.factory._analyze_domain_requirements({
            'request': 'Need a data scientist for ML project',
            'context': {}
        })
        
        assert 'data_scientist' in assessment['required_agents']

class TestAgent03Planner:
    """Test cases for Agent 03 (Planner)"""
    
    def setup_method(self):
        """Setup test environment"""
        self.planner = Agent03Planner()
        
    def test_planning_task(self):
        """Test planning functionality"""
        task = {
            'task_id': 'test_003',
            'request': 'Plan a mobile app development project',
            'context': {'deadline': '3 months', 'budget': '$100000'}
        }
        
        result = self.planner.process_task(task)
        
        assert result['response_type'] == 'detailed_plan'
        assert 'GOAL ANALYSIS' in result['content']
        assert 'TASK STRUCTURE' in result['content']
        
    def test_goal_classification(self):
        """Test goal type classification"""
        software_request = "Develop a web application"
        goal_type = self.planner._classify_goal_type(software_request)
        
        assert goal_type == 'software_development'
        
    def test_complexity_assessment(self):
        """Test complexity assessment"""
        complex_request = "Build a complex enterprise system with multiple integrations"
        complexity = self.planner._assess_goal_complexity(complex_request)
        
        assert complexity == 'high'

class TestAgent04Executor:
    """Test cases for Agent 04 (Executor)"""
    
    def setup_method(self):
        """Setup test environment"""
        self.executor = Agent04Executor()
        
    def test_execution_analysis(self):
        """Test execution requirements analysis"""
        task = {
            'task_id': 'test_004',
            'request': 'Execute a Python script to process data',
            'context': {}
        }
        
        result = self.executor.process_task(task)
        
        assert result['response_type'] == 'execution_report'
        assert 'EXECUTION PLAN' in result['content']
        
    def test_script_detection(self):
        """Test script execution detection"""
        script_items = self.executor._detect_script_requirements(
            'run python script', {}
        )
        
        assert len(script_items) > 0
        assert script_items[0]['type'] == 'python_script'

class TestAgent05Designer:
    """Test cases for Agent 05 (Designer)"""
    
    def setup_method(self):
        """Setup test environment"""
        self.designer = Agent05Designer()
        
    def test_design_analysis(self):
        """Test design requirements analysis"""
        task = {
            'task_id': 'test_005',
            'request': 'Create a modern UI design for mobile app',
            'context': {}
        }
        
        result = self.designer.process_task(task)
        
        assert result['response_type'] == 'design_deliverable'
        assert 'DESIGN BRIEF' in result['content']
        
    def test_design_type_classification(self):
        """Test design type classification"""
        ui_request = "Create a user interface design"
        design_type = self.designer._classify_design_type(ui_request)
        
        assert design_type == 'ui_design'

class TestAgent06Specialist:
    """Test cases for Agent 06 (Specialist)"""
    
    def setup_method(self):
        """Setup test environment"""
        self.specialist = Agent06Specialist()
        
    def test_specialist_consultation(self):
        """Test specialist domain consultation"""
        task = {
            'task_id': 'test_006',
            'request': 'Review security aspects of the system',
            'context': {}
        }
        
        result = self.specialist.process_task(task)
        
        assert result['response_type'] == 'specialist_consultation'
        assert 'DOMAIN ANALYSIS' in result['content']
        
    def test_domain_identification(self):
        """Test domain identification"""
        security_request = "Conduct security audit and vulnerability assessment"
        domain = self.specialist._identify_primary_domain(security_request)
        
        assert domain == 'security'

class TestOutputHandler:
    """Test cases for Output Handler"""
    
    def setup_method(self):
        """Setup test environment"""
        self.handler = OutputHandler()
        
    def test_output_compilation(self):
        """Test output compilation"""
        task = {
            'task_id': 'test_007',
            'request': 'Compile results from all agents',
            'context': {
                'planning_completed': True,
                'execution_completed': True
            }
        }
        
        result = self.handler.process_task(task)
        
        assert result['response_type'] == 'final_deliverable'
        assert 'EXECUTIVE SUMMARY' in result['content']
        
    def test_quality_validation(self):
        """Test quality validation"""
        collected_results = {
            'agent_contributions': {
                'planner': {'status': 'completed', 'deliverables': ['plan']},
                'executor': {'status': 'completed', 'deliverables': ['execution']}
            }
        }
        
        validation = self.handler._validate_completeness_quality(collected_results)
        
        assert validation['completion_status'] in ['complete', 'complete_high_quality']

class TestAgentManager:
    """Test cases for Agent Manager"""
    
    def setup_method(self):
        """Setup test environment"""
        self.manager = AgentManager()
        
    def test_agent_registration(self):
        """Test agent registration"""
        agent = AgentBase()
        self.manager.register_agent(agent)
        
        assert len(self.manager.agents) == 1
        assert 'agent_base' in self.manager.agents
        
    def test_agent_retrieval(self):
        """Test agent retrieval"""
        agent = AgentBase()
        self.manager.register_agent(agent)
        
        retrieved_agent = self.manager.get_agent('agent_base')
        
        assert retrieved_agent is not None
        assert retrieved_agent.agent_id == 'agent_base'
        
    def test_system_status(self):
        """Test system status"""
        # Register some agents
        agents = [AgentBase(), Agent03Planner(), Agent04Executor()]
        for agent in agents:
            self.manager.register_agent(agent)
            
        status = self.manager.get_system_status()
        
        assert 'total_agents' in status
        assert status['total_agents'] == 3
        assert 'agent_status' in status

class TestIntegration:
    """Integration tests for multiple agents working together"""
    
    def setup_method(self):
        """Setup test environment"""
        self.manager = AgentManager()
        
        # Register all agents
        self.agents = [
            AgentBase(),
            Agent03Planner(),
            Agent04Executor(),
            Agent05Designer(),
            Agent06Specialist(),
            OutputHandler()
        ]
        
        for agent in self.agents:
            self.manager.register_agent(agent)
            
    def test_multi_agent_workflow(self):
        """Test multi-agent workflow execution"""
        # This would be an async test in practice
        workflow_request = {
            'name': 'Test Workflow',
            'description': 'Integration test workflow'
        }
        
        # Test that we can execute basic workflow steps
        assert len(self.manager.agents) == 6
        
        # Test communication between agents
        for agent in self.agents:
            status = agent.get_performance_metrics()
            assert status['agent_id'] == agent.agent_id
            
    def test_task_delegation(self):
        """Test task delegation between agents"""
        base_agent = self.manager.get_agent('agent_base')
        
        task = {
            'task_id': 'integration_001',
            'request': 'Create a comprehensive project plan and execute it',
            'context': {'integration_test': True}
        }
        
        result = base_agent.process_task(task)
        
        assert result['response_type'] == 'coordination_plan'
        assert 'ASSIGNMENT AGENT' in result['content']

# Performance tests
class TestPerformance:
    """Performance tests for the agent system"""
    
    def test_concurrent_task_processing(self):
        """Test concurrent task processing"""
        import time
        import threading
        
        agent = AgentBase()
        results = []
        
        def process_task(task_id):
            task = {
                'task_id': f'perf_test_{task_id}',
                'request': f'Process task {task_id}',
                'context': {}
            }
            result = agent.process_task(task)
            results.append(result)
        
        # Create multiple threads
        threads = []
        start_time = time.time()
        
        for i in range(10):
            thread = threading.Thread(target=process_task, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        duration = end_time - start_time
        
        assert len(results) == 10
        assert duration < 5.0  # Should complete within 5 seconds
        
    def test_memory_usage(self):
        """Test memory usage during extended operation"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Process many tasks
        agent = AgentBase()
        for i in range(100):
            task = {
                'task_id': f'memory_test_{i}',
                'request': f'Memory test task {i}',
                'context': {}
            }
            agent.process_task(task)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 100MB)
        assert memory_increase < 100 * 1024 * 1024

if __name__ == '__main__':
    pytest.main([__file__])
