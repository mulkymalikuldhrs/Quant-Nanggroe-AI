"""
Agent 03 (Planner) - Goal Breakdown & Step-by-Step Planning
"""

from typing import Dict, List, Any, Optional, Tuple
import json
from datetime import datetime, timedelta
import re

from ..core.base_agent import BaseAgent

class Agent03Planner(BaseAgent):
    """Specialized planning agent for task breakdown and scheduling"""
    
    def __init__(self, config_path: str = "config/prompts.yaml"):
        super().__init__("agent_03_planner", config_path)
        self.planning_templates = {}
        self.created_plans = {}
        self._load_planning_templates()
        
    def _load_planning_templates(self):
        """Load planning templates for different types of projects"""
        self.planning_templates = {
            'software_development': {
                'phases': ['Analysis', 'Design', 'Implementation', 'Testing', 'Deployment'],
                'typical_duration': 'weeks',
                'key_deliverables': ['Requirements', 'Architecture', 'Code', 'Tests', 'Documentation']
            },
            'content_creation': {
                'phases': ['Research', 'Planning', 'Creation', 'Review', 'Publishing'],
                'typical_duration': 'days',
                'key_deliverables': ['Content Plan', 'Draft', 'Final Content', 'Assets']
            },
            'data_analysis': {
                'phases': ['Data Collection', 'Cleaning', 'Analysis', 'Visualization', 'Reporting'],
                'typical_duration': 'days',
                'key_deliverables': ['Dataset', 'Clean Data', 'Analysis', 'Charts', 'Report']
            },
            'design_project': {
                'phases': ['Discovery', 'Concept', 'Design', 'Iteration', 'Final'],
                'typical_duration': 'days',
                'key_deliverables': ['Brief', 'Concepts', 'Designs', 'Revisions', 'Final Assets']
            },
            'research': {
                'phases': ['Planning', 'Data Gathering', 'Analysis', 'Synthesis', 'Documentation'],
                'typical_duration': 'days',
                'key_deliverables': ['Research Plan', 'Data', 'Analysis', 'Findings', 'Report']
            }
        }
    
    def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process planning request and create detailed execution plan"""
        
        if not self.validate_input(task):
            return self.handle_error(
                Exception("Invalid task format"), task
            )
        
        try:
            self.update_status("planning", task)
            
            # Analyze the goal
            goal_analysis = self._analyze_goal(task)
            
            # Create task breakdown structure
            task_breakdown = self._create_task_breakdown(goal_analysis)
            
            # Create timeline and scheduling
            timeline = self._create_timeline(task_breakdown, goal_analysis)
            
            # Identify resource requirements
            resources = self._identify_resources(task_breakdown)
            
            # Assess risks and create mitigation strategies
            risk_assessment = self._assess_risks(task_breakdown, timeline)
            
            # Define success criteria
            success_criteria = self._define_success_criteria(goal_analysis)
            
            self.update_status("ready")
            
            # Prepare comprehensive plan response
            plan_id = f"plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            response_content = f"""
📋 GOAL ANALYSIS: {goal_analysis['summary']}

🎯 TASK STRUCTURE:
{self._format_task_breakdown(task_breakdown)}

⏱️ TIMELINE:
{self._format_timeline(timeline)}

👥 RESOURCES:
{self._format_resources(resources)}

⚠️ RISKS:
{self._format_risks(risk_assessment)}

