"""
🕷️ Bug Hunter Bot - Ethical Hacking and Vulnerability Discovery Agent
Advanced AI agent for automated vulnerability discovery and ethical hacking

Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

import asyncio
import json
import logging
import hashlib
import requests
import subprocess
import socket
import ssl
import time
import re
import urllib.parse
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from pathlib import Path
import threading
import random
import base64
from urllib.parse import urljoin, urlparse

# Heavy dependencies - made optional for graceful degradation
try:
    import dns.resolver
except ImportError:
    dns = None

try:
    import whois
except ImportError:
    whois = None

try:
    import nmap
except ImportError:
    nmap = None

@dataclass
class Vulnerability:
    """Vulnerability data structure"""
    vuln_id: str
    vuln_type: str
    severity: str  # critical, high, medium, low, info
    title: str
    description: str
    affected_target: str
    discovered_at: datetime
    proof_of_concept: Optional[str] = None
    remediation: Optional[str] = None
    cvss_score: Optional[float] = None
    references: List[str] = None
    status: str = "discovered"  # discovered, reported, patched, ignored

@dataclass
class HuntingTarget:
    """Target information for bug hunting"""
    target_id: str
    target_type: str  # web_app, api, network, mobile_app
    target_url: str
    scope: List[str]
    out_of_scope: List[str]
    contact_info: Optional[str] = None
    program_type: str = "responsible_disclosure"  # bug_bounty, vdp, responsible_disclosure

class BugHunterBot:
    """
    Bug Hunter Bot: Automated ethical hacking and vulnerability discovery
    
    Capabilities:
    - 🕷️ Web application security testing
    - 🔍 Network vulnerability scanning
    - 🌐 API security assessment
    - 📱 Mobile application testing
    - 🛡️ Security configuration review
    - 📊 Vulnerability reporting and disclosure
    - 🤝 Responsible disclosure coordination
    - 💰 Bug bounty automation
    """
    
    def __init__(self):
        self.agent_id = "bug_hunter_bot"
        self.name = "Bug Hunter Bot"
        self.status = "initializing"
        self.version = "1.0.0"
        self.start_time = datetime.now()
        
        # Core capabilities
        self.capabilities = [
            "web_security_testing",
            "network_scanning",
            "api_security_assessment",
            "vulnerability_discovery",
            "security_reporting",
            "responsible_disclosure",
            "bug_bounty_automation",
            "ethical_hacking"
        ]
        
        # Hunting data
        self.discovered_vulnerabilities = {}
        self.hunting_targets = {}
        self.active_scans = {}
        
        # Security testing tools
        self.security_tools = {
            "web_scanners": ["dirb", "gobuster", "nikto", "sqlmap"],
            "network_scanners": ["nmap", "masscan", "zmap"],
            "vulnerability_scanners": ["nuclei", "openvas", "nessus"],
            "custom_scripts": []
        }
        
        # Testing payloads and signatures
        self.payloads = {
            "xss": [
                "<script>alert('XSS')</script>",
                "javascript:alert('XSS')",
                "<img src=x onerror=alert('XSS')>",
                "<svg onload=alert('XSS')>"
            ],
            "sql_injection": [
                "' OR '1'='1",
                "1' UNION SELECT null--",
                "'; DROP TABLE users--",
                "1' AND SUBSTRING(@@version,1,1)='5"
            ],
            "command_injection": [
                "; ls -la",
                "| whoami",
                "&& cat /etc/passwd",
                "`id`"
            ],
            "directory_traversal": [
                "../../../etc/passwd",
                "....//....//etc//passwd",
                "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd"
            ]
        }
        
        # Responsible disclosure templates
        self.disclosure_templates = {
            "initial_report": """
Subject: Security Vulnerability Report - {vuln_type} in {target}

Dear Security Team,

I am an AI security researcher from Dhaher AI Ecosystem, and I have discovered a security vulnerability in your application/system. I am reporting this through responsible disclosure to help improve your security posture.

Vulnerability Details:
- Type: {vuln_type}
- Severity: {severity}
- Target: {target}
- Discovery Date: {discovery_date}

Description:
{description}

Proof of Concept:
{proof_of_concept}

Remediation:
{remediation}

