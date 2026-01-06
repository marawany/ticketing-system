#!/bin/bash
# ============================================================================
# Turing NexusFlow - Azure VM Deployment Script
# ============================================================================
# This script deploys NexusFlow to an Azure VM using Azure CLI
# 
# Prerequisites:
#   - Azure CLI installed and logged in (az login)
#   - SSH key pair for VM access
#
# Usage:
#   ./scripts/deploy-azure.sh --resource-group nexusflow-rg --vm-name nexusflow-vm
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Default configuration
RESOURCE_GROUP=""
VM_NAME=""
LOCATION="eastus"
VM_SIZE="Standard_D4s_v3"  # 4 vCPU, 16GB RAM - good for ML workloads
ADMIN_USER="azureuser"
SSH_KEY_PATH="$HOME/.ssh/id_rsa"
IMAGE="Ubuntu2204"
DISK_SIZE=128  # GB

# Project info
PROJECT_NAME="nexusflow"
REPO_URL="https://github.com/YOUR_USERNAME/ticketing-system.git"

print_header() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════════╗"
    echo "║           TURING NEXUSFLOW - Azure Deployment                    ║"
    echo "╚══════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_step() {
    echo -e "${GREEN}[STEP]${NC} $1"
}

print_info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Deploy Turing NexusFlow to an Azure VM"
    echo ""
    echo "Required:"
    echo "  --resource-group NAME    Azure resource group name"
    echo "  --vm-name NAME          Virtual machine name"
    echo ""
    echo "Optional:"
    echo "  --location REGION       Azure region (default: $LOCATION)"
    echo "  --vm-size SIZE          VM size (default: $VM_SIZE)"
    echo "  --admin-user USER       Admin username (default: $ADMIN_USER)"
    echo "  --ssh-key PATH          SSH key path (default: $SSH_KEY_PATH)"
    echo "  --disk-size GB          OS disk size in GB (default: $DISK_SIZE)"
    echo "  --help                  Show this help message"
    echo ""
    echo "Example:"
    echo "  $0 --resource-group nexusflow-rg --vm-name nexusflow-prod"
    echo ""
    echo "VM Size Recommendations:"
    echo "  Development:  Standard_B2s     (2 vCPU, 4GB RAM)   ~\$30/month"
    echo "  Production:   Standard_D4s_v3  (4 vCPU, 16GB RAM)  ~\$140/month"
    echo "  High Load:    Standard_D8s_v3  (8 vCPU, 32GB RAM)  ~\$280/month"
}

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --resource-group) RESOURCE_GROUP="$2"; shift ;;
        --vm-name) VM_NAME="$2"; shift ;;
        --location) LOCATION="$2"; shift ;;
        --vm-size) VM_SIZE="$2"; shift ;;
        --admin-user) ADMIN_USER="$2"; shift ;;
        --ssh-key) SSH_KEY_PATH="$2"; shift ;;
        --disk-size) DISK_SIZE="$2"; shift ;;
        --help) show_help; exit 0 ;;
        *) print_error "Unknown parameter: $1"; show_help; exit 1 ;;
    esac
    shift
done

# Validate required arguments
if [ -z "$RESOURCE_GROUP" ] || [ -z "$VM_NAME" ]; then
    print_error "Missing required arguments"
    show_help
    exit 1
fi

# Validate SSH key exists
if [ ! -f "$SSH_KEY_PATH" ]; then
    print_warning "SSH key not found at $SSH_KEY_PATH"
    print_info "Generating new SSH key pair..."
    ssh-keygen -t rsa -b 4096 -f "$SSH_KEY_PATH" -N "" -q
    print_info "SSH key generated at $SSH_KEY_PATH"
fi

print_header

echo "Configuration:"
echo "  Resource Group: $RESOURCE_GROUP"
echo "  VM Name:        $VM_NAME"
echo "  Location:       $LOCATION"
echo "  VM Size:        $VM_SIZE"
echo "  Admin User:     $ADMIN_USER"
echo "  SSH Key:        $SSH_KEY_PATH"
echo "  Disk Size:      ${DISK_SIZE}GB"
echo ""

# Check Azure CLI
print_step "Checking Azure CLI..."
if ! command -v az &> /dev/null; then
    print_error "Azure CLI not found. Please install it: https://docs.microsoft.com/cli/azure/install-azure-cli"
    exit 1
fi

# Check Azure login
print_step "Checking Azure authentication..."
if ! az account show &> /dev/null; then
    print_info "Not logged in. Starting Azure login..."
    az login
fi

SUBSCRIPTION=$(az account show --query name -o tsv)
print_info "Using subscription: $SUBSCRIPTION"

# Create resource group
print_step "Creating resource group..."
az group create \
    --name "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --output none

# Create NSG with required ports
print_step "Creating network security group..."
NSG_NAME="${VM_NAME}-nsg"
az network nsg create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$NSG_NAME" \
    --location "$LOCATION" \
    --output none

# Add NSG rules
print_info "Adding firewall rules..."
for rule in "SSH:22:1000" "HTTP:80:1001" "HTTPS:443:1002" "API:8000:1003" "Frontend:3000:1004" "Phoenix:6006:1005" "Neo4j:7687:1006"; do
    IFS=':' read -r name port priority <<< "$rule"
    az network nsg rule create \
        --resource-group "$RESOURCE_GROUP" \
        --nsg-name "$NSG_NAME" \
        --name "Allow$name" \
        --priority "$priority" \
        --destination-port-ranges "$port" \
        --access Allow \
        --protocol Tcp \
        --output none
done

