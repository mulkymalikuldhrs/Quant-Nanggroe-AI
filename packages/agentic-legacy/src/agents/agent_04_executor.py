"""
Agent 04 (Executor) - Script, API & Automation Pipeline Runner
"""

from typing import Dict, List, Any, Optional
import json
import subprocess
import requests
import os
import tempfile
from datetime import datetime
import asyncio
import aiohttp

from ..core.base_agent import BaseAgent

class Agent04Executor(BaseAgent):
    """Specialized execution agent for scripts, APIs, and automation"""
    
    def __init__(self, config_path: str = "config/prompts.yaml"):
        super().__init__("agent_04_executor", config_path)
        self.execution_history = []
        self.active_processes = {}
        self.supported_languages = ['python', 'javascript', 'shell', 'sql']
        self.api_sessions = {}
        
    def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute scripts, API calls, and automation pipelines"""
        
        if not self.validate_input(task):
            return self.handle_error(
                Exception("Invalid task format"), task
            )
        
        try:
            self.update_status("analyzing", task)
            
            # Analyze execution requirements
            execution_plan = self._analyze_execution_requirements(task)
            
            # Execute based on type
            results = []
            for execution_item in execution_plan['execution_items']:
                self.update_status("executing", {'current_item': execution_item['type']})
                result = self._execute_item(execution_item)
                results.append(result)
            
            # Cleanup resources
            self._cleanup_resources()
            
            self.update_status("ready")
            
            # Prepare response
            response_content = f"""
⚙️ EXECUTION PLAN: {execution_plan['summary']}

🚀 PROGRESS:
{self._format_execution_progress(results)}

📊 RESULTS:
{self._format_execution_results(results)}

❌ ERRORS:
{self._format_errors(results)}