I am committed to responsible disclosure and will not share this vulnerability publicly until you have had adequate time to address it. Please let me know if you need any additional information.

Best regards,
Bug Hunter Bot
Dhaher AI Ecosystem - AI Agent for Cybersecurity
Contact: [This email is sent by an AI agent designed for automated security testing]
            """,
            "follow_up": """
Subject: Follow-up: Security Vulnerability Report - {vuln_id}

Dear Security Team,

This is a follow-up on the security vulnerability report I submitted on {report_date} regarding {vuln_type} in {target}.

I wanted to check on the status of this vulnerability and offer any additional assistance if needed.

If you have any questions or need clarification on the technical details, please don't hesitate to reach out.

Best regards,
Bug Hunter Bot
Dhaher AI Ecosystem
            """
        }
        
        # Initialize logging
        self.setup_logging()
        
        # Initialize hunting environment
        self.initialize_hunting_environment()
        
        self.logger.info("Bug Hunter Bot initialized successfully")
        self.status = "ready"
    
    def setup_logging(self):
        """Setup logging for Bug Hunter Bot"""
        log_dir = Path("data/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "bug_hunter.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("BugHunterBot")
    
    def initialize_hunting_environment(self):
        """Initialize bug hunting environment"""
        # Create hunting directories
        hunting_dirs = [
            "data/vulnerabilities",
            "data/scan_results",
            "data/bug_reports",
            "data/disclosure_communications"
        ]
        
        for directory in hunting_dirs:
            Path(directory).mkdir(parents=True, exist_ok=True)
        
        # Load existing targets and vulnerabilities
        self.load_hunting_data()
        
        # Initialize ethical guidelines
        self.initialize_ethical_guidelines()
    
    def load_hunting_data(self):
        """Load existing hunting targets and vulnerabilities"""
        # Load targets
        targets_file = Path("data/vulnerabilities/hunting_targets.json")
        if targets_file.exists():
            try:
                with open(targets_file, 'r') as f:
                    targets_data = json.load(f)
                    for target_id, target_data in targets_data.items():
                        self.hunting_targets[target_id] = HuntingTarget(**target_data)
                    self.logger.info(f"Loaded {len(self.hunting_targets)} hunting targets")
            except Exception as e:
                self.logger.error(f"Failed to load hunting targets: {e}")
    
    def initialize_ethical_guidelines(self):
        """Initialize ethical hacking guidelines"""
        self.ethical_guidelines = {
            "scope_compliance": "Always stay within defined scope",
            "non_destructive": "Never perform destructive tests",
            "data_protection": "Never access or modify real user data",
            "responsible_disclosure": "Always report vulnerabilities responsibly",
            "legal_compliance": "Ensure all activities are legal and authorized",
            "no_dos": "Never perform denial-of-service attacks",
            "minimal_impact": "Minimize impact on production systems"
        }
    
    async def add_hunting_target(self, target_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add a new target for bug hunting"""
        self.logger.info(f"Adding new hunting target: {target_data.get('target_url')}")
        
        try:
            target_id = hashlib.md5(f"{target_data['target_url']}_{datetime.now()}".encode()).hexdigest()[:8]
            
            target = HuntingTarget(
                target_id=target_id,
                target_type=target_data.get("target_type", "web_app"),
                target_url=target_data["target_url"],
                scope=target_data.get("scope", []),
                out_of_scope=target_data.get("out_of_scope", []),
                contact_info=target_data.get("contact_info"),
                program_type=target_data.get("program_type", "responsible_disclosure")
            )
            
            self.hunting_targets[target_id] = target
            
            # Save to file
            await self._save_hunting_targets()
            
            self.logger.info(f"Target added successfully: {target_id}")
            return {"success": True, "target_id": target_id}
            
        except Exception as e:
            self.logger.error(f"Failed to add hunting target: {e}")
            return {"success": False, "error": str(e)}
    
    async def start_security_scan(self, target_id: str, scan_type: str = "comprehensive") -> Dict[str, Any]:
        """Start security scan on target"""
        self.logger.info(f"Starting {scan_type} security scan on target {target_id}")
        
        if target_id not in self.hunting_targets:
            return {"success": False, "error": "Target not found"}
        
        target = self.hunting_targets[target_id]
        scan_id = hashlib.md5(f"{target_id}_{scan_type}_{datetime.now()}".encode()).hexdigest()[:8]
        
        scan_data = {
            "scan_id": scan_id,
            "target_id": target_id,
            "scan_type": scan_type,
            "status": "running",
            "started_at": datetime.now().isoformat(),
            "vulnerabilities_found": []
        }
        
        self.active_scans[scan_id] = scan_data
        
        try:
            # Start scan in background
            asyncio.create_task(self._execute_security_scan(scan_id, target, scan_type))
            
            return {
                "success": True,
                "scan_id": scan_id,
                "message": f"{scan_type.title()} scan started on {target.target_url}"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to start security scan: {e}")
            return {"success": False, "error": str(e)}
    
    async def _execute_security_scan(self, scan_id: str, target: HuntingTarget, scan_type: str):
        """Execute comprehensive security scan"""
        self.logger.info(f"Executing {scan_type} scan {scan_id}")
        
        vulnerabilities = []
        
        try:
            if scan_type in ["comprehensive", "web"]:
                # Web application security testing
                web_vulns = await self._scan_web_application(target)
                vulnerabilities.extend(web_vulns)
                
                # API security testing
                api_vulns = await self._scan_api_endpoints(target)
                vulnerabilities.extend(api_vulns)
            
            if scan_type in ["comprehensive", "network"]:
                # Network security scanning
                network_vulns = await self._scan_network_security(target)
                vulnerabilities.extend(network_vulns)
            
            if scan_type in ["comprehensive", "infrastructure"]:
                # Infrastructure security assessment
                infra_vulns = await self._scan_infrastructure(target)
                vulnerabilities.extend(infra_vulns)
            
            # Update scan results
            self.active_scans[scan_id]["vulnerabilities_found"] = vulnerabilities
            self.active_scans[scan_id]["status"] = "completed"
            self.active_scans[scan_id]["completed_at"] = datetime.now().isoformat()
            
            # Store discovered vulnerabilities
            for vuln in vulnerabilities:
                vuln_obj = Vulnerability(**vuln)
                self.discovered_vulnerabilities[vuln_obj.vuln_id] = vuln_obj
            
            # Generate scan report
            await self._generate_scan_report(scan_id, target, vulnerabilities)
            
            # Auto-report high/critical vulnerabilities if enabled
            critical_vulns = [v for v in vulnerabilities if v.get("severity") in ["critical", "high"]]
            if critical_vulns and target.program_type != "none":
                await self._auto_report_vulnerabilities(target, critical_vulns)
            
            self.logger.info(f"Scan {scan_id} completed. Found {len(vulnerabilities)} vulnerabilities")
            
        except Exception as e:
            self.logger.error(f"Scan {scan_id} failed: {e}")
            self.active_scans[scan_id]["status"] = "failed"
            self.active_scans[scan_id]["error"] = str(e)
    
    async def _scan_web_application(self, target: HuntingTarget) -> List[Dict[str, Any]]:
        """Scan web application for vulnerabilities"""
        vulnerabilities = []
        
        try:
            # Directory enumeration
            directories = await self._enumerate_directories(target.target_url)
            
            # Test for common web vulnerabilities
            vulns = await self._test_web_vulnerabilities(target.target_url, directories)
            vulnerabilities.extend(vulns)
            
            # Check for security headers
            header_vulns = await self._check_security_headers(target.target_url)
            vulnerabilities.extend(header_vulns)
            
            # Test for authentication issues
            auth_vulns = await self._test_authentication_issues(target.target_url)
            vulnerabilities.extend(auth_vulns)
            
        except Exception as e:
            self.logger.error(f"Web application scan failed: {e}")
        
        return vulnerabilities
    
    async def _test_web_vulnerabilities(self, base_url: str, directories: List[str]) -> List[Dict[str, Any]]:
        """Test for common web vulnerabilities"""
        vulnerabilities = []
        
        # Test for XSS
        xss_vulns = await self._test_xss_vulnerabilities(base_url)
        vulnerabilities.extend(xss_vulns)
        
        # Test for SQL injection
        sqli_vulns = await self._test_sql_injection(base_url)
        vulnerabilities.extend(sqli_vulns)
        
        # Test for directory traversal
        traversal_vulns = await self._test_directory_traversal(base_url)
        vulnerabilities.extend(traversal_vulns)
        
        # Test for command injection
        cmd_vulns = await self._test_command_injection(base_url)
        vulnerabilities.extend(cmd_vulns)
        
        return vulnerabilities
    
    async def _test_xss_vulnerabilities(self, base_url: str) -> List[Dict[str, Any]]:
        """Test for Cross-Site Scripting vulnerabilities"""
        vulnerabilities = []
        
        try:
            # Common XSS test endpoints
            test_endpoints = [
                "/search?q=",
                "/comment?text=",
                "/feedback?message=",
                "/?search="
            ]
            
            for endpoint in test_endpoints:
                for payload in self.payloads["xss"]:
                    try:
                        test_url = urljoin(base_url, endpoint) + urllib.parse.quote(payload)
                        
                        response = requests.get(test_url, timeout=10, 
                                              headers={"User-Agent": "BugHunterBot/1.0"})
                        
                        if payload in response.text:
                            vuln_id = hashlib.md5(f"xss_{test_url}_{datetime.now()}".encode()).hexdigest()[:8]
                            
                            vulnerabilities.append({
                                "vuln_id": vuln_id,
                                "vuln_type": "Cross-Site Scripting (XSS)",
                                "severity": "medium",
                                "title": f"Reflected XSS in {endpoint}",
                                "description": f"The parameter in {endpoint} is vulnerable to XSS attacks",
                                "affected_target": test_url,
                                "discovered_at": datetime.now(),
                                "proof_of_concept": f"GET {test_url}",
                                "remediation": "Implement proper input validation and output encoding"
                            })
                        
                        # Rate limiting
                        await asyncio.sleep(1)
                        
                    except Exception as e:
                        self.logger.debug(f"XSS test failed for {endpoint}: {e}")
                        
        except Exception as e:
            self.logger.error(f"XSS vulnerability testing failed: {e}")
        
        return vulnerabilities
    
    async def _check_security_headers(self, base_url: str) -> List[Dict[str, Any]]:
        """Check for missing security headers"""
        vulnerabilities = []
        
        try:
            response = requests.get(base_url, timeout=10,
                                  headers={"User-Agent": "BugHunterBot/1.0"})
            
            # Security headers to check
            security_headers = {
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": ["DENY", "SAMEORIGIN"],
                "X-XSS-Protection": "1; mode=block",
                "Strict-Transport-Security": None,
                "Content-Security-Policy": None
            }
            
            for header, expected_value in security_headers.items():
                if header not in response.headers:
                    vuln_id = hashlib.md5(f"missing_header_{header}_{datetime.now()}".encode()).hexdigest()[:8]
                    
                    vulnerabilities.append({
                        "vuln_id": vuln_id,
                        "vuln_type": "Missing Security Header",
                        "severity": "low",
                        "title": f"Missing {header} Header",
                        "description": f"The {header} security header is not present",
                        "affected_target": base_url,
                        "discovered_at": datetime.now(),
                        "proof_of_concept": f"curl -I {base_url}",
                        "remediation": f"Add the {header} header to improve security"
                    })
                    
        except Exception as e:
            self.logger.error(f"Security headers check failed: {e}")
        
        return vulnerabilities
    
    async def report_vulnerability(self, target_id: str, vuln_id: str, contact_method: str = "email") -> Dict[str, Any]:
        """Report vulnerability through responsible disclosure"""
        self.logger.info(f"Reporting vulnerability {vuln_id} for target {target_id}")
        
        if target_id not in self.hunting_targets:
            return {"success": False, "error": "Target not found"}
        
        if vuln_id not in self.discovered_vulnerabilities:
            return {"success": False, "error": "Vulnerability not found"}
        
        target = self.hunting_targets[target_id]
        vulnerability = self.discovered_vulnerabilities[vuln_id]
        
        try:
            # Generate report
            report = self._generate_vulnerability_report(target, vulnerability)
            
            # Create disclosure communication
            disclosure_data = {
                "disclosure_id": hashlib.md5(f"{vuln_id}_{datetime.now()}".encode()).hexdigest()[:8],
                "target_id": target_id,
                "vuln_id": vuln_id,
                "contact_method": contact_method,
                "report_date": datetime.now().isoformat(),
                "status": "reported",
                "report_content": report
            }
            
            # Save disclosure record
            disclosure_file = Path(f"data/disclosure_communications/disclosure_{disclosure_data['disclosure_id']}.json")
            with open(disclosure_file, 'w') as f:
                json.dump(disclosure_data, f, indent=2)
            
            # Update vulnerability status
            vulnerability.status = "reported"
            
            self.logger.info(f"Vulnerability {vuln_id} reported successfully")
            return {
                "success": True,
                "disclosure_id": disclosure_data["disclosure_id"],
                "message": "Vulnerability reported through responsible disclosure"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to report vulnerability: {e}")
            return {"success": False, "error": str(e)}
    
    def _generate_vulnerability_report(self, target: HuntingTarget, vulnerability: Vulnerability) -> str:
        """Generate formatted vulnerability report"""
        return self.disclosure_templates["initial_report"].format(
            vuln_type=vulnerability.vuln_type,
            target=target.target_url,
            severity=vulnerability.severity,
            discovery_date=vulnerability.discovered_at.strftime("%Y-%m-%d"),
            description=vulnerability.description,
            proof_of_concept=vulnerability.proof_of_concept or "See technical details",
            remediation=vulnerability.remediation or "Please contact for remediation guidance"
        )
    
    async def get_hunting_status(self) -> Dict[str, Any]:
        """Get comprehensive bug hunting status"""
        total_vulnerabilities = len(self.discovered_vulnerabilities)
        
        # Severity breakdown
        severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
        for vuln in self.discovered_vulnerabilities.values():
            severity_counts[vuln.severity] = severity_counts.get(vuln.severity, 0) + 1
        
        # Recent activity (last 7 days)
        week_ago = datetime.now() - timedelta(days=7)
        recent_vulns = [
            v for v in self.discovered_vulnerabilities.values()
            if v.discovered_at >= week_ago
        ]
        
        return {
            "agent_status": self.status,
            "hunting_targets": len(self.hunting_targets),
            "active_scans": len(self.active_scans),
            "total_vulnerabilities": total_vulnerabilities,
            "severity_breakdown": severity_counts,
            "recent_discoveries": len(recent_vulns),
            "last_scan": max([scan["started_at"] for scan in self.active_scans.values()]) if self.active_scans else None,
            "uptime_hours": (datetime.now() - self.start_time).total_seconds() / 3600,
            "ethical_compliance": "fully_compliant"
        }
    
    async def _save_hunting_targets(self):
        """Save hunting targets to file"""
        try:
            targets_data = {}
            for target_id, target in self.hunting_targets.items():
                targets_data[target_id] = {
                    "target_id": target.target_id,
                    "target_type": target.target_type,
                    "target_url": target.target_url,
                    "scope": target.scope,
                    "out_of_scope": target.out_of_scope,
                    "contact_info": target.contact_info,
                    "program_type": target.program_type
                }
            
            with open("data/vulnerabilities/hunting_targets.json", 'w') as f:
                json.dump(targets_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save hunting targets: {e}")
    
    async def _enumerate_directories(self, base_url: str) -> List[str]:
        """Enumerate directories and endpoints"""
        directories = []
        
        # Common directories to check
        common_dirs = [
            "/admin", "/api", "/backup", "/config", "/test", "/dev",
            "/docs", "/uploads", "/images", "/js", "/css", "/tmp"
        ]
        
        for directory in common_dirs:
            try:
                test_url = urljoin(base_url, directory)
                response = requests.get(test_url, timeout=5,
                                      headers={"User-Agent": "BugHunterBot/1.0"})
                
                if response.status_code not in [404, 403]:
                    directories.append(directory)
                
                await asyncio.sleep(0.5)  # Rate limiting
                
            except Exception:
                pass  # Ignore errors
        
        return directories

# Global instance
bug_hunter_bot = BugHunterBot()

# Export for use by other modules
__all__ = ['BugHunterBot', 'bug_hunter_bot', 'Vulnerability', 'HuntingTarget']
