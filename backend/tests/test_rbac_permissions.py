"""
Test RBAC permissions for Kubernetes service accounts

This test verifies that the service accounts have the correct permissions
according to the principle of least privilege.
"""

import subprocess
import pytest
from typing import List, Tuple


class TestRBACPermissions:
    """Test RBAC permissions for DevOps Platform service accounts"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Check if kubectl is available and cluster is accessible"""
        try:
            result = subprocess.run(
                ["kubectl", "cluster-info"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                pytest.skip("Kubernetes cluster not accessible")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("kubectl not available or cluster not accessible")
    
    def check_permission(
        self,
        service_account: str,
        verb: str,
        resource: str,
        namespace: str = "default"
    ) -> bool:
        """
        Check if a service account has a specific permission
        
        Args:
            service_account: Name of the service account
            verb: Kubernetes verb (get, list, create, update, delete, etc.)
            resource: Kubernetes resource type
            namespace: Namespace to check (default: default)
            
        Returns:
            True if permission is granted, False otherwise
        """
        try:
            result = subprocess.run(
                [
                    "kubectl", "auth", "can-i", verb, resource,
                    f"--as=system:serviceaccount:{namespace}:{service_account}",
                    f"-n={namespace}"
                ],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip().lower() == "yes"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def test_deployer_service_account_exists(self):
        """Test that the deployer service account exists"""
        result = subprocess.run(
            ["kubectl", "get", "serviceaccount", "devops-platform-deployer", "-n", "default"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "Deployer service account does not exist"
    
    def test_monitor_service_account_exists(self):
        """Test that the monitor service account exists"""
        result = subprocess.run(
            ["kubectl", "get", "serviceaccount", "devops-platform-monitor", "-n", "default"],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0, "Monitor service account does not exist"
    
    # Deployer Permissions Tests
    
    def test_deployer_can_create_deployments(self):
        """Test that deployer can create deployments"""
        assert self.check_permission(
            "devops-platform-deployer", "create", "deployments"
        ), "Deployer should be able to create deployments"
    
    def test_deployer_can_update_deployments(self):
        """Test that deployer can update deployments"""
        assert self.check_permission(
            "devops-platform-deployer", "update", "deployments"
        ), "Deployer should be able to update deployments"
    
    def test_deployer_can_delete_deployments(self):
        """Test that deployer can delete deployments"""
        assert self.check_permission(
            "devops-platform-deployer", "delete", "deployments"
        ), "Deployer should be able to delete deployments"
    
    def test_deployer_can_create_services(self):
        """Test that deployer can create services"""
        assert self.check_permission(
            "devops-platform-deployer", "create", "services"
        ), "Deployer should be able to create services"
    
    def test_deployer_can_create_configmaps(self):
        """Test that deployer can create configmaps"""
        assert self.check_permission(
            "devops-platform-deployer", "create", "configmaps"
        ), "Deployer should be able to create configmaps"
    
    def test_deployer_can_create_secrets(self):
        """Test that deployer can create secrets"""
        assert self.check_permission(
            "devops-platform-deployer", "create", "secrets"
        ), "Deployer should be able to create secrets"
    
    def test_deployer_can_create_pvcs(self):
        """Test that deployer can create PVCs"""
        assert self.check_permission(
            "devops-platform-deployer", "create", "persistentvolumeclaims"
        ), "Deployer should be able to create PVCs"
    
    def test_deployer_can_get_pods(self):
        """Test that deployer can get pods (for health checks)"""
        assert self.check_permission(
            "devops-platform-deployer", "get", "pods"
        ), "Deployer should be able to get pods for health checks"
    
    def test_deployer_can_list_pods(self):
        """Test that deployer can list pods"""
        assert self.check_permission(
            "devops-platform-deployer", "list", "pods"
        ), "Deployer should be able to list pods"
    
    def test_deployer_cannot_delete_pods(self):
        """Test that deployer cannot delete pods directly"""
        assert not self.check_permission(
            "devops-platform-deployer", "delete", "pods"
        ), "Deployer should NOT be able to delete pods directly"
    
    def test_deployer_can_get_events(self):
        """Test that deployer can get events (for health checks)"""
        assert self.check_permission(
            "devops-platform-deployer", "get", "events"
        ), "Deployer should be able to get events for health checks"
    
    def test_deployer_can_list_namespaces(self):
        """Test that deployer can list namespaces"""
        # This is a cluster-scoped permission
        result = subprocess.run(
            [
                "kubectl", "auth", "can-i", "list", "namespaces",
                "--as=system:serviceaccount:default:devops-platform-deployer"
            ],
            capture_output=True,
            text=True
        )
        assert result.stdout.strip().lower() == "yes", \
            "Deployer should be able to list namespaces"
    
    # Monitor Permissions Tests
    
    def test_monitor_can_get_pods(self):
        """Test that monitor can get pods"""
        assert self.check_permission(
            "devops-platform-monitor", "get", "pods"
        ), "Monitor should be able to get pods"
    
    def test_monitor_can_list_pods(self):
        """Test that monitor can list pods"""
        assert self.check_permission(
            "devops-platform-monitor", "list", "pods"
        ), "Monitor should be able to list pods"
    
    def test_monitor_can_get_pod_logs(self):
        """Test that monitor can get pod logs"""
        assert self.check_permission(
            "devops-platform-monitor", "get", "pods/log"
        ), "Monitor should be able to get pod logs"
    
    def test_monitor_can_get_deployments(self):
        """Test that monitor can get deployments"""
        assert self.check_permission(
            "devops-platform-monitor", "get", "deployments"
        ), "Monitor should be able to get deployments"
    
    def test_monitor_can_get_services(self):
        """Test that monitor can get services"""
        assert self.check_permission(
            "devops-platform-monitor", "get", "services"
        ), "Monitor should be able to get services"
    
    def test_monitor_can_get_events(self):
        """Test that monitor can get events"""
        assert self.check_permission(
            "devops-platform-monitor", "get", "events"
        ), "Monitor should be able to get events"
    
    def test_monitor_cannot_create_deployments(self):
        """Test that monitor cannot create deployments"""
        assert not self.check_permission(
            "devops-platform-monitor", "create", "deployments"
        ), "Monitor should NOT be able to create deployments"
    
    def test_monitor_cannot_delete_deployments(self):
        """Test that monitor cannot delete deployments"""
        assert not self.check_permission(
            "devops-platform-monitor", "delete", "deployments"
        ), "Monitor should NOT be able to delete deployments"
    
    def test_monitor_cannot_create_services(self):
        """Test that monitor cannot create services"""
        assert not self.check_permission(
            "devops-platform-monitor", "create", "services"
        ), "Monitor should NOT be able to create services"
    
    def test_monitor_cannot_delete_pods(self):
        """Test that monitor cannot delete pods"""
        assert not self.check_permission(
            "devops-platform-monitor", "delete", "pods"
        ), "Monitor should NOT be able to delete pods"
    
    def test_monitor_cannot_create_secrets(self):
        """Test that monitor cannot create secrets"""
        assert not self.check_permission(
            "devops-platform-monitor", "create", "secrets"
        ), "Monitor should NOT be able to create secrets"
    
    # Cluster-scoped permissions
    
    def test_monitor_can_list_nodes(self):
        """Test that monitor can list nodes"""
        result = subprocess.run(
            [
                "kubectl", "auth", "can-i", "list", "nodes",
                "--as=system:serviceaccount:default:devops-platform-monitor"
            ],
            capture_output=True,
            text=True
        )
        assert result.stdout.strip().lower() == "yes", \
            "Monitor should be able to list nodes"
    
    def test_deployer_can_list_nodes(self):
        """Test that deployer can list nodes"""
        result = subprocess.run(
            [
                "kubectl", "auth", "can-i", "list", "nodes",
                "--as=system:serviceaccount:default:devops-platform-deployer"
            ],
            capture_output=True,
            text=True
        )
        assert result.stdout.strip().lower() == "yes", \
            "Deployer should be able to list nodes"
    
    # Negative tests - ensure neither has cluster-admin
    
    def test_deployer_cannot_delete_namespaces(self):
        """Test that deployer cannot delete namespaces"""
        result = subprocess.run(
            [
                "kubectl", "auth", "can-i", "delete", "namespaces",
                "--as=system:serviceaccount:default:devops-platform-deployer"
            ],
            capture_output=True,
            text=True
        )
        assert result.stdout.strip().lower() == "no", \
            "Deployer should NOT be able to delete namespaces"
    
    def test_monitor_cannot_delete_namespaces(self):
        """Test that monitor cannot delete namespaces"""
        result = subprocess.run(
            [
                "kubectl", "auth", "can-i", "delete", "namespaces",
                "--as=system:serviceaccount:default:devops-platform-monitor"
            ],
            capture_output=True,
            text=True
        )
        assert result.stdout.strip().lower() == "no", \
            "Monitor should NOT be able to delete namespaces"
    
    def test_deployer_cannot_create_clusterroles(self):
        """Test that deployer cannot create cluster roles"""
        result = subprocess.run(
            [
                "kubectl", "auth", "can-i", "create", "clusterroles",
                "--as=system:serviceaccount:default:devops-platform-deployer"
            ],
            capture_output=True,
            text=True
        )
        assert result.stdout.strip().lower() == "no", \
            "Deployer should NOT be able to create cluster roles"
    
    def test_monitor_cannot_create_clusterroles(self):
        """Test that monitor cannot create cluster roles"""
        result = subprocess.run(
            [
                "kubectl", "auth", "can-i", "create", "clusterroles",
                "--as=system:serviceaccount:default:devops-platform-monitor"
            ],
            capture_output=True,
            text=True
        )
        assert result.stdout.strip().lower() == "no", \
            "Monitor should NOT be able to create cluster roles"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
