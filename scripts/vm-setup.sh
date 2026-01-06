#!/bin/bash
# ============================================================================
# Turing NexusFlow - VM Setup Script
# ============================================================================
# Run this script on the VM after cloning the repository
#
# Usage:
#   cd /opt/nexusflow
#   ./scripts/vm-setup.sh
# ============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${CYAN}[NEXUSFLOW]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

APP_DIR="/opt/nexusflow"
cd "$APP_DIR"

# ============================================================================
# Check for .env file
# ============================================================================
if [ ! -f ".env" ]; then
    warn ".env file not found!"
    log "Creating .env from example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        warn "Please edit .env and add your API keys!"
    else
        error ".env.example not found. Please create .env manually."
    fi
fi

# ============================================================================
# Create required directories
# ============================================================================
log "Creating data directories..."
mkdir -p data
mkdir -p logs

# ============================================================================
# Start infrastructure services
# ============================================================================
log "Starting infrastructure services (PostgreSQL, Neo4j, Milvus, Phoenix)..."

docker compose --profile local-dbs up -d postgres neo4j etcd minio

# Wait for services
log "Waiting for databases to be ready..."
sleep 30

docker compose --profile local-dbs up -d milvus-standalone phoenix

# Wait for Milvus
log "Waiting for Milvus..."
sleep 15

success "Infrastructure services started"

# ============================================================================
# Setup Python environment
# ============================================================================
log "Setting up Python environment..."

# Use uv if available, otherwise pip
if command -v uv &> /dev/null; then
    uv venv .venv
    source .venv/bin/activate
    uv pip install -e .
else
    python3.11 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -e .
fi

success "Python environment ready"

# ============================================================================
# Initialize databases
# ============================================================================
log "Initializing databases..."

source .venv/bin/activate

# Generate synthetic data and setup databases
python scripts/generate_synthetic_data.py

success "Databases initialized"

# ============================================================================
# Setup frontend
# ============================================================================
log "Setting up frontend..."

cd frontend
npm install
npm run build

cd "$APP_DIR"

success "Frontend built"

# ============================================================================
# Create systemd services
# ============================================================================
log "Creating systemd services..."

# API Service
sudo tee /etc/systemd/system/nexusflow-api.service > /dev/null << EOF
[Unit]
Description=NexusFlow API Server
After=network.target docker.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/.venv/bin:/usr/local/bin:/usr/bin
ExecStart=$APP_DIR/.venv/bin/uvicorn nexusflow.api.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# MCP Service
sudo tee /etc/systemd/system/nexusflow-mcp.service > /dev/null << EOF
[Unit]
Description=NexusFlow MCP Server
After=network.target nexusflow-api.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$APP_DIR
Environment=PATH=$APP_DIR/.venv/bin:/usr/local/bin:/usr/bin
ExecStart=$APP_DIR/.venv/bin/python -m nexusflow.mcp.server
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Frontend Service
sudo tee /etc/systemd/system/nexusflow-frontend.service > /dev/null << EOF
[Unit]
Description=NexusFlow Frontend
After=network.target nexusflow-api.service

[Service]
Type=simple
User=$USER
WorkingDirectory=$APP_DIR/frontend
ExecStart=/usr/bin/npm run start
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Enable and start services
sudo systemctl daemon-reload
sudo systemctl enable nexusflow-api nexusflow-mcp nexusflow-frontend
sudo systemctl start nexusflow-api
sleep 5
sudo systemctl start nexusflow-mcp nexusflow-frontend

success "Systemd services created and started"

# ============================================================================
# Configure Nginx reverse proxy
# ============================================================================
log "Configuring Nginx..."

sudo tee /etc/nginx/sites-available/nexusflow > /dev/null << 'EOF'
server {
    listen 80;
    server_name _;

    # Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }

    # API
    location /api/ {
        proxy_pass http://localhost:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # API Docs
    location /docs {
        proxy_pass http://localhost:8000/docs;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }

    location /openapi.json {
        proxy_pass http://localhost:8000/openapi.json;
    }

    # Health endpoints
    location /health {
        proxy_pass http://localhost:8000/health;
    }

    # WebSocket support for real-time features
    location /ws/ {
        proxy_pass http://localhost:8000/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }

    # Phoenix observability
    location /phoenix/ {
        proxy_pass http://localhost:6006/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/nexusflow /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

success "Nginx configured"

# ============================================================================
# Final checks
# ============================================================================
log "Running final checks..."

# Check API
if curl -s http://localhost:8000/health | grep -q "healthy"; then
    success "API is healthy"
else
    warn "API health check failed"
fi

# Check Frontend
if curl -s -o /dev/null -w "%{http_code}" http://localhost:3000 | grep -q "200"; then
    success "Frontend is running"
else
    warn "Frontend may not be ready yet"
fi

# ============================================================================
# Summary
# ============================================================================
PUBLIC_IP=$(curl -s ifconfig.me)

echo ""
echo "============================================================================"
echo -e "${GREEN}NexusFlow Setup Complete!${NC}"
echo "============================================================================"
echo ""
echo "Services Status:"
sudo systemctl status nexusflow-api --no-pager -l | head -5
echo ""
echo "Access URLs:"
echo "  Frontend:  http://$PUBLIC_IP"
echo "  API:       http://$PUBLIC_IP/api/v1"
echo "  API Docs:  http://$PUBLIC_IP/docs"
echo "  Phoenix:   http://$PUBLIC_IP/phoenix"
echo ""
echo "Useful Commands:"
echo "  View API logs:       sudo journalctl -u nexusflow-api -f"
echo "  View frontend logs:  sudo journalctl -u nexusflow-frontend -f"
echo "  Restart services:    sudo systemctl restart nexusflow-api nexusflow-frontend"
echo "  Check status:        sudo systemctl status nexusflow-api"
echo ""
echo "============================================================================"

