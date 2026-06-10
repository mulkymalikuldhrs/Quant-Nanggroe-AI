#!/usr/bin/env python3
"""
Trading Terminal Launcher for AI Quant Hedge Fund

Usage:
    python3 run_terminal.py              # Start with defaults
    python3 run_terminal.py --port 8080  # Custom port
    python3 run_terminal.py --debug      # Debug mode
    python3 run_terminal.py --demo       # Demo mode without core dependencies
"""

import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def check_dependencies():
    """Check if required packages are installed."""
    required = ['dash', 'plotly', 'pandas', 'numpy']
    missing = []
    
    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"Missing dependencies: {', '.join(missing)}")
        print(f"Install with: pip install dash plotly pandas numpy")
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description='AI Quant Hedge Fund Trading Terminal')
    parser.add_argument('--port', type=int, default=8050, help='Port to run the terminal (default: 8050)')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host to bind (default: 0.0.0.0)')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--demo', action='store_true', help='Run in demo mode without core dependencies')
    parser.add_argument('--reload', action='store_true', help='Enable auto-reload (debug only)')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("  AI QUANT HEDGE FUND - TRADING TERMINAL v2.0")
    print("=" * 60)
    print()
    
    if not check_dependencies():
        sys.exit(1)
    
    try:
        from src.ui.web.trading_terminal import app, run_terminal
        
        print(f"Starting trading terminal...")
        print(f"  URL: http://{args.host}:{args.port}")
        print(f"  Mode: {'Debug' if args.debug else 'Production'}")
        print()
        print("Press Ctrl+C to stop")
        print("-" * 60)
        
        run_terminal(debug=args.debug, port=args.port)
        
    except KeyboardInterrupt:
        print("\nShutting down...")
    except ImportError as e:
        print(f"Error importing modules: {e}")
        print("Try running with --demo flag for demo mode")
        sys.exit(1)


if __name__ == '__main__':
    main()
