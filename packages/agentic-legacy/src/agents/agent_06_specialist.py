"""
Agent 06 (Specialist) - Domain Expertise: Security, Legal, AI Tuning, etc.
"""

from typing import Dict, List, Any, Optional
import json
from datetime import datetime

from ..core.base_agent import BaseAgent

class Agent06Specialist(BaseAgent):
    """Domain specialist agent for expert consultation"""
    
    def __init__(self, config_path: str = "config/prompts.yaml"):
        super().__init__("agent_06_specialist", config_path)
        self.specializations = self._load_specializations()
        self.consultation_history = []
        
    def _load_specializations(self) -> Dict[str, Any]:
        """Load specialization knowledge bases"""
        return {
            'security': {
                'frameworks': ['OWASP', 'NIST', 'ISO 27001', 'SOC 2'],
                'common_vulnerabilities': ['SQL Injection', 'XSS', 'CSRF', 'Authentication flaws'],
                'best_practices': [
                    'Input validation and sanitization',
                    'Secure authentication mechanisms', 
                    'Regular security audits',
                    'Principle of least privilege'
                ]
            },
            'legal_compliance': {
                'regulations': ['GDPR', 'CCPA', 'HIPAA', 'SOX', 'PCI DSS'],
                'key_requirements': [
                    'Data protection and privacy',
                    'Audit trails and logging',
                    'User consent mechanisms',
                    'Data retention policies'
                ]
            },
            'ai_ml_optimization': {
                'model_types': ['Neural Networks', 'Random Forest', 'SVM', 'Gradient Boosting'],
                'optimization_techniques': [
                    'Hyperparameter tuning',
                    'Feature engineering',
                    'Model ensembling',
                    'Cross-validation'
                ],
                'performance_metrics': ['Accuracy', 'Precision', 'Recall', 'F1-Score', 'AUC-ROC']
            },
            'financial_analysis': {
                'metrics': ['ROI', 'NPV', 'IRR', 'EBITDA', 'Cash Flow'],
                'analysis_types': [
                    'Cost-benefit analysis',
                    'Risk assessment',
                    'Budget planning',
                    'Financial forecasting'
                ]
            },
            'architecture': {
                'patterns': ['Microservices', 'Event-driven', 'Layered', 'Hexagonal'],
                'scalability_factors': [
                    'Load balancing',
                    'Caching strategies',
                    'Database sharding',
                    'CDN implementation'
                ]
            },
            'quality_assurance': {
                'testing_types': ['Unit', 'Integration', 'System', 'Acceptance', 'Performance'],
                'methodologies': ['TDD', 'BDD', 'Agile Testing', 'Risk-based Testing'],
                'tools': ['Selenium', 'Jest', 'Postman', 'JMeter', 'SonarQube']
            }
        }
    
    def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Provide specialist domain expertise"""
        
        if not self.validate_input(task):
            return self.handle_error(Exception("Invalid task format"), task)
        
        try:
            self.update_status("analyzing", task)
            
            # Identify required specialization
            domain_analysis = self._analyze_domain_requirements(task)
            
            # Perform specialist analysis
            expert_findings = self._conduct_specialist_analysis(domain_analysis, task)
            
            # Generate recommendations
            recommendations = self._generate_expert_recommendations(expert_findings, domain_analysis)
            
            # Assess risks and compliance
            risk_compliance = self._assess_risks_and_compliance(expert_findings, domain_analysis)
            
            # Create implementation guidance
            implementation = self._create_implementation_guidance(recommendations, expert_findings)
            
            # Identify optimization opportunities
            optimization = self._identify_optimization_opportunities(expert_findings)
            
            self.update_status("ready")
            
            # Prepare expert response
            response_content = f"""
🔬 DOMAIN ANALYSIS: {domain_analysis['summary']}

📊 EXPERT FINDINGS:
{self._format_expert_findings(expert_findings)}

💡 RECOMMENDATIONS:
{self._format_recommendations(recommendations)}

⚠️ RISKS & COMPLIANCE:
{self._format_risks_compliance(risk_compliance)}

🎯 IMPLEMENTATION:
{self._format_implementation_guidance(implementation)}

