"""
Agent 02 (Meta-Spawner) - Performance Monitor & Bottleneck Analysis
"""

from typing import Dict, List, Any, Optional
import json
import time
from datetime import datetime, timedelta
from collections import defaultdict

from ..core.base_agent import BaseAgent

class Agent02MetaSpawner(BaseAgent):
    """Performance monitor and bottleneck analyzer"""
    
    def __init__(self, config_path: str = "config/prompts.yaml"):
        super().__init__("agent_02_meta_spawner", config_path)
        self.performance_history = []
        self.bottleneck_reports = []
        self.monitoring_config = {
            'response_time_threshold': 30.0,  # seconds
            'error_rate_threshold': 0.1,      # 10%
            'queue_length_threshold': 5,
            'resource_usage_threshold': 0.8   # 80%
        }
        self.last_analysis_time = datetime.now()
        
    def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor system performance and identify bottlenecks"""
        
        if not self.validate_input(task):
            return self.handle_error(
                Exception("Invalid task format"), task
            )
        
        try:
            self.update_status("monitoring", task)
            
            # Collect current system metrics
            system_metrics = self._collect_system_metrics(task)
            
            # Analyze performance trends
            performance_analysis = self._analyze_performance_trends()
            
            # Detect bottlenecks
            bottlenecks = self._detect_bottlenecks(system_metrics)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(bottlenecks, performance_analysis)
            
            # Generate optimization actions
            actions = self._generate_optimization_actions(bottlenecks)
            
            self.update_status("ready")
            
            # Prepare response
            response_content = f"""
📊 SYSTEM HEALTH: {self._get_overall_health_status(system_metrics)}

🔍 BOTTLENECKS:
{self._format_bottlenecks(bottlenecks)}

📈 METRICS:
{self._format_metrics(system_metrics)}

🛠️ RECOMMENDATIONS:
{self._format_recommendations(recommendations)}

