#!/bin/bash
# ============================================================================
# Quick Deploy - Copy local code to Azure VM and deploy
# ============================================================================
# Usage: ./scripts/quick-deploy.sh <VM_IP> [SSH_KEY_PATH]
# ============================================================================

set -e

VM_IP="$1"
SSH_KEY="${2:-$HOME/.ssh/id_rsa}"
ADMIN_USER="azureuser"
REMOTE_DIR="/opt/nexusflow"

if [ -z "$VM_IP" ]; then
    echo "Usage: $0 <VM_IP> [SSH_KEY_PATH]"
    echo "Example: $0 20.85.123.45"
    exit 1
fi

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║           Quick Deploy to Azure VM                               ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""
echo "Target: $ADMIN_USER@$VM_IP"
echo ""

# Create tarball of project (excluding unnecessary files)
echo "[1/5] Creating project archive..."
tar --exclude='.venv' \
    --exclude='node_modules' \
    --exclude='.next' \
    --exclude='__pycache__' \
    --exclude='.git' \
    --exclude='*.pyc' \
    --exclude='logs/*.log' \
    --exclude='.env' \
    -czf /tmp/nexusflow.tar.gz .

echo "[2/5] Copying files to VM..."
scp -i "$SSH_KEY" /tmp/nexusflow.tar.gz "$ADMIN_USER@$VM_IP:/tmp/"

echo "[3/5] Extracting on VM..."
ssh -i "$SSH_KEY" "$ADMIN_USER@$VM_IP" << 'REMOTE'
sudo mkdir -p /opt/nexusflow
sudo chown -R $USER:$USER /opt/nexusflow
cd /opt/nexusflow
tar -xzf /tmp/nexusflow.tar.gz
rm /tmp/nexusflow.tar.gz
REMOTE

echo "[4/5] Setting up environment on VM..."
ssh -i "$SSH_KEY" "$ADMIN_USER@$VM_IP" << 'REMOTE'
cd /opt/nexusflow
export PATH="$HOME/.local/bin:$PATH"

# Create Python virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating Python environment..."
    python3.11 -m venv .venv
fi

source .venv/bin/activate

# Install Python dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -e . 2>/dev/null || pip install -e ".[dev]"

# Install frontend dependencies
echo "Installing frontend dependencies..."
cd frontend
npm install
npm run build 2>/dev/null || true
cd ..

echo "Environment setup complete!"
REMOTE

echo "[5/5] Starting services..."
ssh -i "$SSH_KEY" "$ADMIN_USER@$VM_IP" << 'REMOTE'
cd /opt/nexusflow
source .venv/bin/activate

# Stop existing services
pkill -f "uvicorn nexusflow" 2>/dev/null || true
pkill -f "next" 2>/dev/null || true
sleep 2

# Create logs directory
mkdir -p logs

# Start backend
echo "Starting backend API..."
nohup uvicorn nexusflow.api.main:app --host 0.0.0.0 --port 8000 > logs/api.log 2>&1 &

# Start frontend (production mode)
echo "Starting frontend..."
cd frontend
nohup npm start > ../logs/frontend.log 2>&1 &
cd ..

sleep 5
echo ""
echo "Services started!"
REMOTE

rm /tmp/nexusflow.tar.gz

echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                    DEPLOYMENT COMPLETE!                          ║"
echo "╠══════════════════════════════════════════════════════════════════╣"
echo "║  Frontend:  http://$VM_IP:3000                              ║"
echo "║  API:       http://$VM_IP:8000                              ║"
echo "║  API Docs:  http://$VM_IP:8000/docs                         ║"
echo "╚══════════════════════════════════════════════════════════════════╝"

