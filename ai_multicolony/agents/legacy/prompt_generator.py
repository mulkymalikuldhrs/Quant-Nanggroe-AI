"""
📝 Prompt Generator Agent - AI Prompt Engineering & Optimization
Generates optimized prompts for various AI tasks and models

Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import re

class PromptGeneratorAgent:
    """
    Prompt Generator Agent that:
    - Creates optimized prompts for different AI models
    - Generates role-based prompts for various professions
    - Optimizes prompts for specific tasks and domains
    - Provides prompt templates and variations
    - Analyzes and improves existing prompts
    """
    
    def __init__(self):
        self.agent_id = "prompt_generator"
        self.name = "Prompt Generator Agent"
        self.status = "ready"
        self.capabilities = [
            "prompt_creation",
            "prompt_optimization",
            "role_based_prompts",
            "task_specific_prompts",
            "prompt_analysis",
            "template_generation"
        ]
        
        # Prompt templates and patterns
        self.prompt_patterns = self._load_prompt_patterns()
        self.role_templates = self._load_role_templates()
        self.optimization_techniques = self._load_optimization_techniques()
        
        # Generated prompts tracking
        self.generated_prompts: Dict[str, Dict] = {}
        
        # Import LLM Gateway for testing prompts
        try:
            from connectors.llm_gateway import llm_gateway
            self.llm = llm_gateway
        except ImportError:
            self.llm = None
    
    def _load_prompt_patterns(self) -> Dict[str, Dict]:
        """Load prompt patterns and structures"""
        return {
            "role_task_format": {
                "description": "Role-based task prompt with clear instructions",
                "structure": [
                    "ROLE_DEFINITION",
                    "CONTEXT_SETTING", 
                    "TASK_DESCRIPTION",
                    "CONSTRAINTS_RULES",
                    "OUTPUT_FORMAT",
                    "EXAMPLES"
                ],
                "template": """You are a {role} with expertise in {domain}.

CONTEXT:
{context}

TASK:
{task_description}

CONSTRAINTS:
{constraints}

OUTPUT FORMAT:
{format_specification}

EXAMPLE:
{example}"""
            },
            "chain_of_thought": {
                "description": "Structured thinking process prompt",
                "structure": [
                    "PROBLEM_STATEMENT",
                    "THINKING_STEPS",
                    "REASONING_CHAIN",
                    "CONCLUSION"
                ],
                "template": """Let's approach this step by step:

PROBLEM: {problem}

THINKING PROCESS:
1. First, I need to understand: {step1}
2. Then, I should consider: {step2}
3. Next, I'll analyze: {step3}
4. Finally, I'll conclude: {step4}

Please follow this reasoning chain for: {task}"""
            },
            "few_shot_learning": {
                "description": "Learning from examples prompt",
                "structure": [
                    "INSTRUCTION",
                    "EXAMPLES",
                    "NEW_TASK"
                ],
                "template": """Here are examples of how to {task_type}:

Example 1:
Input: {input1}
Output: {output1}

Example 2:
Input: {input2}
Output: {output2}

Example 3:
Input: {input3}
Output: {output3}

Now, apply the same pattern to:
Input: {new_input}
Output: """
            },
            "creative_generation": {
                "description": "Creative content generation prompt",
                "structure": [
                    "CREATIVE_BRIEF",
                    "STYLE_GUIDELINES",
                    "TARGET_AUDIENCE",
                    "CONSTRAINTS",
                    "INSPIRATION"
                ],
                "template": """Create {content_type} with the following specifications:

BRIEF: {brief}
STYLE: {style}
AUDIENCE: {audience}
TONE: {tone}

REQUIREMENTS:
{requirements}

INSPIRATION: {inspiration_sources}

Generate creative content that meets these criteria."""
            }
        }
    
    def _load_role_templates(self) -> Dict[str, Dict]:
        """Load role-based prompt templates"""
        return {
            "software_developer": {
                "description": "Expert software developer and programmer",
                "expertise": ["coding", "architecture", "debugging", "optimization"],
                "prompt_template": """You are an expert software developer with {years} years of experience in {technologies}.