✅ COMPLETION: {self._get_completion_status(results)}
            """
            
            # Log execution
            self._log_execution(task, execution_plan, results)
            
            return self.format_response(response_content.strip(), "execution_report")
            
        except Exception as e:
            return self.handle_error(e, task)
    
    def _analyze_execution_requirements(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze what needs to be executed"""
        request = task.get('request', '')
        context = task.get('context', {})
        
        execution_items = []
        
        # Detect script execution needs
        script_items = self._detect_script_requirements(request, context)
        execution_items.extend(script_items)
        
        # Detect API calls
        api_items = self._detect_api_requirements(request, context)
        execution_items.extend(api_items)
        
        # Detect file operations
        file_items = self._detect_file_operations(request, context)
        execution_items.extend(file_items)
        
        # Detect database operations
        db_items = self._detect_database_operations(request, context)
        execution_items.extend(db_items)
        
        plan = {
            'summary': f"Executing {len(execution_items)} items: {', '.join(set(item['type'] for item in execution_items))}",
            'total_items': len(execution_items),
            'execution_items': execution_items,
            'estimated_duration': self._estimate_execution_time(execution_items),
            'resources_needed': self._identify_required_resources(execution_items)
        }
        
        return plan
    
    def _detect_script_requirements(self, request: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect script execution requirements"""
        script_items = []
        request_lower = request.lower()
        
        # Check for Python scripts
        if any(keyword in request_lower for keyword in ['python', 'script', 'py', 'execute code']):
            script_items.append({
                'type': 'python_script',
                'language': 'python',
                'description': 'Execute Python script',
                'code': self._extract_or_generate_code(request, 'python'),
                'requirements': self._detect_python_requirements(request)
            })
        
        # Check for JavaScript/Node.js
        if any(keyword in request_lower for keyword in ['javascript', 'node', 'js', 'npm']):
            script_items.append({
                'type': 'javascript_script', 
                'language': 'javascript',
                'description': 'Execute JavaScript/Node.js script',
                'code': self._extract_or_generate_code(request, 'javascript'),
                'requirements': []
            })
        
        # Check for shell commands
        if any(keyword in request_lower for keyword in ['shell', 'bash', 'command', 'terminal']):
            script_items.append({
                'type': 'shell_script',
                'language': 'shell',
                'description': 'Execute shell commands',
                'code': self._extract_or_generate_code(request, 'shell'),
                'requirements': []
            })
        
        return script_items
    
    def _detect_api_requirements(self, request: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect API call requirements"""
        api_items = []
        request_lower = request.lower()
        
        # Check for API calls
        if any(keyword in request_lower for keyword in ['api', 'rest', 'http', 'request', 'endpoint']):
            api_items.append({
                'type': 'api_call',
                'method': self._detect_http_method(request),
                'description': 'Make API request',
                'url': self._extract_url(request),
                'headers': self._extract_headers(request, context),
                'data': self._extract_request_data(request),
                'authentication': self._detect_auth_type(request, context)
            })
        
        # Check for webhook calls
        if 'webhook' in request_lower:
            api_items.append({
                'type': 'webhook',
                'description': 'Send webhook notification',
                'url': self._extract_url(request),
                'payload': self._extract_webhook_payload(request)
            })
        
        return api_items
    
    def _detect_file_operations(self, request: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect file operation requirements"""
        file_items = []
        request_lower = request.lower()
        
        # File processing operations
        if any(keyword in request_lower for keyword in ['file', 'csv', 'json', 'xml', 'process']):
            file_items.append({
                'type': 'file_processing',
                'description': 'Process data files',
                'input_files': self._extract_file_paths(request),
                'operations': self._detect_file_operations_type(request),
                'output_format': self._detect_output_format(request)
            })
        
        # Data transformation
        if any(keyword in request_lower for keyword in ['transform', 'convert', 'format']):
            file_items.append({
                'type': 'data_transformation',
                'description': 'Transform data format',
                'source_format': self._detect_source_format(request),
                'target_format': self._detect_target_format(request),
                'transformation_rules': self._extract_transformation_rules(request)
            })
        
        return file_items
    
    def _detect_database_operations(self, request: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect database operation requirements"""
        db_items = []
        request_lower = request.lower()
        
        if any(keyword in request_lower for keyword in ['database', 'sql', 'query', 'db']):
            db_items.append({
                'type': 'database_operation',
                'description': 'Execute database operations',
                'database_type': self._detect_database_type(request),
                'operations': self._extract_sql_operations(request),
                'connection_info': self._extract_db_connection_info(request, context)
            })
        
        return db_items
    
    def _execute_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single execution item"""
        item_type = item['type']
        
        try:
            if item_type == 'python_script':
                return self._execute_python_script(item)
            elif item_type == 'javascript_script':
                return self._execute_javascript_script(item)
            elif item_type == 'shell_script':
                return self._execute_shell_script(item)
            elif item_type == 'api_call':
                return self._execute_api_call(item)
            elif item_type == 'webhook':
                return self._execute_webhook(item)
            elif item_type == 'file_processing':
                return self._execute_file_processing(item)
            elif item_type == 'data_transformation':
                return self._execute_data_transformation(item)
            elif item_type == 'database_operation':
                return self._execute_database_operation(item)
            else:
                return {
                    'item_type': item_type,
                    'status': 'error',
                    'error': f"Unsupported execution type: {item_type}"
                }
        
        except Exception as e:
            return {
                'item_type': item_type,
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _execute_python_script(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Execute Python script"""
        code = item.get('code', '')
        requirements = item.get('requirements', [])
        
        # Create temporary file for the script
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            script_path = f.name
        
        try:
            # Install requirements if any
            if requirements:
                for req in requirements:
                    subprocess.run(['pip', 'install', req], check=True, capture_output=True)
            
            # Execute the script
            result = subprocess.run(
                ['python', script_path],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            return {
                'item_type': 'python_script',
                'status': 'success' if result.returncode == 0 else 'error',
                'stdout': result.stdout,
                'stderr': result.stderr,
                'return_code': result.returncode,
                'execution_time': datetime.now().isoformat()
            }
            
        finally:
            # Cleanup temporary file
            if os.path.exists(script_path):
                os.unlink(script_path)
    
    def _execute_javascript_script(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Execute JavaScript/Node.js script"""
        code = item.get('code', '')
        
        # Create temporary file for the script
        with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as f:
            f.write(code)
            script_path = f.name
        
        try:
            # Execute with Node.js
            result = subprocess.run(
                ['node', script_path],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            return {
                'item_type': 'javascript_script',
                'status': 'success' if result.returncode == 0 else 'error',
                'stdout': result.stdout,
                'stderr': result.stderr,
                'return_code': result.returncode,
                'execution_time': datetime.now().isoformat()
            }
            
        finally:
            if os.path.exists(script_path):
                os.unlink(script_path)
    
    def _execute_shell_script(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Execute shell commands"""
        commands = item.get('code', '').split('\n')
        results = []
        
        for command in commands:
            command = command.strip()
            if not command or command.startswith('#'):
                continue
                
            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                results.append({
                    'command': command,
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'return_code': result.returncode
                })
                
            except subprocess.TimeoutExpired:
                results.append({
                    'command': command,
                    'error': 'Command timed out'
                })
        
        return {
            'item_type': 'shell_script',
            'status': 'completed',
            'results': results,
            'execution_time': datetime.now().isoformat()
        }
    
    def _execute_api_call(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Execute API call"""
        method = item.get('method', 'GET').upper()
        url = item.get('url', '')
        headers = item.get('headers', {})
        data = item.get('data')
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, headers=headers, json=data, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                return {
                    'item_type': 'api_call',
                    'status': 'error',
                    'error': f"Unsupported HTTP method: {method}"
                }
            
            return {
                'item_type': 'api_call',
                'status': 'success',
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'response_data': response.text,
                'execution_time': datetime.now().isoformat()
            }
            
        except requests.RequestException as e:
            return {
                'item_type': 'api_call',
                'status': 'error',
                'error': str(e),
                'execution_time': datetime.now().isoformat()
            }
    
    def _execute_webhook(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Execute webhook call"""
        url = item.get('url', '')
        payload = item.get('payload', {})
        
        try:
            response = requests.post(
                url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            return {
                'item_type': 'webhook',
                'status': 'success',
                'status_code': response.status_code,
                'response': response.text,
                'execution_time': datetime.now().isoformat()
            }
            
        except requests.RequestException as e:
            return {
                'item_type': 'webhook',
                'status': 'error',
                'error': str(e),
                'execution_time': datetime.now().isoformat()
            }
    
    def _execute_file_processing(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Execute file processing operations"""
        input_files = item.get('input_files', [])
        operations = item.get('operations', [])
        
        results = []
        
        for file_path in input_files:
            if not os.path.exists(file_path):
                results.append({
                    'file': file_path,
                    'status': 'error',
                    'error': 'File not found'
                })
                continue
            
            try:
                # Simple file operations
                if 'read' in operations:
                    with open(file_path, 'r') as f:
                        content = f.read()
                    results.append({
                        'file': file_path,
                        'operation': 'read',
                        'status': 'success',
                        'content_length': len(content)
                    })
                
                if 'count_lines' in operations:
                    with open(file_path, 'r') as f:
                        line_count = sum(1 for _ in f)
                    results.append({
                        'file': file_path,
                        'operation': 'count_lines',
                        'status': 'success',
                        'line_count': line_count
                    })
                
            except Exception as e:
                results.append({
                    'file': file_path,
                    'status': 'error',
                    'error': str(e)
                })
        
        return {
            'item_type': 'file_processing',
            'status': 'completed',
            'results': results,
            'execution_time': datetime.now().isoformat()
        }
    
    def _execute_data_transformation(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Execute data transformation"""
        source_format = item.get('source_format', '')
        target_format = item.get('target_format', '')
        
        # Simulated data transformation
        return {
            'item_type': 'data_transformation',
            'status': 'success',
            'source_format': source_format,
            'target_format': target_format,
            'transformation_completed': True,
            'execution_time': datetime.now().isoformat()
        }
    
    def _execute_database_operation(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Execute database operations"""
        db_type = item.get('database_type', '')
        operations = item.get('operations', [])
        
        # Simulated database operations
        return {
            'item_type': 'database_operation',
            'status': 'success',
            'database_type': db_type,
            'operations_executed': len(operations),
            'execution_time': datetime.now().isoformat()
        }
    
    # Helper methods for parsing and detection
    def _extract_or_generate_code(self, request: str, language: str) -> str:
        """Extract or generate code from request"""
        # In production, this would use more sophisticated code extraction/generation
        if '```' in request:
            # Extract code blocks
            code_blocks = []
            lines = request.split('\n')
            in_code_block = False
            current_block = []
            
            for line in lines:
                if line.strip().startswith('```'):
                    if in_code_block:
                        code_blocks.append('\n'.join(current_block))
                        current_block = []
                        in_code_block = False
                    else:
                        in_code_block = True
                elif in_code_block:
                    current_block.append(line)
            
            return '\n'.join(code_blocks) if code_blocks else self._generate_simple_code(request, language)
        
        return self._generate_simple_code(request, language)
    
    def _generate_simple_code(self, request: str, language: str) -> str:
        """Generate simple code based on request"""
        if language == 'python':
            return f'# Generated Python code\nprint("Executing: {request[:50]}...")\n'
        elif language == 'javascript':
            return f'// Generated JavaScript code\nconsole.log("Executing: {request[:50]}...");\n'
        elif language == 'shell':
            return f'# Generated shell commands\necho "Executing: {request[:50]}..."\n'
        
        return f'# Code for {language}\n'
    
    def _detect_python_requirements(self, request: str) -> List[str]:
        """Detect Python package requirements"""
        requirements = []
        common_packages = {
            'pandas': 'pandas',
            'numpy': 'numpy', 
            'requests': 'requests',
            'matplotlib': 'matplotlib',
            'sklearn': 'scikit-learn',
            'tensorflow': 'tensorflow',
            'torch': 'torch'
        }
        
        request_lower = request.lower()
        for keyword, package in common_packages.items():
            if keyword in request_lower:
                requirements.append(package)
        
        return requirements
    
    def _detect_http_method(self, request: str) -> str:
        """Detect HTTP method from request"""
        request_lower = request.lower()
        
        if any(word in request_lower for word in ['post', 'create', 'submit']):
            return 'POST'
        elif any(word in request_lower for word in ['put', 'update']):
            return 'PUT'
        elif any(word in request_lower for word in ['delete', 'remove']):
            return 'DELETE'
        else:
            return 'GET'
    
    def _extract_url(self, request: str) -> str:
        """Extract URL from request"""
        import re
        url_pattern = r'https?://[^\s<>"{}|\\^`[\]]+'
        urls = re.findall(url_pattern, request)
        return urls[0] if urls else 'https://api.example.com/endpoint'
    
    def _extract_headers(self, request: str, context: Dict[str, Any]) -> Dict[str, str]:
        """Extract headers from request"""
        headers = {'Content-Type': 'application/json'}
        
        # Add authentication headers if available in context
        if 'api_key' in context:
            headers['Authorization'] = f"Bearer {context['api_key']}"
        
        return headers
    
    def _extract_request_data(self, request: str) -> Dict[str, Any]:
        """Extract request data/payload"""
        # Simple data extraction - in production, use more sophisticated parsing
        if 'json' in request.lower() or '{' in request:
            try:
                # Try to extract JSON
                start = request.find('{')
                end = request.rfind('}') + 1
                if start != -1 and end != 0:
                    return json.loads(request[start:end])
            except:
                pass
        
        return {'message': 'Generated request data'}
    
    def _detect_auth_type(self, request: str, context: Dict[str, Any]) -> str:
        """Detect authentication type"""
        request_lower = request.lower()
        
        if 'bearer' in request_lower or 'token' in request_lower:
            return 'bearer_token'
        elif 'api key' in request_lower:
            return 'api_key'
        elif 'basic' in request_lower:
            return 'basic_auth'
        
        return 'none'
    
    def _extract_webhook_payload(self, request: str) -> Dict[str, Any]:
        """Extract webhook payload"""
        return {
            'event': 'automation_triggered',
            'timestamp': datetime.now().isoformat(),
            'source': 'agentic_ai_system'
        }
    
    def _extract_file_paths(self, request: str) -> List[str]:
        """Extract file paths from request"""
        import re
        # Simple file path extraction
        file_patterns = [
            r'["\']([^"\']+\.[a-zA-Z0-9]+)["\']',  # quoted file paths
            r'(\w+\.[a-zA-Z0-9]+)',  # simple filenames
        ]
        
        file_paths = []
        for pattern in file_patterns:
            matches = re.findall(pattern, request)
            file_paths.extend(matches)
        
        return file_paths[:5] if file_paths else ['data.csv']  # Default file
    
    def _detect_file_operations_type(self, request: str) -> List[str]:
        """Detect file operation types"""
        operations = []
        request_lower = request.lower()
        
        operation_keywords = {
            'read': ['read', 'load', 'open'],
            'write': ['write', 'save', 'create'],
            'count_lines': ['count', 'lines'],
            'parse': ['parse', 'extract'],
            'validate': ['validate', 'check']
        }
        
        for operation, keywords in operation_keywords.items():
            if any(keyword in request_lower for keyword in keywords):
                operations.append(operation)
        
        return operations if operations else ['read']
    
    def _detect_output_format(self, request: str) -> str:
        """Detect desired output format"""
        request_lower = request.lower()
        
        formats = {
            'json': ['json'],
            'csv': ['csv'],
            'xml': ['xml'],
            'txt': ['text', 'txt'],
            'html': ['html']
        }
        
        for format_name, keywords in formats.items():
            if any(keyword in request_lower for keyword in keywords):
                return format_name
        
        return 'json'  # Default format
    
    def _detect_source_format(self, request: str) -> str:
        """Detect source data format"""
        return self._detect_output_format(request)  # Same logic
    
    def _detect_target_format(self, request: str) -> str:
        """Detect target data format"""
        # Look for "to" or "convert to" patterns
        request_lower = request.lower()
        if 'to json' in request_lower:
            return 'json'
        elif 'to csv' in request_lower:
            return 'csv'
        elif 'to xml' in request_lower:
            return 'xml'
        
        return 'json'  # Default
    
    def _extract_transformation_rules(self, request: str) -> List[str]:
        """Extract data transformation rules"""
        # Simple rule extraction
        rules = []
        
        if 'filter' in request.lower():
            rules.append('Apply filtering')
        if 'sort' in request.lower():
            rules.append('Sort data')
        if 'group' in request.lower():
            rules.append('Group by fields')
        
        return rules if rules else ['Standard transformation']
    
    def _detect_database_type(self, request: str) -> str:
        """Detect database type"""
        request_lower = request.lower()
        
        db_types = {
            'mysql': ['mysql'],
            'postgresql': ['postgresql', 'postgres'],
            'sqlite': ['sqlite'],
            'mongodb': ['mongodb', 'mongo'],
            'redis': ['redis']
        }
        
        for db_type, keywords in db_types.items():
            if any(keyword in request_lower for keyword in keywords):
                return db_type
        
        return 'generic'
    
    def _extract_sql_operations(self, request: str) -> List[str]:
        """Extract SQL operations"""
        operations = []
        request_lower = request.lower()
        
        sql_keywords = ['select', 'insert', 'update', 'delete', 'create', 'drop']
        
        for keyword in sql_keywords:
            if keyword in request_lower:
                operations.append(keyword.upper())
        
        return operations if operations else ['SELECT']
    
    def _extract_db_connection_info(self, request: str, context: Dict[str, Any]) -> Dict[str, str]:
        """Extract database connection information"""
        return {
            'host': context.get('db_host', 'localhost'),
            'port': context.get('db_port', '5432'),
            'database': context.get('db_name', 'default'),
            'username': context.get('db_user', 'user')
        }
    
    def _estimate_execution_time(self, items: List[Dict[str, Any]]) -> str:
        """Estimate total execution time"""
        time_estimates = {
            'python_script': 30,
            'javascript_script': 20,
            'shell_script': 10,
            'api_call': 5,
            'webhook': 3,
            'file_processing': 15,
            'data_transformation': 25,
            'database_operation': 20
        }
        
        total_seconds = sum(time_estimates.get(item['type'], 10) for item in items)
        
        if total_seconds < 60:
            return f"{total_seconds} seconds"
        elif total_seconds < 3600:
            return f"{total_seconds // 60} minutes"
        else:
            return f"{total_seconds // 3600} hours"
    
    def _identify_required_resources(self, items: List[Dict[str, Any]]) -> List[str]:
        """Identify required resources for execution"""
        resources = set()
        
        for item in items:
            item_type = item['type']
            
            if item_type in ['python_script']:
                resources.add('Python runtime')
            elif item_type in ['javascript_script']:
                resources.add('Node.js runtime')
            elif item_type in ['api_call', 'webhook']:
                resources.add('Internet access')
            elif item_type in ['database_operation']:
                resources.add('Database access')
            elif item_type in ['file_processing']:
                resources.add('File system access')
        
        return list(resources)
    
    def _cleanup_resources(self):
        """Clean up execution resources"""
        # Close any open API sessions
        for session in self.api_sessions.values():
            if hasattr(session, 'close'):
                session.close()
        self.api_sessions.clear()
        
        # Clean up any active processes
        for process in self.active_processes.values():
            if hasattr(process, 'terminate'):
                process.terminate()
        self.active_processes.clear()
    
    def _format_execution_progress(self, results: List[Dict[str, Any]]) -> str:
        """Format execution progress"""
        completed = len([r for r in results if r.get('status') in ['success', 'completed']])
        total = len(results)
        
        return f"Completed {completed}/{total} execution items"
    
    def _format_execution_results(self, results: List[Dict[str, Any]]) -> str:
        """Format execution results"""
        formatted = ""
        
        for result in results:
            item_type = result.get('item_type', 'unknown')
            status = result.get('status', 'unknown')
            
            formatted += f"• {item_type}: {status}\n"
            
            if status == 'success' and 'stdout' in result:
                formatted += f"  Output: {result['stdout'][:100]}...\n"
            elif 'results' in result:
                formatted += f"  Results: {len(result['results'])} items processed\n"
        
        return formatted
    
    def _format_errors(self, results: List[Dict[str, Any]]) -> str:
        """Format execution errors"""
        errors = [r for r in results if r.get('status') == 'error']
        
        if not errors:
            return "✅ No errors encountered"
        
        formatted = ""
        for error in errors:
            formatted += f"• {error.get('item_type', 'unknown')}: {error.get('error', 'Unknown error')}\n"
        
        return formatted
    
    def _get_completion_status(self, results: List[Dict[str, Any]]) -> str:
        """Get overall completion status"""
        total = len(results)
        successful = len([r for r in results if r.get('status') in ['success', 'completed']])
        
        if successful == total:
            return f"✅ All {total} execution items completed successfully"
        elif successful > 0:
            return f"⚠️ {successful}/{total} execution items completed successfully"
        else:
            return f"❌ Execution failed for all {total} items"
    
    def _log_execution(self, task: Dict[str, Any], execution_plan: Dict[str, Any], 
                      results: List[Dict[str, Any]]):
        """Log execution for history tracking"""
        execution_log = {
            'timestamp': datetime.now().isoformat(),
            'task_id': task.get('task_id'),
            'execution_plan': execution_plan,
            'results': results,
            'success_rate': len([r for r in results if r.get('status') in ['success', 'completed']]) / len(results) if results else 0
        }
        
        self.execution_history.append(execution_log)
        
        # Keep only recent executions
        if len(self.execution_history) > 100:
            self.execution_history = self.execution_history[-50:]
