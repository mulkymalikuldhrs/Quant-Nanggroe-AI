#!/usr/bin/env python3
"""Production startup script — launches API + dashboard."""
import subprocess, sys, time, os

PORT_API = 8000
PORT_DASH = 3000
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def start_api():
    print(f"Starting API on port {PORT_API}...")
    return subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "quant_nanggroe.api.app:app",
         "--host", "0.0.0.0", "--port", str(PORT_API)],
        cwd=ROOT, env={**os.environ, "PYTHONPATH": ROOT}
    )

def start_dashboard():
    dash_dir = os.path.join(ROOT, "dashboard")
    if not os.path.exists(os.path.join(dash_dir, "node_modules")):
        print("Installing dashboard dependencies...")
        subprocess.run(["npm", "install"], cwd=dash_dir, check=True)
    print(f"Starting dashboard on port {PORT_DASH}...")
    return subprocess.Popen(["npm", "run", "dev"], cwd=dash_dir)

def main():
    api = start_api()
    dash = start_dashboard()
    print(f"\nQuant-Nanggroe-AI Hedge Fund running:")
    print(f"  API:     http://localhost:{PORT_API}")
    print(f"  Dashboard: http://localhost:{PORT_DASH}")
    print(f"  Health:  http://localhost:{PORT_API}/health")
    print(f"\nPress Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        api.terminate()
        dash.terminate()
        print("\nShutdown complete.")

if __name__ == "__main__":
    main()