✅ SUCCESS CRITERIA:
{self._format_success_criteria(success_criteria)}
            """
            
            # Store the plan
            self._store_plan(plan_id, task, goal_analysis, task_breakdown, timeline, resources, risk_assessment, success_criteria)
            
            return self.format_response(response_content.strip(), "detailed_plan")
            
        except Exception as e:
            return self.handle_error(e, task)
    
    def _analyze_goal(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze the main goal and requirements"""
        request = task.get('request', '')
        context = task.get('context', {})
        
        # Extract key information
        goal_type = self._classify_goal_type(request)
        complexity = self._assess_goal_complexity(request)
        constraints = self._extract_constraints(request, context)
        stakeholders = self._identify_stakeholders(context)
        
        analysis = {
            'summary': self._create_goal_summary(request),
            'type': goal_type,
            'complexity': complexity,
            'constraints': constraints,
            'stakeholders': stakeholders,
            'key_objectives': self._extract_key_objectives(request),
            'deliverables': self._identify_main_deliverables(request, goal_type)
        }
        
        return analysis
    
    def _classify_goal_type(self, request: str) -> str:
        """Classify the type of goal/project"""
        request_lower = request.lower()
        
        # Check for software development keywords
        if any(word in request_lower for word in ['code', 'develop', 'program', 'software', 'app', 'system']):
            return 'software_development'
        
        # Check for content creation keywords
        if any(word in request_lower for word in ['write', 'content', 'article', 'blog', 'documentation']):
            return 'content_creation'
        
        # Check for data analysis keywords
        if any(word in request_lower for word in ['data', 'analyze', 'analytics', 'statistics', 'report']):
            return 'data_analysis'
        
        # Check for design keywords
        if any(word in request_lower for word in ['design', 'ui', 'ux', 'visual', 'graphics', 'logo']):
            return 'design_project'
        
        # Check for research keywords
        if any(word in request_lower for word in ['research', 'study', 'investigate', 'analyze']):
            return 'research'
        
        return 'general'
    
    def _assess_goal_complexity(self, request: str) -> str:
        """Assess the complexity of the goal"""
        request_lower = request.lower()
        
        # High complexity indicators
        high_complexity_words = ['complex', 'enterprise', 'multiple', 'integrate', 'scalable', 'advanced']
        if any(word in request_lower for word in high_complexity_words) or len(request) > 500:
            return 'high'
        
        # Medium complexity indicators
        medium_complexity_words = ['create', 'build', 'develop', 'design', 'implement']
        if any(word in request_lower for word in medium_complexity_words) or len(request) > 200:
            return 'medium'
        
        return 'low'
    
    def _extract_constraints(self, request: str, context: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract constraints from request and context"""
        constraints = []
        
        # Time constraints
        time_patterns = [
            r'(\d+)\s*(day|week|month)s?',
            r'by\s+(\w+\s+\d+)',
            r'deadline\s+(\w+\s+\d+)',
            r'urgent',
            r'asap',
            r'quickly'
        ]
        
        for pattern in time_patterns:
            if re.search(pattern, request.lower()):
                constraints.append({
                    'type': 'time',
                    'description': 'Time constraint identified in request'
                })
                break
        
        # Budget constraints
        if any(word in request.lower() for word in ['budget', 'cost', 'cheap', 'affordable']):
            constraints.append({
                'type': 'budget',
                'description': 'Budget constraint mentioned'
            })
        
        # Resource constraints
        if any(word in request.lower() for word in ['limited', 'small team', 'minimal resources']):
            constraints.append({
                'type': 'resources',
                'description': 'Resource limitations mentioned'
            })
        
        # Technical constraints
        if any(word in request.lower() for word in ['must use', 'requirement', 'standard']):
            constraints.append({
                'type': 'technical',
                'description': 'Technical requirements specified'
            })
        
        return constraints
    
    def _identify_stakeholders(self, context: Dict[str, Any]) -> List[str]:
        """Identify project stakeholders"""
        stakeholders = ['Project Requester']  # Always include requester
        
        # Add stakeholders based on context
        if context.get('team_size', 0) > 1:
            stakeholders.append('Team Members')
        
        if context.get('client_facing', False):
            stakeholders.append('End Users/Clients')
        
        if context.get('management_visibility', False):
            stakeholders.append('Management')
        
        return stakeholders
    
    def _extract_key_objectives(self, request: str) -> List[str]:
        """Extract key objectives from the request"""
        # Simple objective extraction - in production, use NLP
        objectives = []
        
        # Look for action words and their objects
        action_patterns = [
            r'(create|build|develop|design|make)\s+([^.]+)',
            r'(improve|optimize|enhance)\s+([^.]+)',
            r'(analyze|study|research)\s+([^.]+)',
            r'(implement|deploy|launch)\s+([^.]+)'
        ]
        
        for pattern in action_patterns:
            matches = re.findall(pattern, request.lower())
            for match in matches:
                objectives.append(f"{match[0].title()} {match[1].strip()}")
        
        # If no specific objectives found, use general ones
        if not objectives:
            objectives = ['Complete the requested task', 'Deliver high-quality results']
        
        return objectives[:5]  # Limit to top 5 objectives
    
    def _identify_main_deliverables(self, request: str, goal_type: str) -> List[str]:
        """Identify main project deliverables"""
        # Get template deliverables for goal type
        template = self.planning_templates.get(goal_type, {})
        base_deliverables = template.get('key_deliverables', ['Final Output'])
        
        # Customize based on request content
        custom_deliverables = []
        request_lower = request.lower()
        
        if 'document' in request_lower:
            custom_deliverables.append('Documentation')
        if 'report' in request_lower:
            custom_deliverables.append('Report')
        if 'presentation' in request_lower:
            custom_deliverables.append('Presentation')
        if 'code' in request_lower:
            custom_deliverables.append('Source Code')
        if 'design' in request_lower:
            custom_deliverables.append('Design Assets')
        
        # Combine and deduplicate
        all_deliverables = list(set(base_deliverables + custom_deliverables))
        return all_deliverables[:6]  # Limit to top 6
    
    def _create_goal_summary(self, request: str) -> str:
        """Create a concise goal summary"""
        # Simple summarization - in production, use LLM
        if len(request) <= 100:
            return request
        
        # Extract first sentence or first 100 characters
        first_sentence = request.split('.')[0]
        if len(first_sentence) <= 150:
            return first_sentence + ('.' if not first_sentence.endswith('.') else '')
        
        return request[:100] + "..."
    
    def _create_task_breakdown(self, goal_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Create hierarchical task breakdown structure"""
        goal_type = goal_analysis['type']
        complexity = goal_analysis['complexity']
        
        # Get template phases
        template = self.planning_templates.get(goal_type, self.planning_templates['software_development'])
        base_phases = template['phases']
        
        # Create detailed task breakdown
        task_structure = {
            'total_phases': len(base_phases),
            'phases': []
        }
        
        for i, phase in enumerate(base_phases):
            phase_tasks = self._generate_phase_tasks(phase, goal_analysis, i)
            
            phase_info = {
                'phase_number': i + 1,
                'phase_name': phase,
                'description': self._get_phase_description(phase, goal_type),
                'tasks': phase_tasks,
                'estimated_duration': self._estimate_phase_duration(phase, complexity),
                'dependencies': [f"Phase {i}"] if i > 0 else [],
                'deliverables': self._get_phase_deliverables(phase, goal_analysis['deliverables'])
            }
            
            task_structure['phases'].append(phase_info)
        
        return task_structure
    
    def _generate_phase_tasks(self, phase: str, goal_analysis: Dict[str, Any], phase_number: int) -> List[Dict[str, str]]:
        """Generate specific tasks for a phase"""
        tasks = []
        
        # Phase-specific task templates
        phase_tasks_map = {
            'Analysis': [
                'Gather requirements', 'Define scope', 'Identify constraints',
                'Analyze stakeholder needs', 'Document specifications'
            ],
            'Design': [
                'Create system architecture', 'Design user interface',
                'Plan data structure', 'Create wireframes', 'Define APIs'
            ],
            'Implementation': [
                'Set up development environment', 'Implement core features',
                'Write code modules', 'Integrate components', 'Handle edge cases'
            ],
            'Testing': [
                'Create test cases', 'Execute unit tests', 'Perform integration testing',
                'User acceptance testing', 'Bug fixing'
            ],
            'Deployment': [
                'Prepare deployment environment', 'Deploy application',
                'Configure monitoring', 'Documentation update', 'Launch announcement'
            ],
            'Research': [
                'Literature review', 'Data collection', 'Initial analysis',
                'Hypothesis formation', 'Methodology design'
            ],
            'Planning': [
                'Define objectives', 'Create timeline', 'Allocate resources',
                'Risk assessment', 'Stakeholder alignment'
            ],
            'Creation': [
                'Create initial draft', 'Develop content', 'Add visual elements',
                'Format content', 'Quality review'
            ],
            'Review': [
                'Internal review', 'Stakeholder feedback', 'Revisions',
                'Final quality check', 'Approval process'
            ]
        }
        
        # Get tasks for this phase
        phase_task_templates = phase_tasks_map.get(phase, ['Execute phase tasks', 'Review progress', 'Document results'])
        
        # Create task objects
        for j, task_template in enumerate(phase_task_templates[:5]):  # Limit to 5 tasks per phase
            task = {
                'task_id': f"T{phase_number+1}.{j+1}",
                'task_name': task_template,
                'description': f"{task_template} for {phase} phase",
                'estimated_effort': self._estimate_task_effort(task_template, goal_analysis['complexity']),
                'required_skills': self._identify_task_skills(task_template)
            }
            tasks.append(task)
        
        return tasks
    
    def _get_phase_description(self, phase: str, goal_type: str) -> str:
        """Get description for a phase"""
        descriptions = {
            'Analysis': 'Understand requirements and define project scope',
            'Design': 'Create architectural and visual designs',
            'Implementation': 'Build and develop the solution',
            'Testing': 'Verify quality and functionality',
            'Deployment': 'Launch and make available to users',
            'Research': 'Gather information and insights',
            'Planning': 'Create detailed execution strategy',
            'Creation': 'Produce the main deliverables',
            'Review': 'Quality assurance and feedback incorporation',
            'Discovery': 'Explore and understand the problem space',
            'Concept': 'Develop initial ideas and concepts'
        }
        return descriptions.get(phase, f'Execute {phase} activities')
    
    def _estimate_phase_duration(self, phase: str, complexity: str) -> str:
        """Estimate duration for a phase"""
        base_durations = {
            'low': {
                'Analysis': '2-4 hours', 'Design': '4-8 hours', 'Implementation': '1-2 days',
                'Testing': '2-4 hours', 'Deployment': '1-2 hours', 'Research': '4-8 hours',
                'Planning': '1-2 hours', 'Creation': '4-8 hours', 'Review': '1-2 hours'
            },
            'medium': {
                'Analysis': '1-2 days', 'Design': '2-3 days', 'Implementation': '1-2 weeks',
                'Testing': '2-3 days', 'Deployment': '1 day', 'Research': '2-3 days',
                'Planning': '1 day', 'Creation': '2-3 days', 'Review': '1 day'
            },
            'high': {
                'Analysis': '1 week', 'Design': '1-2 weeks', 'Implementation': '2-4 weeks',
                'Testing': '1 week', 'Deployment': '2-3 days', 'Research': '1-2 weeks',
                'Planning': '2-3 days', 'Creation': '1-2 weeks', 'Review': '2-3 days'
            }
        }
        
        return base_durations.get(complexity, base_durations['medium']).get(phase, '1 day')
    
    def _get_phase_deliverables(self, phase: str, all_deliverables: List[str]) -> List[str]:
        """Get deliverables for a specific phase"""
        phase_deliverable_map = {
            'Analysis': ['Requirements Document', 'Project Scope'],
            'Design': ['Architecture Document', 'Design Mockups'],
            'Implementation': ['Source Code', 'Working Prototype'],
            'Testing': ['Test Results', 'Bug Reports'],
            'Deployment': ['Live System', 'Deployment Documentation'],
            'Research': ['Research Report', 'Data Analysis'],
            'Planning': ['Project Plan', 'Timeline'],
            'Creation': ['Content', 'Draft Materials'],
            'Review': ['Final Version', 'Quality Report']
        }
        
        return phase_deliverable_map.get(phase, ['Phase Output'])
    
    def _estimate_task_effort(self, task_name: str, complexity: str) -> str:
        """Estimate effort for individual task"""
        effort_map = {
            'low': '1-2 hours',
            'medium': '2-4 hours', 
            'high': '4-8 hours'
        }
        return effort_map.get(complexity, '2-4 hours')
    
    def _identify_task_skills(self, task_name: str) -> List[str]:
        """Identify required skills for a task"""
        skill_keywords = {
            'requirements': ['analysis', 'communication'],
            'design': ['design', 'creativity'],
            'code': ['programming', 'technical'],
            'test': ['testing', 'quality_assurance'],
            'deploy': ['devops', 'technical'],
            'research': ['research', 'analysis'],
            'write': ['writing', 'communication'],
            'review': ['review', 'quality_assurance']
        }
        
        task_lower = task_name.lower()
        skills = []
        
        for keyword, associated_skills in skill_keywords.items():
            if keyword in task_lower:
                skills.extend(associated_skills)
        
        return list(set(skills)) if skills else ['general']
    
    def _create_timeline(self, task_breakdown: Dict[str, Any], goal_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Create project timeline with milestones"""
        phases = task_breakdown['phases']
        
        # Calculate total duration
        total_duration_text = self._calculate_total_duration(phases)
        
        # Create milestone schedule
        milestones = []
        current_date = datetime.now()
        
        for i, phase in enumerate(phases):
            milestone = {
                'milestone_id': f"M{i+1}",
                'name': f"{phase['phase_name']} Complete",
                'description': f"Completion of {phase['phase_name']} phase",
                'target_date': self._calculate_phase_end_date(current_date, phase['estimated_duration'], i),
                'dependencies': phase['dependencies'],
                'deliverables': phase['deliverables']
            }
            milestones.append(milestone)
        
        # Identify critical path
        critical_path = [f"Phase {i+1}" for i in range(len(phases))]
        
        timeline = {
            'project_start': current_date.isoformat(),
            'estimated_completion': milestones[-1]['target_date'] if milestones else current_date.isoformat(),
            'total_duration': total_duration_text,
            'milestones': milestones,
            'critical_path': critical_path,
            'buffer_time': '10-20% recommended for unforeseen issues'
        }
        
        return timeline
    
    def _calculate_total_duration(self, phases: List[Dict[str, Any]]) -> str:
        """Calculate total project duration"""
        # Simple duration calculation - in production, use more sophisticated scheduling
        complexity_multipliers = {'low': 1, 'medium': 1.5, 'high': 2}
        base_duration = len(phases) * 3  # 3 days per phase average
        
        return f"{base_duration}-{int(base_duration * 1.5)} days"
    
    def _calculate_phase_end_date(self, start_date: datetime, duration_text: str, phase_index: int) -> str:
        """Calculate end date for a phase"""
        # Simple calculation - add days based on phase index
        days_to_add = (phase_index + 1) * 3  # 3 days per phase
        end_date = start_date + timedelta(days=days_to_add)
        return end_date.isoformat()
    
    def _identify_resources(self, task_breakdown: Dict[str, Any]) -> Dict[str, Any]:
        """Identify required resources"""
        all_skills = set()
        all_tools = set()
        
        # Collect all required skills from tasks
        for phase in task_breakdown['phases']:
            for task in phase['tasks']:
                all_skills.update(task['required_skills'])
        
        # Map skills to tools and roles
        skill_to_tools = {
            'programming': ['IDE', 'Version Control', 'Testing Framework'],
            'design': ['Design Software', 'Prototyping Tools'],
            'analysis': ['Analytics Tools', 'Documentation Tools'],
            'testing': ['Testing Tools', 'Bug Tracking'],
            'research': ['Research Tools', 'Data Collection Tools']
        }
        
        for skill in all_skills:
            if skill in skill_to_tools:
                all_tools.update(skill_to_tools[skill])
        
        # Determine team composition
        team_roles = self._determine_team_roles(all_skills)
        
        resources = {
            'human_resources': {
                'required_skills': list(all_skills),
                'team_roles': team_roles,
                'estimated_team_size': len(team_roles)
            },
            'tools_and_technology': {
                'required_tools': list(all_tools),
                'software_licenses': self._identify_licenses(all_tools),
                'hardware_requirements': self._identify_hardware_needs(all_skills)
            },
            'time_allocation': {
                'total_person_hours': self._estimate_total_hours(task_breakdown),
                'peak_resource_periods': self._identify_peak_periods(task_breakdown)
            }
        }
        
        return resources
    
    def _determine_team_roles(self, skills: set) -> List[str]:
        """Determine required team roles based on skills"""
        role_skill_map = {
            'Project Manager': ['planning', 'communication'],
            'Developer': ['programming', 'technical'],
            'Designer': ['design', 'creativity'],
            'Analyst': ['analysis', 'research'],
            'QA Tester': ['testing', 'quality_assurance'],
            'Writer': ['writing', 'communication']
        }
        
        required_roles = []
        for role, required_skills in role_skill_map.items():
            if any(skill in skills for skill in required_skills):
                required_roles.append(role)
        
        return required_roles if required_roles else ['Generalist']
    
    def _identify_licenses(self, tools: set) -> List[str]:
        """Identify required software licenses"""
        license_map = {
            'Design Software': 'Adobe Creative Suite or Figma Pro',
            'IDE': 'JetBrains IntelliJ or Visual Studio Pro',
            'Analytics Tools': 'Tableau or Power BI License'
        }
        
        licenses = []
        for tool in tools:
            if tool in license_map:
                licenses.append(license_map[tool])
        
        return licenses
    
    def _identify_hardware_needs(self, skills: set) -> List[str]:
        """Identify hardware requirements"""
        hardware_needs = ['Standard Development Machine']
        
        if 'design' in skills:
            hardware_needs.append('High-resolution Display')
        if 'programming' in skills:
            hardware_needs.append('Multi-core Processor, 16GB+ RAM')
        
        return hardware_needs
    
    def _estimate_total_hours(self, task_breakdown: Dict[str, Any]) -> str:
        """Estimate total person-hours required"""
        total_tasks = sum(len(phase['tasks']) for phase in task_breakdown['phases'])
        estimated_hours = total_tasks * 4  # 4 hours per task average
        
        return f"{estimated_hours}-{int(estimated_hours * 1.3)} hours"
    
    def _identify_peak_periods(self, task_breakdown: Dict[str, Any]) -> List[str]:
        """Identify periods of peak resource utilization"""
        # Implementation phase typically requires most resources
        peak_phases = []
        for phase in task_breakdown['phases']:
            if phase['phase_name'] in ['Implementation', 'Creation', 'Development']:
                peak_phases.append(f"Phase {phase['phase_number']}: {phase['phase_name']}")
        
        return peak_phases if peak_phases else ['Mid-project phases typically require peak resources']
    
    def _assess_risks(self, task_breakdown: Dict[str, Any], timeline: Dict[str, Any]) -> Dict[str, Any]:
        """Assess project risks and create mitigation strategies"""
        risks = []
        
        # Common project risks
        common_risks = [
            {
                'risk_id': 'R001',
                'category': 'Schedule',
                'description': 'Task duration may exceed estimates',
                'probability': 'Medium',
                'impact': 'High',
                'mitigation': 'Add 20% buffer time to critical path tasks'
            },
            {
                'risk_id': 'R002', 
                'category': 'Technical',
                'description': 'Technical challenges may arise during implementation',
                'probability': 'Medium',
                'impact': 'Medium',
                'mitigation': 'Conduct technical feasibility study early; have backup solutions'
            },
            {
                'risk_id': 'R003',
                'category': 'Resource',
                'description': 'Key team members may become unavailable',
                'probability': 'Low',
                'impact': 'High',
                'mitigation': 'Cross-train team members; maintain documentation'
            },
            {
                'risk_id': 'R004',
                'category': 'Scope',
                'description': 'Requirements may change during project',
                'probability': 'High',
                'impact': 'Medium',
                'mitigation': 'Implement change control process; regular stakeholder reviews'
            }
        ]
        
        risks.extend(common_risks)
        
        # Add project-specific risks based on complexity
        total_phases = task_breakdown['total_phases']
        if total_phases > 4:
            risks.append({
                'risk_id': 'R005',
                'category': 'Complexity',
                'description': 'High complexity may lead to coordination challenges',
                'probability': 'Medium',
                'impact': 'Medium',
                'mitigation': 'Implement regular checkpoint meetings; use project management tools'
            })
        
        risk_assessment = {
            'total_risks_identified': len(risks),
            'risk_categories': list(set(risk['category'] for risk in risks)),
            'high_impact_risks': [risk for risk in risks if risk['impact'] == 'High'],
            'risks': risks,
            'overall_risk_level': self._calculate_overall_risk_level(risks)
        }
        
        return risk_assessment
    
    def _calculate_overall_risk_level(self, risks: List[Dict[str, Any]]) -> str:
        """Calculate overall project risk level"""
        high_impact_count = len([r for r in risks if r['impact'] == 'High'])
        high_prob_count = len([r for r in risks if r['probability'] == 'High'])
        
        if high_impact_count >= 2 or high_prob_count >= 3:
            return 'High'
        elif high_impact_count >= 1 or high_prob_count >= 2:
            return 'Medium'
        else:
            return 'Low'
    
    def _define_success_criteria(self, goal_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Define project success criteria"""
        criteria = {
            'primary_objectives': goal_analysis['key_objectives'],
            'deliverable_criteria': [],
            'quality_standards': [],
            'performance_metrics': [],
            'stakeholder_satisfaction': []
        }
        
        # Define deliverable criteria
        for deliverable in goal_analysis['deliverables']:
            criteria['deliverable_criteria'].append(f"{deliverable} completed and approved")
        
        # Define quality standards
        criteria['quality_standards'] = [
            'All deliverables meet specified requirements',
            'Code/content passes quality review',
            'No critical defects in final output',
            'Documentation is complete and accurate'
        ]
        
        # Define performance metrics
        criteria['performance_metrics'] = [
            'Project completed within estimated timeline (+/- 20%)',
            'Budget stays within allocated range',
            'All major milestones achieved',
            'Stakeholder approval obtained'
        ]
        
        # Define stakeholder satisfaction criteria
        criteria['stakeholder_satisfaction'] = [
            'Client/requester approval of final deliverables',
            'Team satisfaction with process and outcomes',
            'End-user acceptance (if applicable)'
        ]
        
        return criteria
    
    def _format_task_breakdown(self, task_breakdown: Dict[str, Any]) -> str:
        """Format task breakdown for display"""
        formatted = f"Total Phases: {task_breakdown['total_phases']}\n\n"
        
        for phase in task_breakdown['phases']:
            formatted += f"Phase {phase['phase_number']}: {phase['phase_name']}\n"
            formatted += f"Description: {phase['description']}\n"
            formatted += f"Duration: {phase['estimated_duration']}\n"
            formatted += f"Deliverables: {', '.join(phase['deliverables'])}\n"
            
            formatted += "Tasks:\n"
            for task in phase['tasks']:
                formatted += f"  • {task['task_id']}: {task['task_name']} ({task['estimated_effort']})\n"
            
            formatted += "\n"
        
        return formatted
    
    def _format_timeline(self, timeline: Dict[str, Any]) -> str:
        """Format timeline for display"""
        formatted = f"Start Date: {timeline['project_start'][:10]}\n"
        formatted += f"Estimated Completion: {timeline['estimated_completion'][:10]}\n"
        formatted += f"Total Duration: {timeline['total_duration']}\n\n"
        
        formatted += "Milestones:\n"
        for milestone in timeline['milestones']:
            formatted += f"• {milestone['name']}: {milestone['target_date'][:10]}\n"
        
        formatted += f"\nCritical Path: {' → '.join(timeline['critical_path'])}\n"
        formatted += f"Buffer Recommendation: {timeline['buffer_time']}\n"
        
        return formatted
    
    def _format_resources(self, resources: Dict[str, Any]) -> str:
        """Format resources for display"""
        hr = resources['human_resources']
        tech = resources['tools_and_technology']
        time = resources['time_allocation']
        
        formatted = f"Team Size: {hr['estimated_team_size']} people\n"
        formatted += f"Required Roles: {', '.join(hr['team_roles'])}\n"
        formatted += f"Key Skills: {', '.join(hr['required_skills'])}\n\n"
        
        formatted += f"Tools Needed: {', '.join(tech['required_tools'])}\n"
        if tech['software_licenses']:
            formatted += f"Licenses Required: {', '.join(tech['software_licenses'])}\n"
        formatted += f"Hardware: {', '.join(tech['hardware_requirements'])}\n\n"
        
        formatted += f"Total Effort: {time['total_person_hours']}\n"
        if time['peak_resource_periods']:
            formatted += f"Peak Periods: {', '.join(time['peak_resource_periods'])}\n"
        
        return formatted
    
    def _format_risks(self, risk_assessment: Dict[str, Any]) -> str:
        """Format risk assessment for display"""
        formatted = f"Overall Risk Level: {risk_assessment['overall_risk_level']}\n"
        formatted += f"Total Risks: {risk_assessment['total_risks_identified']}\n"
        formatted += f"Categories: {', '.join(risk_assessment['risk_categories'])}\n\n"
        
        formatted += "Key Risks:\n"
        for risk in risk_assessment['risks'][:5]:  # Show top 5 risks
            formatted += f"• {risk['risk_id']}: {risk['description']}\n"
            formatted += f"  Impact: {risk['impact']}, Probability: {risk['probability']}\n"
            formatted += f"  Mitigation: {risk['mitigation']}\n\n"
        
        return formatted
    
    def _format_success_criteria(self, success_criteria: Dict[str, Any]) -> str:
        """Format success criteria for display"""
        formatted = "Primary Objectives:\n"
        for obj in success_criteria['primary_objectives']:
            formatted += f"• {obj}\n"
        
        formatted += "\nDeliverable Criteria:\n"
        for criteria in success_criteria['deliverable_criteria']:
            formatted += f"• {criteria}\n"
        
        formatted += "\nQuality Standards:\n"
        for standard in success_criteria['quality_standards']:
            formatted += f"• {standard}\n"
        
        formatted += "\nSuccess Metrics:\n"
        for metric in success_criteria['performance_metrics']:
            formatted += f"• {metric}\n"
        
        return formatted
    
    def _store_plan(self, plan_id: str, task: Dict[str, Any], goal_analysis: Dict[str, Any], 
                   task_breakdown: Dict[str, Any], timeline: Dict[str, Any], 
                   resources: Dict[str, Any], risk_assessment: Dict[str, Any], 
                   success_criteria: Dict[str, Any]):
        """Store the created plan for future reference"""
        plan = {
            'plan_id': plan_id,
            'created_at': datetime.now().isoformat(),
            'original_task': task,
            'goal_analysis': goal_analysis,
            'task_breakdown': task_breakdown,
            'timeline': timeline,
            'resources': resources,
            'risk_assessment': risk_assessment,
            'success_criteria': success_criteria,
            'status': 'created'
        }
        
        self.created_plans[plan_id] = plan
        
        # Keep only recent plans
        if len(self.created_plans) > 50:
            # Remove oldest plans
            oldest_plans = sorted(self.created_plans.keys())[:10]
            for old_plan_id in oldest_plans:
                del self.created_plans[old_plan_id]
    
    def get_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a previously created plan"""
        return self.created_plans.get(plan_id)
    
    def list_plans(self) -> List[Dict[str, str]]:
        """List all stored plans"""
        return [
            {
                'plan_id': plan_id,
                'created_at': plan['created_at'],
                'goal_summary': plan['goal_analysis']['summary'],
                'status': plan['status']
            }
            for plan_id, plan in self.created_plans.items()
        ]
