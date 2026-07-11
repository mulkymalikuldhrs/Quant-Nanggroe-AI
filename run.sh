#!/bin/bash

# 🧠 Agentic AI System - Startup Script
# Made with ❤️ by Mulky Malikul Dhaher in Indonesia 🇮🇩

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Print banner
echo -e "${PURPLE}"
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║                        🧠 AGENTIC AI SYSTEM 🧠                               ║"
echo "║                                                                              ║"
echo "║                    Autonomous Multi-Agent Intelligence                       ║"
echo "║                           STARTUP SCRIPT                                     ║"
echo "║                                                                              ║"
echo "║                Made with ❤️ by Mulky Malikul Dhaher 🇮🇩                     ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Function to print colored messages
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check if Python is installed
check_python() {
    print_step "Checking Python installation..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
        print_status "Python $PYTHON_VERSION found"
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_VERSION=$(python --version 2>&1 | cut -d' ' -f2)
        print_status "Python $PYTHON_VERSION found"
        PYTHON_CMD="python"
    else
        print_error "Python not found! Please install Python 3.8+ to continue."
        exit 1
    fi
    
    # Check Python version (should be 3.8+)
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
    
    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
        print_error "Python 3.8+ is required. Found version $PYTHON_VERSION"
        exit 1
    fi
}

# Setup environment
setup_environment() {
    print_step "Setting up environment..."
    
    # Load environment variables if .env exists
    if [ -f .env ]; then
        print_status "Loading environment variables from .env"
        export $(grep -v '^#' .env | xargs)
    else
        print_warning ".env file not found. Creating from template..."
        if [ -f .env.example ]; then
            cp .env.example .env
            print_status ".env created from .env.example template"
        fi
    fi
    
    # Create required directories
    print_status "Creating required directories..."
    mkdir -p data/logs data/backups data/cache projects ui/generated reports
    
    # Set Python path
    export PYTHONPATH="${PYTHONPATH}:$(pwd)"
}

# Install dependencies
install_dependencies() {
    print_step "Installing Python dependencies..."
    
    if [ -f requirements.txt ]; then
        if command -v pip3 &> /dev/null; then
            pip3 install -r requirements.txt
        elif command -v pip &> /dev/null; then
            pip install -r requirements.txt
        else
            print_error "pip not found! Please install pip to continue."
            exit 1
        fi
        print_status "Dependencies installed successfully"
    else
        print_warning "requirements.txt not found. Attempting to install basic dependencies..."
        if command -v pip3 &> /dev/null; then
            pip3 install asyncio aiohttp aiofiles python-dotenv redis psutil websockets
        else
            pip install asyncio aiohttp aiofiles python-dotenv redis psutil websockets
        fi
    fi
}

# Check system health
check_system_health() {
    print_step "Performing system health check..."
    
    # Check disk space
    DISK_USAGE=$(df . | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ "$DISK_USAGE" -gt 90 ]; then
        print_warning "Disk usage is high: ${DISK_USAGE}%"
    else
        print_status "Disk usage: ${DISK_USAGE}%"
    fi
    
    # Check memory
    if command -v free &> /dev/null; then
        MEMORY_USAGE=$(free | grep Mem | awk '{printf("%.0f", $3/$2 * 100.0)}')
        print_status "Memory usage: ${MEMORY_USAGE}%"
    fi
    
    # Check if ports are available
    check_port() {
        local port=$1
        local service=$2
        
        if command -v netstat &> /dev/null; then
            if netstat -tuln | grep ":$port " > /dev/null; then
                print_warning "Port $port is already in use (needed for $service)"
                return 1
            fi
        elif command -v ss &> /dev/null; then
            if ss -tuln | grep ":$port " > /dev/null; then
                print_warning "Port $port is already in use (needed for $service)"
                return 1
            fi
        fi
        return 0
    }
    
    check_port 5000 "Web Interface"
    check_port 8765 "Sync Engine WebSocket"
}

# Start the system
start_system() {
    print_step "Starting Agentic AI System..."
    
    # Check if we should run in background
    if [ "$1" = "--background" ] || [ "$1" = "-b" ]; then
        print_status "Starting system in background mode..."
        nohup $PYTHON_CMD main.py > data/logs/system.log 2>&1 &
        SYSTEM_PID=$!
        echo $SYSTEM_PID > data/system.pid
        print_status "System started with PID: $SYSTEM_PID"
        print_status "Logs available at: data/logs/system.log"
        print_status "Web interface will be available at: http://localhost:5000"
    else
        print_status "Starting system in interactive mode..."
        print_status "Press Ctrl+C to stop the system"
        echo ""
        
        # Handle cleanup on exit
        trap cleanup EXIT
        
        # Run the system
        $PYTHON_CMD main.py "$@"
    fi
}

