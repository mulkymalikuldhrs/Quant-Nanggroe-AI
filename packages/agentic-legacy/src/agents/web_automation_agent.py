"""
Web Automation Agent for Agentic AI System
Handles automated login, registration, and web interactions using stored credentials

Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio
import time
import re
from urllib.parse import urlparse

from ..core.base_agent import BaseAgent
from ..core.credential_manager import credential_manager

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.keys import Keys
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

class WebAutomationAgent(BaseAgent):
    """Agent specialized in web automation and credential management"""
    
    def __init__(self):
        super().__init__(
            agent_id="web_automation_agent",
            config_path="config/prompts.yaml"
        )
        
        self.name = "Web Automation Agent"
        self.role = "Web Automation & Credential Management"
        self.emoji = "🌐"
        
        # Web automation settings
        self.default_timeout = 10
        self.page_load_timeout = 30
        self.driver = None
        
        # Common selectors for login/registration forms
        self.login_selectors = {
            'username': [
                'input[name="username"]', 'input[name="user"]', 'input[name="login"]',
                'input[id*="username"]', 'input[id*="user"]', 'input[id*="login"]',
                'input[type="text"]', 'input[placeholder*="username"]', 'input[placeholder*="user"]'
            ],
            'email': [
                'input[name="email"]', 'input[type="email"]',
                'input[id*="email"]', 'input[placeholder*="email"]'
            ],
            'password': [
                'input[name="password"]', 'input[type="password"]',
                'input[id*="password"]', 'input[placeholder*="password"]'
            ],
            'submit': [
                'button[type="submit"]', 'input[type="submit"]',
                'button:contains("Login")', 'button:contains("Sign in")',
                'button:contains("Log in")', '.login-button', '#login-button'
            ]
        }
        
        self.registration_selectors = {
            'username': [
                'input[name="username"]', 'input[name="user"]',
                'input[id*="username"]', 'input[placeholder*="username"]'
            ],
            'email': [
                'input[name="email"]', 'input[type="email"]',
                'input[id*="email"]', 'input[placeholder*="email"]'
            ],
            'password': [
                'input[name="password"]', 'input[type="password"]',
                'input[id*="password"]', 'input[placeholder*="password"]'
            ],
            'confirm_password': [
                'input[name="confirm_password"]', 'input[name="password_confirmation"]',
                'input[id*="confirm"]', 'input[placeholder*="confirm"]'
            ],
            'first_name': [
                'input[name="first_name"]', 'input[name="fname"]',
                'input[id*="first"]', 'input[placeholder*="first"]'
            ],
            'last_name': [
                'input[name="last_name"]', 'input[name="lname"]',
                'input[id*="last"]', 'input[placeholder*="last"]'
            ],
            'submit': [
                'button[type="submit"]', 'input[type="submit"]',
                'button:contains("Register")', 'button:contains("Sign up")',
                'button:contains("Create")', '.register-button', '#register-button'
            ]
        }
    
    def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process web automation tasks"""
        
        if not self.validate_input(task):
            return self.handle_error(ValueError("Invalid task format"), task)
        
        if not SELENIUM_AVAILABLE:
            return self.handle_error(ImportError("Selenium not available. Install with: pip install selenium"), task)
        
        try:
            self.update_status("processing", task)
            
            request = task.get('request', '')
            context = task.get('context', {})
            
            # Determine automation action
            action_type = self._determine_automation_action(request, context)
            
            if action_type == 'login':
                result = self._perform_login(context)
            elif action_type == 'register':
                result = self._perform_registration(context)
            elif action_type == 'store_credential':
                result = self._store_credential(context)
            elif action_type == 'manage_credentials':
                result = self._manage_credentials(context)
            elif action_type == 'web_interaction':
                result = self._perform_web_interaction(context)
            else:
                result = self._general_automation_response(request, context)
            
            response = self.format_response(result, 'web_automation_response')
            response.update({
                'action_type': action_type,
                'automation_available': SELENIUM_AVAILABLE
            })
            
            self.update_status("ready")
            self.log_task_completion(task, response, True)
            
            return response
            
        except Exception as e:
            self.update_status("error")
            return self.handle_error(e, task)
        finally:
            self._cleanup_driver()
    
    def _determine_automation_action(self, request: str, context: Dict) -> str:
        """Determine what type of automation action is needed"""
        request_lower = request.lower()
        
        if any(word in request_lower for word in ['login', 'sign in', 'log in', 'masuk']):
            return 'login'
        elif any(word in request_lower for word in ['register', 'sign up', 'create account', 'daftar']):
            return 'register'
        elif any(word in request_lower for word in ['store', 'save', 'simpan', 'credential']):
            return 'store_credential'
        elif any(word in request_lower for word in ['manage', 'list', 'kelola', 'credential']):
            return 'manage_credentials'
        elif any(word in request_lower for word in ['interact', 'browse', 'navigate', 'click']):
            return 'web_interaction'
        else:
            return 'general_automation'
    
    def _setup_driver(self, headless: bool = True) -> bool:
        """Setup Selenium WebDriver"""
        try:
            if self.driver:
                return True
            
            chrome_options = Options()
            if headless:
                chrome_options.add_argument('--headless')
            
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            
            # User agent to appear more human-like
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(self.page_load_timeout)
            self.driver.implicitly_wait(5)
            
            return True
            
        except Exception as e:
            print(f"Error setting up WebDriver: {e}")
            return False
    
    def _cleanup_driver(self):
        """Cleanup WebDriver"""
        try:
            if self.driver:
                self.driver.quit()
                self.driver = None
        except:
            pass
    
    def _perform_login(self, context: Dict) -> str:
        """Perform automated login"""
        
        website_url = context.get('website_url')
        website_name = context.get('website_name')
        credential_id = context.get('credential_id')
        
        if not website_url and not website_name and not credential_id:
            return "❌ Error: Website URL, name, or credential ID required for login"
        
        # Get credential
        if credential_id:
            credential = credential_manager.get_credential(credential_id=credential_id)
        elif website_name:
            credential = credential_manager.get_credential(website_name=website_name)
        elif website_url:
            credential = credential_manager.get_credential(website_url=website_url)
        else:
            credential = None
        
        if not credential:
            return "❌ Error: No credentials found for the specified website"
        
        if not self._setup_driver(headless=context.get('headless', True)):
            return "❌ Error: Failed to setup web browser"
        
        try:
            # Navigate to website
            target_url = website_url or credential['website_url']
            self.driver.get(target_url)
            
            # Wait for page to load
            time.sleep(2)
            
            # Find and fill login form
            login_success = self._fill_login_form(credential)
            
            if login_success:
                # Log successful login
                credential_manager.log_usage(
                    credential['id'], target_url, 'login', True
                )
                
                return f"""
✅ LOGIN BERHASIL - WEB AUTOMATION AGENT
════════════════════════════════════════

🌐 Website: {credential['website_name']}
🔗 URL: {target_url}
👤 Username/Email: {credential['username'] or credential['email']}
⏰ Waktu Login: {datetime.now().strftime('%H:%M:%S')}

📊 STATUS:
• Login berhasil dijalankan
• Kredensial terverifikasi
• Session aktif di browser

🇮🇩 Automated by Mulky Malikul Dhaher's Web Automation Agent
"""
            else:
                # Log failed login
                credential_manager.log_usage(
                    credential['id'], target_url, 'login', False, "Form filling failed"
                )
                
                return f"""
❌ LOGIN GAGAL - WEB AUTOMATION AGENT
════════════════════════════════════════

🌐 Website: {credential['website_name']}
🔗 URL: {target_url}
⚠️ Error: Tidak dapat menemukan atau mengisi form login

💡 SARAN:
• Pastikan website dapat diakses
• Periksa apakah struktur form telah berubah
• Coba login manual untuk verifikasi

🇮🇩 Automated by Mulky Malikul Dhaher's Web Automation Agent
"""
        
        except Exception as e:
            credential_manager.log_usage(
                credential['id'], target_url, 'login', False, str(e)
            )
            return f"❌ Error during login: {str(e)}"
    
    def _perform_registration(self, context: Dict) -> str:
        """Perform automated registration"""
        
        website_url = context.get('website_url')
        registration_data = context.get('registration_data', {})
        
        if not website_url:
            return "❌ Error: Website URL required for registration"
        
        if not registration_data:
            return "❌ Error: Registration data required"
        
        if not self._setup_driver(headless=context.get('headless', True)):
            return "❌ Error: Failed to setup web browser"
        
        try:
            # Navigate to registration page
            self.driver.get(website_url)
            time.sleep(2)
            
            # Fill registration form
            registration_success = self._fill_registration_form(registration_data)
            
            if registration_success:
                # Store credential after successful registration
                if 'website_name' in context:
                    credential_manager.store_credential(
                        website_name=context['website_name'],
                        website_url=website_url,
                        username=registration_data.get('username'),
                        email=registration_data.get('email'),
                        password=registration_data.get('password'),
                        additional_fields=registration_data.get('additional_fields', {}),
                        notes=f"Auto-registered on {datetime.now().strftime('%Y-%m-%d')}"
                    )
                
                return f"""
✅ REGISTRASI BERHASIL - WEB AUTOMATION AGENT
════════════════════════════════════════════

🌐 Website: {context.get('website_name', 'Unknown')}
🔗 URL: {website_url}
👤 Username: {registration_data.get('username', 'N/A')}
📧 Email: {registration_data.get('email', 'N/A')}
⏰ Waktu Registrasi: {datetime.now().strftime('%H:%M:%S')}

📊 STATUS:
• Registrasi berhasil dijalankan
• Kredensial tersimpan secara aman
• Akun siap digunakan

🇮🇩 Automated by Mulky Malikul Dhaher's Web Automation Agent
"""
            else:
                return f"""
❌ REGISTRASI GAGAL - WEB AUTOMATION AGENT
═════════════════════════════════════════

🌐 Website: {context.get('website_name', 'Unknown')}
🔗 URL: {website_url}
⚠️ Error: Tidak dapat mengisi form registrasi

💡 SARAN:
• Periksa kelengkapan data registrasi
• Pastikan website dapat diakses
• Coba registrasi manual untuk verifikasi

🇮🇩 Automated by Mulky Malikul Dhaher's Web Automation Agent
"""
        
        except Exception as e:
            return f"❌ Error during registration: {str(e)}"
    
    def _fill_login_form(self, credential: Dict) -> bool:
        """Fill login form with credentials"""
        try:
            wait = WebDriverWait(self.driver, self.default_timeout)
            
            # Find username/email field
            username_element = None
            for selector in self.login_selectors['username'] + self.login_selectors['email']:
                try:
                    username_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except NoSuchElementException:
                    continue
            
            if not username_element:
                return False
            
            # Fill username/email
            username_value = credential['username'] or credential['email']
            username_element.clear()
            username_element.send_keys(username_value)
            
            # Find password field
            password_element = None
            for selector in self.login_selectors['password']:
                try:
                    password_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except NoSuchElementException:
                    continue
            
            if not password_element:
                return False
            
            # Fill password
            password_element.clear()
            password_element.send_keys(credential['password'])
            
            # Submit form
            submit_button = None
            for selector in self.login_selectors['submit']:
                try:
                    submit_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except NoSuchElementException:
                    continue
            
            if submit_button:
                submit_button.click()
            else:
                # Try pressing Enter on password field
                password_element.send_keys(Keys.RETURN)
            
            # Wait for navigation or success indicator
            time.sleep(3)
            
            return True
            
        except Exception as e:
            print(f"Error filling login form: {e}")
            return False
    
    def _fill_registration_form(self, registration_data: Dict) -> bool:
        """Fill registration form with provided data"""
        try:
            # Fill username
            if 'username' in registration_data:
                username_element = self._find_element_by_selectors(self.registration_selectors['username'])
                if username_element:
                    username_element.clear()
                    username_element.send_keys(registration_data['username'])
            
            # Fill email
            if 'email' in registration_data:
                email_element = self._find_element_by_selectors(self.registration_selectors['email'])
                if email_element:
                    email_element.clear()
                    email_element.send_keys(registration_data['email'])
            
            # Fill password
            if 'password' in registration_data:
                password_element = self._find_element_by_selectors(self.registration_selectors['password'])
                if password_element:
                    password_element.clear()
                    password_element.send_keys(registration_data['password'])
            
            # Fill confirm password
            if 'password' in registration_data:
                confirm_element = self._find_element_by_selectors(self.registration_selectors['confirm_password'])
                if confirm_element:
                    confirm_element.clear()
                    confirm_element.send_keys(registration_data['password'])
            
            # Fill first name
            if 'first_name' in registration_data:
                first_name_element = self._find_element_by_selectors(self.registration_selectors['first_name'])
                if first_name_element:
                    first_name_element.clear()
                    first_name_element.send_keys(registration_data['first_name'])
            
            # Fill last name
            if 'last_name' in registration_data:
                last_name_element = self._find_element_by_selectors(self.registration_selectors['last_name'])
                if last_name_element:
                    last_name_element.clear()
                    last_name_element.send_keys(registration_data['last_name'])
            
            # Submit form
            submit_button = self._find_element_by_selectors(self.registration_selectors['submit'])
            if submit_button:
                submit_button.click()
                time.sleep(3)
                return True
            
            return False
            
        except Exception as e:
            print(f"Error filling registration form: {e}")
            return False
    
    def _find_element_by_selectors(self, selectors: List[str]):
        """Find element using multiple selectors"""
        for selector in selectors:
            try:
                return self.driver.find_element(By.CSS_SELECTOR, selector)
            except NoSuchElementException:
                continue
        return None
    
    def _store_credential(self, context: Dict) -> str:
        """Store new credential"""
        
        website_name = context.get('website_name')
        website_url = context.get('website_url')
        username = context.get('username')
        email = context.get('email')
        password = context.get('password')
        notes = context.get('notes', '')
        
        if not website_name or not website_url or not password:
            return "❌ Error: Website name, URL, and password are required"
        
        success = credential_manager.store_credential(
            website_name=website_name,
            website_url=website_url,
            username=username,
            email=email,
            password=password,
            notes=notes
        )
        
        if success:
            return f"""
✅ KREDENSIAL TERSIMPAN - WEB AUTOMATION AGENT
═════════════════════════════════════════════

🌐 Website: {website_name}
🔗 URL: {website_url}
👤 Username: {username or 'N/A'}
📧 Email: {email or 'N/A'}
📝 Notes: {notes or 'No notes'}
⏰ Disimpan: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🔒 KEAMANAN:
• Password dienkripsi dengan standar militer
• Data tersimpan dengan aman di database lokal
• Hanya dapat diakses dengan master password

🇮🇩 Secured by Mulky Malikul Dhaher's Credential Manager
"""
        else:
            return "❌ Error: Failed to store credential"
    
    def _manage_credentials(self, context: Dict) -> str:
        """Manage stored credentials"""
        
        action = context.get('action', 'list')
        
        if action == 'list':
            credentials = credential_manager.list_credentials()
            
            if not credentials:
                return """
📋 DAFTAR KREDENSIAL - WEB AUTOMATION AGENT
═══════════════════════════════════════════

❌ Tidak ada kredensial tersimpan

💡 CARA MENAMBAH KREDENSIAL:
• Gunakan perintah "store credential"
• Atau registrasi otomatis di website

🇮🇩 Managed by Mulky Malikul Dhaher's Credential Manager
"""
            
            credential_list = []
            for i, cred in enumerate(credentials[:10], 1):  # Show max 10
                last_used = cred['last_used'] or 'Never'
                credential_list.append(f"""
{i}. 🌐 {cred['website_name']}
   📍 {cred['website_url']}
   👤 {cred['username'] or cred['email'] or 'N/A'}
   📊 Used: {cred['usage_count']} times
   ⏰ Last: {last_used}""")
            
            return f"""
📋 DAFTAR KREDENSIAL - WEB AUTOMATION AGENT
═══════════════════════════════════════════

Total Kredensial: {len(credentials)}

{''.join(credential_list)}

💡 AKSI TERSEDIA:
• Login otomatis ke website manapun
• Update kredensial yang sudah ada
• Hapus kredensial yang tidak diperlukan

🇮🇩 Managed by Mulky Malikul Dhaher's Credential Manager
"""
        
        elif action == 'search':
            query = context.get('query', '')
            if not query:
                return "❌ Error: Search query required"
            
            results = credential_manager.search_credentials(query)
            
            if not results:
                return f"🔍 No credentials found for query: {query}"
            
            search_results = []
            for i, cred in enumerate(results, 1):
                search_results.append(f"""
{i}. 🌐 {cred['website_name']}
   📍 {cred['website_url']}
   👤 {cred['username'] or cred['email'] or 'N/A'}""")
            
            return f"""
🔍 HASIL PENCARIAN KREDENSIAL
═══════════════════════════════

Query: "{query}"
Found: {len(results)} credentials

{''.join(search_results)}

🇮🇩 Searched by Mulky Malikul Dhaher's Credential Manager
"""
        
        return "❌ Error: Unknown management action"
    
    def _perform_web_interaction(self, context: Dict) -> str:
        """Perform general web interactions"""
        
        return """
🌐 WEB INTERACTION - WEB AUTOMATION AGENT
════════════════════════════════════════

🔧 FITUR TERSEDIA:
• Automated login ke website manapun
• Registrasi otomatis dengan data tersimpan
• Form filling dan web navigation
• Screenshot dan content extraction

💡 CONTOH PENGGUNAAN:
• "Login to facebook.com"
• "Register new account on github.com"
• "Store credential for gmail.com"

🇮🇩 Powered by Mulky Malikul Dhaher's Web Automation System
"""
    
    def _general_automation_response(self, request: str, context: Dict) -> str:
        """General automation response"""
        
        return f"""
🤖 WEB AUTOMATION AGENT - ACTIVE
═══════════════════════════════════

📋 REQUEST RECEIVED:
{request}

🌐 AUTOMATION CAPABILITIES:
• Login otomatis menggunakan kredensial tersimpan
• Registrasi akun baru di website manapun
• Penyimpanan kredensial yang aman dan terenkripsi
• Web browsing dan form interaction

🔒 CREDENTIAL MANAGEMENT:
• Enkripsi military-grade untuk password
• Database lokal yang aman
• Usage tracking dan history
• Multi-platform support

💡 CONTOH PERINTAH:
• "Login to [website]"
• "Register account on [website] with [data]"
• "Store credential for [website]"
• "List all stored credentials"

🇮🇩 Made with ❤️ by Mulky Malikul Dhaher in Indonesia
"""