# Create VM
print_step "Creating virtual machine (this may take a few minutes)..."
az vm create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$VM_NAME" \
    --location "$LOCATION" \
    --image "$IMAGE" \
    --size "$VM_SIZE" \
    --admin-username "$ADMIN_USER" \
    --ssh-key-values "${SSH_KEY_PATH}.pub" \
    --os-disk-size-gb "$DISK_SIZE" \
    --nsg "$NSG_NAME" \
    --public-ip-sku Standard \
    --output none

# Get public IP
print_step "Getting VM public IP..."
PUBLIC_IP=$(az vm show \
    --resource-group "$RESOURCE_GROUP" \
    --name "$VM_NAME" \
    --show-details \
    --query publicIps \
    -o tsv)

print_info "VM Public IP: $PUBLIC_IP"

# Wait for VM to be ready
print_step "Waiting for VM to be ready..."
sleep 30

# Create setup script to run on VM
print_step "Creating VM setup script..."
SETUP_SCRIPT=$(cat << 'VMSETUP'
#!/bin/bash
set -e

echo "=== NexusFlow VM Setup ==="

# Update system
echo "Updating system packages..."
sudo apt-get update -y
sudo apt-get upgrade -y

# Install Docker
echo "Installing Docker..."
sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update -y
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker $USER

# Install Node.js 20
echo "Installing Node.js..."
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install Python 3.11 and uv
echo "Installing Python and uv..."
sudo apt-get install -y python3.11 python3.11-venv python3-pip
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

# Install Git
sudo apt-get install -y git

# Create app directory
echo "Setting up application directory..."
sudo mkdir -p /opt/nexusflow
sudo chown -R $USER:$USER /opt/nexusflow

echo "=== VM Setup Complete ==="
VMSETUP
)

# Copy and run setup script on VM
print_step "Running setup script on VM..."
echo "$SETUP_SCRIPT" | ssh -i "$SSH_KEY_PATH" -o StrictHostKeyChecking=no "$ADMIN_USER@$PUBLIC_IP" "cat > /tmp/setup.sh && chmod +x /tmp/setup.sh && /tmp/setup.sh"

# Create deployment script
print_step "Creating deployment script..."
DEPLOY_SCRIPT=$(cat << 'DEPLOYSCRIPT'
#!/bin/bash
set -e

cd /opt/nexusflow

# Pull latest code (assumes git repo is set up)
if [ -d ".git" ]; then
    echo "Pulling latest code..."
    git pull
fi

# Setup Python environment
echo "Setting up Python environment..."
export PATH="$HOME/.local/bin:$PATH"
uv venv
source .venv/bin/activate
uv pip install -e .

# Setup frontend
echo "Setting up frontend..."
cd frontend
npm install
npm run build
cd ..

# Create production .env if not exists
if [ ! -f ".env" ]; then
    echo "Creating production .env file..."
    cat > .env << 'ENVFILE'
# Production Environment
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Authentication - ENABLED for production
ENABLE_AUTH=true
ENABLE_TEST_AUTH_BYPASS=false
JWT_SECRET_KEY=CHANGE_THIS_TO_A_SECURE_RANDOM_STRING

# Database
DATABASE_URL=postgresql+asyncpg://nexusflow:nexusflow_password@localhost:5432/nexusflow

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=nexusflow_password

# Milvus
MILVUS_HOST=localhost
MILVUS_PORT=19530

# Phoenix
PHOENIX_HOST=localhost
PHOENIX_PORT=6006

# OpenAI
OPENAI_API_KEY=your_openai_api_key_here

# Admin credentials
ADMIN_EMAIL=marawan.y@turing.com
ADMIN_PASSWORD=CHANGE_THIS_ADMIN_PASSWORD
ENVFILE
    echo "IMPORTANT: Edit /opt/nexusflow/.env with your actual secrets!"
fi

# Start services with Docker Compose
echo "Starting Docker services..."
docker compose up -d

# Wait for services
echo "Waiting for services to start..."
sleep 30

# Initialize database
echo "Initializing database..."
source .venv/bin/activate
python scripts/setup_databases.py || true

# Start application services
echo "Starting application..."
mkdir -p logs
nohup uvicorn nexusflow.api.main:app --host 0.0.0.0 --port 8000 > logs/api.log 2>&1 &
cd frontend && nohup npm start > ../logs/frontend.log 2>&1 &

echo "=== Deployment Complete ==="
echo "API: http://$(curl -s ifconfig.me):8000"
echo "Frontend: http://$(curl -s ifconfig.me):3000"
DEPLOYSCRIPT
)

# Save deploy script to VM
echo "$DEPLOY_SCRIPT" | ssh -i "$SSH_KEY_PATH" "$ADMIN_USER@$PUBLIC_IP" "cat > /opt/nexusflow/deploy.sh && chmod +x /opt/nexusflow/deploy.sh"

# Print completion message
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              DEPLOYMENT INFRASTRUCTURE READY!                    ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "VM Details:"
echo "  Public IP:     $PUBLIC_IP"
echo "  SSH Command:   ssh -i $SSH_KEY_PATH $ADMIN_USER@$PUBLIC_IP"
echo ""
echo "Next Steps:"
echo "  1. SSH into the VM:"
echo "     ssh -i $SSH_KEY_PATH $ADMIN_USER@$PUBLIC_IP"
echo ""
echo "  2. Clone your repository:"
echo "     cd /opt/nexusflow"
echo "     git clone YOUR_REPO_URL ."
echo ""
echo "  3. Copy your .env file with secrets"
echo ""
echo "  4. Run deployment:"
echo "     ./deploy.sh"
echo ""
echo "  5. Access the application:"
echo "     Frontend: http://$PUBLIC_IP:3000"
echo "     API:      http://$PUBLIC_IP:8000"
echo "     API Docs: http://$PUBLIC_IP:8000/docs"
echo ""
echo "To delete this deployment:"
echo "  az group delete --name $RESOURCE_GROUP --yes --no-wait"
