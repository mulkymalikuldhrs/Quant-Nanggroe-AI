#!/usr/bin/env python3
"""
Comprehensive Browser Test Suite for AI-MultiColony-Ecosystem
Uses Playwright to test the Flask web interface end-to-end.
"""

import json
import os
import subprocess
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

# Configuration
PROJECT_DIR = Path(__file__).parent.resolve()
WEB_DIR = PROJECT_DIR / "web_interface"
PYTHON_BIN = os.getenv("PYTHON_BIN", sys.executable)
BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:5000")
SCREENSHOTS_DIR = PROJECT_DIR / "screenshots"
SCREENSHOTS_DIR.mkdir(exist_ok=True)
APP_STARTUP_TIMEOUT = int(os.getenv("APP_STARTUP_TIMEOUT", "20"))
PAGE_LOAD_TIMEOUT = int(os.getenv("PAGE_LOAD_TIMEOUT", "30000"))

PAGE_ROUTES = [
    ("/", "Home Dashboard"),
    ("/dashboard", "System Dashboard"),
    ("/agents", "Agents Management"),
    ("/workflows", "Workflows Management"),
    ("/monitoring", "System Monitoring"),
    ("/platform_integrations", "Platform Integrations"),
    ("/credentials", "Credential Management"),
]

API_ENDPOINTS = [
    ("GET", "/api/system/status", None),
    ("GET", "/api/agents/list", None),
    ("GET", "/api/memory/stats", None),
    ("GET", "/api/llm/providers", None),
    ("POST", "/api/prompt/process", {"prompt": "Hello test", "input_type": "text"}),
    ("POST", "/api/task/submit", {"agent_id": "nonexistent", "task": {}}),
]

results = {
    "test_run_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
    "started_at": datetime.now().isoformat(),
    "pages": [],
    "apis": [],
    "console_errors": [],
    "broken_links": [],
    "missing_resources": [],
    "summary": {},
}