You specialize in:
- Writing clean, efficient, and maintainable code
- Software architecture and design patterns
- Debugging and troubleshooting
- Performance optimization
- Best practices and code review

Your coding style emphasizes:
- Readability and documentation
- Error handling and edge cases
- Testing and quality assurance
- Security considerations
- Scalability and performance"""
            },
            "data_scientist": {
                "description": "Data science and machine learning expert",
                "expertise": ["data_analysis", "machine_learning", "statistics", "visualization"],
                "prompt_template": """You are a senior data scientist with expertise in {specializations}.

Your capabilities include:
- Statistical analysis and hypothesis testing
- Machine learning model development
- Data preprocessing and feature engineering
- Data visualization and storytelling
- Business intelligence and insights

You approach problems with:
- Scientific methodology
- Evidence-based conclusions
- Clear explanations of complex concepts
- Actionable recommendations
- Ethical data practices"""
            },
            "content_writer": {
                "description": "Professional content writer and copywriter",
                "expertise": ["writing", "storytelling", "marketing", "communication"],
                "prompt_template": """You are a professional content writer specializing in {content_types}.

Your writing strengths:
- Engaging and persuasive content
- Clear and concise communication
- Audience-appropriate tone and style
- SEO optimization when relevant
- Brand voice consistency

You create content that:
- Captures attention and maintains interest
- Delivers value to the target audience
- Achieves specific business objectives
- Follows content best practices
- Is optimized for the intended platform"""
            },
            "business_analyst": {
                "description": "Strategic business analyst and consultant",
                "expertise": ["analysis", "strategy", "process_improvement", "consulting"],
                "prompt_template": """You are a strategic business analyst with {experience} in {industries}.

Your analytical approach includes:
- Comprehensive business analysis
- Strategic planning and recommendations
- Process optimization and improvement
- Risk assessment and mitigation
- Stakeholder communication

You deliver insights that are:
- Data-driven and evidence-based
- Actionable and implementation-focused
- Aligned with business objectives
- Cost-effective and practical
- Clearly communicated to stakeholders"""
            },
            "teacher_educator": {
                "description": "Educational expert and instructional designer",
                "expertise": ["education", "curriculum_design", "pedagogy", "assessment"],
                "prompt_template": """You are an experienced educator and instructional designer with expertise in {subjects}.

Your educational approach focuses on:
- Student-centered learning experiences
- Clear learning objectives and outcomes
- Engaging and interactive content
- Differentiated instruction methods
- Constructive assessment and feedback

