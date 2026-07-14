#!/usr/bin/env python3
"""
⚡ Quant Nanggroe AI — Legacy Click CLI (Preserved for Backward Compatibility)

This file preserves the original Click-based CLI for backward compatibility.
It is called by cli.py when 'python cli.py legacy' is used.

New code should use 'python qna.py cli' instead.

Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent.resolve()))


class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.CYAN}{'=' * (len(text) + 3)}{Colors.ENDC}")

def print_success(text: str):
    print(f"{Colors.GREEN}{text}{Colors.ENDC}")

def print_error(text: str):
    print(f"{Colors.RED}{text}{Colors.ENDC}")

def print_warning(text: str):
    print(f"{Colors.YELLOW}{text}{Colors.ENDC}")

def print_info(text: str):
    print(f"{Colors.BLUE}{text}{Colors.ENDC}")


# ══════════════════════════════════════════════════════════════════════
#  Click CLI Group & Commands
# ══════════════════════════════════════════════════════════════════════

try:
    import click

    @click.group()
    @click.version_option(version="4.3.4", prog_name="Quant Nanggroe AI")
    def cli():
        """Quant Nanggroe AI — Agentic Trading Intelligence OS"""
        pass

    @cli.group()
    def system():
        """System management commands"""
        pass

    @cli.group()
    def agents():
        """Agent management commands"""
        pass

    @system.command()
    @click.option('--config', default='config/system_config.yaml', help='Configuration file path')
    @click.option('--debug', is_flag=True, help='Enable debug mode')
    def start(config, debug):
        """Start the system via qna.py daemon"""
        print_header("Starting Quant Nanggroe AI")
        from qna import run_daemon, build_parser
        parser = build_parser()
        args = parser.parse_args(["daemon"])
        run_daemon(args)

    @system.command()
    def status():
        """Check system status"""
        print_header("System Status")
        from qna import run_status, build_parser
        parser = build_parser()
        args = parser.parse_args(["status"])
        run_status(args)

    @system.command()
    def stop():
        """Stop the system"""
        print_header("Stopping System")
        from qna import run_status
        print_info("Use Ctrl+C in the running daemon, or:")
        print_info("  pkill -f 'python qna.py daemon'")

    @agents.command()
    def list():
        """List all agents"""
        print_header("Agent List")
        from qna import load_agent_config
        agents = load_agent_config()
        print(f"Found {len(agents)} agents:\n")
        for name, cfg in agents.items():
            desc = cfg.get("description", "🤖")
            print(f"  {desc} {name} (priority {cfg['priority']})")
        print()

    @cli.command()
    @click.option('--test', is_flag=True, help='Run system tests')
    def demo(test):
        """Run demo and examples"""
        print_header("Quant Nanggroe AI Demo")
        if test:
            print_info("Running system tests...")
            import subprocess
            result = subprocess.run([sys.executable, '-m', 'pytest', 'tests/', '-v'],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(result.stdout)
                print_success("Tests completed successfully")
            else:
                print_warning("Some tests failed:")

except ImportError:
    # Click not installed — provide fallback
    import warnings
    warnings.warn("Click not installed. Legacy CLI unavailable. pip install click")
    cli = None


if __name__ == "__main__":
    if cli is not None:
        cli()
    else:
        print("Click is not installed. Install it with: pip install click")
        sys.exit(1)