class FlaskAppManager:
    def __init__(self):
        self.process = None
        self.ready = False
        self.port = 5000

    def start(self):
        print(f"\n🚀 Starting Flask app from {WEB_DIR}")
        app_script = WEB_DIR / "app.py"
        if not app_script.exists():
            print(f"   ❌ App script not found: {app_script}")
            return False

        env = os.environ.copy()
        env["FLASK_ENV"] = "testing"
        env["WEB_INTERFACE_PORT"] = str(self.port)
        env["WEB_INTERFACE_HOST"] = "0.0.0.0"

        self.process = subprocess.Popen(
            [PYTHON_BIN, str(app_script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=str(PROJECT_DIR),
            env=env,
        )

        import urllib.request
        import urllib.error

        base = f"http://localhost:{self.port}"
        start = time.time()
        while time.time() - start < APP_STARTUP_TIMEOUT:
            try:
                resp = urllib.request.urlopen(f"{base}/", timeout=2)
                if resp.status == 200:
                    self.ready = True
                    print(f"   ✅ Flask app ready at {base} (PID {self.process.pid})")
                    return True
            except (urllib.error.URLError, ConnectionRefusedError, OSError):
                pass
            self.process.poll()
            if self.process.returncode is not None:
                output = self.process.stdout.read().decode("utf-8", errors="replace")
                print(f"   ❌ Flask app exited with code {self.process.returncode}")
                print(f"   Output: {output[:2000]}")
                return False
            time.sleep(1)

        print(f"   ❌ Flask app did not become ready within {APP_STARTUP_TIMEOUT}s")
        return False

    def stop(self):
        if self.process and self.process.poll() is None:
            print("\n🛑 Stopping Flask app...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=3)
            print("   ✅ Flask app stopped")


class BrowserTestRunner:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.console_errors = []
        self.failed_resources = []

    def setup(self):
        from playwright.sync_api import sync_playwright
        self.pw = sync_playwright().start()
        self.browser = self.pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage",
                  "--disable-gpu", "--single-process"],
        )
        self.context = self.browser.new_context(
            viewport={"width": 1440, "height": 900},
            ignore_https_errors=True,
        )
        self.context.on("pageerror", self._on_page_error)
        self.page = self.context.new_page()
        self.page.on("console", self._on_console)
        self.page.on("requestfailed", self._on_request_failed)
        print("   ✅ Playwright browser initialized (Chromium headless)")

    def _on_console(self, msg):
        if msg.type == "error":
            entry = {"url": self.page.url, "message": msg.text, "timestamp": datetime.now().isoformat()}
            self.console_errors.append(entry)
            results["console_errors"].append(entry)

    def _on_page_error(self, error):
        entry = {"url": self.page.url, "error": str(error), "timestamp": datetime.now().isoformat()}
        self.console_errors.append(entry)
        results["console_errors"].append(entry)

    def _on_request_failed(self, request):
        entry = {"url": request.url, "failure": request.failure, "timestamp": datetime.now().isoformat()}
        self.failed_resources.append(entry)
        results["missing_resources"].append(entry)

    def test_page(self, path, name):
        url = f"{BASE_URL}{path}"
        page_result = {"path": path, "name": name, "url": url, "status": "pending",
                       "http_status": None, "title": None, "load_time_ms": None,
                       "errors": [], "interactive_elements": 0, "links": [], "screenshot": None}
        print(f"\n📄 Testing page: {name} ({path})")
        try:
            page_errors_before = len(self.console_errors)
            start_time = time.time()
            response = self.page.goto(url, wait_until="networkidle", timeout=PAGE_LOAD_TIMEOUT)
            load_time = (time.time() - start_time) * 1000
            page_result["load_time_ms"] = round(load_time, 1)
            page_result["http_status"] = response.status if response else None
            self.page.wait_for_timeout(2000)
            page_result["title"] = self.page.title()

            screenshot_name = f"page_{path.strip('/').replace('/', '_') or 'index'}.png"
            screenshot_path = str(SCREENSHOTS_DIR / screenshot_name)
            self.page.screenshot(path=screenshot_path, full_page=True)
            page_result["screenshot"] = screenshot_path
            print(f"   📸 Screenshot saved: {screenshot_name}")

            buttons = self.page.query_selector_all("button, [role='button'], .btn")
            links = self.page.query_selector_all("a[href]")
            inputs = self.page.query_selector_all("input, textarea, select")
            page_result["interactive_elements"] = len(buttons) + len(inputs)
            page_result["button_count"] = len(buttons)
            page_result["link_count"] = len(links)
            page_result["input_count"] = len(inputs)

            page_links = []
            for link in links:
                href = link.get_attribute("href")
                text = link.inner_text().strip()[:50] if link.inner_text() else ""
                if href:
                    page_links.append({"href": href, "text": text})
            page_result["links"] = page_links

            page_errors = self.console_errors[page_errors_before:]
            if page_errors:
                page_result["errors"] = [{"message": e.get("message", str(e))} for e in page_errors]
                print(f"   ⚠️  {len(page_errors)} console error(s) found")
            else:
                print(f"   ✅ No console errors")

            print(f"   🔗 {len(links)} links, {len(buttons)} buttons, {len(inputs)} inputs")
            print(f"   ⏱️  Load: {page_result['load_time_ms']}ms | HTTP {page_result['http_status']}")
            page_result["status"] = "passed"
        except Exception as e:
            page_result["status"] = "failed"
            page_result["errors"].append({"message": str(e)})
            print(f"   ❌ Error: {e}")
            try:
                screenshot_name = f"page_{path.strip('/').replace('/', '_') or 'index'}_error.png"
                screenshot_path = str(SCREENSHOTS_DIR / screenshot_name)
                self.page.screenshot(path=screenshot_path, full_page=True)
                page_result["screenshot"] = screenshot_path
            except Exception:
                pass

        results["pages"].append(page_result)
        return page_result

    def test_interactive_elements(self):
        print("\n🖱️  Testing interactive elements on home page...")
        interactive_result = {"name": "Interactive Elements Test", "status": "pending", "actions_tested": []}
        try:
            self.page.goto(f"{BASE_URL}/", wait_until="networkidle", timeout=PAGE_LOAD_TIMEOUT)
            self.page.wait_for_timeout(2000)

            nav_links = self.page.query_selector_all(".sidebar .nav-link[href], nav .nav-link[href]")
            for i, link in enumerate(nav_links[:5]):
                href = link.get_attribute("href")
                if href and href.startswith("/"):
                    try:
                        link.click()
                        self.page.wait_for_timeout(1500)
                        current_url = self.page.url
                        interactive_result["actions_tested"].append(
                            {"action": f"click_nav_link_{i}", "href": href, "status": "success", "navigated_to": current_url})
                        print(f"   ✅ Nav link click: {href}")
                        self.page.go_back(wait_until="networkidle", timeout=PAGE_LOAD_TIMEOUT)
                        self.page.wait_for_timeout(1000)
                    except Exception as e:
                        interactive_result["actions_tested"].append(
                            {"action": f"click_nav_link_{i}", "href": href, "status": "failed", "error": str(e)})
                        print(f"   ⚠️  Nav link click failed: {href}")

            self.page.goto(f"{BASE_URL}/", wait_until="networkidle", timeout=PAGE_LOAD_TIMEOUT)
            self.page.wait_for_timeout(2000)
            quick_actions = self.page.query_selector_all(".quick-action-card")
            if quick_actions:
                for i, action in enumerate(quick_actions[:3]):
                    try:
                        self.page.once("dialog", lambda dialog: dialog.accept())
                        action.click()
                        self.page.wait_for_timeout(500)
                        interactive_result["actions_tested"].append(
                            {"action": f"click_quick_action_{i}", "status": "success"})
                        print(f"   ✅ Quick action card {i} click")
                    except Exception as e:
                        interactive_result["actions_tested"].append(
                            {"action": f"click_quick_action_{i}", "status": "failed", "error": str(e)})
            interactive_result["status"] = "passed"
        except Exception as e:
            interactive_result["status"] = "failed"
            interactive_result["error"] = str(e)
            print(f"   ❌ Interactive test error: {e}")
        results["pages"].append(interactive_result)
        return interactive_result

    def test_api_endpoints(self):
        print("\n🔌 Testing API endpoints...")
        for method, path, body in API_ENDPOINTS:
            url = f"{BASE_URL}{path}"
            api_result = {"method": method, "path": path, "url": url, "status": "pending",
                          "http_status": None, "response_time_ms": None, "response_valid": False}
            print(f"   Testing: {method} {path}")
            try:
                start_time = time.time()
                if method == "GET":
                    response = self.page.request.get(url, timeout=10000)
                elif method == "POST":
                    response = self.page.request.post(
                        url, data=json.dumps(body) if body else None,
                        headers={"Content-Type": "application/json"}, timeout=10000)
                else:
                    continue
                elapsed = (time.time() - start_time) * 1000
                api_result["response_time_ms"] = round(elapsed, 1)
                api_result["http_status"] = response.status
                try:
                    data = response.json()
                    api_result["response_valid"] = True
                    api_result["response_success"] = data.get("success", None)
                    if response.status >= 400:
                        api_result["has_error_field"] = "error" in data
                        print(f"      {response.status} - Error: {data.get('error', 'unknown')}")
                    else:
                        print(f"      ✅ {response.status} - success={data.get('success')}")
                except Exception as e:
                    api_result["response_valid"] = False
                    api_result["parse_error"] = str(e)
                    print(f"      ⚠️  JSON parse error: {e}")
                api_result["status"] = "passed"
            except Exception as e:
                api_result["status"] = "failed"
                api_result["error"] = str(e)
                print(f"      ❌ Request failed: {e}")
            results["apis"].append(api_result)

    def test_broken_links(self):
        print("\n🔗 Checking for broken internal links...")
        all_links = set()
        for page_result in results["pages"]:
            if "links" in page_result:
                for link in page_result.get("links", []):
                    href = link.get("href", "")
                    if href.startswith("/"):
                        all_links.add(href)
        for path, _ in PAGE_ROUTES:
            all_links.add(path)
        broken = []
        for href in sorted(all_links):
            url = f"{BASE_URL}{href}"
            try:
                response = self.page.request.get(url, timeout=10000)
                if response.status >= 400:
                    broken.append({"href": href, "url": url, "http_status": response.status})
                    print(f"   ❌ Broken link: {href} -> {response.status}")
                else:
                    print(f"   ✅ OK: {href} -> {response.status}")
            except Exception as e:
                broken.append({"href": href, "url": url, "error": str(e)})
                print(f"   ❌ Failed: {href} -> {e}")
        results["broken_links"] = broken

    def test_responsive_design(self):
        print("\n📱 Testing responsive design...")
        viewports = [
            {"name": "desktop", "width": 1440, "height": 900},
            {"name": "tablet", "width": 768, "height": 1024},
            {"name": "mobile", "width": 375, "height": 667},
        ]
        responsive_results = []
        for vp in viewports:
            print(f"   Testing viewport: {vp['name']} ({vp['width']}x{vp['height']})")
            try:
                ctx = self.browser.new_context(viewport={"width": vp["width"], "height": vp["height"]})
                new_page = ctx.new_page()
                new_page.goto(f"{BASE_URL}/", wait_until="networkidle", timeout=PAGE_LOAD_TIMEOUT)
                new_page.wait_for_timeout(1500)
                screenshot_name = f"responsive_{vp['name']}.png"
                screenshot_path = str(SCREENSHOTS_DIR / screenshot_name)
                new_page.screenshot(path=screenshot_path, full_page=True)
                has_overflow = new_page.evaluate(
                    "() => document.documentElement.scrollWidth > document.documentElement.clientWidth")
                responsive_results.append({"viewport": vp["name"], "width": vp["width"], "height": vp["height"],
                                           "screenshot": screenshot_path, "has_horizontal_overflow": has_overflow,
                                           "status": "passed"})
                status = "⚠️  has overflow" if has_overflow else "✅ OK"
                print(f"      {status}")
                new_page.close()
                ctx.close()
            except Exception as e:
                responsive_results.append({"viewport": vp["name"], "width": vp["width"], "height": vp["height"],
                                           "status": "failed", "error": str(e)})
                print(f"      ❌ Error: {e}")
        results["responsive"] = responsive_results

    def cleanup(self):
        if self.page: self.page.close()
        if self.context: self.context.close()
        if self.browser: self.browser.close()
        if hasattr(self, "pw"): self.pw.stop()
        print("   ✅ Browser closed")


def generate_report():
    print("\n" + "=" * 70)
    print("📊 TEST REPORT")
    print("=" * 70)
    pages_passed = sum(1 for p in results["pages"] if p.get("status") == "passed")
    pages_failed = sum(1 for p in results["pages"] if p.get("status") == "failed")
    pages_total = len(results["pages"])
    print(f"\n📄 Pages: {pages_passed}/{pages_total} passed")
    for p in results["pages"]:
        icon = "✅" if p.get("status") == "passed" else "❌"
        name = p.get("name", p.get("path", "unknown"))
        load = f" ({p.get('load_time_ms', '?')}ms)" if p.get("load_time_ms") else ""
        http = f" [HTTP {p.get('http_status')}]" if p.get("http_status") else ""
        print(f"   {icon} {name}{load}{http}")

    apis_passed = sum(1 for a in results["apis"] if a.get("status") == "passed")
    apis_total = len(results["apis"])
    print(f"\n🔌 API Endpoints: {apis_passed}/{apis_total} passed")
    for a in results["apis"]:
        icon = "✅" if a.get("status") == "passed" else "❌"
        http = f" [{a.get('http_status')}]" if a.get("http_status") else ""
        rt = f" ({a.get('response_time_ms', '?')}ms)" if a.get("response_time_ms") else ""
        print(f"   {icon} {a['method']} {a['path']}{http}{rt}")

    print(f"\n⚠️  Console Errors: {len(results['console_errors'])}")
    for err in results["console_errors"][:10]:
        msg = err.get("message", str(err))[:100]
        print(f"   • {msg}")
    print(f"\n🔗 Broken Links: {len(results['broken_links'])}")
    for link in results["broken_links"]:
        print(f"   ❌ {link.get('href')} -> {link.get('http_status', link.get('error'))}")
    print(f"\n📦 Missing Resources: {len(results['missing_resources'])}")

    if "responsive" in results:
        print(f"\n📱 Responsive Design:")
        for r in results["responsive"]:
            icon = "✅" if r.get("status") == "passed" else "❌"
            overflow = " (overflow!)" if r.get("has_horizontal_overflow") else ""
            print(f"   {icon} {r['viewport']} ({r['width']}x{r['height']}){overflow}")

    screenshots = [p.get("screenshot") for p in results["pages"] if p.get("screenshot")]
    if "responsive" in results:
        screenshots.extend(r.get("screenshot") for r in results["responsive"] if r.get("screenshot"))
    print(f"\n📸 Screenshots: {len(screenshots)} captured in {SCREENSHOTS_DIR}/")

    total_passed = pages_passed + apis_passed
    total_tests = pages_total + apis_total
    if pages_failed == 0 and apis_passed > 0:
        overall = "PASSED"
    elif total_passed > 0:
        overall = "PARTIAL"
    else:
        overall = "FAILED"

    results["summary"] = {
        "pages_passed": pages_passed, "pages_failed": pages_failed, "pages_total": pages_total,
        "apis_passed": apis_passed, "apis_total": apis_total,
        "console_errors": len(results["console_errors"]),
        "broken_links": len(results["broken_links"]),
        "missing_resources": len(results["missing_resources"]),
        "screenshots_captured": len(screenshots),
        "overall_status": overall,
    }
    print(f"\n{'=' * 70}")
    print(f"🏁 Overall: {overall} ({total_passed}/{total_tests} tests passed)")
    print(f"{'=' * 70}")

    report_path = PROJECT_DIR / "browser_test_report.json"
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n💾 Full report saved to: {report_path}")
    return results


def main():
    print("=" * 70)
    print("🧪 AI-MultiColony-Ecosystem Browser Test Suite")
    print(f"   Project: {PROJECT_DIR}")
    print(f"   Base URL: {BASE_URL}")
    print(f"   Python: {PYTHON_BIN}")
    print(f"   Web Dir: {WEB_DIR}")
    print(f"   Timestamp: {datetime.now().isoformat()}")
    print("=" * 70)

    app_manager = FlaskAppManager()
    test_runner = BrowserTestRunner()
    app_started = False

    try:
        app_started = app_manager.start()
        if not app_started:
            print("\n❌ Cannot start Flask app. Aborting tests.")
            return 1
        test_runner.setup()

        print("\n" + "-" * 50)
        print("📄 PHASE 1: Page Rendering Tests")
        print("-" * 50)
        for path, name in PAGE_ROUTES:
            test_runner.test_page(path, name)

        print("\n" + "-" * 50)
        print("🖱️  PHASE 2: Interactive Elements Tests")
        print("-" * 50)
        test_runner.test_interactive_elements()

        print("\n" + "-" * 50)
        print("🔌 PHASE 3: API Endpoint Tests")
        print("-" * 50)
        test_runner.test_api_endpoints()

        print("\n" + "-" * 50)
        print("🔗 PHASE 4: Broken Link Detection")
        print("-" * 50)
        test_runner.test_broken_links()

        print("\n" + "-" * 50)
        print("📱 PHASE 5: Responsive Design Tests")
        print("-" * 50)
        test_runner.test_responsive_design()

    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test suite error: {e}")
        traceback.print_exc()
    finally:
        test_runner.cleanup()
        app_manager.stop()
        try:
            subprocess.run(["fuser", "-k", "5000/tcp"], capture_output=True, timeout=5)
        except Exception:
            pass

    report = generate_report()
    return 0 if report["summary"].get("overall_status") != "FAILED" else 1


if __name__ == "__main__":
    sys.exit(main())
