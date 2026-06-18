"""
🧠 AI Selector - Intelligent Agent Selection System
Selects best agent for each task using AI analysis

Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime
try:
    import numpy as np
except ImportError:
    np = None

class AISelector:
    """
    Intelligent agent selection system that:
    - Analyzes task requirements
    - Matches agents based on capabilities
    - Considers agent performance history
    - Load balances across agents
    - Self-optimizes selection logic
    """
    
    def __init__(self):
        self.selection_history = []
        self.agent_performance = {}
        self.capability_weights = {
            "shell_execution": 1.0,
            "ui_design": 1.0,
            "backend": 1.0,
            "frontend": 1.0,
            "database": 1.0,
            "deployment": 1.0,
            "ai_development": 1.0,
            "automation": 1.0
        }
    
    def select_best_agent(self, task_type: str, required_capabilities: List[str], 
                         agent_registry: Dict[str, Any], 
                         exclude_agents: List[str] = None) -> str:
        """
        Select the best agent for a given task
        
        Args:
            task_type: Type of task (web_app, mobile_app, automation, etc.)
            required_capabilities: List of required capabilities
            agent_registry: Available agents and their info
            exclude_agents: Agents to exclude from selection
        
        Returns:
            Selected agent ID
        """
        
        exclude_agents = exclude_agents or []
        scores = {}
        
        # Score each agent
        for agent_id, agent_info in agent_registry.items():
            if agent_id in exclude_agents:
                continue
                
            if agent_info.get("status") != "active":
                continue
            
            score = self._calculate_agent_score(
                agent_id, agent_info, task_type, required_capabilities
            )
            scores[agent_id] = score
        
        # Select highest scoring agent
        if not scores:
            return "fullstack_dev"  # Default fallback
        
        best_agent = max(scores, key=scores.get)
        
        # Record selection for learning
        self._record_selection(task_type, required_capabilities, best_agent, scores)
        
        return best_agent
    
    def _calculate_agent_score(self, agent_id: str, agent_info: Dict, 
                              task_type: str, required_capabilities: List[str]) -> float:
        """Calculate score for an agent"""
        
        score = 0.0
        
        # Base priority score
        base_score = agent_info.get("priority", 5) * 10
        score += base_score
        
        # Capability match score
        agent_capabilities = agent_info.get("capabilities", [])
        capability_score = self._calculate_capability_score(
            agent_capabilities, required_capabilities
        )
        score += capability_score * 50
        
        # Performance history score
        performance_score = self._get_performance_score(agent_id)
        score += performance_score * 30
        
        # Load balancing score (prefer less busy agents)
        load_score = self._get_load_balance_score(agent_id)
        score += load_score * 20
        
        # Task type specialization score
        specialization_score = self._get_specialization_score(agent_id, task_type)
        score += specialization_score * 40
        
        return score
    
    def _calculate_capability_score(self, agent_capabilities: List[str], 
                                   required_capabilities: List[str]) -> float:
        """Calculate how well agent capabilities match requirements"""
        
        if not required_capabilities:
            return 0.5  # Neutral score if no specific requirements
        
        matches = 0
        total_weight = 0
        
        for required_cap in required_capabilities:
            weight = self.capability_weights.get(required_cap, 1.0)
            total_weight += weight
            
            # Direct match
            if required_cap in agent_capabilities:
                matches += weight
                continue
            
            # Partial matches using keywords
            for agent_cap in agent_capabilities:
                if self._capabilities_similar(required_cap, agent_cap):
                    matches += weight * 0.7  # Partial match
                    break
        
        return matches / total_weight if total_weight > 0 else 0
    
    def _capabilities_similar(self, cap1: str, cap2: str) -> bool:
        """Check if two capabilities are similar"""
        
        # Define capability similarity mappings
        similarity_map = {
            "ui_design": ["frontend", "react", "design", "css"],
            "backend": ["api", "server", "database"],
            "frontend": ["ui", "react", "vue", "angular", "css"],
            "database": ["sql", "nosql", "storage", "data"],
            "deployment": ["deploy", "docker", "cloud", "devops"],
            "automation": ["script", "cli", "shell", "workflow"]
        }
        
        # Check direct similarity
        for base_cap, similar_caps in similarity_map.items():
            if cap1 == base_cap and any(sim in cap2.lower() for sim in similar_caps):
                return True
            if cap2 == base_cap and any(sim in cap1.lower() for sim in similar_caps):
                return True
        
        return False
    
    def _get_performance_score(self, agent_id: str) -> float:
        """Get performance score based on historical data"""
        
        if agent_id not in self.agent_performance:
            return 0.5  # Neutral score for new agents
        
        perf_data = self.agent_performance[agent_id]
        
        # Calculate weighted performance score
        success_rate = perf_data.get("success_rate", 0.5)
        avg_time = perf_data.get("avg_completion_time", 300)  # seconds
        total_tasks = perf_data.get("total_tasks", 0)
        
        # Higher success rate is better
        score = success_rate
        
        # Faster completion is better (normalize to 0-1)
        time_score = max(0, 1 - (avg_time / 3600))  # Normalize to 1 hour max
        score += time_score * 0.3
        
        # Experience bonus (more tasks = more experience)
        experience_bonus = min(0.2, total_tasks / 100)
        score += experience_bonus
        
        return min(1.0, score)
    
    def _get_load_balance_score(self, agent_id: str) -> float:
        """Get load balancing score (prefer less busy agents)"""
        
        # Count recent tasks assigned to this agent
        recent_assignments = len([
            selection for selection in self.selection_history[-50:]  # Last 50 selections
            if selection.get("selected_agent") == agent_id
        ])
        
        # Convert to score (fewer assignments = higher score)
        if recent_assignments == 0:
            return 1.0
        elif recent_assignments <= 2:
            return 0.8
        elif recent_assignments <= 5:
            return 0.6
        elif recent_assignments <= 10:
            return 0.4
        else:
            return 0.2
    
    def _get_specialization_score(self, agent_id: str, task_type: str) -> float:
        """Get specialization score for specific task types"""
        
        # Define agent specializations
        specializations = {
            "cybershell": ["automation", "cli", "system_admin", "scripting"],
            "ui_designer": ["web_app", "mobile_app", "design", "frontend"],
            "dev_engine": ["project_setup", "architecture", "scaffolding"],
            "agent_maker": ["ai_development", "automation", "agent_creation"],
            "fullstack_dev": ["web_app", "mobile_app", "api", "full_development"],
            "backend_dev": ["api", "backend", "server", "database"],
            "frontend_dev": ["web_app", "mobile_app", "ui", "frontend"],
            "data_sync": ["database", "data_processing", "sync", "storage"],
            "github_agent": ["version_control", "ci_cd", "deployment", "collaboration"],
            "deploy_manager": ["deployment", "cloud", "devops", "infrastructure"],
            "web3_plugin": ["blockchain", "smart_contracts", "defi", "crypto"],
            "voice_agent": ["voice_processing", "speech", "audio", "nlp"]
        }
        
        agent_specializations = specializations.get(agent_id, [])
        
        # Direct match
        if task_type in agent_specializations:
            return 1.0
        
        # Partial match
        for spec in agent_specializations:
            if spec in task_type or task_type in spec:
                return 0.7
        
        return 0.1  # Low score for non-specialized tasks
    
    def _record_selection(self, task_type: str, required_capabilities: List[str], 
                         selected_agent: str, all_scores: Dict[str, float]):
        """Record selection for learning and optimization"""
        
        selection_record = {
            "timestamp": datetime.now().isoformat(),
            "task_type": task_type,
            "required_capabilities": required_capabilities,
            "selected_agent": selected_agent,
            "all_scores": all_scores,
            "selection_reason": self._generate_selection_reason(selected_agent, all_scores)
        }
        
        self.selection_history.append(selection_record)
        
        # Keep only last 1000 selections
        if len(self.selection_history) > 1000:
            self.selection_history = self.selection_history[-1000:]
    
    def _generate_selection_reason(self, selected_agent: str, scores: Dict[str, float]) -> str:
        """Generate human-readable reason for selection"""
        
        max_score = scores[selected_agent]
        other_scores = [score for agent, score in scores.items() if agent != selected_agent]
        
        if not other_scores:
            return f"Only available agent: {selected_agent}"
        
        margin = max_score - max(other_scores)
        
        if margin > 20:
            return f"Clear best choice: {selected_agent} (score: {max_score:.1f})"
        elif margin > 10:
            return f"Good match: {selected_agent} (score: {max_score:.1f})"
        else:
            return f"Close decision: {selected_agent} (score: {max_score:.1f})"
    
    def update_agent_performance(self, agent_id: str, task_success: bool, 
                                completion_time: float, task_type: str = None):
        """Update agent performance metrics"""
        
        if agent_id not in self.agent_performance:
            self.agent_performance[agent_id] = {
                "total_tasks": 0,
                "successful_tasks": 0,
                "total_time": 0,
                "success_rate": 0,
                "avg_completion_time": 0,
                "task_types": {}
            }
        
        perf = self.agent_performance[agent_id]
        
        # Update counters
        perf["total_tasks"] += 1
        if task_success:
            perf["successful_tasks"] += 1
        perf["total_time"] += completion_time
        
        # Recalculate metrics
        perf["success_rate"] = perf["successful_tasks"] / perf["total_tasks"]
        perf["avg_completion_time"] = perf["total_time"] / perf["total_tasks"]
        
        # Track by task type
        if task_type:
            if task_type not in perf["task_types"]:
                perf["task_types"][task_type] = {"count": 0, "success": 0}
            
            perf["task_types"][task_type]["count"] += 1
            if task_success:
                perf["task_types"][task_type]["success"] += 1
    
    def get_agent_recommendations(self, task_type: str) -> List[Dict[str, Any]]:
        """Get agent recommendations with explanations"""
        
        # Mock agent registry for demonstration
        mock_registry = {
            "fullstack_dev": {"capabilities": ["frontend", "backend", "database"], "priority": 10, "status": "active"},
            "ui_designer": {"capabilities": ["ui_design", "react", "css"], "priority": 7, "status": "active"},
            "backend_dev": {"capabilities": ["backend", "api", "database"], "priority": 8, "status": "active"}
        }
        
        recommendations = []
        
        for agent_id, agent_info in mock_registry.items():
            score = self._calculate_agent_score(agent_id, agent_info, task_type, [])
            
            recommendations.append({
                "agent_id": agent_id,
                "score": round(score, 2),
                "reason": self._get_recommendation_reason(agent_id, task_type),
                "capabilities": agent_info["capabilities"],
                "estimated_time": self._estimate_completion_time(agent_id, task_type)
            })
        
        # Sort by score
        recommendations.sort(key=lambda x: x["score"], reverse=True)
        
        return recommendations[:5]  # Top 5 recommendations
    
    def _get_recommendation_reason(self, agent_id: str, task_type: str) -> str:
        """Get reason for recommending an agent"""
        
        reasons = {
            "fullstack_dev": "Versatile developer capable of handling end-to-end development",
            "ui_designer": "Specialized in creating beautiful and functional user interfaces",
            "backend_dev": "Expert in server-side logic and API development",
            "cybershell": "Perfect for automation and system-level tasks",
            "deploy_manager": "Specialized in deployment and infrastructure management"
        }
        
        return reasons.get(agent_id, f"Suitable for {task_type} tasks")
    
    def _estimate_completion_time(self, agent_id: str, task_type: str) -> str:
        """Estimate completion time for agent and task type"""
        
        if agent_id in self.agent_performance:
            avg_time = self.agent_performance[agent_id].get("avg_completion_time", 300)
        else:
            avg_time = 300  # Default 5 minutes
        
        # Adjust based on task complexity
        complexity_multipliers = {
            "web_app": 2.0,
            "mobile_app": 2.5,
            "automation": 1.0,
            "ui_design": 1.5,
            "backend": 1.8,
            "deployment": 1.2
        }
        
        multiplier = complexity_multipliers.get(task_type, 1.0)
        estimated_seconds = avg_time * multiplier
        
        if estimated_seconds < 60:
            return f"{int(estimated_seconds)}s"
        elif estimated_seconds < 3600:
            return f"{int(estimated_seconds/60)}min"
        else:
            return f"{estimated_seconds/3600:.1f}h"
    
    def optimize_selection_weights(self):
        """Optimize capability weights based on historical performance"""
        
        # Analyze successful vs failed selections
        successful_selections = [
            s for s in self.selection_history 
            if s.get("task_success", True)  # Assume success if not recorded
        ]
        
        failed_selections = [
            s for s in self.selection_history 
            if not s.get("task_success", True)
        ]
        
        # Adjust weights based on success patterns
        # This is a simplified version - in practice would use ML
        
        for capability in self.capability_weights:
            success_with_cap = len([
                s for s in successful_selections
                if capability in s.get("required_capabilities", [])
            ])
            
            total_with_cap = len([
                s for s in self.selection_history
                if capability in s.get("required_capabilities", [])
            ])
            
            if total_with_cap > 10:  # Only adjust if we have enough data
                success_rate = success_with_cap / total_with_cap
                
                # Increase weight for capabilities with higher success rates
                if success_rate > 0.8:
                    self.capability_weights[capability] *= 1.1
                elif success_rate < 0.6:
                    self.capability_weights[capability] *= 0.9
                
                # Keep weights in reasonable range
                self.capability_weights[capability] = max(0.1, min(2.0, self.capability_weights[capability]))
    
    def get_selection_analytics(self) -> Dict[str, Any]:
        """Get analytics on agent selection patterns"""
        
        if not self.selection_history:
            return {"message": "No selection history available"}
        
        # Agent usage statistics
        agent_usage = {}
        task_type_distribution = {}
        
        for selection in self.selection_history:
            agent = selection["selected_agent"]
            task_type = selection["task_type"]
            
            agent_usage[agent] = agent_usage.get(agent, 0) + 1
            task_type_distribution[task_type] = task_type_distribution.get(task_type, 0) + 1
        
        # Most used agents
        most_used = sorted(agent_usage.items(), key=lambda x: x[1], reverse=True)[:5]
        
        # Most common task types
        common_tasks = sorted(task_type_distribution.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "total_selections": len(self.selection_history),
            "most_used_agents": most_used,
            "common_task_types": common_tasks,
            "current_weights": self.capability_weights,
            "agents_with_performance_data": len(self.agent_performance)
        }

# Global instance
ai_selector = AISelector()
