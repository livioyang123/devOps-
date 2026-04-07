#!/bin/bash

# Script to apply RBAC manifests to Kubernetes cluster
# This script creates service accounts, roles, and role bindings for the DevOps K8s Platform

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== DevOps K8s Platform RBAC Setup ===${NC}"
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

# Apply service accounts
echo -e "${YELLOW}Creating service accounts...${NC}"
kubectl apply -f "$SCRIPT_DIR/service-account.yaml"
echo -e "${GREEN}✓ Service accounts created${NC}"
echo ""

# Apply deployer role
echo -e "${YELLOW}Creating deployer roles...${NC}"
kubectl apply -f "$SCRIPT_DIR/deployer-role.yaml"
echo -e "${GREEN}✓ Deployer roles created${NC}"
echo ""

# Apply monitor role
echo -e "${YELLOW}Creating monitor roles...${NC}"
kubectl apply -f "$SCRIPT_DIR/monitor-role.yaml"
echo -e "${GREEN}✓ Monitor roles created${NC}"
echo ""

# Apply role bindings
echo -e "${YELLOW}Creating role bindings...${NC}"
kubectl apply -f "$SCRIPT_DIR/role-bindings.yaml"
echo -e "${GREEN}✓ Role bindings created${NC}"
echo ""

# Verify installation
echo -e "${YELLOW}Verifying installation...${NC}"
echo ""

echo "Service Accounts:"
kubectl get serviceaccounts -n default | grep devops-platform || echo "  No service accounts found"
echo ""

echo "Roles:"
kubectl get roles -n default | grep devops-platform || echo "  No roles found"
echo ""

echo "ClusterRoles:"
kubectl get clusterroles | grep devops-platform || echo "  No cluster roles found"
echo ""

echo "RoleBindings:"
kubectl get rolebindings -n default | grep devops-platform || echo "  No role bindings found"
echo ""

echo "ClusterRoleBindings:"
kubectl get clusterrolebindings | grep devops-platform || echo "  No cluster role bindings found"
echo ""

echo -e "${GREEN}=== RBAC Setup Complete ===${NC}"
echo ""
echo "To get a service account token for the deployer, run:"
echo -e "${YELLOW}kubectl create token devops-platform-deployer -n default --duration=8760h${NC}"
echo ""
echo "To test deployer permissions, run:"
echo -e "${YELLOW}kubectl auth can-i create deployments --as=system:serviceaccount:default:devops-platform-deployer -n default${NC}"
echo ""
