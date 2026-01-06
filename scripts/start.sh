#!/bin/bash
# ============================================================================
# Turing NexusFlow - Unified Startup Script
# ============================================================================
# Starts all services (Docker + Backend + Frontend)
#
# Usage:
#   ./scripts/start.sh           # Start everything
#   ./scripts/start.sh --docker  # Docker services only
#   ./scripts/start.sh --api     # API server only  
#   ./scripts/start.sh --frontend # Frontend only
#   ./scripts/start.sh --stop    # Stop everything
# ============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${CYAN}[NEXUSFLOW]${NC} $1"; }
success() { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; }
header() { echo -e "\n${BLUE}════════════════════════════════════════════════════════════${NC}"; echo -e "${BLUE}  $1${NC}"; echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"; }

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Parse arguments
DOCKER_ONLY=false
API_ONLY=false
FRONTEND_ONLY=false
STOP=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --docker) DOCKER_ONLY=true; shift ;;
        --api) API_ONLY=true; shift ;;
        --frontend) FRONTEND_ONLY=true; shift ;;
        --stop) STOP=true; shift ;;
        *) shift ;;
    esac
done

# Stop function
stop_all() {
    header "Stopping NexusFlow Services"
    
    log "Stopping frontend..."
    pkill -f "next dev" 2>/dev/null || true
    pkill -f "npm run dev" 2>/dev/null || true
    
    log "Stopping API server..."
    pkill -f "uvicorn nexusflow" 2>/dev/null || true
    
    log "Stopping Docker containers..."
    docker compose down 2>/dev/null || true
    
    success "All services stopped"
    exit 0
}

if [ "$STOP" = true ]; then
    stop_all
fi

# Check prerequisites
check_prereqs() {
    header "Checking Prerequisites"
    
    if ! command -v docker &> /dev/null; then
        error "Docker not found. Please install Docker."
        exit 1
    fi
    success "Docker installed"
    
    if ! docker info &> /dev/null; then
        error "Docker daemon not running. Please start Docker."
        exit 1
    fi
    success "Docker daemon running"
    
    if [ ! -f ".env" ]; then
        warn ".env file not found, copying from .env.example"
        cp .env.example .env 2>/dev/null || {
            error "No .env or .env.example found!"
            exit 1
        }
    fi
    success ".env file present"
}

# Start Docker services
start_docker() {
    header "Starting Infrastructure Services"
    
    log "Starting PostgreSQL, Neo4j, Milvus, Phoenix..."
    docker compose up -d
    
    log "Waiting for services to be healthy..."
    
    # Wait for PostgreSQL
    echo -n "  PostgreSQL: "
    for i in {1..30}; do
        if docker exec nexusflow-postgres pg_isready -U nexusflow &>/dev/null; then
            echo -e "${GREEN}ready${NC}"
            break
        fi
        echo -n "."
        sleep 2
    done
    
    # Wait for Neo4j
    echo -n "  Neo4j: "
    for i in {1..30}; do
        if curl -s http://localhost:7474 &>/dev/null; then
            echo -e "${GREEN}ready${NC}"
            break
        fi
        echo -n "."
        sleep 2
    done
    
    # Wait for Milvus
    echo -n "  Milvus: "
    for i in {1..30}; do
        if curl -s http://localhost:9091/healthz &>/dev/null; then
            echo -e "${GREEN}ready${NC}"
            break
        fi
        echo -n "."
        sleep 2
    done
    
    # Phoenix should start quickly
    echo -n "  Phoenix: "
    for i in {1..15}; do
        if curl -s http://localhost:6006 &>/dev/null; then
            echo -e "${GREEN}ready${NC}"
            break
        fi
        echo -n "."
        sleep 2
    done
    
    success "All infrastructure services started"
}

