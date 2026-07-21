"""
Decision Engine - Core Intelligence Orchestrator

Decides between:
1. Answering directly (fast, cheap, simple)
2. Orchestrating complex workflows (agents, tools, workflows)

Key principles:
- Single API entry point
- Intelligent task routing
- Free model prioritization
- Complexity hiding
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

class TaskType(Enum):
    SIMPLE = "simple"           # Can answer directly
    MODERATE = "moderate"       # May need tools
    COMPLEX = "complex"         # Need orchestration
    RESEARCH = "research"       # Need deep research

@dataclass
class TaskAnalysis:
    task_type: TaskType
    complexity_score: float
    estimated_time: float
    model_preference: str
    needs_orchestration: bool
    suggested_strategy: str

class DecisionEngine:
    """Intelligent task routing engine for Jeumpa"""
    
    def __init__(self):
        self.task_complexity_thresholds = {
            TaskType.SIMPLE: 0.3,
            TaskType.MODERATE: 0.5,
            TaskType.COMPLEX: 0.7,
            TaskType.RESEARCH: 0.8
        }
        
        self.strategy_registry = {
            "simple": "direct_answer",
            "moderate": "tool_use", 
            "complex": "orchestration",
            "research": "research_orchestration"
        }
        
        self.free_model_preferences = {
            "coding": "deepseek-coder,llama-coder,qwen2.5-coder,gpt-4o-mini",
            "reasoning": "llama3.1:405b,claude-3.5-sonnet,gemini-1.5-pro",
            "creative": "gpt-4o,dalle,stable-diffusion",
            "analysis": "gpt-4o-mistral-7b"
        }
    
    def analyze_task(self, prompt: str, context: Dict[str, Any] = None) -> TaskAnalysis:
        """Analyze task and determine optimal strategy"""
        context = context or {}
        
        # Simple heuristics for task analysis
        complexity_score = self._calculate_complexity_score(prompt, context)
        task_type = self._determine_task_type(complexity_score)
        
        # Determine if orchestration is needed
        needs_orchestration = self._requires_orchestration(
            prompt, context, complexity_score
        )
        
        # Select strategy
        suggested_strategy = self.strategy_registry.get(
            task_type.value, "direct_answer"
        )
        
        # Choose model based on task type and cost optimization
        model_preference = self._select_model_for_task(
            prompt, task_type, context
        )
        
        return TaskAnalysis(
            task_type=task_type,
            complexity_score=complexity_score,
            estimated_time=self._estimate_time(complexity_score, task_type),
            model_preference=model_preference,
            needs_orchestration=needs_orchestration,
            suggested_strategy=suggested_strategy
        )
    
    def decide_strategy(self, analysis: TaskAnalysis) -> str:
        """Return the decision strategy based on task analysis"""
        if not analysis.needs_orchestration:
            return "direct_answer"
        
        return analysis.suggested_strategy
    
    def select_free_model(self, task_type: TaskType, context: Dict[str, Any] = None) -> str:
        """Select optimal free model for task"""
        context = context or {}
        
        # Simple keyword-based model selection
        prompt_lower = context.get("prompt", "").lower()
        
        if any(keyword in prompt_lower for keyword in ["code", "program", "function", "api", "bug"]):
            return self._get_free_model_for_category("coding")
        
        elif any(keyword in prompt_lower for keyword in ["analyze", "research", "investigate", "study"]):
            return self._get_free_model_for_category("analysis")
        
        elif any(keyword in prompt_lower for keyword in ["write", "story", "creative", "imagine"]):
            return self._get_free_model_for_category("creative")
        
        # Default to most cost-effective free model
        return self._get_free_model_for_category("reasoning")
    
    def orchestrate_workflow(self, prompt: str, analysis: TaskAnalysis, context: Dict[str, Any] = None):
        """Orchestrate complex workflow using multiple models/tools"""
        context = context or {}
        
        # For research tasks, use specialized research orchestration
        if analysis.task_type == TaskType.RESEARCH:
            return self._orchestrate_research_workflow(prompt, analysis)
        
        # For complex tasks, use agent orchestration
        elif analysis.task_type == TaskType.COMPLEX:
            return self._orchestrate_agent_workflow(prompt, analysis)
        
        # For moderate tasks, use tool-based approach
        elif analysis.task_type == TaskType.MODERATE:
            return self._orchestrate_tool_workflow(prompt, analysis)
        
        # Default to direct answer
        return self._direct_answer_strategy(prompt, analysis)
    
    def _calculate_complexity_score(self, prompt: str, context: Dict[str, Any]) -> float:
        """Calculate task complexity score (0.0 to 1.0)"""
        score = 0.0
        
        # Keywords that increase complexity
        complex_keywords = ["orchestrate", "multiple", "complex", "analysis", "research", "investigate"]
        
        # Check for complexity indicators
        prompt_lower = prompt.lower()
        
        for keyword in complex_keywords:
            if keyword in prompt_lower:
                score += 0.2
        
        # More words = more complex
        score += min(len(prompt.split()) * 0.01, 0.3)
        
        # Check for specific technical terms
        technical_terms = ["api", "machine learning", "neural", "algorithm", "architecture"]
        for term in technical_terms:
            if term in prompt_lower:
                score += 0.15
        
        return min(score, 1.0)
    
    def _determine_task_type(self, complexity_score: float) -> TaskType:
        """Determine task type based on complexity"""
        if complexity_score < 0.3:
            return TaskType.SIMPLE
        elif complexity_score < 0.5:
            return TaskType.MODERATE
        elif complexity_score < 0.7:
            return TaskType.COMPLEX
        else:
            return TaskType.RESEARCH
    
    def _requires_orchestration(self, prompt: str, context: Dict[str, Any], complexity_score: float) -> bool:
        """Determine if orchestration is needed"""
        # Always orchestrate for research tasks
        if complexity_score > 0.8:
            return True
        
        # Check for orchestration keywords
        orchestration_keywords = ["orchestrate", "coordinate", "multiple agents", "workflow"]
        
        prompt_lower = prompt.lower()
        
        for keyword in orchestration_keywords:
            if keyword in prompt_lower:
                return True
        
        # Check context for orchestration requirements
        if context.get("orchestration_required", False):
            return True
        
        # Simple tasks don't need orchestration
        return False
    
    def _select_model_for_task(self, prompt: str, task_type: TaskType, context: Dict[str, Any]) -> str:
        """Select best model for the task"""
        # Use free model selection for all tasks to minimize costs
        return self.select_free_model(task_type, context)
    
    def _estimate_time(self, complexity_score: float, task_type: TaskType) -> float:
        """Estimate task completion time in seconds"""
        base_time = {
            TaskType.SIMPLE: 2.0,
            TaskType.MODERATE: 5.0,
            TaskType.COMPLEX: 10.0,
            TaskType.RESEARCH: 20.0
        }
        
        # Adjust based on complexity
        time_multiplier = 1.0 + (complexity_score * 2)
        
        return base_time[task_type] * time_multiplier
    
    def _get_free_model_for_category(self, category: str) -> str:
        """Get free model for specific category"""
        defaults = {
            "coding": "deepseek-coder",
            "reasoning": "llama3.1:405b", 
            "creative": "gpt-4o",
            "analysis": "gpt-4o-mini"
        }
        return defaults.get(category, defaults["reasoning"])
    
    def _orchestrate_research_workflow(self, prompt: str, analysis: TaskAnalysis):
        """Orchestrate research workflow with multiple models/tools"""
        return {
            "strategy": "research_orchestration",
            "workflow": [
                "initial_research_model",
                "deep_dive_analysis_model", 
                "cross_validation_model",
                "synthesis_model"
            ],
            "estimated_time": analysis.estimated_time,
            "models_needed": ["researcher", "analyst", "validator", "synthesizer"]
        }
    
    def _orchestrate_agent_workflow(self, prompt: str, analysis: TaskAnalysis):
        """Orchestrate agent-based workflow"""
        return {
            "strategy": "agent_orchestration",
            "workflow": [
                "task_decomposition",
                "agent_assignment",
                "execution_coordination",
                "result_aggregation"
            ],
            "estimated_time": analysis.estimated_time,
            "agents_needed": ["planner", "executor", "coordinator", "validator"]
        }
    
    def _orchestrate_tool_workflow(self, prompt: str, analysis: TaskAnalysis):
        """Orchestrate tool-based workflow"""
        return {
            "strategy": "tool_orchestration",
            "workflow": [
                "tool_selection",
                "tool_execution",
                "result_processing"
            ],
            "estimated_time": analysis.estimated_time,
            "tools_needed": ["search", "analysis", "synthesis"]
        }
    
    def _direct_answer_strategy(self, prompt: str, analysis: TaskAnalysis):
        """Direct answer using optimal model"""
        return {
            "strategy": "direct_answer",
            "model": analysis.model_preference,
            "estimated_time": analysis.estimated_time,
            "estimated_cost": 0.0
        }