# Cleanup function
cleanup() {
    print_step "Cleaning up..."
    
    # Kill background processes if any
    if [ -f data/system.pid ]; then
        SYSTEM_PID=$(cat data/system.pid)
        if ps -p $SYSTEM_PID > /dev/null 2>&1; then
            print_status "Stopping system process (PID: $SYSTEM_PID)..."
            kill $SYSTEM_PID
        fi
        rm -f data/system.pid
    fi
}

# Stop system function
stop_system() {
    print_step "Stopping Agentic AI System..."
    
    if [ -f data/system.pid ]; then
        SYSTEM_PID=$(cat data/system.pid)
        if ps -p $SYSTEM_PID > /dev/null 2>&1; then
            print_status "Stopping system process (PID: $SYSTEM_PID)..."
            kill $SYSTEM_PID
            sleep 2
            
            # Force kill if still running
            if ps -p $SYSTEM_PID > /dev/null 2>&1; then
                print_warning "Force stopping system..."
                kill -9 $SYSTEM_PID
            fi
            
            rm -f data/system.pid
            print_status "System stopped"
        else
            print_warning "System is not running"
            rm -f data/system.pid
        fi
    else
        print_warning "System PID file not found. System may not be running."
    fi
}

# Show system status
show_status() {
    print_step "Checking system status..."
    
    if [ -f data/system.pid ]; then
        SYSTEM_PID=$(cat data/system.pid)
        if ps -p $SYSTEM_PID > /dev/null 2>&1; then
            print_status "System is running (PID: $SYSTEM_PID)"
            
            # Check web interface
            if command -v curl &> /dev/null; then
                if curl -s http://localhost:5000 > /dev/null 2>&1; then
                    print_status "Web interface is accessible: http://localhost:5000"
                else
                    print_warning "Web interface is not responding"
                fi
            fi
            
            # Show recent logs
            if [ -f data/logs/system.log ]; then
                print_status "Recent log entries:"
                tail -5 data/logs/system.log
            fi
        else
            print_warning "System is not running (stale PID file)"
            rm -f data/system.pid
        fi
    else
        print_warning "System is not running"
    fi
}

# Show help
show_help() {
    echo -e "${CYAN}Agentic AI System - Startup Script${NC}"
    echo ""
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  start [--background|-b]  Start the system (default: interactive mode)"
    echo "  stop                     Stop the system"
    echo "  restart                  Restart the system"
    echo "  status                   Show system status"
    echo "  install                  Install dependencies only"
    echo "  check                    Run system health check"
    echo "  logs                     Show recent logs"
    echo "  clean                    Clean up temporary files"
    echo "  help                     Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 start                 # Start in interactive mode"
    echo "  $0 start --background    # Start in background"
    echo "  $0 stop                  # Stop the system"
    echo "  $0 status                # Check if running"
    echo ""
    echo "Direct AI Commands:"
    echo "  $0 \"Create a web app called MyApp\""
    echo "  $0 \"Build a React component for login\""
    echo "  $0 \"Deploy my project to production\""
    echo ""
}

# Show logs
show_logs() {
    if [ -f data/logs/system.log ]; then
        if [ "$1" = "--follow" ] || [ "$1" = "-f" ]; then
            tail -f data/logs/system.log
        else
            tail -50 data/logs/system.log
        fi
    else
        print_warning "No log file found"
    fi
}

# Clean up temporary files
clean_system() {
    print_step "Cleaning up temporary files..."
    
    # Remove cache files
    find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
    find . -name "*.pyc" -delete 2>/dev/null || true
    
    # Clean old logs (keep last 10)
    if [ -d data/logs ]; then
        find data/logs -name "*.log.*" -type f | sort | head -n -10 | xargs rm -f 2>/dev/null || true
    fi
    
    # Clean old backups (keep last 20)
    if [ -d data/backups ]; then
        find data/backups -name "backup_*.json" -type f | sort | head -n -20 | xargs rm -f 2>/dev/null || true
    fi
    
    print_status "Cleanup completed"
}

# Main script logic
main() {
    case "${1:-start}" in
        "start")
            check_python
            setup_environment
            install_dependencies
            check_system_health
            shift  # Remove 'start' from arguments
            start_system "$@"
            ;;
        "stop")
            stop_system
            ;;
        "restart")
            stop_system
            sleep 2
            check_python
            setup_environment
            start_system --background
            ;;
        "status")
            show_status
            ;;
        "install")
            check_python
            install_dependencies
            print_status "Dependencies installed. Run './run.sh start' to start the system."
            ;;
        "check")
            check_python
            setup_environment
            check_system_health
            ;;
        "logs")
            show_logs "$2"
            ;;
        "clean")
            clean_system
            ;;
        "help"|"--help"|"-h")
            show_help
            ;;
        *)
            # Treat as AI command
            check_python
            setup_environment
            install_dependencies > /dev/null 2>&1
            print_status "Processing AI command: $*"
            start_system "$@"
            ;;
    esac
}

# Run main function with all arguments
main "$@"