📈 OPTIMIZATION:
{self._format_optimization_opportunities(optimization)}
            """
            
            # Log consultation
            self._log_consultation(task, domain_analysis, expert_findings, recommendations)
            
            return self.format_response(response_content.strip(), "specialist_consultation")
            
        except Exception as e:
            return self.handle_error(e, task)
    
    def _analyze_domain_requirements(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze which domain expertise is needed"""
        request = task.get('request', '')
        context = task.get('context', {})
        
        # Identify primary domain
        primary_domain = self._identify_primary_domain(request)
        
        # Identify secondary domains
        secondary_domains = self._identify_secondary_domains(request)
        
        # Assess complexity level
        complexity = self._assess_domain_complexity(request, primary_domain)
        
        analysis = {
            'summary': self._create_domain_summary(request, primary_domain),
            'primary_domain': primary_domain,
            'secondary_domains': secondary_domains,
            'complexity': complexity,
            'consultation_type': self._determine_consultation_type(request),
            'stakeholders': self._identify_domain_stakeholders(primary_domain, context)
        }
        
        return analysis
    
    def _identify_primary_domain(self, request: str) -> str:
        """Identify primary domain of expertise needed"""
        request_lower = request.lower()
        
        domain_keywords = {
            'security': ['security', 'vulnerability', 'encryption', 'authentication', 'authorization', 'owasp'],
            'legal_compliance': ['legal', 'compliance', 'gdpr', 'privacy', 'regulation', 'audit'],
            'ai_ml_optimization': ['ai', 'machine learning', 'model', 'algorithm', 'neural network', 'optimization'],
            'financial_analysis': ['financial', 'cost', 'budget', 'roi', 'revenue', 'profit'],
            'architecture': ['architecture', 'scalability', 'performance', 'microservices', 'system design'],
            'quality_assurance': ['testing', 'quality', 'qa', 'validation', 'verification']
        }
        
        # Score each domain
        domain_scores = {}
        for domain, keywords in domain_keywords.items():
            score = sum(1 for keyword in keywords if keyword in request_lower)
            if score > 0:
                domain_scores[domain] = score
        
        # Return domain with highest score
        if domain_scores:
            return max(domain_scores, key=domain_scores.get)
        
        return 'general'
    
    def _identify_secondary_domains(self, request: str) -> List[str]:
        """Identify secondary domains that may be relevant"""
        primary = self._identify_primary_domain(request)
        request_lower = request.lower()
        
        secondary = []
        
        # Cross-domain relationships
        if primary == 'security' and any(word in request_lower for word in ['compliance', 'regulation']):
            secondary.append('legal_compliance')
        
        if primary == 'ai_ml_optimization' and any(word in request_lower for word in ['performance', 'scale']):
            secondary.append('architecture')
        
        if any(word in request_lower for word in ['cost', 'budget']) and primary != 'financial_analysis':
            secondary.append('financial_analysis')
        
        if any(word in request_lower for word in ['test', 'quality']) and primary != 'quality_assurance':
            secondary.append('quality_assurance')
        
        return secondary
    
    def _assess_domain_complexity(self, request: str, domain: str) -> str:
        """Assess complexity level of domain consultation"""
        request_lower = request.lower()
        
        high_complexity_indicators = [
            'enterprise', 'complex', 'multiple', 'integration', 'advanced', 'sophisticated'
        ]
        
        medium_complexity_indicators = [
            'implementation', 'deployment', 'optimization', 'analysis'
        ]
        
        if any(indicator in request_lower for indicator in high_complexity_indicators):
            return 'high'
        elif any(indicator in request_lower for indicator in medium_complexity_indicators):
            return 'medium'
        else:
            return 'low'
    
    def _conduct_specialist_analysis(self, domain_analysis: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
        """Conduct in-depth specialist analysis"""
        primary_domain = domain_analysis['primary_domain']
        request = task.get('request', '')
        
        findings = {
            'domain': primary_domain,
            'analysis_type': domain_analysis['consultation_type'],
            'key_findings': [],
            'technical_assessment': {},
            'best_practices_applicable': [],
            'industry_standards': [],
            'potential_issues': []
        }
        
        if primary_domain in self.specializations:
            spec = self.specializations[primary_domain]
            findings.update(self._analyze_specific_domain(spec, request, primary_domain))
        
        return findings
    
    def _analyze_specific_domain(self, specialization: Dict[str, Any], request: str, domain: str) -> Dict[str, Any]:
        """Analyze specific domain based on specialization knowledge"""
        analysis = {}
        
        if domain == 'security':
            analysis = self._analyze_security_domain(specialization, request)
        elif domain == 'legal_compliance':
            analysis = self._analyze_legal_domain(specialization, request)
        elif domain == 'ai_ml_optimization':
            analysis = self._analyze_ai_ml_domain(specialization, request)
        elif domain == 'financial_analysis':
            analysis = self._analyze_financial_domain(specialization, request)
        elif domain == 'architecture':
            analysis = self._analyze_architecture_domain(specialization, request)
        elif domain == 'quality_assurance':
            analysis = self._analyze_qa_domain(specialization, request)
        
        return analysis
    
    def _analyze_security_domain(self, spec: Dict[str, Any], request: str) -> Dict[str, Any]:
        """Analyze security domain"""
        request_lower = request.lower()
        
        # Check for vulnerability indicators
        vulnerabilities = []
        for vuln in spec['common_vulnerabilities']:
            if any(keyword in request_lower for keyword in vuln.lower().split()):
                vulnerabilities.append(vuln)
        
        # Identify applicable frameworks
        frameworks = []
        for framework in spec['frameworks']:
            if framework.lower() in request_lower:
                frameworks.append(framework)
        
        return {
            'key_findings': [
                f"Security assessment required for: {request[:100]}...",
                f"Potential vulnerabilities identified: {len(vulnerabilities)}",
                f"Applicable frameworks: {', '.join(frameworks) if frameworks else 'Standard security practices'}"
            ],
            'technical_assessment': {
                'vulnerability_risk': 'Medium' if vulnerabilities else 'Low',
                'compliance_frameworks': frameworks,
                'security_maturity': self._assess_security_maturity(request_lower)
            },
            'best_practices_applicable': spec['best_practices'],
            'industry_standards': spec['frameworks'],
            'potential_issues': vulnerabilities
        }
    
    def _analyze_legal_domain(self, spec: Dict[str, Any], request: str) -> Dict[str, Any]:
        """Analyze legal compliance domain"""
        request_lower = request.lower()
        
        # Check applicable regulations
        applicable_regs = []
        for reg in spec['regulations']:
            if reg.lower() in request_lower or any(keyword in request_lower for keyword in reg.split()):
                applicable_regs.append(reg)
        
        return {
            'key_findings': [
                f"Legal compliance analysis for: {request[:100]}...",
                f"Applicable regulations: {', '.join(applicable_regs) if applicable_regs else 'General compliance'}",
                "Privacy and data protection considerations identified"
            ],
            'technical_assessment': {
                'compliance_risk': 'High' if 'data' in request_lower else 'Medium',
                'applicable_regulations': applicable_regs,
                'privacy_requirements': 'data' in request_lower or 'user' in request_lower
            },
            'best_practices_applicable': spec['key_requirements'],
            'industry_standards': spec['regulations'],
            'potential_issues': ['Data privacy compliance', 'Audit trail requirements']
        }
    
    def _analyze_ai_ml_domain(self, spec: Dict[str, Any], request: str) -> Dict[str, Any]:
        """Analyze AI/ML optimization domain"""
        request_lower = request.lower()
        
        # Identify model types mentioned
        model_types = []
        for model in spec['model_types']:
            if any(keyword in request_lower for keyword in model.lower().split()):
                model_types.append(model)
        
        return {
            'key_findings': [
                f"AI/ML optimization analysis for: {request[:100]}...",
                f"Model types identified: {', '.join(model_types) if model_types else 'General ML approach'}",
                "Performance optimization opportunities available"
            ],
            'technical_assessment': {
                'model_complexity': 'High' if 'neural' in request_lower else 'Medium',
                'optimization_potential': 'High',
                'performance_metrics_needed': spec['performance_metrics']
            },
            'best_practices_applicable': spec['optimization_techniques'],
            'industry_standards': spec['model_types'],
            'potential_issues': ['Overfitting', 'Data quality', 'Model interpretability']
        }
    
    def _analyze_financial_domain(self, spec: Dict[str, Any], request: str) -> Dict[str, Any]:
        """Analyze financial analysis domain"""
        return {
            'key_findings': [
                f"Financial analysis for: {request[:100]}...",
                "ROI and cost-benefit analysis recommended",
                "Budget and resource planning considerations"
            ],
            'technical_assessment': {
                'financial_impact': 'Medium to High',
                'roi_potential': 'Positive',
                'risk_level': 'Medium'
            },
            'best_practices_applicable': spec['analysis_types'],
            'industry_standards': spec['metrics'],
            'potential_issues': ['Budget overruns', 'ROI timeline', 'Resource allocation']
        }
    
    def _analyze_architecture_domain(self, spec: Dict[str, Any], request: str) -> Dict[str, Any]:
        """Analyze architecture domain"""
        request_lower = request.lower()
        
        # Identify patterns mentioned
        patterns = []
        for pattern in spec['patterns']:
            if pattern.lower() in request_lower:
                patterns.append(pattern)
        
        return {
            'key_findings': [
                f"Architecture analysis for: {request[:100]}...",
                f"Architectural patterns: {', '.join(patterns) if patterns else 'Traditional architecture'}",
                "Scalability and performance considerations identified"
            ],
            'technical_assessment': {
                'scalability_requirements': 'High' if 'scale' in request_lower else 'Medium',
                'performance_requirements': 'High' if 'performance' in request_lower else 'Medium',
                'complexity_level': 'High' if patterns else 'Medium'
            },
            'best_practices_applicable': spec['scalability_factors'],
            'industry_standards': spec['patterns'],
            'potential_issues': ['Performance bottlenecks', 'Scalability limits', 'Maintenance complexity']
        }
    
    def _analyze_qa_domain(self, spec: Dict[str, Any], request: str) -> Dict[str, Any]:
        """Analyze quality assurance domain"""
        request_lower = request.lower()
        
        # Identify testing types needed
        testing_types = []
        for test_type in spec['testing_types']:
            if test_type.lower() in request_lower:
                testing_types.append(test_type)
        
        return {
            'key_findings': [
                f"QA analysis for: {request[:100]}...",
                f"Testing types recommended: {', '.join(testing_types) if testing_types else 'Comprehensive testing'}",
                "Quality assurance strategy needed"
            ],
            'technical_assessment': {
                'testing_coverage_needed': '80%+',
                'automation_potential': 'High',
                'quality_risk': 'Medium'
            },
            'best_practices_applicable': spec['methodologies'],
            'industry_standards': spec['tools'],
            'potential_issues': ['Test coverage gaps', 'Manual testing overhead', 'Quality metrics']
        }
    
    def _generate_expert_recommendations(self, findings: Dict[str, Any], domain_analysis: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate expert recommendations"""
        recommendations = []
        
        domain = findings['domain']
        complexity = domain_analysis['complexity']
        
        # Domain-specific recommendations
        if domain == 'security':
            recommendations.extend([
                {
                    'category': 'Immediate Actions',
                    'recommendation': 'Implement security assessment and vulnerability scanning',
                    'priority': 'High',
                    'timeline': '1-2 weeks'
                },
                {
                    'category': 'Best Practices',
                    'recommendation': 'Establish secure coding guidelines and security review process',
                    'priority': 'Medium',
                    'timeline': '2-4 weeks'
                }
            ])
        
        elif domain == 'ai_ml_optimization':
            recommendations.extend([
                {
                    'category': 'Model Optimization',
                    'recommendation': 'Implement hyperparameter tuning and cross-validation',
                    'priority': 'High',
                    'timeline': '1-3 weeks'
                },
                {
                    'category': 'Performance',
                    'recommendation': 'Establish model monitoring and performance tracking',
                    'priority': 'Medium',
                    'timeline': '2-4 weeks'
                }
            ])
        
        # Complexity-based recommendations
        if complexity == 'high':
            recommendations.append({
                'category': 'Project Management',
                'recommendation': 'Consider phased implementation with expert consultation',
                'priority': 'High',
                'timeline': 'Throughout project'
            })
        
        # General recommendations
        recommendations.append({
            'category': 'Documentation',
            'recommendation': 'Create comprehensive documentation and knowledge transfer plan',
            'priority': 'Medium',
            'timeline': 'Ongoing'
        })
        
        return recommendations
    
    def _assess_risks_and_compliance(self, findings: Dict[str, Any], domain_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Assess risks and compliance requirements"""
        domain = findings['domain']
        
        risk_assessment = {
            'overall_risk_level': self._calculate_overall_risk(findings, domain_analysis),
            'specific_risks': findings.get('potential_issues', []),
            'compliance_requirements': [],
            'mitigation_strategies': [],
            'monitoring_requirements': []
        }
        
        # Domain-specific risk assessment
        if domain == 'security':
            risk_assessment['compliance_requirements'] = ['Security audit', 'Penetration testing', 'Compliance certification']
            risk_assessment['mitigation_strategies'] = ['Multi-factor authentication', 'Regular security updates', 'Security training']
            
        elif domain == 'legal_compliance':
            risk_assessment['compliance_requirements'] = ['Legal review', 'Privacy impact assessment', 'Compliance monitoring']
            risk_assessment['mitigation_strategies'] = ['Privacy by design', 'Regular compliance audits', 'Staff training']
            
        elif domain == 'ai_ml_optimization':
            risk_assessment['compliance_requirements'] = ['Model validation', 'Bias testing', 'Performance monitoring']
            risk_assessment['mitigation_strategies'] = ['Data quality checks', 'Model versioning', 'A/B testing']
        
        # Monitoring requirements
        risk_assessment['monitoring_requirements'] = [
            'Regular risk assessments',
            'Performance monitoring',
            'Compliance tracking',
            'Incident response procedures'
        ]
        
        return risk_assessment
    
    def _create_implementation_guidance(self, recommendations: List[Dict[str, str]], findings: Dict[str, Any]) -> Dict[str, Any]:
        """Create implementation guidance"""
        
        # Organize recommendations by priority
        high_priority = [r for r in recommendations if r.get('priority') == 'High']
        medium_priority = [r for r in recommendations if r.get('priority') == 'Medium']
        
        guidance = {
            'implementation_phases': [
                {
                    'phase': 1,
                    'name': 'Immediate Actions',
                    'duration': '1-2 weeks',
                    'actions': [r['recommendation'] for r in high_priority]
                },
                {
                    'phase': 2,
                    'name': 'Foundation Building',
                    'duration': '2-4 weeks', 
                    'actions': [r['recommendation'] for r in medium_priority]
                },
                {
                    'phase': 3,
                    'name': 'Optimization & Monitoring',
                    'duration': 'Ongoing',
                    'actions': ['Continuous monitoring', 'Regular reviews', 'Process improvements']
                }
            ],
            'success_criteria': self._define_success_criteria(findings),
            'resource_requirements': self._identify_implementation_resources(findings),
            'timeline_estimate': self._estimate_implementation_timeline(recommendations)
        }
        
        return guidance
    
    def _identify_optimization_opportunities(self, findings: Dict[str, Any]) -> Dict[str, Any]:
        """Identify optimization opportunities"""
        domain = findings['domain']
        
        opportunities = {
            'performance_improvements': [],
            'cost_optimizations': [],
            'process_enhancements': [],
            'technology_upgrades': [],
            'efficiency_gains': []
        }
        
        # Domain-specific optimizations
        if domain == 'security':
            opportunities['performance_improvements'] = ['Automated security scanning', 'Security testing integration']
            opportunities['process_enhancements'] = ['Security review automation', 'Threat modeling']
            
        elif domain == 'ai_ml_optimization':
            opportunities['performance_improvements'] = ['Model optimization', 'Feature engineering', 'Ensemble methods']
            opportunities['cost_optimizations'] = ['Cloud resource optimization', 'Model compression']
            
        elif domain == 'architecture':
            opportunities['performance_improvements'] = ['Caching strategies', 'Load balancing', 'Database optimization']
            opportunities['cost_optimizations'] = ['Resource right-sizing', 'Auto-scaling implementation']
        
        # General optimizations
        opportunities['efficiency_gains'] = [
            'Process automation',
            'Tool integration',
            'Knowledge sharing',
            'Continuous improvement'
        ]
        
        return opportunities
    
    # Helper methods
    def _assess_security_maturity(self, request: str) -> str:
        """Assess security maturity level"""
        mature_indicators = ['security policy', 'audit', 'compliance', 'framework']
        basic_indicators = ['password', 'authentication', 'basic security']
        
        if any(indicator in request for indicator in mature_indicators):
            return 'Mature'
        elif any(indicator in request for indicator in basic_indicators):
            return 'Developing'
        else:
            return 'Basic'
    
    def _calculate_overall_risk(self, findings: Dict[str, Any], domain_analysis: Dict[str, Any]) -> str:
        """Calculate overall risk level"""
        domain = findings['domain']
        complexity = domain_analysis['complexity']
        issues_count = len(findings.get('potential_issues', []))
        
        # Risk scoring
        risk_score = 0
        
        if domain in ['security', 'legal_compliance']:
            risk_score += 2
        elif domain in ['ai_ml_optimization', 'architecture']:
            risk_score += 1
        
        if complexity == 'high':
            risk_score += 2
        elif complexity == 'medium':
            risk_score += 1
        
        risk_score += min(issues_count, 3)  # Cap at 3 for issues
        
        if risk_score >= 5:
            return 'High'
        elif risk_score >= 3:
            return 'Medium'
        else:
            return 'Low'
    
    def _define_success_criteria(self, findings: Dict[str, Any]) -> List[str]:
        """Define success criteria for implementation"""
        domain = findings['domain']
        
        criteria = [
            'All recommendations implemented successfully',
            'Risk mitigation strategies in place',
            'Compliance requirements met'
        ]
        
        # Domain-specific criteria
        if domain == 'security':
            criteria.extend(['Security vulnerabilities addressed', 'Security audit passed'])
        elif domain == 'ai_ml_optimization':
            criteria.extend(['Model performance improved', 'Monitoring system operational'])
        elif domain == 'quality_assurance':
            criteria.extend(['Test coverage targets met', 'Quality metrics established'])
        
        return criteria
    
    def _identify_implementation_resources(self, findings: Dict[str, Any]) -> Dict[str, Any]:
        """Identify resources needed for implementation"""
        domain = findings['domain']
        
        resources = {
            'human_resources': ['Domain specialist', 'Implementation team'],
            'tools_software': [],
            'training_requirements': [],
            'external_services': []
        }
        
        # Domain-specific resources
        if domain == 'security':
            resources['tools_software'] = ['Security scanning tools', 'Vulnerability management system']
            resources['training_requirements'] = ['Security awareness training', 'Secure coding training']
            resources['external_services'] = ['Security audit firm', 'Penetration testing service']
            
        elif domain == 'ai_ml_optimization':
            resources['tools_software'] = ['ML platforms', 'Model monitoring tools', 'Data pipeline tools']
            resources['training_requirements'] = ['ML engineering training', 'Model optimization techniques']
            
        return resources
    
    def _estimate_implementation_timeline(self, recommendations: List[Dict[str, str]]) -> str:
        """Estimate implementation timeline"""
        high_priority_count = len([r for r in recommendations if r.get('priority') == 'High'])
        total_recommendations = len(recommendations)
        
        if total_recommendations <= 3:
            return '2-4 weeks'
        elif total_recommendations <= 6:
            return '4-8 weeks'
        else:
            return '8-12 weeks'
    
    # Formatting methods
    def _create_domain_summary(self, request: str, domain: str) -> str:
        """Create domain analysis summary"""
        if len(request) <= 100:
            summary = request
        else:
            summary = request[:100] + "..."
        
        return f"{domain.replace('_', ' ').title()} consultation for: {summary}"
    
    def _determine_consultation_type(self, request: str) -> str:
        """Determine type of consultation needed"""
        request_lower = request.lower()
        
        if any(word in request_lower for word in ['review', 'audit', 'assessment']):
            return 'review_audit'
        elif any(word in request_lower for word in ['implement', 'deploy', 'build']):
            return 'implementation'
        elif any(word in request_lower for word in ['optimize', 'improve', 'enhance']):
            return 'optimization'
        else:
            return 'consultation'
    
    def _identify_domain_stakeholders(self, domain: str, context: Dict[str, Any]) -> List[str]:
        """Identify stakeholders for domain consultation"""
        stakeholders = ['Requesting team']
        
        stakeholder_mapping = {
            'security': ['Security team', 'Compliance officer', 'IT management'],
            'legal_compliance': ['Legal team', 'Compliance officer', 'Data protection officer'],
            'ai_ml_optimization': ['Data science team', 'ML engineers', 'Product team'],
            'financial_analysis': ['Finance team', 'Budget owners', 'Executive team'],
            'architecture': ['Architecture team', 'Engineering leads', 'Operations team'],
            'quality_assurance': ['QA team', 'Development team', 'Product team']
        }
        
        domain_stakeholders = stakeholder_mapping.get(domain, [])
        stakeholders.extend(domain_stakeholders)
        
        return stakeholders
    
    def _format_expert_findings(self, findings: Dict[str, Any]) -> str:
        """Format expert findings for display"""
        formatted = f"Domain: {findings['domain'].replace('_', ' ').title()}\n\n"
        
        for finding in findings['key_findings']:
            formatted += f"• {finding}\n"
        
        if findings.get('technical_assessment'):
            formatted += "\nTechnical Assessment:\n"
            for key, value in findings['technical_assessment'].items():
                formatted += f"  {key.replace('_', ' ').title()}: {value}\n"
        
        return formatted
    
    def _format_recommendations(self, recommendations: List[Dict[str, str]]) -> str:
        """Format recommendations for display"""
        formatted = ""
        
        # Group by priority
        high_priority = [r for r in recommendations if r.get('priority') == 'High']
        medium_priority = [r for r in recommendations if r.get('priority') == 'Medium']
        
        if high_priority:
            formatted += "🔴 HIGH PRIORITY:\n"
            for rec in high_priority:
                formatted += f"• {rec['recommendation']} ({rec.get('timeline', 'TBD')})\n"
            formatted += "\n"
        
        if medium_priority:
            formatted += "🟡 MEDIUM PRIORITY:\n"
            for rec in medium_priority:
                formatted += f"• {rec['recommendation']} ({rec.get('timeline', 'TBD')})\n"
        
        return formatted
    
    def _format_risks_compliance(self, risk_assessment: Dict[str, Any]) -> str:
        """Format risks and compliance for display"""
        formatted = f"Overall Risk Level: {risk_assessment['overall_risk_level']}\n\n"
        
        if risk_assessment['specific_risks']:
            formatted += "Specific Risks:\n"
            for risk in risk_assessment['specific_risks']:
                formatted += f"• {risk}\n"
            formatted += "\n"
        
        if risk_assessment['compliance_requirements']:
            formatted += "Compliance Requirements:\n"
            for req in risk_assessment['compliance_requirements']:
                formatted += f"• {req}\n"
            formatted += "\n"
        
        if risk_assessment['mitigation_strategies']:
            formatted += "Mitigation Strategies:\n"
            for strategy in risk_assessment['mitigation_strategies'][:3]:
                formatted += f"• {strategy}\n"
        
        return formatted
    
    def _format_implementation_guidance(self, implementation: Dict[str, Any]) -> str:
        """Format implementation guidance for display"""
        formatted = f"Timeline: {implementation['timeline_estimate']}\n\n"
        
        formatted += "Implementation Phases:\n"
        for phase in implementation['implementation_phases']:
            formatted += f"{phase['phase']}. {phase['name']} ({phase['duration']})\n"
            for action in phase['actions'][:2]:  # Show first 2 actions
                formatted += f"   • {action}\n"
            formatted += "\n"
        
        return formatted
    
    def _format_optimization_opportunities(self, opportunities: Dict[str, Any]) -> str:
        """Format optimization opportunities for display"""
        formatted = ""
        
        for category, items in opportunities.items():
            if items:
                formatted += f"{category.replace('_', ' ').title()}:\n"
                for item in items[:2]:  # Show first 2 items per category
                    formatted += f"• {item}\n"
                formatted += "\n"
        
        return formatted
    
    def _log_consultation(self, task: Dict[str, Any], domain_analysis: Dict[str, Any], 
                         findings: Dict[str, Any], recommendations: List[Dict[str, str]]):
        """Log consultation for history tracking"""
        consultation_log = {
            'timestamp': datetime.now().isoformat(),
            'task_id': task.get('task_id'),
            'domain': domain_analysis['primary_domain'],
            'complexity': domain_analysis['complexity'],
            'findings_summary': findings['key_findings'],
            'recommendations_count': len(recommendations),
            'consultation_type': domain_analysis['consultation_type']
        }
        
        self.consultation_history.append(consultation_log)
        
        # Keep only recent consultations
        if len(self.consultation_history) > 100:
            self.consultation_history = self.consultation_history[-50:]
