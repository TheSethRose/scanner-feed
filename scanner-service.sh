#!/bin/bash
#
# Scanner Feed Service Manager
# Easy way to start, restart, and stop the scanner feed transcription service
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Service names
PARAKEET_SERVICE="com.scanner-feed.parakeet"
DOCKER_SERVICE="scanner"

# Helper functions
print_status() {
    echo -e "${BLUE}[$(date +%H:%M:%S)]${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

check_parakeet() {
    curl -s http://127.0.0.1:18765/health > /dev/null 2>&1
}

check_docker() {
    curl -s http://127.0.0.1:49173/health > /dev/null 2>&1
}

check_docker_container() {
    docker compose ps "$DOCKER_SERVICE" 2>/dev/null | grep -q "Up"
}

# Commands
start_service() {
    print_status "Starting Scanner Feed Service..."
    
    # Start Parakeet server
    print_status "Starting Parakeet server (native MLX)..."
    launchctl kickstart -k "gui/$(id -u)/$PARAKEET_SERVICE"
    
    # Wait a moment for Parakeet to start
    sleep 3
    
    # Check if Parakeet started successfully
    if check_parakeet; then
        print_success "Parakeet server is running"
    else
        print_warning "Parakeet server may not be ready yet (waiting 5 more seconds)"
        sleep 5
        if check_parakeet; then
            print_success "Parakeet server is now running"
        else
            print_error "Parakeet server failed to start"
            return 1
        fi
    fi
    
    # Start Docker worker
    print_status "Starting Docker worker..."
    cd "$PROJECT_DIR"
    docker compose up -d
    
    # Wait a moment for Docker to start
    sleep 3
    
    # Check if Docker worker started successfully
    if check_docker_container; then
        print_success "Docker worker is running"
    else
        print_warning "Docker worker may not be ready yet (waiting 5 more seconds)"
        sleep 5
        if check_docker_container; then
            print_success "Docker worker is now running"
        else
            print_error "Docker worker failed to start"
            return 1
        fi
    fi
    
    print_success "Scanner Feed Service started successfully!"
    echo ""
    echo "Service endpoints:"
    echo "  Parakeet server: http://127.0.0.1:18765/health"
    echo "  Docker worker:   http://127.0.0.1:49173/health"
    echo ""
    echo "View logs:"
    echo "  docker compose logs -f scanner"
    echo ""
    echo "View transcripts:"
    echo "  tail -f $PROJECT_DIR/runtime/scanner-feed.txt"
}

stop_service() {
    print_status "Stopping Scanner Feed Service..."
    
    # Stop Docker worker
    print_status "Stopping Docker worker..."
    cd "$PROJECT_DIR"
    docker compose down
    
    if ! check_docker_container; then
        print_success "Docker worker stopped"
    else
        print_warning "Docker worker may still be running"
    fi
    
    # Stop Parakeet server
    print_status "Stopping Parakeet server..."
    launchctl bootout "gui/$(id -u)/$PARAKEET_SERVICE"
    
    # Wait a moment
    sleep 2
    
    # Check if Parakeet stopped
    if ! check_parakeet; then
        print_success "Parakeet server stopped"
    else
        print_warning "Parakeet server may still be running"
    fi
    
    print_success "Scanner Feed Service stopped successfully!"
}

restart_service() {
    print_status "Restarting Scanner Feed Service..."
    
    stop_service
    echo ""
    sleep 2
    start_service
}

status_service() {
    print_status "Checking Scanner Feed Service status..."
    echo ""
    
    # Check Parakeet server
    echo -n "Parakeet server (port 18765): "
    if check_parakeet; then
        echo -e "${GREEN}Running${NC}"
        curl -s http://127.0.0.1:18765/health | python3 -m json.tool 2>/dev/null || echo ""
    else
        echo -e "${RED}Not running${NC}"
    fi
    echo ""
    
    # Check Docker worker
    echo -n "Docker worker (port 49173): "
    if check_docker_container; then
        echo -e "${GREEN}Running${NC}"
        curl -s http://127.0.0.1:49173/health | python3 -m json.tool 2>/dev/null || echo ""
    else
        echo -e "${RED}Not running${NC}"
    fi
    echo ""
    
    # Check Docker container status
    echo "Docker container status:"
    cd "$PROJECT_DIR"
    docker compose ps 2>/dev/null || echo "  Docker compose not available"
    echo ""
    
    # Check log files
    echo "Log files:"
    if [ -d "$PROJECT_DIR/logs" ]; then
        ls -lh "$PROJECT_DIR/logs/" 2>/dev/null | tail -3
    else
        echo "  No logs directory found"
    fi
    echo ""
    
    # Check transcript files
    echo "Transcript files:"
    if [ -f "$PROJECT_DIR/runtime/scanner-feed.txt" ]; then
        ls -lh "$PROJECT_DIR/runtime/scanner-feed.txt" 2>/dev/null
    else
        echo "  No transcript file found"
    fi
}

view_logs() {
    print_status "Viewing Docker logs (Ctrl+C to exit)..."
    cd "$PROJECT_DIR"
    docker compose logs -f scanner
}

view_transcript() {
    print_status "Viewing transcript (Ctrl+C to exit)..."
    tail -f "$PROJECT_DIR/runtime/scanner-feed.txt" 2>/dev/null || \
    echo -e "${RED}Transcript file not found: $PROJECT_DIR/runtime/scanner-feed.txt${NC}"
}

clean_logs() {
    print_status "Cleaning log data..."
    
    # Ask for confirmation
    echo -e "${YELLOW}WARNING: This will remove all log data including:${NC}"
    echo "  - CSV event logs in logs/"
    echo "  - Transcript files in runtime/"
    echo "  - Raw audit logs in runtime/"
    echo ""
    echo -n "Are you sure you want to continue? (y/N): "
    read -r confirm
    
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        print_status "Clean cancelled."
        return 0
    fi
    
    # Clean CSV logs
    if [ -d "$PROJECT_DIR/logs" ]; then
        print_status "Removing CSV logs..."
        rm -f "$PROJECT_DIR/logs/"*.csv 2>/dev/null
        if [ $? -eq 0 ]; then
            print_success "CSV logs removed"
        else
            print_warning "No CSV logs found or unable to remove"
        fi
    else
        print_warning "Logs directory not found"
    fi
    
    # Clean transcript files
    if [ -d "$PROJECT_DIR/runtime" ]; then
        print_status "Removing transcript files..."
        rm -f "$PROJECT_DIR/runtime/scanner-feed.txt" 2>/dev/null
        rm -f "$PROJECT_DIR/runtime/scanner-feed.raw.txt" 2>/dev/null
        if [ $? -eq 0 ]; then
            print_success "Transcript files removed"
        else
            print_warning "No transcript files found or unable to remove"
        fi
    else
        print_warning "Runtime directory not found"
    fi
    
    # Clean temporary segments (optional)
    if [ -d "$PROJECT_DIR/runtime/segments" ]; then
        print_status "Cleaning temporary segments..."
        rm -f "$PROJECT_DIR/runtime/segments/"*.wav 2>/dev/null
        if [ $? -eq 0 ]; then
            print_success "Temporary segments cleaned"
        else
            print_warning "No segments found or unable to remove"
        fi
    fi
    
    print_success "Log data cleanup completed!"
    echo ""
    echo "Remaining files:"
    echo "  Logs directory: $(ls "$PROJECT_DIR/logs/" 2>/dev/null | wc -l) files"
    echo "  Runtime directory: $(ls "$PROJECT_DIR/runtime/" 2>/dev/null | wc -l) files"
}

# Main script
case "$1" in
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service
        ;;
    status)
        status_service
        ;;
    logs)
        view_logs
        ;;
    transcript)
        view_transcript
        ;;
    clean)
        clean_logs
        ;;
    help|--help|-h)
        echo "Scanner Feed Service Manager"
        echo ""
        echo "Usage: $0 {start|stop|restart|status|logs|transcript|clean|help}"
        echo ""
        echo "Commands:"
        echo "  start      - Start both Parakeet server and Docker worker"
        echo "  stop       - Stop both Parakeet server and Docker worker"
        echo "  restart    - Stop and then start the service"
        echo "  status     - Check service status"
        echo "  logs       - View Docker logs in real-time"
        echo "  transcript - View transcript output in real-time"
        echo "  clean      - Remove all log data (CSV logs, transcripts, audit logs)"
        echo "  help       - Show this help message"
        echo ""
        echo "Examples:"
        echo "  ./scanner-service.sh start"
        echo "  ./scanner-service.sh status"
        echo "  ./scanner-service.sh logs"
        echo "  ./scanner-service.sh clean"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|transcript|clean|help}"
        exit 1
        ;;
esac
