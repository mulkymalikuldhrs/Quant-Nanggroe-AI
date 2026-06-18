"""
🖥️ CyberShell Agent - Advanced Shell Execution & Automation
AI-powered shell operations with security and monitoring

Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

import asyncio
import subprocess
import os
import json
import time
import shlex
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path
import threading
import queue
import psutil

class CyberShellAgent:
    """
    Advanced shell execution agent with:
    - Secure command execution
    - Real-time output streaming
    - Process management
    - System monitoring
    - Automated scripting
    - Security sandboxing
    """
    
    def __init__(self):
        self.agent_id = "cybershell"
        self.name = "CyberShell Agent"
        self.status = "ready"
        self.capabilities = [
            "shell_execution", 
            "process_management",
            "system_monitoring", 
            "automation",
            "file_operations",
            "network_commands"
        ]
        
        # Execution tracking
        self.active_processes: Dict[str, subprocess.Popen] = {}
        self.execution_history: List[Dict] = []
        self.command_queue = queue.Queue()
        
        # Security settings
        self.allowed_commands = self._load_allowed_commands()
        self.blocked_patterns = [
            "rm -rf /", ":(){ :|:& };:", "dd if=/dev/zero", 
            "mkfs", "fdisk", "parted", "shutdown", "reboot"
        ]
        
        # Performance tracking
        self.execution_stats = {
            "total_commands": 0,
            "successful_commands": 0,
            "failed_commands": 0,
            "avg_execution_time": 0
        }
        
        # Initialize working directory
        self.working_dir = os.getcwd()
        
    def _load_allowed_commands(self) -> List[str]:
        """Load list of allowed commands for security"""
        return [
            # File operations
            "ls", "cat", "head", "tail", "grep", "find", "locate",
            "cp", "mv", "mkdir", "rmdir", "touch", "chmod", "chown",
            "echo", "pwd", "whoami", "which", "whereis", "type",
            
            # System info
            "ps", "top", "htop", "free", "df", "du", "uname", "whoami",
            "id", "groups", "uptime", "date", "hostname",
            
            # Network
            "ping", "curl", "wget", "nc", "netstat", "ss", "lsof",
            
            # Development
            "git", "python", "python3", "pip", "pip3", "node", "npm",
            "docker", "docker-compose", "kubectl",
            
            # Text processing
            "awk", "sed", "sort", "uniq", "wc", "tr", "cut",
            
            # Archives
            "tar", "zip", "unzip", "gzip", "gunzip",
            
            # Package management
            "apt", "yum", "dnf", "pacman", "brew"
        ]
    
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process shell task"""
        try:
            task_type = task.get("action", "execute")
            
            if task_type in ("execute", "execute_command"):
                return await self._execute_command(task)
            elif task_type in ("file_operations", "list_files", "read_file", "write_file"):
                return await self._handle_file_action(task)
            elif task_type == "monitor_system":
                return await self._monitor_system(task)
            elif task_type == "manage_processes":
                return await self._manage_processes(task)
            elif task_type == "automation_script":
                return await self._run_automation_script(task)
            else:
                return self._create_error_response(f"Unknown task type: {task_type}")
                
        except Exception as e:
            return self._create_error_response(str(e))
    
    async def _execute_command(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute shell command safely"""
        command = task.get("command", "")
        if not command:
            return self._create_error_response("No command provided")
        
        # Security validation
        security_check = self._validate_command_security(command)
        if not security_check["safe"]:
            return self._create_error_response(f"Security violation: {security_check['reason']}")
        
        try:
            start_time = time.time()
            
            # Parse command
            args = shlex.split(command)
            base_command = args[0] if args else ""
            
            # Set environment
            env = os.environ.copy()
            env.update(task.get("env", {}))
            
            # Set working directory
            work_dir = task.get("working_dir", self.working_dir)
            
            # Execute command
            timeout = task.get("timeout", 300)  # 5 minutes default
            process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=work_dir,
                env=env,
            )
            
            # Store active process
            process_id = f"proc_{int(time.time())}_{len(self.active_processes)}"
            self.active_processes[process_id] = process
            
            # Wait for completion
            stdout, stderr = process.communicate(timeout=timeout)
            
            execution_time = time.time() - start_time
            return_code = process.returncode
            
            # Clean up
            if process_id in self.active_processes:
                del self.active_processes[process_id]
            
            # Create result
            result = {
                "success": return_code == 0,
                "command": command,
                "return_code": return_code,
                "output": stdout,
                "stdout": stdout,
                "stderr": stderr,
                "execution_time": round(execution_time, 2),
                "working_dir": work_dir,
                "process_id": process_id
            }
            
            # Update statistics
            self._update_execution_stats(return_code == 0, execution_time)
            
            # Store in history
            self.execution_history.append({
                **result,
                "timestamp": datetime.now().isoformat(),
                "task_id": task.get("task_id", "unknown")
            })
            
            # Limit history size
            if len(self.execution_history) > 1000:
                self.execution_history = self.execution_history[-500:]
            
            return result
            
        except subprocess.TimeoutExpired:
            return self._create_error_response("Command timed out")
        except FileNotFoundError:
            return self._create_error_response(f"Command not found: {base_command}")
        except Exception as e:
            return self._create_error_response(f"Execution error: {str(e)}")
    
    def _validate_command_security(self, command: str) -> Dict[str, Any]:
        """Validate command for security"""
        
        # Check for blocked patterns
        for pattern in self.blocked_patterns:
            if pattern in command:
                return {
                    "safe": False,
                    "reason": f"Blocked pattern detected: {pattern}"
                }
        
        # Check command whitelist
        args = shlex.split(command)
        if args:
            base_command = args[0]
            
            # Allow full paths if base command is allowed
            if "/" in base_command:
                base_command = os.path.basename(base_command)
            
            if base_command not in self.allowed_commands:
                return {
                    "safe": False,
                    "reason": f"Command not in whitelist: {base_command}"
                }
        
        # Check for dangerous flags
        dangerous_flags = ["-rf", "--force", "--delete", "--remove"]
        for flag in dangerous_flags:
            if flag in command and ("rm" in command or "del" in command):
                return {
                    "safe": False,
                    "reason": f"Dangerous flag detected: {flag}"
                }
        
        return {"safe": True, "reason": "Command passed security checks"}
    
    async def _monitor_system(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor system resources and performance"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            
            # Network stats
            network = psutil.net_io_counters()
            
            # Load average (Unix-like systems)
            try:
                load_avg = os.getloadavg()
            except:
                load_avg = [0, 0, 0]
            
            # Process count
            process_count = len(psutil.pids())
            
            # System uptime
            boot_time = psutil.boot_time()
            uptime = time.time() - boot_time
            
            return {
                "success": True,
                "timestamp": datetime.now().isoformat(),
                "system_stats": {
                    "cpu": {
                        "usage_percent": cpu_percent,
                        "core_count": cpu_count,
                        "load_average": load_avg
                    },
                    "memory": {
                        "total": memory.total,
                        "available": memory.available,
                        "used": memory.used,
                        "percent": memory.percent
                    },
                    "disk": {
                        "total": disk.total,
                        "used": disk.used,
                        "free": disk.free,
                        "percent": (disk.used / disk.total) * 100
                    },
                    "network": {
                        "bytes_sent": network.bytes_sent,
                        "bytes_recv": network.bytes_recv,
                        "packets_sent": network.packets_sent,
                        "packets_recv": network.packets_recv
                    },
                    "processes": {
                        "total": process_count,
                        "active_shell_processes": len(self.active_processes)
                    },
                    "uptime_seconds": uptime
                }
            }
            
        except Exception as e:
            return self._create_error_response(f"System monitoring error: {str(e)}")
    
    async def _manage_processes(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Manage running processes"""
        action = task.get("process_action", "list")
        
        try:
            if action == "list":
                return self._list_processes()
            elif action == "kill":
                return self._kill_process(task.get("process_id"))
            elif action == "status":
                return self._get_process_status(task.get("process_id"))
            else:
                return self._create_error_response(f"Unknown process action: {action}")
                
        except Exception as e:
            return self._create_error_response(f"Process management error: {str(e)}")
    
    def _list_processes(self) -> Dict[str, Any]:
        """List active shell processes"""
        process_list = []
        
        for process_id, process in self.active_processes.items():
            try:
                process_info = {
                    "process_id": process_id,
                    "pid": process.pid,
                    "command": " ".join(process.args) if hasattr(process, 'args') else "unknown",
                    "status": "running" if process.poll() is None else "completed",
                    "return_code": process.returncode
                }
                process_list.append(process_info)
            except:
                process_list.append({
                    "process_id": process_id,
                    "status": "error",
                    "error": "Could not get process info"
                })
        
        return {
            "success": True,
            "active_processes": process_list,
            "total_processes": len(process_list)
        }
    
    def _kill_process(self, process_id: str) -> Dict[str, Any]:
        """Kill a specific process"""
        if process_id not in self.active_processes:
            return self._create_error_response(f"Process {process_id} not found")
        
        try:
            process = self.active_processes[process_id]
            process.terminate()
            
            # Wait a bit for graceful termination
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Force kill if still running
                process.kill()
                process.wait()
            
            del self.active_processes[process_id]
            
            return {
                "success": True,
                "message": f"Process {process_id} terminated",
                "process_id": process_id
            }
            
        except Exception as e:
            return self._create_error_response(f"Failed to kill process: {str(e)}")
    
    async def _handle_file_action(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Handle file action tasks (list_files, read_file, write_file, file_operations)"""
        action = task.get("action", "")
        if action == "list_files":
            path = task.get("path", ".")
            return await self._list_directory(path)
        elif action == "read_file":
            return await self._read_file(task.get("file_path"))
        elif action == "write_file":
            return await self._write_file(task.get("file_path"), task.get("content", ""))
        else:
            # Default to file_operations handler
            return await self._file_operations(task)
    
    async def _list_directory(self, directory: str = ".") -> Dict[str, Any]:
        """List files in a directory"""
        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                return self._create_error_response(f"Directory not found: {directory}")
            if not dir_path.is_dir():
                return self._create_error_response(f"Path is not a directory: {directory}")
            
            files = []
            for item in sorted(dir_path.iterdir()):
                files.append({
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else 0,
                    "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                })
            
            return {
                "success": True,
                "files": files,
                "path": str(dir_path.resolve()),
                "total_files": len(files)
            }
        except Exception as e:
            return self._create_error_response(f"Failed to list directory: {str(e)}")
    
    async def _file_operations(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Perform file operations"""
        operation = task.get("operation", "")
        
        try:
            if operation == "read":
                return await self._read_file(task.get("file_path"))
            elif operation == "write":
                return await self._write_file(task.get("file_path"), task.get("content", ""))
            elif operation == "list":
                return await self._list_directory(task.get("directory", "."))
            elif operation == "create_dir":
                return await self._create_directory(task.get("directory"))
            elif operation == "delete":
                return await self._delete_file(task.get("file_path"))
            else:
                return self._create_error_response(f"Unknown file operation: {operation}")
                
        except Exception as e:
            return self._create_error_response(f"File operation error: {str(e)}")
    
    async def _read_file(self, file_path: str) -> Dict[str, Any]:
        """Read file content"""
        try:
            if not file_path:
                return self._create_error_response("No file path provided")
            
            path = Path(file_path)
            if not path.exists():
                return self._create_error_response(f"File not found: {file_path}")
            
            if not path.is_file():
                return self._create_error_response(f"Path is not a file: {file_path}")
            
            # Security check - prevent reading sensitive files
            sensitive_patterns = ["/etc/passwd", "/etc/shadow", "/.ssh/", "id_rsa"]
            if any(pattern in str(path) for pattern in sensitive_patterns):
                return self._create_error_response("Access to sensitive file denied")
            
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                "success": True,
                "file_path": file_path,
                "content": content,
                "size": len(content),
                "lines": len(content.split('\n'))
            }
            
        except UnicodeDecodeError:
            return self._create_error_response("File is not readable as text")
        except Exception as e:
            return self._create_error_response(f"Failed to read file: {str(e)}")
    
    async def _write_file(self, file_path: str, content: str = "") -> Dict[str, Any]:
        """Write content to a file"""
        try:
            if not file_path:
                return self._create_error_response("No file path provided")
            
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return {
                "success": True,
                "file_path": file_path,
                "size": len(content),
                "message": f"File written successfully: {file_path}"
            }
        except Exception as e:
            return self._create_error_response(f"Failed to write file: {str(e)}")
    
    async def _run_automation_script(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Run automation script with multiple commands"""
        script = task.get("script", [])
        if not script:
            return self._create_error_response("No script provided")
        
        results = []
        overall_success = True
        
        for i, command_task in enumerate(script):
            if isinstance(command_task, str):
                command_task = {"command": command_task}
            
            command_task["task_id"] = f"{task.get('task_id', 'script')}_{i}"
            
            try:
                result = await self._execute_command(command_task)
                results.append(result)
                
                if not result.get("success", False):
                    overall_success = False
                    
                    # Check if we should continue on error
                    if not task.get("continue_on_error", False):
                        break
                        
            except Exception as e:
                error_result = self._create_error_response(f"Script step {i} failed: {str(e)}")
                results.append(error_result)
                overall_success = False
                
                if not task.get("continue_on_error", False):
                    break
        
        return {
            "success": overall_success,
            "script_results": results,
            "steps_completed": len(results),
            "total_steps": len(script)
        }
    
    def _update_execution_stats(self, success: bool, execution_time: float):
        """Update execution statistics"""
        self.execution_stats["total_commands"] += 1
        
        if success:
            self.execution_stats["successful_commands"] += 1
        else:
            self.execution_stats["failed_commands"] += 1
        
        # Update average execution time
        current_avg = self.execution_stats["avg_execution_time"]
        total = self.execution_stats["total_commands"]
        self.execution_stats["avg_execution_time"] = (current_avg * (total - 1) + execution_time) / total
    
    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """Create standardized error response"""
        self._update_execution_stats(False, 0)
        
        return {
            "success": False,
            "error": error_message,
            "timestamp": datetime.now().isoformat(),
            "agent": self.agent_id
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get agent performance metrics"""
        return {
            "agent_id": self.agent_id,
            "status": self.status,
            "capabilities": self.capabilities,
            "execution_stats": self.execution_stats,
            "active_processes": len(self.active_processes),
            "history_size": len(self.execution_history),
            "allowed_commands": len(self.allowed_commands),
            "working_directory": self.working_dir
        }
    
    def get_execution_history(self, limit: int = 50) -> List[Dict]:
        """Get recent execution history"""
        return self.execution_history[-limit:] if self.execution_history else []
    
    def cleanup_completed_processes(self):
        """Clean up completed processes"""
        completed = []
        
        for process_id, process in self.active_processes.items():
            if process.poll() is not None:  # Process completed
                completed.append(process_id)
        
        for process_id in completed:
            del self.active_processes[process_id]
        
        return len(completed)

# Global instance
cybershell_agent = CyberShellAgent()
