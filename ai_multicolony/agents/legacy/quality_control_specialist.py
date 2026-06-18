"""
🔍 Quality Control Specialist - Visual and Analytical Assessment Agent
Advanced AI agent for comprehensive quality control, analysis, and validation

Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

import asyncio
import json
import logging
import hashlib
import base64
import io
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from pathlib import Path
import requests
import subprocess
import threading

# Heavy dependencies - made optional for graceful degradation
try:
    import cv2
except ImportError:
    cv2 = None

try:
    import numpy as np
except ImportError:
    np = None

try:
    from PIL import Image, ImageEnhance, ImageFilter
except ImportError:
    Image = None
    ImageEnhance = None
    ImageFilter = None

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

try:
    import seaborn as sns
except ImportError:
    sns = None

try:
    import pandas as pd
except ImportError:
    pd = None

@dataclass
class QualityAssessment:
    """Quality assessment result data structure"""
    assessment_id: str
    item_type: str  # code, image, document, system, process
    assessment_type: str  # visual, analytical, performance, security
    score: float  # 0-100 quality score
    issues_found: List[Dict[str, Any]]
    recommendations: List[str]
    assessment_time: datetime
    assessor: str = "Quality Control Specialist"
    metadata: Dict[str, Any] = None

@dataclass
class QualityMetrics:
    """Quality metrics tracking"""
    total_assessments: int
    average_score: float
    pass_rate: float
    critical_issues: int
    improvement_trends: Dict[str, float]
    last_updated: datetime

class QualityControlSpecialist:
    """
    Quality Control Specialist: Comprehensive quality assessment and validation
    
    Capabilities:
    - 🔍 Visual quality assessment
    - 📊 Analytical quality evaluation
    - 🧪 Performance testing and analysis
    - 🔒 Security quality validation
    - 📈 Quality metrics tracking
    - 🎯 Issue detection and classification
    - 💡 Improvement recommendations
    - 📋 Quality reporting and documentation
    """
    
    def __init__(self):
        self.agent_id = "quality_control_specialist"
        self.name = "Quality Control Specialist"
        self.status = "initializing"
        self.version = "1.0.0"
        self.start_time = datetime.now()
        
        # Core capabilities
        self.capabilities = [
            "visual_assessment",
            "analytical_evaluation",
            "performance_testing",
            "security_validation",
            "metrics_tracking",
            "issue_detection",
            "improvement_analysis",
            "quality_reporting"
        ]
        
        # Assessment history
        self.assessments = {}
        self.quality_metrics = QualityMetrics(
            total_assessments=0,
            average_score=0.0,
            pass_rate=0.0,
            critical_issues=0,
            improvement_trends={},
            last_updated=datetime.now()
        )
        
        # Quality standards
        self.quality_standards = {
            "code": {
                "minimum_score": 75.0,
                "critical_issues": ["security_vulnerability", "memory_leak", "infinite_loop"],
                "best_practices": ["documentation", "testing", "error_handling", "code_style"]
            },
            "image": {
                "minimum_score": 80.0,
                "quality_factors": ["resolution", "clarity", "composition", "lighting"],
                "technical_requirements": ["format", "size", "compression"]
            },
            "system": {
                "minimum_score": 85.0,
                "performance_metrics": ["response_time", "throughput", "reliability"],
                "security_checks": ["authentication", "authorization", "encryption"]
            },
            "process": {
                "minimum_score": 70.0,
                "efficiency_metrics": ["automation_level", "error_rate", "completion_time"],
                "compliance_checks": ["standards_adherence", "documentation", "traceability"]
            }
        }
        
        # Assessment tools
        self.assessment_tools = {
            "code_analyzers": ["pylint", "flake8", "bandit", "mypy"],
            "image_processors": ["opencv", "pillow", "skimage"],
            "performance_testers": ["pytest", "locust", "ab"],
            "security_scanners": ["semgrep", "safety", "pip-audit"]
        }
        
        # Initialize logging
        self.setup_logging()
        
        # Initialize assessment environment
        self.initialize_assessment_environment()
        
        self.logger.info("Quality Control Specialist initialized successfully")
        self.status = "ready"
    
    def setup_logging(self):
        """Setup logging for Quality Control Specialist"""
        log_dir = Path("data/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "quality_control.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("QualityControlSpecialist")
    
    def initialize_assessment_environment(self):
        """Initialize quality assessment environment"""
        # Create assessment directories
        assessment_dirs = [
            "data/quality_assessments",
            "data/quality_reports", 
            "data/quality_metrics",
            "data/quality_standards"
        ]
        
        for directory in assessment_dirs:
            Path(directory).mkdir(parents=True, exist_ok=True)
        
        # Load existing quality standards if available
        self.load_quality_standards()
    
    def load_quality_standards(self):
        """Load custom quality standards"""
        standards_file = Path("data/quality_standards/custom_standards.json")
        if standards_file.exists():
            try:
                with open(standards_file, 'r') as f:
                    custom_standards = json.load(f)
                    self.quality_standards.update(custom_standards)
                    self.logger.info("Custom quality standards loaded")
            except Exception as e:
                self.logger.error(f"Failed to load custom standards: {e}")
    
    async def assess_code_quality(self, code_data: Union[str, Dict[str, Any]]) -> QualityAssessment:
        """Assess code quality using multiple analysis techniques"""
        self.logger.info("Starting code quality assessment")
        
        assessment_id = hashlib.md5(f"code_{datetime.now()}".encode()).hexdigest()[:8]
        issues_found = []
        recommendations = []
        
        try:
            # Extract code content
            if isinstance(code_data, str):
                code_content = code_data
                file_path = "temp_code.py"
            else:
                code_content = code_data.get("content", "")
                file_path = code_data.get("file_path", "temp_code.py")
            
            # Static code analysis
            static_analysis = await self._perform_static_analysis(code_content, file_path)
            issues_found.extend(static_analysis.get("issues", []))
            
            # Code style analysis
            style_analysis = await self._analyze_code_style(code_content)
            issues_found.extend(style_analysis.get("issues", []))
            
            # Security analysis
            security_analysis = await self._analyze_code_security(code_content)
            issues_found.extend(security_analysis.get("issues", []))
            
            # Complexity analysis
            complexity_analysis = await self._analyze_code_complexity(code_content)
            issues_found.extend(complexity_analysis.get("issues", []))
            
            # Generate recommendations
            recommendations = self._generate_code_recommendations(issues_found)
            
            # Calculate quality score
            quality_score = self._calculate_code_quality_score(issues_found, code_content)
            
            assessment = QualityAssessment(
                assessment_id=assessment_id,
                item_type="code",
                assessment_type="analytical",
                score=quality_score,
                issues_found=issues_found,
                recommendations=recommendations,
                assessment_time=datetime.now(),
                metadata={
                    "file_path": file_path,
                    "lines_of_code": len(code_content.split('\n')),
                    "analysis_tools": list(self.assessment_tools["code_analyzers"])
                }
            )
            
            self.assessments[assessment_id] = assessment
            await self._update_quality_metrics(assessment)
            
            self.logger.info(f"Code quality assessment completed: {quality_score:.1f}/100")
            return assessment
            
        except Exception as e:
            self.logger.error(f"Code quality assessment failed: {e}")
            raise
    
    async def assess_image_quality(self, image_data: Union[str, bytes, Dict[str, Any]]) -> QualityAssessment:
        """Assess image quality using computer vision techniques"""
        self.logger.info("Starting image quality assessment")
        
        assessment_id = hashlib.md5(f"image_{datetime.now()}".encode()).hexdigest()[:8]
        issues_found = []
        recommendations = []
        
        try:
            # Load image
            if isinstance(image_data, str):
                # Assume it's a file path or base64 encoded
                if image_data.startswith('data:image'):
                    # Base64 encoded image
                    image_bytes = base64.b64decode(image_data.split(',')[1])
                    image = Image.open(io.BytesIO(image_bytes))
                else:
                    # File path
                    image = Image.open(image_data)
            elif isinstance(image_data, bytes):
                image = Image.open(io.BytesIO(image_data))
            else:
                # Dictionary with image data
                image_path = image_data.get("path")
                if image_path:
                    image = Image.open(image_path)
                else:
                    raise ValueError("Invalid image data provided")
            
            # Convert to numpy array for analysis
            img_array = np.array(image)
            
            # Technical quality analysis
            technical_analysis = await self._analyze_image_technical_quality(img_array, image)
            issues_found.extend(technical_analysis.get("issues", []))
            
            # Visual quality analysis
            visual_analysis = await self._analyze_image_visual_quality(img_array)
            issues_found.extend(visual_analysis.get("issues", []))
            
            # Composition analysis
            composition_analysis = await self._analyze_image_composition(img_array)
            issues_found.extend(composition_analysis.get("issues", []))
            
            # Generate recommendations
            recommendations = self._generate_image_recommendations(issues_found, image)
            
            # Calculate quality score
            quality_score = self._calculate_image_quality_score(issues_found, img_array)
            
            assessment = QualityAssessment(
                assessment_id=assessment_id,
                item_type="image",
                assessment_type="visual",
                score=quality_score,
                issues_found=issues_found,
                recommendations=recommendations,
                assessment_time=datetime.now(),
                metadata={
                    "dimensions": f"{image.width}x{image.height}",
                    "format": image.format,
                    "mode": image.mode,
                    "file_size": len(img_array.tobytes()) if hasattr(img_array, 'tobytes') else 0
                }
            )
            
            self.assessments[assessment_id] = assessment
            await self._update_quality_metrics(assessment)
            
            self.logger.info(f"Image quality assessment completed: {quality_score:.1f}/100")
            return assessment
            
        except Exception as e:
            self.logger.error(f"Image quality assessment failed: {e}")
            raise
    
    async def assess_system_quality(self, system_data: Dict[str, Any]) -> QualityAssessment:
        """Assess system quality including performance, security, and reliability"""
        self.logger.info("Starting system quality assessment")
        
        assessment_id = hashlib.md5(f"system_{datetime.now()}".encode()).hexdigest()[:8]
        issues_found = []
        recommendations = []
        
        try:
            # Performance assessment
            if "performance_metrics" in system_data:
                performance_analysis = await self._analyze_system_performance(system_data["performance_metrics"])
                issues_found.extend(performance_analysis.get("issues", []))
            
            # Security assessment
            if "security_config" in system_data:
                security_analysis = await self._analyze_system_security(system_data["security_config"])
                issues_found.extend(security_analysis.get("issues", []))
            
            # Reliability assessment
            if "reliability_metrics" in system_data:
                reliability_analysis = await self._analyze_system_reliability(system_data["reliability_metrics"])
                issues_found.extend(reliability_analysis.get("issues", []))
            
            # Scalability assessment
            if "scalability_data" in system_data:
                scalability_analysis = await self._analyze_system_scalability(system_data["scalability_data"])
                issues_found.extend(scalability_analysis.get("issues", []))
            
            # Generate recommendations
            recommendations = self._generate_system_recommendations(issues_found)
            
            # Calculate quality score
            quality_score = self._calculate_system_quality_score(issues_found, system_data)
            
            assessment = QualityAssessment(
                assessment_id=assessment_id,
                item_type="system",
                assessment_type="performance",
                score=quality_score,
                issues_found=issues_found,
                recommendations=recommendations,
                assessment_time=datetime.now(),
                metadata=system_data
            )
            
            self.assessments[assessment_id] = assessment
            await self._update_quality_metrics(assessment)
            
            self.logger.info(f"System quality assessment completed: {quality_score:.1f}/100")
            return assessment
            
        except Exception as e:
            self.logger.error(f"System quality assessment failed: {e}")
            raise
    
    async def assess_process_quality(self, process_data: Dict[str, Any]) -> QualityAssessment:
        """Assess process quality including efficiency, compliance, and automation"""
        self.logger.info("Starting process quality assessment")
        
        assessment_id = hashlib.md5(f"process_{datetime.now()}".encode()).hexdigest()[:8]
        issues_found = []
        recommendations = []
        
        try:
            # Efficiency analysis
            efficiency_analysis = await self._analyze_process_efficiency(process_data)
            issues_found.extend(efficiency_analysis.get("issues", []))
            
            # Compliance analysis
            compliance_analysis = await self._analyze_process_compliance(process_data)
            issues_found.extend(compliance_analysis.get("issues", []))
            
            # Automation analysis
            automation_analysis = await self._analyze_process_automation(process_data)
            issues_found.extend(automation_analysis.get("issues", []))
            
            # Generate recommendations
            recommendations = self._generate_process_recommendations(issues_found)
            
            # Calculate quality score
            quality_score = self._calculate_process_quality_score(issues_found, process_data)
            
            assessment = QualityAssessment(
                assessment_id=assessment_id,
                item_type="process",
                assessment_type="analytical",
                score=quality_score,
                issues_found=issues_found,
                recommendations=recommendations,
                assessment_time=datetime.now(),
                metadata=process_data
            )
            
            self.assessments[assessment_id] = assessment
            await self._update_quality_metrics(assessment)
            
            self.logger.info(f"Process quality assessment completed: {quality_score:.1f}/100")
            return assessment
            
        except Exception as e:
            self.logger.error(f"Process quality assessment failed: {e}")
            raise
    
    async def generate_quality_report(self, time_period: str = "week") -> Dict[str, Any]:
        """Generate comprehensive quality report"""
        self.logger.info(f"Generating quality report for {time_period}")
        
        # Determine time range
        now = datetime.now()
        if time_period == "day":
            start_time = now - timedelta(days=1)
        elif time_period == "week":
            start_time = now - timedelta(weeks=1)
        elif time_period == "month":
            start_time = now - timedelta(days=30)
        else:
            start_time = now - timedelta(weeks=1)  # Default to week
        
        # Filter assessments by time period
        period_assessments = [
            assessment for assessment in self.assessments.values()
            if assessment.assessment_time >= start_time
        ]
        
        if not period_assessments:
            return {
                "period": time_period,
                "total_assessments": 0,
                "message": "No assessments found in the specified period"
            }
        
        # Calculate statistics
        total_assessments = len(period_assessments)
        average_score = sum(a.score for a in period_assessments) / total_assessments
        passing_assessments = len([a for a in period_assessments if a.score >= 75.0])
        pass_rate = (passing_assessments / total_assessments) * 100
        
        # Category breakdown
        category_stats = {}
        for assessment in period_assessments:
            category = assessment.item_type
            if category not in category_stats:
                category_stats[category] = {
                    "count": 0,
                    "average_score": 0.0,
                    "scores": []
                }
            category_stats[category]["count"] += 1
            category_stats[category]["scores"].append(assessment.score)
        
        # Calculate category averages
        for category, stats in category_stats.items():
            stats["average_score"] = sum(stats["scores"]) / len(stats["scores"])
        
        # Top issues
        all_issues = []
        for assessment in period_assessments:
            all_issues.extend(assessment.issues_found)
        
        issue_frequency = {}
        for issue in all_issues:
            issue_type = issue.get("type", "unknown")
            issue_frequency[issue_type] = issue_frequency.get(issue_type, 0) + 1
        
        top_issues = sorted(issue_frequency.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Quality trends
        daily_scores = {}
        for assessment in period_assessments:
            day = assessment.assessment_time.date().isoformat()
            if day not in daily_scores:
                daily_scores[day] = []
            daily_scores[day].append(assessment.score)
        
        trend_data = {}
        for day, scores in daily_scores.items():
            trend_data[day] = {
                "average_score": sum(scores) / len(scores),
                "assessments_count": len(scores)
            }
        
        # Generate report
        report = {
            "report_id": hashlib.md5(f"report_{datetime.now()}".encode()).hexdigest()[:8],
            "generated_at": now.isoformat(),
            "period": time_period,
            "period_start": start_time.isoformat(),
            "period_end": now.isoformat(),
            "summary": {
                "total_assessments": total_assessments,
                "average_score": round(average_score, 2),
                "pass_rate": round(pass_rate, 2),
                "passing_assessments": passing_assessments
            },
            "category_breakdown": category_stats,
            "top_issues": top_issues,
            "quality_trends": trend_data,
            "recommendations": self._generate_period_recommendations(period_assessments)
        }
        
        # Save report
        report_file = Path(f"data/quality_reports/quality_report_{now.strftime('%Y%m%d_%H%M%S')}.json")
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        self.logger.info(f"Quality report generated: {report_file}")
        return report
    
    async def get_quality_metrics(self) -> Dict[str, Any]:
        """Get current quality metrics"""
        await self._update_quality_metrics()
        
        return {
            "total_assessments": self.quality_metrics.total_assessments,
            "average_score": round(self.quality_metrics.average_score, 2),
            "pass_rate": round(self.quality_metrics.pass_rate, 2),
            "critical_issues": self.quality_metrics.critical_issues,
            "improvement_trends": self.quality_metrics.improvement_trends,
            "last_updated": self.quality_metrics.last_updated.isoformat(),
            "agent_status": self.status,
            "uptime_hours": (datetime.now() - self.start_time).total_seconds() / 3600
        }
    
    # Private helper methods
    
    async def _perform_static_analysis(self, code_content: str, file_path: str) -> Dict[str, Any]:
        """Perform static code analysis"""
        issues = []
        
        try:
            # Basic syntax check
            try:
                compile(code_content, file_path, 'exec')
            except SyntaxError as e:
                issues.append({
                    "type": "syntax_error",
                    "severity": "critical",
                    "description": f"Syntax error: {e.msg}",
                    "line": e.lineno
                })
            
            # Check for common issues
            lines = code_content.split('\n')
            for i, line in enumerate(lines, 1):
                line_stripped = line.strip()
                
                # Check for security issues
                if 'eval(' in line or 'exec(' in line:
                    issues.append({
                        "type": "security_vulnerability",
                        "severity": "high",
                        "description": "Use of eval() or exec() can be dangerous",
                        "line": i
                    })
                
                # Check for code quality issues
                if len(line) > 120:
                    issues.append({
                        "type": "line_too_long",
                        "severity": "low",
                        "description": f"Line exceeds 120 characters ({len(line)} chars)",
                        "line": i
                    })
                
                # Check for TODO/FIXME comments
                if 'TODO' in line_stripped or 'FIXME' in line_stripped:
                    issues.append({
                        "type": "todo_comment",
                        "severity": "low",
                        "description": "Unresolved TODO/FIXME comment",
                        "line": i
                    })
            
            return {"issues": issues}
            
        except Exception as e:
            self.logger.error(f"Static analysis failed: {e}")
            return {"issues": []}
    
    async def _update_quality_metrics(self, assessment: QualityAssessment = None):
        """Update overall quality metrics"""
        try:
            if not self.assessments:
                return
            
            assessments = list(self.assessments.values())
            
            self.quality_metrics.total_assessments = len(assessments)
            self.quality_metrics.average_score = sum(a.score for a in assessments) / len(assessments)
            
            passing_assessments = len([a for a in assessments if a.score >= 75.0])
            self.quality_metrics.pass_rate = (passing_assessments / len(assessments)) * 100
            
            # Count critical issues
            critical_issues = 0
            for assessment in assessments:
                for issue in assessment.issues_found:
                    if issue.get("severity") == "critical":
                        critical_issues += 1
            self.quality_metrics.critical_issues = critical_issues
            
            self.quality_metrics.last_updated = datetime.now()
            
        except Exception as e:
            self.logger.error(f"Failed to update quality metrics: {e}")
    
    def _calculate_code_quality_score(self, issues: List[Dict[str, Any]], code_content: str) -> float:
        """Calculate code quality score based on issues found"""
        base_score = 100.0
        
        for issue in issues:
            severity = issue.get("severity", "low")
            if severity == "critical":
                base_score -= 20
            elif severity == "high":
                base_score -= 10
            elif severity == "medium":
                base_score -= 5
            else:  # low
                base_score -= 2
        
        # Bonus for good practices
        lines = code_content.split('\n')
        has_docstring = any('"""' in line or "'''" in line for line in lines[:10])
        has_type_hints = any(':' in line and '->' in line for line in lines)
        
        if has_docstring:
            base_score += 5
        if has_type_hints:
            base_score += 5
        
        return max(0.0, min(100.0, base_score))
    
    def _generate_code_recommendations(self, issues: List[Dict[str, Any]]) -> List[str]:
        """Generate code improvement recommendations"""
        recommendations = []
        
        issue_types = [issue.get("type") for issue in issues]
        
        if "syntax_error" in issue_types:
            recommendations.append("Fix syntax errors before proceeding with other improvements")
        
        if "security_vulnerability" in issue_types:
            recommendations.append("Address security vulnerabilities immediately")
            recommendations.append("Consider using safer alternatives to eval() and exec()")
        
        if "line_too_long" in issue_types:
            recommendations.append("Break long lines into multiple lines for better readability")
        
        if len([i for i in issues if i.get("severity") == "critical"]) > 0:
            recommendations.append("Focus on critical issues first as they may cause system failures")
        
        return recommendations

    async def _analyze_code_style(self, code_content: str) -> Dict[str, Any]:
        """Analyze code style and formatting"""
        issues = []
        lines = code_content.split('\n')

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Check indentation consistency
            if line.startswith(' ') and not line.startswith('    '):
                leading_spaces = len(line) - len(stripped)
                if leading_spaces % 4 != 0:
                    issues.append({
                        "type": "inconsistent_indentation",
                        "severity": "medium",
                        "description": f"Inconsistent indentation ({leading_spaces} spaces)",
                        "line": i
                    })

            # Check for trailing whitespace
            if line != line.rstrip():
                issues.append({
                    "type": "trailing_whitespace",
                    "severity": "low",
                    "description": "Trailing whitespace detected",
                    "line": i
                })

            # Check for missing blank lines between functions/classes
            if stripped.startswith('def ') or stripped.startswith('class '):
                if i > 1 and lines[i - 2].strip() and not lines[i - 2].strip().startswith('#'):
                    issues.append({
                        "type": "missing_blank_line",
                        "severity": "low",
                        "description": "Missing blank line before definition",
                        "line": i
                    })

            # Check naming conventions
            if stripped.startswith('def '):
                func_name = stripped.split('(')[0].replace('def ', '').strip()
                if func_name and not func_name.startswith('_') and not func_name.islower():
                    has_upper = any(c.isupper() for c in func_name)
                    if has_upper:
                        issues.append({
                            "type": "naming_convention",
                            "severity": "medium",
                            "description": f"Function '{func_name}' should use snake_case",
                            "line": i
                        })

        return {"issues": issues}

    async def _analyze_code_security(self, code_content: str) -> Dict[str, Any]:
        """Analyze code for security vulnerabilities"""
        issues = []
        lines = code_content.split('\n')

        security_patterns = {
            'eval(': {'type': 'security_vulnerability', 'severity': 'critical',
                      'desc': 'Use of eval() is a security risk - use ast.literal_eval() for safe parsing'},
            'exec(': {'type': 'security_vulnerability', 'severity': 'critical',
                      'desc': 'Use of exec() is a security risk - consider safer alternatives'},
            'subprocess.call(': {'type': 'security_vulnerability', 'severity': 'high',
                                 'desc': 'Subprocess call without shell=False may allow command injection'},
            'subprocess.Popen(': {'type': 'security_vulnerability', 'severity': 'high',
                                  'desc': 'Subprocess Popen without shell=False may allow command injection'},
            'os.system(': {'type': 'security_vulnerability', 'severity': 'high',
                           'desc': 'os.system() is vulnerable to command injection - use subprocess with args list'},
            'pickle.loads(': {'type': 'security_vulnerability', 'severity': 'high',
                              'desc': 'pickle.loads() can execute arbitrary code - use json or msgpack'},
            'yaml.load(': {'type': 'security_vulnerability', 'severity': 'high',
                           'desc': 'yaml.load() is unsafe - use yaml.safe_load() instead'},
            'hashlib.md5(': {'type': 'weak_hash', 'severity': 'medium',
                             'desc': 'MD5 is cryptographically broken - use SHA-256 or stronger'},
            'hashlib.sha1(': {'type': 'weak_hash', 'severity': 'medium',
                              'desc': 'SHA-1 is cryptographically weak - use SHA-256 or stronger'},
            'password': {'type': 'hardcoded_secret', 'severity': 'high',
                         'desc': 'Potential hardcoded password/secret detected'},
            'api_key': {'type': 'hardcoded_secret', 'severity': 'high',
                        'desc': 'Potential hardcoded API key detected'},
            'secret': {'type': 'hardcoded_secret', 'severity': 'medium',
                       'desc': 'Potential hardcoded secret detected'},
            'sql_string': {'type': 'sql_injection', 'severity': 'high',
                           'desc': 'String formatting in SQL may allow SQL injection'},
        }

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            # Skip comments
            if stripped.startswith('#'):
                continue

            for pattern, info in security_patterns.items():
                if pattern in stripped.lower() if pattern in ['password', 'api_key', 'secret'] else pattern in stripped:
                    # Avoid false positives in variable names by checking assignment patterns
                    if pattern in ['password', 'api_key', 'secret']:
                        if '=' in stripped and not stripped.startswith('#') and 'get(' not in stripped and 'env(' not in stripped and 'os.getenv' not in stripped:
                            issues.append({
                                "type": info['type'],
                                "severity": info['severity'],
                                "description": info['desc'],
                                "line": i
                            })
                    elif pattern == 'sql_string' and ('%' in stripped or 'format(' in stripped or 'f"' in stripped) and 'SELECT' in stripped.upper():
                        issues.append({
                            "type": info['type'],
                            "severity": info['severity'],
                            "description": info['desc'],
                            "line": i
                        })
                    else:
                        # Check specific patterns with context
                        if pattern in ['yaml.load('] and 'safe_load' not in stripped:
                            issues.append({
                                "type": info['type'],
                                "severity": info['severity'],
                                "description": info['desc'],
                                "line": i
                            })
                        elif pattern in ['eval(', 'exec(', 'os.system(', 'pickle.loads(', 'subprocess.call(', 'subprocess.Popen(']:
                            issues.append({
                                "type": info['type'],
                                "severity": info['severity'],
                                "description": info['desc'],
                                "line": i
                            })

        return {"issues": issues}

    async def _analyze_code_complexity(self, code_content: str) -> Dict[str, Any]:
        """Analyze code complexity metrics"""
        issues = []
        lines = code_content.split('\n')

        # Track function complexity
        current_function = None
        current_complexity = 1
        function_start = 0
        function_lines = 0

        complexity_keywords = ['if ', 'elif ', 'else:', 'for ', 'while ', 'except ',
                               'and ', 'or ', 'with ']

        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            # Track function definitions
            if stripped.startswith('def '):
                # Save previous function
                if current_function and current_complexity > 10:
                    issues.append({
                        "type": "high_complexity",
                        "severity": "medium",
                        "description": f"Function '{current_function}' has cyclomatic complexity of {current_complexity} (recommended max: 10)",
                        "line": function_start
                    })

                # Start tracking new function
                current_function = stripped.split('(')[0].replace('def ', '').strip()
                current_complexity = 1
                function_start = i
                function_lines = 0

            if current_function:
                function_lines += 1
                for keyword in complexity_keywords:
                    if keyword in stripped:
                        current_complexity += 1

                # Check function length
                if function_lines > 50:
                    issues.append({
                        "type": "function_too_long",
                        "severity": "low",
                        "description": f"Function '{current_function}' is {function_lines} lines (recommended max: 50)",
                        "line": function_start
                    })

        # Check last function
        if current_function and current_complexity > 10:
            issues.append({
                "type": "high_complexity",
                "severity": "medium",
                "description": f"Function '{current_function}' has cyclomatic complexity of {current_complexity} (recommended max: 10)",
                "line": function_start
            })

        return {"issues": issues}

    async def _analyze_image_technical_quality(self, img_array, image) -> Dict[str, Any]:
        """Analyze image technical quality metrics"""
        issues = []

        try:
            # Check resolution
            height, width = img_array.shape[:2]
            if width < 640 or height < 480:
                issues.append({
                    "type": "low_resolution",
                    "severity": "medium",
                    "description": f"Low resolution: {width}x{height} (minimum recommended: 640x480)"
                })

            # Check aspect ratio
            aspect_ratio = width / height
            if aspect_ratio < 0.5 or aspect_ratio > 3.0:
                issues.append({
                    "type": "unusual_aspect_ratio",
                    "severity": "low",
                    "description": f"Unusual aspect ratio: {aspect_ratio:.2f}"
                })

            # Check if image is too dark or too bright using numpy
            if np is not None:
                mean_brightness = np.mean(img_array)
                if mean_brightness < 30:
                    issues.append({
                        "type": "too_dark",
                        "severity": "medium",
                        "description": f"Image appears too dark (mean brightness: {mean_brightness:.1f})"
                    })
                elif mean_brightness > 225:
                    issues.append({
                        "type": "too_bright",
                        "severity": "medium",
                        "description": f"Image appears too bright (mean brightness: {mean_brightness:.1f})"
                    })

                # Check contrast
                std_dev = np.std(img_array)
                if std_dev < 20:
                    issues.append({
                        "type": "low_contrast",
                        "severity": "medium",
                        "description": f"Low contrast (std dev: {std_dev:.1f})"
                    })

            # Check color mode
            if hasattr(image, 'mode'):
                if image.mode == 'L':
                    issues.append({
                        "type": "grayscale",
                        "severity": "low",
                        "description": "Image is grayscale - may lack visual appeal for some use cases"
                    })

        except Exception as e:
            self.logger.error(f"Image technical analysis failed: {e}")

        return {"issues": issues}

    async def _analyze_image_visual_quality(self, img_array) -> Dict[str, Any]:
        """Analyze visual quality aspects of an image"""
        issues = []

        try:
            if np is not None and img_array is not None:
                # Check for noise (high frequency variation)
                if len(img_array.shape) == 3:
                    gray = np.mean(img_array, axis=2)
                else:
                    gray = img_array.astype(float)

                # Simple noise detection using gradient magnitude
                if gray.shape[0] > 2 and gray.shape[1] > 2:
                    grad_x = np.diff(gray, axis=1)
                    grad_y = np.diff(gray, axis=0)
                    noise_level = np.mean(np.abs(grad_x)) + np.mean(np.abs(grad_y))

                    if noise_level > 80:
                        issues.append({
                            "type": "high_noise",
                            "severity": "medium",
                            "description": f"High noise level detected (noise metric: {noise_level:.1f})"
                        })

                # Check for blurriness using Laplacian variance
                if cv2 is not None:
                    laplacian_var = cv2.Laplacian(img_array.astype(np.uint8), cv2.CV_64F).var()
                    if laplacian_var < 50:
                        issues.append({
                            "type": "blurry",
                            "severity": "high",
                            "description": f"Image appears blurry (Laplacian variance: {laplacian_var:.1f})"
                        })

        except Exception as e:
            self.logger.error(f"Image visual analysis failed: {e}")

        return {"issues": issues}

    async def _analyze_image_composition(self, img_array) -> Dict[str, Any]:
        """Analyze image composition"""
        issues = []

        try:
            if np is not None and img_array is not None:
                height, width = img_array.shape[:2]

                # Check rule of thirds (simplified)
                third_h = height // 3
                third_w = width // 3

                if len(img_array.shape) == 3:
                    # Check if there's interesting content at the thirds intersections
                    sections = [
                        img_array[:third_h, :third_w],
                        img_array[:third_h, 2*third_w:],
                        img_array[2*third_h:, :third_w],
                        img_array[2*third_h:, 2*third_w:]
                    ]
                    section_variances = [np.var(s) for s in sections]

                    # If all sections have very similar variance, the composition may be flat
                    if max(section_variances) > 0 and min(section_variances) > 0:
                        variance_ratio = max(section_variances) / min(section_variances)
                        if variance_ratio < 1.5:
                            issues.append({
                                "type": "flat_composition",
                                "severity": "low",
                                "description": "Image composition may lack a clear focal point (consider rule of thirds)"
                            })

        except Exception as e:
            self.logger.error(f"Image composition analysis failed: {e}")

        return {"issues": issues}

    def _calculate_image_quality_score(self, issues: List[Dict[str, Any]], img_array) -> float:
        """Calculate image quality score based on issues found"""
        base_score = 100.0

        for issue in issues:
            severity = issue.get("severity", "low")
            if severity == "critical":
                base_score -= 25
            elif severity == "high":
                base_score -= 15
            elif severity == "medium":
                base_score -= 8
            else:
                base_score -= 3

        # Resolution bonus
        if np is not None and img_array is not None:
            height, width = img_array.shape[:2]
            total_pixels = width * height
            if total_pixels > 2000000:  # > 2MP
                base_score += 5
            if total_pixels > 8000000:  # > 8MP
                base_score += 5

        return max(0.0, min(100.0, base_score))

    def _generate_image_recommendations(self, issues: List[Dict[str, Any]], image) -> List[str]:
        """Generate image improvement recommendations"""
        recommendations = []
        issue_types = [issue.get("type") for issue in issues]

        if "low_resolution" in issue_types:
            recommendations.append("Increase image resolution - consider using higher resolution source images")
        if "too_dark" in issue_types:
            recommendations.append("Increase brightness - use image editing tools to adjust exposure")
        if "too_bright" in issue_types:
            recommendations.append("Reduce brightness - the image may be overexposed")
        if "low_contrast" in issue_types:
            recommendations.append("Increase contrast - apply contrast enhancement or histogram equalization")
        if "high_noise" in issue_types:
            recommendations.append("Reduce noise - apply denoising filters or use a lower ISO setting")
        if "blurry" in issue_types:
            recommendations.append("Improve sharpness - use a tripod, faster shutter speed, or apply sharpening filters")
        if "flat_composition" in issue_types:
            recommendations.append("Improve composition - apply rule of thirds to place key subjects at intersection points")
        if "grayscale" in issue_types:
            recommendations.append("Consider adding color for better visual appeal, if the content allows")

        if not recommendations:
            recommendations.append("Image quality is acceptable - no major improvements needed")

        return recommendations

    async def _analyze_system_performance(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze system performance metrics"""
        issues = []

        # Response time analysis
        if "response_time" in metrics:
            avg_response = metrics["response_time"].get("average", 0)
            p99_response = metrics["response_time"].get("p99", 0)
            if avg_response > 2000:  # > 2s
                issues.append({
                    "type": "slow_response_time",
                    "severity": "high",
                    "description": f"Average response time is {avg_response}ms (target: <2000ms)"
                })
            if p99_response > 10000:  # > 10s
                issues.append({
                    "type": "slow_p99_response",
                    "severity": "critical",
                    "description": f"P99 response time is {p99_response}ms (target: <10000ms)"
                })

        # Throughput analysis
        if "throughput" in metrics:
            rps = metrics["throughput"].get("requests_per_second", 0)
            if rps < 10:
                issues.append({
                    "type": "low_throughput",
                    "severity": "medium",
                    "description": f"Throughput is {rps} rps (minimum recommended: 10 rps)"
                })

        # Error rate analysis
        if "error_rate" in metrics:
            error_rate = metrics["error_rate"]
            if error_rate > 0.05:  # > 5%
                issues.append({
                    "type": "high_error_rate",
                    "severity": "critical",
                    "description": f"Error rate is {error_rate*100:.1f}% (target: <5%)"
                })
            elif error_rate > 0.01:  # > 1%
                issues.append({
                    "type": "elevated_error_rate",
                    "severity": "medium",
                    "description": f"Error rate is {error_rate*100:.1f}% (target: <1%)"
                })

        # Resource utilization
        if "cpu_usage" in metrics and metrics["cpu_usage"] > 80:
            issues.append({
                "type": "high_cpu_usage",
                "severity": "high",
                "description": f"CPU usage is {metrics['cpu_usage']}% (target: <80%)"
            })
        if "memory_usage" in metrics and metrics["memory_usage"] > 85:
            issues.append({
                "type": "high_memory_usage",
                "severity": "high",
                "description": f"Memory usage is {metrics['memory_usage']}% (target: <85%)"
            })

        return {"issues": issues}

    async def _analyze_system_security(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze system security configuration"""
        issues = []

        # Authentication checks
        if not config.get("authentication_enabled", True):
            issues.append({
                "type": "missing_authentication",
                "severity": "critical",
                "description": "System authentication is not enabled"
            })

        # HTTPS/TLS checks
        if not config.get("tls_enabled", True):
            issues.append({
                "type": "no_tls",
                "severity": "critical",
                "description": "TLS/HTTPS is not enabled - data may be transmitted in plaintext"
            })

        # Encryption at rest
        if not config.get("encryption_at_rest", True):
            issues.append({
                "type": "no_encryption_at_rest",
                "severity": "high",
                "description": "Data at rest is not encrypted"
            })

        # Rate limiting
        if not config.get("rate_limiting_enabled", True):
            issues.append({
                "type": "no_rate_limiting",
                "severity": "medium",
                "description": "Rate limiting is not configured - system may be vulnerable to DoS"
            })

        # CORS configuration
        cors_config = config.get("cors", {})
        if cors_config.get("allow_all_origins", False):
            issues.append({
                "type": "open_cors",
                "severity": "high",
                "description": "CORS allows all origins - restrict to known domains"
            })

        # Secret management
        if config.get("hardcoded_secrets", False):
            issues.append({
                "type": "hardcoded_secrets",
                "severity": "critical",
                "description": "Secrets appear to be hardcoded - use environment variables or secret managers"
            })

        return {"issues": issues}

    async def _analyze_system_reliability(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze system reliability metrics"""
        issues = []

        # Uptime analysis
        uptime_percent = metrics.get("uptime_percentage", 100)
        if uptime_percent < 99.0:
            issues.append({
                "type": "low_uptime",
                "severity": "critical",
                "description": f"Uptime is {uptime_percent}% (SLA target: 99.9%)"
            })
        elif uptime_percent < 99.9:
            issues.append({
                "type": "below_sla",
                "severity": "medium",
                "description": f"Uptime is {uptime_percent}% (SLA target: 99.9%)"
            })

        # MTTR (Mean Time To Recovery)
        mttr = metrics.get("mttr_minutes", 0)
        if mttr > 60:
            issues.append({
                "type": "slow_recovery",
                "severity": "high",
                "description": f"MTTR is {mttr} minutes (target: <60 minutes)"
            })

        # Deployment frequency
        deploy_freq = metrics.get("deploy_frequency_per_week", 0)
        if deploy_freq < 1:
            issues.append({
                "type": "infrequent_deployments",
                "severity": "low",
                "description": "Deployment frequency is less than once per week"
            })

        # Backup status
        if not metrics.get("backups_enabled", True):
            issues.append({
                "type": "no_backups",
                "severity": "critical",
                "description": "Database backups are not enabled"
            })

        return {"issues": issues}

    async def _analyze_system_scalability(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze system scalability characteristics"""
        issues = []

        # Horizontal scaling
        if not data.get("supports_horizontal_scaling", True):
            issues.append({
                "type": "no_horizontal_scaling",
                "severity": "high",
                "description": "System does not support horizontal scaling"
            })

        # Connection pooling
        if not data.get("connection_pooling_enabled", True):
            issues.append({
                "type": "no_connection_pooling",
                "severity": "medium",
                "description": "Connection pooling is not enabled - may limit scalability"
            })

        # Caching
        if not data.get("caching_enabled", True):
            issues.append({
                "type": "no_caching",
                "severity": "medium",
                "description": "Caching is not configured - repeated queries may overload the database"
            })

        # Database scalability
        db_type = data.get("database_type", "")
        if db_type.lower() == "sqlite":
            issues.append({
                "type": "sqlite_for_production",
                "severity": "medium",
                "description": "SQLite may not scale well for concurrent write workloads - consider PostgreSQL"
            })

        return {"issues": issues}

    def _generate_system_recommendations(self, issues: List[Dict[str, Any]]) -> List[str]:
        """Generate system improvement recommendations"""
        recommendations = []
        issue_types = [issue.get("type") for issue in issues]

        if "slow_response_time" in issue_types:
            recommendations.append("Optimize response time by adding caching, optimizing database queries, or scaling horizontally")
        if "high_error_rate" in issue_types:
            recommendations.append("Investigate and fix errors - add monitoring, error tracking, and circuit breakers")
        if "missing_authentication" in issue_types:
            recommendations.append("Implement authentication immediately - use OAuth2, JWT, or API key-based auth")
        if "no_tls" in issue_types:
            recommendations.append("Enable TLS/HTTPS to protect data in transit - use Let's Encrypt for free certificates")
        if "no_encryption_at_rest" in issue_types:
            recommendations.append("Enable encryption at rest for sensitive data - use AES-256 or cloud provider encryption")
        if "open_cors" in issue_types:
            recommendations.append("Restrict CORS to known origins - never use wildcard (*) in production")
        if "low_uptime" in issue_types:
            recommendations.append("Improve uptime by adding redundancy, health checks, and automated failover")
        if "no_backups" in issue_types:
            recommendations.append("Enable automated database backups with point-in-time recovery")
        if "no_horizontal_scaling" in issue_types:
            recommendations.append("Design for horizontal scaling - use stateless services and external session stores")
        if "sqlite_for_production" in issue_types:
            recommendations.append("Consider migrating from SQLite to PostgreSQL for production workloads")

        return recommendations

    def _calculate_system_quality_score(self, issues: List[Dict[str, Any]], data: Dict[str, Any]) -> float:
        """Calculate system quality score"""
        base_score = 100.0

        for issue in issues:
            severity = issue.get("severity", "low")
            if severity == "critical":
                base_score -= 20
            elif severity == "high":
                base_score -= 12
            elif severity == "medium":
                base_score -= 6
            else:
                base_score -= 2

        # Bonus for best practices
        if data.get("monitoring_enabled"):
            base_score += 3
        if data.get("ci_cd_enabled"):
            base_score += 3
        if data.get("automated_testing"):
            base_score += 3

        return max(0.0, min(100.0, base_score))

    async def _analyze_process_efficiency(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze process efficiency"""
        issues = []

        automation_level = data.get("automation_percentage", 0)
        if automation_level < 30:
            issues.append({
                "type": "low_automation",
                "severity": "high",
                "description": f"Only {automation_level}% of the process is automated (target: >70%)"
            })
        elif automation_level < 70:
            issues.append({
                "type": "partial_automation",
                "severity": "medium",
                "description": f"Process is {automation_level}% automated (target: >70%)"
            })

        error_rate = data.get("error_rate", 0)
        if error_rate > 0.1:
            issues.append({
                "type": "high_error_rate",
                "severity": "high",
                "description": f"Process error rate is {error_rate*100:.1f}% (target: <5%)"
            })

        avg_completion = data.get("avg_completion_time_minutes", 0)
        target_time = data.get("target_completion_time_minutes", 30)
        if avg_completion > target_time * 1.5:
            issues.append({
                "type": "slow_process",
                "severity": "medium",
                "description": f"Average completion time is {avg_completion}min (target: {target_time}min)"
            })

        return {"issues": issues}

    async def _analyze_process_compliance(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze process compliance with standards"""
        issues = []

        if not data.get("documentation_complete", True):
            issues.append({
                "type": "incomplete_documentation",
                "severity": "high",
                "description": "Process documentation is incomplete"
            })

        if not data.get("audit_trail_enabled", True):
            issues.append({
                "type": "no_audit_trail",
                "severity": "high",
                "description": "Audit trail is not enabled - cannot trace process changes"
            })

        if not data.get("standards_adherence", True):
            issues.append({
                "type": "standards_non_compliance",
                "severity": "medium",
                "description": "Process does not adhere to defined standards"
            })

        return {"issues": issues}

    async def _analyze_process_automation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze process automation opportunities"""
        issues = []

        manual_steps = data.get("manual_steps_count", 0)
        if manual_steps > 5:
            issues.append({
                "type": "too_many_manual_steps",
                "severity": "medium",
                "description": f"Process has {manual_steps} manual steps - consider automation"
            })

        if not data.get("automated_notifications", True):
            issues.append({
                "type": "no_auto_notifications",
                "severity": "low",
                "description": "Notifications are not automated - may cause delays"
            })

        if not data.get("automated_error_handling", True):
            issues.append({
                "type": "no_auto_error_handling",
                "severity": "medium",
                "description": "Error handling is not automated - manual intervention required"
            })

        return {"issues": issues}

    def _generate_process_recommendations(self, issues: List[Dict[str, Any]]) -> List[str]:
        """Generate process improvement recommendations"""
        recommendations = []
        issue_types = [issue.get("type") for issue in issues]

        if "low_automation" in issue_types or "partial_automation" in issue_types:
            recommendations.append("Increase automation level by identifying repetitive manual tasks and automating them with scripts or workflows")
        if "high_error_rate" in issue_types:
            recommendations.append("Reduce error rate by adding validation steps, automated testing, and error recovery mechanisms")
        if "slow_process" in issue_types:
            recommendations.append("Optimize process speed by parallelizing independent steps and eliminating bottlenecks")
        if "incomplete_documentation" in issue_types:
            recommendations.append("Complete process documentation including SOPs, flowcharts, and decision trees")
        if "no_audit_trail" in issue_types:
            recommendations.append("Enable audit trail to track all process changes for compliance and debugging")
        if "too_many_manual_steps" in issue_types:
            recommendations.append("Automate manual steps using CI/CD pipelines, scheduling tools, or custom scripts")

        return recommendations

    def _calculate_process_quality_score(self, issues: List[Dict[str, Any]], data: Dict[str, Any]) -> float:
        """Calculate process quality score"""
        base_score = 100.0

        for issue in issues:
            severity = issue.get("severity", "low")
            if severity == "critical":
                base_score -= 20
            elif severity == "high":
                base_score -= 12
            elif severity == "medium":
                base_score -= 6
            else:
                base_score -= 2

        # Bonus for good practices
        if data.get("automation_percentage", 0) > 80:
            base_score += 5
        if data.get("monitoring_enabled"):
            base_score += 3
        if data.get("continuous_improvement"):
            base_score += 3

        return max(0.0, min(100.0, base_score))

    def _generate_period_recommendations(self, period_assessments: List[QualityAssessment]) -> List[str]:
        """Generate recommendations based on period assessment trends"""
        recommendations = []

        if not period_assessments:
            return recommendations

        # Analyze trends
        avg_score = sum(a.score for a in period_assessments) / len(period_assessments)

        if avg_score < 60:
            recommendations.append("Overall quality is critically low - prioritize fixing critical issues across all categories")
        elif avg_score < 75:
            recommendations.append("Quality is below target - focus on the lowest-scoring categories first")

        # Check for declining trends
        if len(period_assessments) >= 3:
            recent_scores = [a.score for a in period_assessments[:len(period_assessments)//2]]
            older_scores = [a.score for a in period_assessments[len(period_assessments)//2:]]
            if recent_scores and older_scores:
                recent_avg = sum(recent_scores) / len(recent_scores)
                older_avg = sum(older_scores) / len(older_scores)
                if recent_avg < older_avg - 5:
                    recommendations.append("Quality trend is declining - investigate recent changes that may have introduced regressions")

        # Category-specific recommendations
        categories = {}
        for a in period_assessments:
            if a.item_type not in categories:
                categories[a.item_type] = []
            categories[a.item_type].append(a.score)

        for category, scores in categories.items():
            cat_avg = sum(scores) / len(scores)
            if cat_avg < 70:
                recommendations.append(f"Focus on improving {category} quality (current average: {cat_avg:.1f})")

        if not recommendations:
            recommendations.append("Quality is on track - continue monitoring and maintain current standards")

        return recommendations

# Global instance
quality_control_specialist = QualityControlSpecialist()

# Export for use by other modules
__all__ = ['QualityControlSpecialist', 'quality_control_specialist', 'QualityAssessment', 'QualityMetrics']
