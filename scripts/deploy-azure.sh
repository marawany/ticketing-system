#!/bin/bash
# ============================================================================
# Turing NexusFlow - Azure VM Deployment Script
# ============================================================================
# This script deploys NexusFlow to an Azure VM using Azure CLI
#
# Prerequisites:
#   - Azure CLI installed and logged in (az login)
#   - SSH key pair available
#   - Sufficient Azure permissions
#
# Usage:
#   ./scripts/deploy-azure.sh [--resource-group RG_NAME] [--vm-name VM_NAME]
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log() { echo -e "${CYAN}[NEXUSFLOW]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ============================================================================
# Configuration
# ============================================================================
RESOURCE_GROUP="${RESOURCE_GROUP:-nexusflow-rg}"
LOCATION="${LOCATION:-eastus}"
VM_NAME="${VM_NAME:-nexusflow-vm}"
VM_SIZE="${VM_SIZE:-Standard_D4s_v3}"  # 4 vCPU, 16GB RAM
ADMIN_USER="${ADMIN_USER:-azureuser}"
SSH_KEY_PATH="${SSH_KEY_PATH:-~/.ssh/id_rsa.pub}"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --resource-group) RESOURCE_GROUP="$2"; shift 2 ;;
        --vm-name) VM_NAME="$2"; shift 2 ;;
        --location) LOCATION="$2"; shift 2 ;;
        --size) VM_SIZE="$2"; shift 2 ;;
        *) error "Unknown option: $1" ;;
    esac
done

log "Starting NexusFlow Azure Deployment..."
log "Resource Group: $RESOURCE_GROUP"
log "VM Name: $VM_NAME"
log "Location: $LOCATION"
log "VM Size: $VM_SIZE"

# ============================================================================
# Check Prerequisites
# ============================================================================
log "Checking prerequisites..."

if ! command -v az &> /dev/null; then
    error "Azure CLI not found. Install: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
fi

if ! az account show &> /dev/null; then
    error "Not logged into Azure. Run: az login"
fi

if [ ! -f "$SSH_KEY_PATH" ]; then
    warn "SSH key not found at $SSH_KEY_PATH"
    log "Generating new SSH key pair..."
    ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N "" -q
fi

success "Prerequisites checked"

# ============================================================================
# Create Resource Group
# ============================================================================
log "Creating resource group..."

az group create \
    --name "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --output none

success "Resource group created: $RESOURCE_GROUP"

# ============================================================================
# Create Virtual Network
# ============================================================================
log "Creating virtual network..."

az network vnet create \
    --resource-group "$RESOURCE_GROUP" \
    --name "${VM_NAME}-vnet" \
    --address-prefix "10.0.0.0/16" \
    --subnet-name "default" \
    --subnet-prefix "10.0.1.0/24" \
    --output none

success "Virtual network created"

# ============================================================================
# Create Network Security Group
# ============================================================================
log "Creating network security group..."

az network nsg create \
    --resource-group "$RESOURCE_GROUP" \
    --name "${VM_NAME}-nsg" \
    --output none

# Open required ports
declare -A PORTS=(
    ["SSH"]="22"
    ["HTTP"]="80"
    ["HTTPS"]="443"
    ["API"]="8000"
    ["MCP"]="8001"
    ["Frontend"]="3000"
    ["Phoenix"]="6006"
    ["Neo4j-HTTP"]="7474"
    ["Neo4j-Bolt"]="7687"
    ["Milvus"]="19530"
    ["Postgres"]="5432"
)

PRIORITY=100
for NAME in "${!PORTS[@]}"; do
    az network nsg rule create \
        --resource-group "$RESOURCE_GROUP" \
        --nsg-name "${VM_NAME}-nsg" \
        --name "Allow-${NAME}" \
        --priority $PRIORITY \
        --destination-port-ranges "${PORTS[$NAME]}" \
        --access Allow \
        --protocol Tcp \
        --output none
    PRIORITY=$((PRIORITY + 10))
done

success "Network security group configured"

# ============================================================================
# Create Public IP
# ============================================================================
log "Creating public IP address..."