⚡ ACTIONS:
{self._format_actions(actions)}
            """
            
            # Log the analysis
            self._log_analysis(system_metrics, bottlenecks, recommendations)
            
            return self.format_response(response_content.strip(), "performance_analysis")
            
        except Exception as e:
            return self.handle_error(e, task)
    
    def _collect_system_metrics(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Collect current system performance metrics"""
        context = task.get('context', {})
        
        # In a real implementation, this would collect actual metrics
        # For now, we'll simulate based on available context
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'agents': self._collect_agent_metrics(context),
            'workflows': self._collect_workflow_metrics(context),
            'resources': self._collect_resource_metrics(context),
            'communication': self._collect_communication_metrics(context)
        }
        
        # Store metrics for trend analysis
        self.performance_history.append(metrics)
        
        # Keep only recent history (last 24 hours worth)
        cutoff_time = datetime.now() - timedelta(hours=24)
        self.performance_history = [
            m for m in self.performance_history 
            if datetime.fromisoformat(m['timestamp']) > cutoff_time
        ]
        
        return metrics
    
    def _collect_agent_metrics(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Collect metrics for individual agents"""
        # Simulated agent metrics - in production, get from actual agents
        agent_metrics = {}
        
        # Common agents to monitor
        agent_ids = [
            'agent_base', 'agent_03_planner', 'agent_04_executor',
            'agent_05_designer', 'agent_06_specialist', 'output_handler'
        ]
        
        for agent_id in agent_ids:
            agent_metrics[agent_id] = {
                'status': 'active',
                'avg_response_time': self._simulate_response_time(agent_id),
                'task_count': self._simulate_task_count(agent_id),
                'success_rate': self._simulate_success_rate(agent_id),
                'error_count': self._simulate_error_count(agent_id),
                'resource_usage': self._simulate_resource_usage(agent_id)
            }
        
        return agent_metrics
    
    def _collect_workflow_metrics(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Collect workflow performance metrics"""
        return {
            'active_workflows': context.get('active_workflows', 0),
            'completed_workflows': context.get('completed_workflows', 0),
            'failed_workflows': context.get('failed_workflows', 0),
            'avg_workflow_duration': context.get('avg_workflow_duration', 45.0),
            'queue_length': context.get('queue_length', 2)
        }
    
    def _collect_resource_metrics(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Collect system resource metrics"""
        # Simulated resource metrics
        return {
            'cpu_usage': 0.45,
            'memory_usage': 0.62,
            'disk_usage': 0.33,
            'network_latency': 15.2,
            'concurrent_tasks': 8
        }
    
    def _collect_communication_metrics(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Collect inter-agent communication metrics"""
        return {
            'total_messages': context.get('total_messages', 156),
            'avg_message_delay': context.get('avg_message_delay', 1.2),
            'failed_communications': context.get('failed_communications', 0),
            'communication_rate': context.get('communication_rate', 23.5)
        }
    
    def _simulate_response_time(self, agent_id: str) -> float:
        """Simulate response time for agent (in production, get actual data)"""
        base_times = {
            'agent_base': 2.5,
            'agent_03_planner': 8.2,
            'agent_04_executor': 15.7,
            'agent_05_designer': 45.3,
            'agent_06_specialist': 12.1,
            'output_handler': 5.8
        }
        return base_times.get(agent_id, 10.0)
    
    def _simulate_task_count(self, agent_id: str) -> int:
        """Simulate task count for agent"""
        base_counts = {
            'agent_base': 25,
            'agent_03_planner': 12,
            'agent_04_executor': 18,
            'agent_05_designer': 8,
            'agent_06_specialist': 15,
            'output_handler': 20
        }
        return base_counts.get(agent_id, 10)
    
    def _simulate_success_rate(self, agent_id: str) -> float:
        """Simulate success rate for agent"""
        base_rates = {
            'agent_base': 0.98,
            'agent_03_planner': 0.95,
            'agent_04_executor': 0.88,
            'agent_05_designer': 0.92,
            'agent_06_specialist': 0.96,
            'output_handler': 0.99
        }
        return base_rates.get(agent_id, 0.95)
    
    def _simulate_error_count(self, agent_id: str) -> int:
        """Simulate error count for agent"""
        error_counts = {
            'agent_base': 0,
            'agent_03_planner': 1,
            'agent_04_executor': 3,
            'agent_05_designer': 2,
            'agent_06_specialist': 1,
            'output_handler': 0
        }
        return error_counts.get(agent_id, 1)
    
    def _simulate_resource_usage(self, agent_id: str) -> float:
        """Simulate resource usage for agent"""
        resource_usage = {
            'agent_base': 0.25,
            'agent_03_planner': 0.35,
            'agent_04_executor': 0.75,
            'agent_05_designer': 0.85,
            'agent_06_specialist': 0.45,
            'output_handler': 0.30
        }
        return resource_usage.get(agent_id, 0.50)
    
    def _analyze_performance_trends(self) -> Dict[str, Any]:
        """Analyze performance trends over time"""
        if len(self.performance_history) < 2:
            return {'trend': 'insufficient_data', 'analysis': 'Need more data points for trend analysis'}
        
        # Calculate trends (simplified)
        recent_metrics = self.performance_history[-5:] if len(self.performance_history) >= 5 else self.performance_history
        
        # Analyze response time trends
        response_times = []
        for metric in recent_metrics:
            avg_response = sum(
                agent['avg_response_time'] 
                for agent in metric['agents'].values()
            ) / len(metric['agents'])
            response_times.append(avg_response)
        
        trend = 'stable'
        if len(response_times) >= 2:
            if response_times[-1] > response_times[0] * 1.2:
                trend = 'degrading'
            elif response_times[-1] < response_times[0] * 0.8:
                trend = 'improving'
        
        return {
            'trend': trend,
            'avg_response_time': sum(response_times) / len(response_times),
            'analysis': self._generate_trend_analysis(trend, response_times)
        }
    
    def _generate_trend_analysis(self, trend: str, response_times: List[float]) -> str:
        """Generate human-readable trend analysis"""
        if trend == 'degrading':
            return f"Performance is degrading. Response time increased from {response_times[0]:.1f}s to {response_times[-1]:.1f}s"
        elif trend == 'improving':
            return f"Performance is improving. Response time decreased from {response_times[0]:.1f}s to {response_times[-1]:.1f}s"
        else:
            return f"Performance is stable. Average response time: {sum(response_times)/len(response_times):.1f}s"
    
    def _detect_bottlenecks(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect system bottlenecks"""
        bottlenecks = []
        
        # Check agent response times
        for agent_id, agent_metrics in metrics['agents'].items():
            if agent_metrics['avg_response_time'] > self.monitoring_config['response_time_threshold']:
                bottlenecks.append({
                    'type': 'slow_agent',
                    'agent_id': agent_id,
                    'severity': 'high',
                    'metric': 'response_time',
                    'value': agent_metrics['avg_response_time'],
                    'threshold': self.monitoring_config['response_time_threshold'],
                    'description': f"Agent {agent_id} response time ({agent_metrics['avg_response_time']:.1f}s) exceeds threshold"
                })
        
        # Check error rates
        for agent_id, agent_metrics in metrics['agents'].items():
            if agent_metrics['success_rate'] < (1 - self.monitoring_config['error_rate_threshold']):
                bottlenecks.append({
                    'type': 'high_error_rate',
                    'agent_id': agent_id,
                    'severity': 'medium',
                    'metric': 'error_rate',
                    'value': 1 - agent_metrics['success_rate'],
                    'threshold': self.monitoring_config['error_rate_threshold'],
                    'description': f"Agent {agent_id} error rate ({(1-agent_metrics['success_rate'])*100:.1f}%) exceeds threshold"
                })
        
        # Check resource usage
        for agent_id, agent_metrics in metrics['agents'].items():
            if agent_metrics['resource_usage'] > self.monitoring_config['resource_usage_threshold']:
                bottlenecks.append({
                    'type': 'high_resource_usage',
                    'agent_id': agent_id,
                    'severity': 'medium',
                    'metric': 'resource_usage',
                    'value': agent_metrics['resource_usage'],
                    'threshold': self.monitoring_config['resource_usage_threshold'],
                    'description': f"Agent {agent_id} resource usage ({agent_metrics['resource_usage']*100:.1f}%) exceeds threshold"
                })
        
        # Check workflow queue
        if metrics['workflows']['queue_length'] > self.monitoring_config['queue_length_threshold']:
            bottlenecks.append({
                'type': 'queue_backup',
                'severity': 'high',
                'metric': 'queue_length',
                'value': metrics['workflows']['queue_length'],
                'threshold': self.monitoring_config['queue_length_threshold'],
                'description': f"Workflow queue length ({metrics['workflows']['queue_length']}) exceeds threshold"
            })
        
        return bottlenecks
    
    def _generate_recommendations(self, bottlenecks: List[Dict[str, Any]], 
                                performance_analysis: Dict[str, Any]) -> List[str]:
        """Generate optimization recommendations"""
        recommendations = []
        
        # Recommendations based on bottlenecks
        for bottleneck in bottlenecks:
            if bottleneck['type'] == 'slow_agent':
                recommendations.append(
                    f"Consider scaling {bottleneck['agent_id']} or optimizing its processing logic"
                )
            elif bottleneck['type'] == 'high_error_rate':
                recommendations.append(
                    f"Investigate error causes in {bottleneck['agent_id']} and improve error handling"
                )
            elif bottleneck['type'] == 'high_resource_usage':
                recommendations.append(
                    f"Optimize resource consumption in {bottleneck['agent_id']} or allocate more resources"
                )
            elif bottleneck['type'] == 'queue_backup':
                recommendations.append(
                    "Add more worker agents or optimize task distribution to reduce queue length"
                )
        
        # Recommendations based on trends
        if performance_analysis['trend'] == 'degrading':
            recommendations.append(
                "Performance is declining - consider system-wide optimization or scaling"
            )
        
        # General recommendations
        if not bottlenecks:
            recommendations.append("System is performing well - continue monitoring")
        
        return recommendations
    
    def _generate_optimization_actions(self, bottlenecks: List[Dict[str, Any]]) -> List[str]:
        """Generate immediate optimization actions"""
        actions = []
        
        high_severity_bottlenecks = [b for b in bottlenecks if b['severity'] == 'high']
        
        if high_severity_bottlenecks:
            actions.append("URGENT: Address high-severity bottlenecks immediately")
            for bottleneck in high_severity_bottlenecks:
                if bottleneck['type'] == 'slow_agent':
                    actions.append(f"→ Scale or restart {bottleneck['agent_id']}")
                elif bottleneck['type'] == 'queue_backup':
                    actions.append("→ Add temporary worker agents to clear queue")
        
        medium_severity_bottlenecks = [b for b in bottlenecks if b['severity'] == 'medium']
        if medium_severity_bottlenecks:
            actions.append("Schedule optimization for medium-priority issues")
        
        if not bottlenecks:
            actions.append("No immediate actions required - system is healthy")
        
        return actions
    
    def _get_overall_health_status(self, metrics: Dict[str, Any]) -> str:
        """Get overall system health status"""
        # Simple health scoring
        health_score = 100
        
        for agent_metrics in metrics['agents'].values():
            if agent_metrics['avg_response_time'] > self.monitoring_config['response_time_threshold']:
                health_score -= 20
            if agent_metrics['success_rate'] < 0.9:
                health_score -= 15
            if agent_metrics['resource_usage'] > self.monitoring_config['resource_usage_threshold']:
                health_score -= 10
        
        if metrics['workflows']['queue_length'] > self.monitoring_config['queue_length_threshold']:
            health_score -= 25
        
        if health_score >= 90:
            return "🟢 EXCELLENT (System performing optimally)"
        elif health_score >= 70:
            return "🟡 GOOD (Minor issues detected)"
        elif health_score >= 50:
            return "🟠 DEGRADED (Performance issues need attention)"
        else:
            return "🔴 CRITICAL (Immediate action required)"
    
    def _format_bottlenecks(self, bottlenecks: List[Dict[str, Any]]) -> str:
        """Format bottlenecks for display"""
        if not bottlenecks:
            return "✅ No bottlenecks detected"
        
        formatted = ""
        for bottleneck in bottlenecks:
            severity_emoji = "🔴" if bottleneck['severity'] == 'high' else "🟡"
            formatted += f"{severity_emoji} {bottleneck['description']}\n"
        
        return formatted
    
    def _format_metrics(self, metrics: Dict[str, Any]) -> str:
        """Format metrics for display"""
        formatted = ""
        
        # Agent metrics summary
        formatted += "Agent Performance:\n"
        for agent_id, agent_metrics in metrics['agents'].items():
            formatted += f"• {agent_id}: {agent_metrics['avg_response_time']:.1f}s avg, "
            formatted += f"{agent_metrics['success_rate']*100:.1f}% success\n"
        
        formatted += f"\nWorkflows: {metrics['workflows']['active_workflows']} active, "
        formatted += f"{metrics['workflows']['queue_length']} queued\n"
        
        formatted += f"Resources: CPU {metrics['resources']['cpu_usage']*100:.1f}%, "
        formatted += f"Memory {metrics['resources']['memory_usage']*100:.1f}%\n"
        
        return formatted
    
    def _format_recommendations(self, recommendations: List[str]) -> str:
        """Format recommendations for display"""
        if not recommendations:
            return "No specific recommendations at this time"
        
        return "\n".join(f"• {rec}" for rec in recommendations)
    
    def _format_actions(self, actions: List[str]) -> str:
        """Format actions for display"""
        if not actions:
            return "No immediate actions required"
        
        return "\n".join(f"• {action}" for action in actions)
    
    def _log_analysis(self, metrics: Dict[str, Any], bottlenecks: List[Dict[str, Any]], 
                     recommendations: List[str]):
        """Log analysis for historical tracking"""
        analysis_log = {
            'timestamp': datetime.now().isoformat(),
            'metrics_summary': {
                'total_agents': len(metrics['agents']),
                'avg_response_time': sum(a['avg_response_time'] for a in metrics['agents'].values()) / len(metrics['agents']),
                'avg_success_rate': sum(a['success_rate'] for a in metrics['agents'].values()) / len(metrics['agents'])
            },
            'bottlenecks_count': len(bottlenecks),
            'recommendations_count': len(recommendations),
            'bottlenecks': bottlenecks,
            'recommendations': recommendations
        }
        
        self.bottleneck_reports.append(analysis_log)
        
        # Keep only recent reports
        if len(self.bottleneck_reports) > 100:
            self.bottleneck_reports = self.bottleneck_reports[-50:]
