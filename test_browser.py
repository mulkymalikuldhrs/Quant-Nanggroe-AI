"""
Browser automation test for Quant Nanggroe AI dashboard.
Screenshots home page and /brokers page, captures console errors.
"""
import sys, os, json
from datetime import datetime

project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:3000"
SCREENSHOTS_DIR = os.path.join(project_root, "screenshots")
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

def run():
    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "pages_loaded": [],
        "console_errors": [],
        "crashes": [],
        "screenshots": [],
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1280, "height": 800},
            ignore_https_errors=True,
        )
        page = context.new_page()

        # Collect all console messages
        page.on("console", lambda msg: _handle_console(msg, results))
        # Collect crashes
        page.on("crash", lambda: results["crashes"].append("Page crashed"))
        page.on("pageerror", lambda err: results["crashes"].append(str(err)))

        # 1) Load home page
        print("=== Loading home page: %s ===" % BASE_URL)
        try:
            page.goto(BASE_URL, wait_until="networkidle", timeout=30000)
            results["pages_loaded"].append({"url": BASE_URL, "status": "loaded"})
            print("Home page loaded, title: %s" % page.title())

            screenshot_path = os.path.join(SCREENSHOTS_DIR, "home.png")
            page.screenshot(path=screenshot_path, full_page=True)
            results["screenshots"].append("home.png")
            print("Screenshot saved: %s" % screenshot_path)
        except Exception as e:
            results["pages_loaded"].append({"url": BASE_URL, "status": "error", "error": str(e)})
            print("Home page error: %s" % e)

        # 2) Navigate to /brokers
        brokers_url = BASE_URL + "/brokers"
        print("\n=== Navigating to /brokers: %s ===" % brokers_url)
        try:
            page.goto(brokers_url, wait_until="networkidle", timeout=30000)
            results["pages_loaded"].append({"url": brokers_url, "status": "loaded"})
            print("Brokers page loaded, title: %s" % page.title())

            screenshot_path = os.path.join(SCREENSHOTS_DIR, "brokers.png")
            page.screenshot(path=screenshot_path, full_page=True)
            results["screenshots"].append("brokers.png")
            print("Screenshot saved: %s" % screenshot_path)
        except Exception as e:
            results["pages_loaded"].append({"url": brokers_url, "status": "error", "error": str(e)})
            print("Brokers page error: %s" % e)

        browser.close()

    # Write report
    report = {
        "summary": {
            "pages_loaded": len([p for p in results["pages_loaded"] if p["status"] == "loaded"]),
            "pages_errored": len([p for p in results["pages_loaded"] if p["status"] == "error"]),
            "console_errors_count": len(results["console_errors"]),
            "crashes_count": len(results["crashes"]),
        },
        "details": results,
    }

    report_path = os.path.join(SCREENSHOTS_DIR, "browser_test_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    # Print summary
    print("\n" + "=" * 60)
    print("TEST RESULTS")
    print("=" * 60)
    print("Pages loaded: %s" % results["pages_loaded"])
    print("Console errors: %d" % len(results["console_errors"]))
    for ce in results["console_errors"]:
        print("  - [%s] %s" % (ce.get("type", ""), ce.get("text", "")))
    print("Crashes: %d" % len(results["crashes"]))
    for c in results["crashes"]:
        print("  - %s" % c)
    print("Screenshots: %s" % results["screenshots"])
    print("Report: %s" % report_path)

    return report


def _handle_console(msg, results):
    entry = {
        "type": msg.type,
        "text": msg.text,
        "location": str(msg.location) if hasattr(msg, "location") else "",
    }
    if msg.type == "error" or "error" in msg.text.lower() or "fail" in msg.text.lower():
        results["console_errors"].append(entry)
        print("[CONSOLE %s] %s" % (msg.type, msg.text))
    elif msg.type in ("warning", "trace"):
        pass  # ignore these for the report
    else:
        pass  # info/log messages


if __name__ == "__main__":
    run()