# Start API server
start_api() {
    header "Starting API Server"
    
    # Check if already running
    if curl -s http://localhost:8000/health &>/dev/null; then
        warn "API server already running on port 8000"
        return
    fi
    
    # Activate virtual environment
    if [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
    else
        warn "Virtual environment not found, creating..."
        python3 -m venv .venv
        source .venv/bin/activate
        pip install -e . --quiet
    fi
    
    # Initialize databases if needed
    log "Initializing databases..."
    python -c "
from nexusflow.db.session import init_db
import asyncio
asyncio.run(init_db())
print('Database initialized')
" 2>/dev/null || warn "Database init skipped"
    
    # Start API in background
    log "Starting uvicorn server..."
    nohup uvicorn nexusflow.api.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --reload \
        > logs/api.log 2>&1 &
    
    # Wait for API to be ready
    echo -n "  API: "
    for i in {1..20}; do
        if curl -s http://localhost:8000/health &>/dev/null; then
            echo -e "${GREEN}ready${NC}"
            break
        fi
        echo -n "."
        sleep 1
    done
    
    success "API server started on http://localhost:8000"
}

# Start Frontend
start_frontend() {
    header "Starting Frontend"
    
    # Check if already running
    if curl -s http://localhost:3000 &>/dev/null; then
        warn "Frontend already running on port 3000"
        return
    fi
    
    cd frontend
    
    # Install dependencies if needed
    if [ ! -d "node_modules" ]; then
        log "Installing frontend dependencies..."
        npm install --silent
    fi
    
    # Start frontend in background
    log "Starting Next.js dev server..."
    nohup npm run dev > ../logs/frontend.log 2>&1 &
    
    cd "$PROJECT_DIR"
    
    # Wait for frontend
    echo -n "  Frontend: "
    for i in {1..30}; do
        if curl -s http://localhost:3000 &>/dev/null; then
            echo -e "${GREEN}ready${NC}"
            break
        fi
        echo -n "."
        sleep 2
    done
    
    success "Frontend started on http://localhost:3000"
}

# Print status
print_status() {
    header "NexusFlow Service Status"
    
    echo ""
    echo -e "  ${CYAN}Service${NC}              ${CYAN}URL${NC}                           ${CYAN}Status${NC}"
    echo "  ─────────────────────────────────────────────────────────────────"
    
    # Check each service
    services=(
        "Frontend|http://localhost:3000|3000"
        "API|http://localhost:8000|8000"
        "API Docs|http://localhost:8000/docs|8000"
        "Phoenix|http://localhost:6006|6006"
        "Neo4j Browser|http://localhost:7474|7474"
        "PostgreSQL|localhost:5432|5432"
        "Milvus|localhost:19530|19530"
    )
    
    for svc in "${services[@]}"; do
        IFS='|' read -r name url port <<< "$svc"
        if curl -s "http://localhost:$port" &>/dev/null || nc -z localhost "$port" 2>/dev/null; then
            status="${GREEN}● Running${NC}"
        else
            status="${RED}○ Stopped${NC}"
        fi
        printf "  %-18s %-30s %b\n" "$name" "$url" "$status"
    done
    
    echo ""
    echo "  ─────────────────────────────────────────────────────────────────"
    echo ""
    echo -e "  ${YELLOW}Quick Commands:${NC}"
    echo "    View API logs:      tail -f logs/api.log"
    echo "    View frontend logs: tail -f logs/frontend.log"
    echo "    Stop all:           ./scripts/start.sh --stop"
    echo ""
}

# Main execution
main() {
    echo -e "${CYAN}"
    echo "  ╔════════════════════════════════════════════════════════════╗"
    echo "  ║                                                            ║"
    echo "  ║   ████████╗██╗   ██╗██████╗ ██╗███╗   ██╗ ██████╗          ║"
    echo "  ║      ██╔══╝██║   ██║██╔══██╗██║████╗  ██║██╔════╝          ║"
    echo "  ║      ██║   ██║   ██║██████╔╝██║██╔██╗ ██║██║  ███╗         ║"
    echo "  ║      ██║   ██║   ██║██╔══██╗██║██║╚██╗██║██║   ██║         ║"
    echo "  ║      ██║   ╚██████╔╝██║  ██║██║██║ ╚████║╚██████╔╝         ║"
    echo "  ║      ╚═╝    ╚═════╝ ╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝ ╚═════╝          ║"
    echo "  ║                                                            ║"
    echo "  ║               N E X U S F L O W                            ║"
    echo "  ║         AI-Powered Ticket Classification                   ║"
    echo "  ║                                                            ║"
    echo "  ╚════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    # Create logs directory
    mkdir -p logs
    
    check_prereqs
    
    if [ "$DOCKER_ONLY" = true ]; then
        start_docker
    elif [ "$API_ONLY" = true ]; then
        start_api
    elif [ "$FRONTEND_ONLY" = true ]; then
        start_frontend
    else
        # Start everything
        start_docker
        start_api
        start_frontend
    fi
    
    print_status
    
    header "NexusFlow Ready!"
    echo ""
    echo -e "  ${GREEN}Open http://localhost:3000 in your browser${NC}"
    echo ""
}

main "$@"

