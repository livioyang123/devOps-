#!/bin/bash

# Script to delete RBAC manifests from Kubernetes cluster
# This script removes service accounts, roles, and role bindings for the DevOps K8s Platform

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== DevOps K8s Platform RBAC Cleanup ===${NC}"
echo ""

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}Error: kubectl is not installed or not in PATH${NC}"
    exit 1
fi

# Check if we can connect to the cluster
if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}Error: Cannot connect to Kubernetes cluster${NC}"
    echo "Please ensure your kubeconfig is properly configured"
    exit 1
fi

echo -e "${GREEN}✓ Connected to Kubernetes cluster${NC}"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Delete in reverse order of creation

# Delete role bindings
echo -e "${YELLOW}Deleting role bindings...${NC}"
kubectl delete -f "$SCRIPT_DIR/role-bindings.yaml" --ignore-not-found=true
echo -e "${GREEN}✓ Role bindings deleted${NC}"
echo ""

# Delete monitor role
echo -e "${YELLOW}Deleting monitor roles...${NC}"
kubectl delete -f "$SCRIPT_DIR/monitor-role.yaml" --ignore-not-found=true
echo -e "${GREEN}✓ Monitor roles deleted${NC}"
echo ""

# Delete deployer role
echo -e "${YELLOW}Deleting deployer roles...${NC}"
kubectl delete -f "$SCRIPT_DIR/deployer-role.yaml" --ignore-not-found=true
echo -e "${GREEN}✓ Deployer roles deleted${NC}"
echo ""

# Delete service accounts
echo -e "${YELLOW}Deleting service accounts...${NC}"
kubectl delete -f "$SCRIPT_DIR/service-account.yaml" --ignore-not-found=true
echo -e "${GREEN}✓ Service accounts deleted${NC}"
echo ""

echo -e "${GREEN}=== RBAC Cleanup Complete ===${NC}"
echo ""