az network public-ip create \
    --resource-group "$RESOURCE_GROUP" \
    --name "${VM_NAME}-ip" \
    --allocation-method Static \
    --sku Standard \
    --output none

PUBLIC_IP=$(az network public-ip show \
    --resource-group "$RESOURCE_GROUP" \
    --name "${VM_NAME}-ip" \
    --query ipAddress -o tsv)

success "Public IP: $PUBLIC_IP"

# ============================================================================
# Create Network Interface
# ============================================================================
log "Creating network interface..."

az network nic create \
    --resource-group "$RESOURCE_GROUP" \
    --name "${VM_NAME}-nic" \
    --vnet-name "${VM_NAME}-vnet" \
    --subnet "default" \
    --network-security-group "${VM_NAME}-nsg" \
    --public-ip-address "${VM_NAME}-ip" \
    --output none

success "Network interface created"

# ============================================================================
# Create Virtual Machine
# ============================================================================
log "Creating virtual machine (this may take a few minutes)..."

az vm create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$VM_NAME" \
    --nics "${VM_NAME}-nic" \
    --image "Ubuntu2204" \
    --size "$VM_SIZE" \
    --admin-username "$ADMIN_USER" \
    --ssh-key-values "$SSH_KEY_PATH" \
    --storage-sku Premium_LRS \
    --os-disk-size-gb 128 \
    --output none

success "Virtual machine created"

# ============================================================================
# Configure VM
# ============================================================================
log "Configuring VM with Docker and dependencies..."

# Create setup script
SETUP_SCRIPT=$(cat << 'SCRIPT'
#!/bin/bash
set -e

# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install Python 3.11 and uv
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3.11-dev
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install other dependencies
sudo apt-get install -y git nginx certbot python3-certbot-nginx

# Create app directory
sudo mkdir -p /opt/nexusflow
sudo chown $USER:$USER /opt/nexusflow

# Configure firewall
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 8000/tcp
sudo ufw allow 8001/tcp
sudo ufw allow 3000/tcp
sudo ufw allow 6006/tcp
sudo ufw --force enable

echo "VM setup complete!"
SCRIPT
)

# Run setup script on VM
echo "$SETUP_SCRIPT" | az vm run-command invoke \
    --resource-group "$RESOURCE_GROUP" \
    --name "$VM_NAME" \
    --command-id RunShellScript \
    --scripts @- \
    --output none

success "VM configured with Docker and dependencies"

# ============================================================================
# Output Connection Info
# ============================================================================
echo ""
echo "============================================================================"
echo -e "${GREEN}Deployment Complete!${NC}"
echo "============================================================================"
echo ""
echo "VM Public IP: $PUBLIC_IP"
echo ""
echo "SSH Connection:"
echo "  ssh $ADMIN_USER@$PUBLIC_IP"
echo ""
echo "Next Steps:"
echo "  1. Clone the repository on the VM:"
echo "     ssh $ADMIN_USER@$PUBLIC_IP"
echo "     cd /opt/nexusflow"
echo "     git clone <your-repo-url> ."
echo ""
echo "  2. Copy your .env file:"
echo "     scp .env $ADMIN_USER@$PUBLIC_IP:/opt/nexusflow/"
echo ""
echo "  3. Start the services:"
echo "     ssh $ADMIN_USER@$PUBLIC_IP 'cd /opt/nexusflow && docker compose --profile local-dbs up -d'"
echo ""
echo "  4. Access the application:"
echo "     Frontend: http://$PUBLIC_IP:3000"
echo "     API:      http://$PUBLIC_IP:8000"
echo "     Docs:     http://$PUBLIC_IP:8000/docs"
echo "     Phoenix:  http://$PUBLIC_IP:6006"
echo ""
echo "============================================================================"

# Save deployment info
echo "{
  \"resource_group\": \"$RESOURCE_GROUP\",
  \"vm_name\": \"$VM_NAME\",
  \"public_ip\": \"$PUBLIC_IP\",
  \"admin_user\": \"$ADMIN_USER\",
  \"location\": \"$LOCATION\",
  \"deployed_at\": \"$(date -Iseconds)\"
}" > deployment-info.json

log "Deployment info saved to deployment-info.json"

