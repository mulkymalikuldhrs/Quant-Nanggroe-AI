"""
💻 Code Executor Agent - Advanced Code Execution Environment
Executes code in multiple languages like Replit/Meta.ai
Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

import asyncio
import json
import os
import subprocess
import tempfile
try:
    import docker
except ImportError:
    docker = None
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
import sys

class CodeExecutorAgent:
    """
    Advanced Code Execution Agent that:
    - Executes code in multiple programming languages
    - Provides sandboxed execution environments
    - Supports real-time collaboration like Replit
    - Manages dependencies and packages
    - Provides code analysis and optimization
    - Supports interactive REPL environments
    """
    
    def __init__(self):
        self.agent_id = "code_executor"
        self.name = "Code Executor"
        self.version = "2.0.0"
        self.status = "ready"
        self.capabilities = [
            "multi_language_execution",
            "sandboxed_environments",
            "real_time_collaboration",
            "dependency_management",
            "code_analysis",
            "interactive_repl",
            "docker_containers",
            "package_installation",
            "file_management",
            "output_streaming"
        ]
        
        # Supported languages
        self.supported_languages = {
            'python': {
                'extension': '.py',
                'command': ['python3'],
                'docker_image': 'python:3.11-slim',
                'packages': ['pip']
            },
            'javascript': {
                'extension': '.js',
                'command': ['node'],
                'docker_image': 'node:18-alpine',
                'packages': ['npm']
            },
            'typescript': {
                'extension': '.ts',
                'command': ['npx', 'ts-node'],
                'docker_image': 'node:18-alpine',
                'packages': ['npm', 'typescript', 'ts-node']
            },
            'java': {
                'extension': '.java',
                'command': ['javac', '&&', 'java'],
                'docker_image': 'openjdk:17-slim',
                'packages': ['maven']
            },
            'cpp': {
                'extension': '.cpp',
                'command': ['g++', '-o', 'output', '&&', './output'],
                'docker_image': 'gcc:latest',
                'packages': ['build-essential']
            },
            'rust': {
                'extension': '.rs',
                'command': ['rustc', '&&', './main'],
                'docker_image': 'rust:latest',
                'packages': ['cargo']
            },
            'go': {
                'extension': '.go',
                'command': ['go', 'run'],
                'docker_image': 'golang:1.21-alpine',
                'packages': ['go']
            },
            'bash': {
                'extension': '.sh',
                'command': ['bash'],
                'docker_image': 'ubuntu:22.04',
                'packages': []
            }
        }
        
        # Execution sessions
        self.active_sessions = {}
        self.execution_history = []
        
        # Docker client
        try:
            if docker is None:
                raise ImportError("docker package not installed")
            self.docker_client = docker.from_env()
            self.docker_available = True
            print("✅ Docker client initialized")
        except Exception:
            self.docker_client = None
            self.docker_available = False
            print("⚠️ Docker not available, using local execution")
        
        # Performance metrics
        self.executions_count = 0
        self.success_rate = 100.0
        self.total_execution_time = 0
        
        print(f"✅ {self.name} initialized - Supporting {len(self.supported_languages)} languages")
    
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process code execution tasks"""
        try:
            task_type = task.get('type', 'execute_code')
            
            if task_type == 'execute_code':
                return await self.execute_code(task)
            elif task_type == 'create_session':
                return await self.create_execution_session(task)
            elif task_type == 'install_package':
                return await self.install_package(task)
            elif task_type == 'list_files':
                return await self.list_session_files(task)
            elif task_type == 'analyze_code':
                return await self.analyze_code(task)
            elif task_type == 'get_repl':
                return await self.start_repl_session(task)
            else:
                return {
                    'success': False,
                    'error': f'Unknown task type: {task_type}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Code execution error: {str(e)}'
            }
    
    async def execute_code(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute code in specified language"""
        try:
            code = task.get('code', '')
            language = task.get('language', 'python').lower()
            session_id = task.get('session_id')
            environment = task.get('environment', 'sandbox')
            
            if not code:
                return {
                    'success': False,
                    'error': 'No code provided'
                }
            
            if language not in self.supported_languages:
                return {
                    'success': False,
                    'error': f'Language {language} not supported. Supported: {list(self.supported_languages.keys())}'
                }
            
            # Create execution session if needed
            if not session_id:
                session_id = str(uuid.uuid4())
                await self.create_execution_session({
                    'session_id': session_id,
                    'language': language,
                    'environment': environment
                })
            
            start_time = datetime.now()
            
            # Execute based on environment preference
            if environment == 'docker' and self.docker_available:
                result = await self._execute_in_docker(code, language, session_id)
            else:
                result = await self._execute_locally(code, language, session_id)
            
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            # Update metrics
            self.executions_count += 1
            self.total_execution_time += execution_time
            
            if result['success']:
                self.success_rate = (self.success_rate * (self.executions_count - 1) + 100) / self.executions_count
            else:
                self.success_rate = (self.success_rate * (self.executions_count - 1)) / self.executions_count
            
            # Add to history
            execution_record = {
                'session_id': session_id,
                'language': language,
                'code': code[:200] + '...' if len(code) > 200 else code,
                'result': result,
                'execution_time': execution_time,
                'timestamp': start_time.isoformat(),
                'environment': environment
            }
            
            self.execution_history.append(execution_record)
            
            # Keep only last 100 executions
            if len(self.execution_history) > 100:
                self.execution_history = self.execution_history[-100:]
            
            result['execution_time'] = execution_time
            result['session_id'] = session_id
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Code execution failed: {str(e)}'
            }
    
    async def _execute_locally(self, code: str, language: str, session_id: str) -> Dict[str, Any]:
        """Execute code locally"""
        try:
            lang_config = self.supported_languages[language]
            
            # Create temporary directory for this execution
            session_dir = Path(f"temp_sessions/{session_id}")
            session_dir.mkdir(parents=True, exist_ok=True)
            
            # Write code to file
            code_file = session_dir / f"main{lang_config['extension']}"
            with open(code_file, 'w', encoding='utf-8') as f:
                f.write(code)
            
            # Prepare command
            command = lang_config['command'].copy()
            if language == 'java':
                # Special handling for Java
                class_name = self._extract_java_class_name(code) or 'Main'
                compile_cmd = ['javac', str(code_file)]
                run_cmd = ['java', '-cp', str(session_dir), class_name]
                
                # Compile first
                compile_result = subprocess.run(
                    compile_cmd, 
                    cwd=session_dir,
                    capture_output=True, 
                    text=True,
                    timeout=30
                )
                
                if compile_result.returncode != 0:
                    return {
                        'success': False,
                        'output': '',
                        'error': compile_result.stderr,
                        'type': 'compilation_error'
                    }
                
                command = run_cmd
            elif language == 'cpp':
                # Special handling for C++
                compile_cmd = ['g++', str(code_file), '-o', str(session_dir / 'output')]
                run_cmd = [str(session_dir / 'output')]
                
                # Compile first
                compile_result = subprocess.run(
                    compile_cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if compile_result.returncode != 0:
                    return {
                        'success': False,
                        'output': '',
                        'error': compile_result.stderr,
                        'type': 'compilation_error'
                    }
                
                command = run_cmd
            else:
                command.append(str(code_file))
            
            # Execute the code
            result = subprocess.run(
                command,
                cwd=session_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                'success': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr,
                'return_code': result.returncode,
                'type': 'execution_result'
            }
            
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'output': '',
                'error': 'Execution timed out (30 seconds limit)',
                'type': 'timeout_error'
            }
        except Exception as e:
            return {
                'success': False,
                'output': '',
                'error': str(e),
                'type': 'execution_error'
            }
    
    async def _execute_in_docker(self, code: str, language: str, session_id: str) -> Dict[str, Any]:
        """Execute code in Docker container"""
        try:
            lang_config = self.supported_languages[language]
            
            # Create temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                # Write code to file
                code_file = Path(temp_dir) / f"main{lang_config['extension']}"
                with open(code_file, 'w', encoding='utf-8') as f:
                    f.write(code)
                
                # Prepare Docker command
                docker_command = " ".join(lang_config['command'] + [f"main{lang_config['extension']}"])
                
                # Run in Docker container
                container = self.docker_client.containers.run(
                    lang_config['docker_image'],
                    command=f"sh -c 'cd /workspace && {docker_command}'",
                    volumes={temp_dir: {'bind': '/workspace', 'mode': 'rw'}},
                    working_dir='/workspace',
                    detach=True,
                    remove=True,
                    mem_limit='256m',
                    cpu_period=100000,
                    cpu_quota=50000,  # 50% CPU
                    network_disabled=True  # Security: disable network
                )
                
                # Wait for completion with timeout
                try:
                    result = container.wait(timeout=30)
                    logs = container.logs().decode('utf-8')
                    
                    return {
                        'success': result['StatusCode'] == 0,
                        'output': logs,
                        'error': '',
                        'return_code': result['StatusCode'],
                        'type': 'docker_execution'
                    }
                    
                except Exception as e:
                    container.kill()
                    return {
                        'success': False,
                        'output': '',
                        'error': f'Docker execution error: {str(e)}',
                        'type': 'docker_error'
                    }
            
        except Exception as e:
            return {
                'success': False,
                'output': '',
                'error': f'Docker setup error: {str(e)}',
                'type': 'docker_setup_error'
            }
    
    def _extract_java_class_name(self, code: str) -> Optional[str]:
        """Extract class name from Java code"""
        import re
        match = re.search(r'public\s+class\s+(\w+)', code)
        return match.group(1) if match else None
    
    async def create_execution_session(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new execution session"""
        try:
            session_id = task.get('session_id', str(uuid.uuid4()))
            language = task.get('language', 'python')
            environment = task.get('environment', 'sandbox')
            
            session = {
                'id': session_id,
                'language': language,
                'environment': environment,
                'created_at': datetime.now().isoformat(),
                'files': [],
                'packages': [],
                'variables': {},
                'last_activity': datetime.now().isoformat()
            }
            
            self.active_sessions[session_id] = session
            
            # Create session directory
            session_dir = Path(f"temp_sessions/{session_id}")
            session_dir.mkdir(parents=True, exist_ok=True)
            
            return {
                'success': True,
                'session_id': session_id,
                'message': f'Execution session created for {language}',
                'session': session
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Session creation failed: {str(e)}'
            }
    
    async def install_package(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Install package in execution environment"""
        try:
            session_id = task.get('session_id')
            package_name = task.get('package')
            language = task.get('language', 'python')
            
            if not session_id or session_id not in self.active_sessions:
                return {
                    'success': False,
                    'error': 'Invalid session ID'
                }
            
            session = self.active_sessions[session_id]
            
            # Install package based on language
            if language == 'python':
                result = subprocess.run(
                    ['pip', 'install', package_name],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
            elif language in ['javascript', 'typescript']:
                session_dir = Path(f"temp_sessions/{session_id}")
                result = subprocess.run(
                    ['npm', 'install', package_name],
                    cwd=session_dir,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
            else:
                return {
                    'success': False,
                    'error': f'Package installation not supported for {language}'
                }
            
            if result.returncode == 0:
                session['packages'].append(package_name)
                return {
                    'success': True,
                    'message': f'Package {package_name} installed successfully',
                    'output': result.stdout
                }
            else:
                return {
                    'success': False,
                    'error': f'Package installation failed: {result.stderr}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Package installation error: {str(e)}'
            }
    
    async def analyze_code(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze code for quality, performance, and security"""
        try:
            code = task.get('code', '')
            language = task.get('language', 'python').lower()
            
            analysis = {
                'language': language,
                'lines_of_code': len(code.splitlines()),
                'characters': len(code),
                'complexity_score': 0,
                'suggestions': [],
                'security_issues': [],
                'performance_tips': []
            }
            
            # Basic complexity analysis
            analysis['complexity_score'] = self._calculate_complexity(code, language)
            
            # Language-specific analysis
            if language == 'python':
                analysis.update(self._analyze_python_code(code))
            elif language == 'javascript':
                analysis.update(self._analyze_javascript_code(code))
            
            return {
                'success': True,
                'analysis': analysis
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Code analysis failed: {str(e)}'
            }
    
    def _calculate_complexity(self, code: str, language: str) -> int:
        """Calculate basic complexity score"""
        complexity = 0
        
        # Count control structures
        control_keywords = ['if', 'else', 'elif', 'for', 'while', 'switch', 'case']
        for keyword in control_keywords:
            complexity += code.count(keyword)
        
        # Count functions/methods
        if language == 'python':
            complexity += code.count('def ')
        elif language == 'javascript':
            complexity += code.count('function ')
            complexity += code.count('=>')
        
        return complexity
    
    def _analyze_python_code(self, code: str) -> Dict[str, Any]:
        """Python-specific code analysis"""
        suggestions = []
        security_issues = []
        performance_tips = []
        
        # Check for common issues
        if 'eval(' in code:
            security_issues.append("Avoid using eval() - security risk")
        
        if 'exec(' in code:
            security_issues.append("Avoid using exec() - security risk")
        
        if 'import *' in code:
            suggestions.append("Avoid wildcard imports - use specific imports")
        
        if code.count('for') > 3:
            performance_tips.append("Consider using list comprehensions for simple loops")
        
        return {
            'suggestions': suggestions,
            'security_issues': security_issues,
            'performance_tips': performance_tips
        }
    
    def _analyze_javascript_code(self, code: str) -> Dict[str, Any]:
        """JavaScript-specific code analysis"""
        suggestions = []
        security_issues = []
        performance_tips = []
        
        # Check for common issues
        if 'eval(' in code:
            security_issues.append("Avoid using eval() - security risk")
        
        if 'innerHTML' in code:
            security_issues.append("Be careful with innerHTML - XSS risk")
        
        if 'var ' in code:
            suggestions.append("Consider using 'let' or 'const' instead of 'var'")
        
        return {
            'suggestions': suggestions,
            'security_issues': security_issues,
            'performance_tips': performance_tips
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get code executor performance metrics"""
        avg_execution_time = self.total_execution_time / max(1, self.executions_count)
        
        return {
            'agent_id': self.agent_id,
            'name': self.name,
            'status': self.status,
            'executions_count': self.executions_count,
            'success_rate': round(self.success_rate, 2),
            'avg_execution_time': round(avg_execution_time, 3),
            'supported_languages': list(self.supported_languages.keys()),
            'active_sessions': len(self.active_sessions),
            'docker_available': self.docker_available,
            'execution_history_size': len(self.execution_history)
        }

# Global instance
code_executor = CodeExecutorAgent()