You create educational content that:
- Is pedagogically sound and evidence-based
- Accommodates different learning styles
- Promotes critical thinking and problem-solving
- Is age and skill-level appropriate
- Encourages active participation and engagement"""
            }
        }
    
    def _load_optimization_techniques(self) -> Dict[str, str]:
        """Load prompt optimization techniques"""
        return {
            "specificity": "Make instructions specific and unambiguous",
            "context": "Provide relevant context and background information",
            "examples": "Include concrete examples to illustrate expectations",
            "constraints": "Define clear boundaries and limitations",
            "format": "Specify desired output format and structure",
            "persona": "Establish clear role and expertise level",
            "step_by_step": "Break complex tasks into sequential steps",
            "chain_of_thought": "Encourage explicit reasoning process",
            "few_shot": "Provide multiple examples for pattern learning",
            "temperature_control": "Adjust creativity vs consistency as needed"
        }
    
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process prompt generation task"""
        try:
            action = task.get("action", "generate_prompt")
            
            if action == "generate_prompt":
                return await self._generate_prompt(task)
            elif action == "optimize_prompt":
                return await self._optimize_prompt(task)
            elif action == "create_role_prompt":
                return await self._create_role_prompt(task)
            elif action == "analyze_prompt":
                return await self._analyze_prompt(task)
            elif action == "generate_variations":
                return await self._generate_variations(task)
            elif action == "test_prompt":
                return await self._test_prompt(task)
            else:
                return self._create_error_response(f"Unknown action: {action}")
                
        except Exception as e:
            return self._create_error_response(str(e))
    
    async def _optimize_prompt(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize an existing prompt"""
        original_prompt = task.get("original_prompt", "")
        target_model = task.get("target_model", "gpt-4")
        optimization_goals = task.get("optimization_goals", ["specificity", "clarity"])
        
        if not original_prompt:
            return self._create_error_response("Original prompt is required")
        
        # Apply optimization techniques
        optimized_prompt = original_prompt
        
        # Add specificity if requested
        if "specificity" in optimization_goals:
            if not optimized_prompt.strip().endswith("."):
                optimized_prompt = optimized_prompt.rstrip() + "."
            if "be specific" not in optimized_prompt.lower():
                optimized_prompt += "\n\nPlease be specific and detailed in your response."
        
        # Add clarity improvements
        if "clarity" in optimization_goals:
            if "step by step" not in optimized_prompt.lower():
                optimized_prompt += "\n\nThink step by step."
        
        # Add structure if requested
        if "structure" in optimization_goals:
            optimized_prompt += "\n\nProvide your response in a clear, structured format."
        
        # Add context if requested
        if "context" in optimization_goals:
            optimized_prompt += "\n\nConsider the broader context and implications."
        
        # Add examples if requested
        if "examples" in optimization_goals:
            optimized_prompt += "\n\nInclude examples to illustrate key points."
        
        # Optimize for target model
        optimized_prompt = self._optimize_for_model(optimized_prompt, target_model)
        
        return {
            "success": True,
            "original_prompt": original_prompt,
            "optimized_prompt": optimized_prompt,
            "target_model": target_model,
            "optimization_goals": optimization_goals,
            "improvements": [f"Applied {goal}" for goal in optimization_goals],
            "timestamp": datetime.now().isoformat()
        }
    
    async def _generate_prompt(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Generate optimized prompt based on requirements"""
        try:
            task_type = task.get("task_type", "general")
            domain = task.get("domain", "general")
            requirements = task.get("requirements", {})
            target_model = task.get("target_model", "general")
            
            # Select appropriate pattern
            pattern = self._select_best_pattern(task_type, requirements)
            
            # Generate prompt
            generated_prompt = await self._create_prompt_from_pattern(
                pattern, task_type, domain, requirements
            )
            
            # Optimize for target model
            optimized_prompt = self._optimize_for_model(generated_prompt, target_model)
            
            # Store generated prompt
            prompt_id = f"prompt_{int(time.time())}_{len(self.generated_prompts)}"
            prompt_info = {
                "prompt_id": prompt_id,
                "task_type": task_type,
                "domain": domain,
                "pattern_used": pattern,
                "requirements": requirements,
                "target_model": target_model,
                "generated_prompt": optimized_prompt,
                "created_at": datetime.now().isoformat(),
                "optimization_techniques": self._get_applied_techniques(requirements)
            }
            
            self.generated_prompts[prompt_id] = prompt_info
            
            return {
                "success": True,
                "prompt_id": prompt_id,
                "generated_prompt": optimized_prompt,
                "pattern_used": pattern,
                "optimization_techniques": prompt_info["optimization_techniques"],
                "metadata": {
                    "task_type": task_type,
                    "domain": domain,
                    "target_model": target_model
                }
            }
            
        except Exception as e:
            return self._create_error_response(f"Failed to generate prompt: {str(e)}")
    
    def _select_best_pattern(self, task_type: str, requirements: Dict) -> str:
        """Select the best prompt pattern for the task"""
        
        # Pattern selection logic
        if requirements.get("reasoning_required"):
            return "chain_of_thought"
        elif requirements.get("examples_needed"):
            return "few_shot_learning"
        elif requirements.get("creative_output"):
            return "creative_generation"
        else:
            return "role_task_format"
    
    async def _create_prompt_from_pattern(self, pattern: str, task_type: str, 
                                         domain: str, requirements: Dict) -> str:
        """Create prompt using selected pattern"""
        
        pattern_info = self.prompt_patterns.get(pattern, self.prompt_patterns["role_task_format"])
        template = pattern_info["template"]
        
        # Fill template variables
        variables = {
            "role": requirements.get("role", "expert assistant"),
            "domain": domain,
            "context": requirements.get("context", f"Working on {task_type} tasks"),
            "task_description": requirements.get("task_description", f"Complete {task_type} effectively"),
            "constraints": requirements.get("constraints", "Follow best practices"),
            "format_specification": requirements.get("output_format", "Clear and structured response"),
            "example": requirements.get("example", "Provide relevant example")
        }
        
        # Handle pattern-specific variables
        if pattern == "chain_of_thought":
            variables.update({
                "problem": requirements.get("problem", "The given task"),
                "step1": "the requirements and constraints",
                "step2": "possible approaches and solutions",
                "step3": "the best approach and implementation",
                "step4": "based on the analysis",
                "task": requirements.get("task_description", "the given task")
            })
        elif pattern == "few_shot_learning":
            examples = requirements.get("examples", [])
            if len(examples) >= 3:
                variables.update({
                    "task_type": task_type,
                    "input1": examples[0].get("input", "Example input 1"),
                    "output1": examples[0].get("output", "Example output 1"),
                    "input2": examples[1].get("input", "Example input 2"), 
                    "output2": examples[1].get("output", "Example output 2"),
                    "input3": examples[2].get("input", "Example input 3"),
                    "output3": examples[2].get("output", "Example output 3"),
                    "new_input": "{user_input}"
                })
        elif pattern == "creative_generation":
            variables.update({
                "content_type": requirements.get("content_type", "content"),
                "brief": requirements.get("brief", "Create engaging content"),
                "style": requirements.get("style", "professional"),
                "audience": requirements.get("audience", "general audience"),
                "tone": requirements.get("tone", "informative"),
                "requirements": requirements.get("specific_requirements", "High quality output"),
                "inspiration_sources": requirements.get("inspiration", "industry best practices")
            })
        
        # Replace template variables
        prompt = template
        for key, value in variables.items():
            prompt = prompt.replace(f"{{{key}}}", str(value))
        
        return prompt
    
    def _optimize_for_model(self, prompt: str, target_model: str) -> str:
        """Optimize prompt for specific AI model"""
        
        optimizations = {
            "gpt-4": {
                "prefix": "You are a highly capable AI assistant. ",
                "style": "detailed and comprehensive",
                "max_length": 4000
            },
            "gpt-3.5-turbo": {
                "prefix": "",
                "style": "concise but complete",
                "max_length": 2000
            },
            "claude": {
                "prefix": "I'm Claude, an AI assistant. ",
                "style": "thoughtful and analytical",
                "max_length": 3000
            },
            "llama": {
                "prefix": "",
                "style": "step-by-step and clear",
                "max_length": 2500
            }
        }
        
        model_config = optimizations.get(target_model, optimizations["gpt-3.5-turbo"])
        
        # Apply model-specific optimizations
        optimized = model_config["prefix"] + prompt
        
        # Ensure length limits
        if len(optimized) > model_config["max_length"]:
            optimized = optimized[:model_config["max_length"]] + "..."
        
        return optimized
    
    def _get_applied_techniques(self, requirements: Dict) -> List[str]:
        """Get list of optimization techniques applied"""
        techniques = ["specificity", "format"]
        
        if requirements.get("context"):
            techniques.append("context")
        if requirements.get("examples") or requirements.get("example"):
            techniques.append("examples")
        if requirements.get("constraints"):
            techniques.append("constraints")
        if requirements.get("role"):
            techniques.append("persona")
        if requirements.get("reasoning_required"):
            techniques.append("chain_of_thought")
        
        return techniques
    
    async def _create_role_prompt(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Create role-based prompt"""
        try:
            role = task.get("role", "")
            specialization = task.get("specialization", "")
            experience_level = task.get("experience_level", "expert")
            
            if not role:
                return self._create_error_response("Role is required")
            
            # Get role template
            if role in self.role_templates:
                template_info = self.role_templates[role]
                base_template = template_info["prompt_template"]
                
                # Customize template
                customized_prompt = base_template.format(
                    years=self._get_experience_years(experience_level),
                    technologies=specialization or "various technologies",
                    specializations=specialization or "multiple domains",
                    content_types=specialization or "various content types",
                    experience=f"{experience_level} level",
                    industries=specialization or "multiple industries",
                    subjects=specialization or "various subjects"
                )
                
                return {
                    "success": True,
                    "role_prompt": customized_prompt,
                    "role": role,
                    "capabilities": template_info["expertise"],
                    "experience_level": experience_level,
                    "specialization": specialization
                }
            else:
                # Create custom role prompt
                custom_prompt = await self._create_custom_role_prompt(role, specialization, experience_level)
                
                return {
                    "success": True,
                    "role_prompt": custom_prompt,
                    "role": role,
                    "experience_level": experience_level,
                    "specialization": specialization,
                    "note": "Custom role prompt generated"
                }
                
        except Exception as e:
            return self._create_error_response(f"Failed to create role prompt: {str(e)}")
    
    async def _create_custom_role_prompt(self, role: str, specialization: str, experience_level: str) -> str:
        """Create custom role prompt for non-standard roles"""
        
        experience_years = self._get_experience_years(experience_level)
        
        return f"""You are a {experience_level} {role} with {experience_years} years of professional experience{f' specializing in {specialization}' if specialization else ''}.

Your expertise includes:
- Deep knowledge in your field of specialization
- Best practices and industry standards
- Problem-solving and analytical thinking
- Clear communication and explanation skills
- Practical, actionable advice and solutions

You approach tasks with:
- Professional competence and attention to detail
- Evidence-based reasoning and recommendations
- Clear, structured responses
- Consideration of real-world constraints and implications
- Focus on delivering valuable, actionable insights

Please apply your professional expertise to help with the following tasks."""
    
    def _get_experience_years(self, level: str) -> str:
        """Get experience years based on level"""
        levels = {
            "junior": "2-3",
            "mid": "5-7", 
            "senior": "8-12",
            "expert": "15+",
            "lead": "10-15"
        }
        
        return levels.get(level, "10+")
    
    async def _test_prompt(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Test generated prompt with sample input"""
        try:
            prompt = task.get("prompt", "")
            test_input = task.get("test_input", "")
            
            if not prompt or not self.llm:
                return {
                    "success": False,
                    "error": "Prompt and LLM required for testing"
                }
            
            # Test prompt with LLM
            full_prompt = f"{prompt}\n\nInput: {test_input}"
            
            response = await self.llm.generate_text(
                full_prompt,
                temperature=0.7,
                max_tokens=500
            )
            
            # Analyze response quality
            quality_score = self._analyze_response_quality(response, test_input)
            
            return {
                "success": True,
                "test_input": test_input,
                "response": response,
                "quality_score": quality_score,
                "prompt_effectiveness": "good" if quality_score > 0.7 else "needs_improvement"
            }
            
        except Exception as e:
            return self._create_error_response(f"Prompt testing failed: {str(e)}")
    
    def _analyze_response_quality(self, response: str, input_text: str) -> float:
        """Analyze response quality (simplified scoring)"""
        score = 0.5  # Base score
        
        # Check response length (appropriate length)
        if 50 <= len(response) <= 1000:
            score += 0.1
        
        # Check for structure
        if any(indicator in response.lower() for indicator in ['first', 'second', 'next', 'finally', '1.', '2.']):
            score += 0.1
        
        # Check for relevance (contains key terms from input)
        input_words = set(input_text.lower().split())
        response_words = set(response.lower().split())
        relevance = len(input_words & response_words) / len(input_words) if input_words else 0
        score += relevance * 0.3
        
        return min(score, 1.0)
    
    def get_prompt_library(self) -> Dict[str, Any]:
        """Get comprehensive prompt library"""
        return {
            "patterns": self.prompt_patterns,
            "role_templates": self.role_templates,
            "optimization_techniques": self.optimization_techniques,
            "generated_prompts_count": len(self.generated_prompts)
        }
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create standardized error response"""
        return {
            "success": False,
            "error": error_message,
            "agent": self.agent_id,
            "timestamp": datetime.now().isoformat()
        }

# Global instance
prompt_generator_agent = PromptGeneratorAgent()
