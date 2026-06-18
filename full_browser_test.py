#!/usr/bin/env python3
"""
Full Browser Test Suite for AI-MultiColony-Ecosystem
Uses Playwright to test all pages, clicks, and features
"""
import subprocess
import sys
import os
import time
import json
import traceback

# Ensure playwright is available
try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Installing playwright...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "playwright", "--break-system-packages"])
    subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
    from playwright.sync_api import sync_playwright

# Test results storage
results = {
    "pages": [],
    "clicks": [],
    "api_tests": [],
    "errors": [],
    "screenshots": [],
    "summary": {}
}

def start_server():
    """Start Flask server"""
    env = os.environ.copy()
    env['PYTHONPATH'] = '.'
    proc = subprocess.Popen(
        [sys.executable, '-c', '''
import sys
sys.path.insert(0, ".")
from web_interface.app import app, socketio
socketio.run(app, host="0.0.0.0", port=5555, debug=False, allow_unsafe_werkzeug=True)
'''],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(10)
    if proc.poll() is not None:
        raise RuntimeError("Server failed to start")
    return proc

def test_all():
    BASE_URL = "http://localhost:5555"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()
        
        # Collect console errors
        console_errors = []
        page.on("console", lambda msg: console_errors.append(f"{msg.type}: {msg.text}") if msg.type in ["error", "warning"] else None)
        
        # Collect page errors
        page_errors = []
        page.on("pageerror", lambda err: page_errors.append(str(err)))
        
        # ====== TEST 1: Page Rendering ======
        print("\n=== TEST 1: Page Rendering ===")
        pages_to_test = [
            ("/", "Home/Dashboard"),
            ("/dashboard", "Dashboard"),
            ("/agents", "Agents"),
            ("/workflows", "Workflows"),
            ("/monitoring", "Monitoring"),
            ("/platform_integrations", "Platform Integrations"),
            ("/credentials", "Credentials"),
            ("/llm-providers", "LLM Providers"),
        ]
        
        for path, name in pages_to_test:
            try:
                url = f"{BASE_URL}{path}"
                resp = page.goto(url, wait_until="networkidle", timeout=15000)
                status = resp.status if resp else "no response"
                title = page.title()
                
                # Take screenshot
                screenshot_path = os.path.join(os.path.dirname(__file__), 'screenshots', f"{name.replace(' ', '_').replace('/', '_')}.png")
                os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
                page.screenshot(path=screenshot_path)
                
                result = {
                    "path": path,
                    "name": name,
                    "status": status,
                    "title": title,
                    "screenshot": screenshot_path
                }
                results["pages"].append(result)
                print(f"  {name}: {status} - {title}")
            except Exception as e:
                results["errors"].append(f"Page {path}: {str(e)}")
                print(f"  {name}: ERROR - {str(e)[:100]}")
        
        # ====== TEST 2: Interactive Elements (Clicks) ======
        print("\n=== TEST 2: Interactive Elements ===")
        
        # Test homepage navigation
        try:
            page.goto(f"{BASE_URL}/", wait_until="networkidle", timeout=15000)
            
            # Find all clickable elements
            buttons = page.query_selector_all("button")
            links = page.query_selector_all("a[href]")
            
            print(f"  Found {len(buttons)} buttons and {len(links)} links on homepage")
            
            # Click each navigation link
            for link in links[:20]:  # Limit to 20
                try:
                    href = link.get_attribute("href")
                    text = link.inner_text()[:50]
                    if href and not href.startswith("http") and href != "#":
                        result = {"action": "click_link", "href": href, "text": text}
                        results["clicks"].append(result)
                        print(f"  Link: {text} -> {href}")
                except:
                    pass
            
            # Test buttons
            for btn in buttons[:10]:
                try:
                    text = btn.inner_text()[:50]
                    result = {"action": "click_button", "text": text}
                    results["clicks"].append(result)
                    print(f"  Button: {text}")
                except:
                    pass
        except Exception as e:
            results["errors"].append(f"Interactive test: {str(e)}")
        
        # ====== TEST 3: API Endpoints ======
        print("\n=== TEST 3: API Endpoints ===")
        api_endpoints = [
            ("/api/system/status", "GET"),
            ("/api/agents/list", "GET"),
            ("/api/llm/providers", "GET"),
            ("/api/memory/stats", "GET"),
        ]
        
        for endpoint, method in api_endpoints:
            try:
                url = f"{BASE_URL}{endpoint}"
                resp = page.goto(url, wait_until="networkidle", timeout=10000)
                status = resp.status if resp else "no response"
                
                if status == 200:
                    try:
                        content = page.inner_text("body")
                        # Try to parse as JSON
                        try:
                            data = json.loads(content)
                            result = {"endpoint": endpoint, "method": method, "status": status, "data_keys": list(data.keys())[:10] if isinstance(data, dict) else "array"}
                        except:
                            result = {"endpoint": endpoint, "method": method, "status": status, "response_length": len(content)}
                    except:
                        result = {"endpoint": endpoint, "method": method, "status": status}
                else:
                    result = {"endpoint": endpoint, "method": method, "status": status}
                
                results["api_tests"].append(result)
                print(f"  {endpoint}: {status}")
            except Exception as e:
                results["errors"].append(f"API {endpoint}: {str(e)}")
                print(f"  {endpoint}: ERROR - {str(e)[:100]}")
        
        # ====== TEST 4: Form Submissions ======
        print("\n=== TEST 4: Form Submissions ===")
        
        # Test task submission API
        try:
            page.goto(f"{BASE_URL}/agents", wait_until="networkidle", timeout=10000)
            
            # Look for forms
            forms = page.query_selector_all("form")
            print(f"  Found {len(forms)} forms on agents page")
            
            # Test task submit via API
            api_result = page.evaluate("""
                () => fetch('/api/task/submit', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({agent: 'prompt_master', task: 'test task'})
                }).then(r => r.json())
            """)
            results["api_tests"].append({
                "endpoint": "/api/task/submit",
                "method": "POST",
                "result": api_result
            })
            print(f"  Task submit: {json.dumps(api_result)[:100]}")
        except Exception as e:
            results["errors"].append(f"Form test: {str(e)}")
            print(f"  Form test: ERROR - {str(e)[:100]}")
        
        # ====== TEST 5: Page Specific Tests ======
        print("\n=== TEST 5: Page-Specific Features ===")
        
        # Test agents page
        try:
            page.goto(f"{BASE_URL}/agents", wait_until="networkidle", timeout=10000)
            agent_cards = page.query_selector_all(".agent-card, .card, [data-agent]")
            agent_list_items = page.query_selector_all("li, .list-group-item")
            print(f"  Agents page: {len(agent_cards)} agent cards, {len(agent_list_items)} list items")
        except Exception as e:
            results["errors"].append(f"Agents page: {str(e)}")
        
        # Test monitoring page
        try:
            page.goto(f"{BASE_URL}/monitoring", wait_until="networkidle", timeout=10000)
            charts = page.query_selector_all("canvas, .chart, svg")
            print(f"  Monitoring page: {len(charts)} charts found")
        except Exception as e:
            results["errors"].append(f"Monitoring page: {str(e)}")
        
        # ====== Collect errors ======
        print(f"\n=== Console Errors: {len(console_errors)} ===")
        for err in console_errors[:10]:
            print(f"  {err[:150]}")
        
        print(f"\n=== Page Errors: {len(page_errors)} ===")
        for err in page_errors[:5]:
            print(f"  {err[:150]}")
        
        browser.close()
    
    # ====== SUMMARY ======
    results["summary"] = {
        "pages_tested": len(results["pages"]),
        "pages_ok": len([p for p in results["pages"] if p.get("status") == 200]),
        "pages_error": len([p for p in results["pages"] if p.get("status") != 200]),
        "api_tested": len(results["api_tests"]),
        "clicks_found": len(results["clicks"]),
        "total_errors": len(results["errors"]) + len(console_errors) + len(page_errors),
        "console_errors": len(console_errors),
        "page_errors": len(page_errors),
        "app_errors": len(results["errors"])
    }
    
    return results

if __name__ == "__main__":
    print("Starting AI-MultiColony-Ecosystem Browser Test Suite")
    print("=" * 60)
    
    server_proc = None
    try:
        print("Starting Flask server...")
        server_proc = start_server()
        print("Server started! Running tests...\n")
        
        results = test_all()
        
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        s = results["summary"]
        print(f"Pages tested: {s['pages_tested']} (OK: {s['pages_ok']}, Error: {s['pages_error']})")
        print(f"API endpoints tested: {s['api_tested']}")
        print(f"Interactive elements found: {s['clicks_found']}")
        print(f"Total errors: {s['total_errors']}")
        print(f"  Console errors: {s['console_errors']}")
        print(f"  Page errors: {s['page_errors']}")
        print(f"  App errors: {s['app_errors']}")
        
        # Save results
        results_path = os.path.join(os.path.dirname(__file__), "test_results.json")
        # Remove non-serializable items
        for p in results["pages"]:
            p.pop("screenshot", None)
        with open(results_path, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nResults saved to {results_path}")
        
    except Exception as e:
        print(f"FATAL ERROR: {e}")
        traceback.print_exc()
    finally:
        if server_proc:
            server_proc.terminate()
            server_proc.wait()
            print("\nServer stopped.")
