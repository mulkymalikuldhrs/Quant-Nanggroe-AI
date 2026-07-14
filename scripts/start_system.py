#!/usr/bin/env python3
"""
Agentic AI System - Startup Script
Sistem startup otomatis untuk menjalankan semua komponen

Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

import os
import sys
import time
import subprocess
import threading
import signal
from pathlib import Path

def print_banner():
    """Print startup banner"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                    🤖 AGENTIC AI SYSTEM 🤖                   ║
║                                                              ║
║              Multi-Agent Intelligent System                 ║
║                                                              ║
║        Made with ❤️ by Mulky Malikul Dhaher 🇮🇩             ║
║                     Version 1.0.0                           ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)

def check_dependencies():
    """Check if all required dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    required_packages = [
        'flask', 'flask_socketio', 'pandas', 'numpy', 
        'pyyaml', 'requests', 'aiohttp'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"  ✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"  ❌ {package}")
    
    if missing_packages:
        print(f"\n⚠️  Missing packages: {', '.join(missing_packages)}")
        print("Installing missing packages...")
        
        try:
            subprocess.check_call([
                sys.executable, '-m', 'pip', 'install', 
                *missing_packages
            ])
            print("✅ All packages installed successfully!")
        except subprocess.CalledProcessError:
            print("❌ Failed to install packages. Please install manually:")
            print(f"   pip install {' '.join(missing_packages)}")
            return False
    
    return True

def setup_directories():
    """Create necessary directories"""
    print("📁 Setting up directories...")
    
    directories = [
        'logs',
        'logs/shell',
        'data',
        'temp',
        'reports'
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"  ✅ {directory}")

def check_ports():
    """Check if required ports are available"""
    print("🔌 Checking port availability...")
    
    import socket
    
    ports_to_check = [5000]  # Flask default port
    
    for port in ports_to_check:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        
        if result == 0:
            print(f"  ⚠️  Port {port} is already in use")
            print(f"     Please stop the service using port {port} or choose a different port")
            return False
        else:
            print(f"  ✅ Port {port} is available")
    
    return True

def start_web_interface():
    """Start the web interface"""
    print("🌐 Starting web interface...")
    
    try:
        # Change to web_interface directory
        web_interface_path = Path(__file__).parent / 'web_interface'
        os.chdir(web_interface_path)
        
        # Start Flask application
        process = subprocess.Popen([
            sys.executable, 'app.py'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        return process
        
    except Exception as e:
        print(f"❌ Failed to start web interface: {e}")
        return None

def monitor_system():
    """Monitor system health"""
    print("📊 Starting system monitor...")
    
    while True:
        time.sleep(30)  # Check every 30 seconds
        
        # Simple health check - in production, this would be more sophisticated
        try:
            import requests
            response = requests.get('http://localhost:5000/api/system/status', timeout=5)
            if response.status_code == 200:
                print("💚 System health check: OK")
            else:
                print(f"⚠️  System health check: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ System health check failed: {e}")

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    print("\n🛑 Shutdown signal received. Stopping system...")
    sys.exit(0)

def main():
    """Main startup function"""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print_banner()
    
    # Pre-flight checks
    if not check_dependencies():
        print("❌ Dependency check failed. Exiting.")
        sys.exit(1)
    
    setup_directories()
    
    if not check_ports():
        print("❌ Port check failed. Exiting.")
        sys.exit(1)
    
    print("\n🚀 Starting Agentic AI System...")
    
    # Start web interface
    web_process = start_web_interface()
    
    if not web_process:
        print("❌ Failed to start web interface. Exiting.")
        sys.exit(1)
    
    # Start system monitor in background
    monitor_thread = threading.Thread(target=monitor_system, daemon=True)
    monitor_thread.start()
    
    print("\n✅ System started successfully!")
    print("\n📊 Access the dashboard at: http://localhost:5000")
    print("🤖 All agents are ready and waiting for tasks")
    print("\nPress Ctrl+C to stop the system")
    
    try:
        # Wait for web process to finish
        web_process.wait()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        web_process.terminate()
        web_process.wait()
        print("✅ System stopped successfully")

if __name__ == "__main__":
    main()
