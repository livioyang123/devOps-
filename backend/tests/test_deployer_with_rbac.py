"""
Test DeployerService with RBAC service account authentication

This test verifies that the DeployerService can authenticate using
service account tokens and respects RBAC permissions.
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from app.services.deployer import DeployerService
from app.schemas import KubernetesManifest


class TestDeployerWithRBAC:
    """Test DeployerService with RBAC authentication"""
    
    def test_deployer_initialization_with_token(self):
        """Test that DeployerService can be initialized with a service account token"""
        token = "test-service-account-token"
        deployer = DeployerService(service_account_token=token)
        
        assert deployer.service_account_token == token
        assert deployer.k8s_client is None  # Not initialized until validate_cluster_connectivity
    
    def test_deployer_initialization_without_token(self):
        """Test that DeployerService can be initialized without a token"""
        deployer = DeployerService()
        
        assert deployer.service_account_token is None
    
    @patch('app.services.deployer.client.ApiClient')
    @patch('app.services.deployer.client.CoreV1Api')
    def test_validate_cluster_with_token_in_config(self, mock_core_v1, mock_api_client):
        """Test cluster validation with token in cluster_config"""
        # Setup mocks
        mock_client_instance = MagicMock()
        mock_api_client.return_value = mock_client_instance
        
        mock_core_instance = MagicMock()
        mock_core_v1.return_value = mock_core_instance
        
        # Mock list_namespace to return successfully
        mock_namespace_list = MagicMock()
        mock_core_instance.list_namespace.return_value = mock_namespace_list
        
        # Create deployer
        deployer = DeployerService()
        
        # Cluster config with token
        cluster_config = {
            'host': 'https://test-cluster.example.com',
            'token': 'test-token-from-config',
            'verify_ssl': True
        }
        
        # Validate connectivity
        with patch('app.services.deployer.client.Configuration') as mock_config:
            mock_config_instance = MagicMock()
            mock_config.return_value = mock_config_instance
            
            success, message = deployer.validate_cluster_connectivity(cluster_config)
        
        assert success is True
        assert "Successfully connected" in message
        
        # Verify configuration was set up correctly
        assert mock_config_instance.host == 'https://test-cluster.example.com'
        assert mock_config_instance.api_key == {"authorization": "Bearer test-token-from-config"}
        assert mock_config_instance.verify_ssl is True
    
    @patch('app.services.deployer.client.ApiClient')
    @patch('app.services.deployer.client.CoreV1Api')
    def test_validate_cluster_with_instance_token(self, mock_core_v1, mock_api_client):
        """Test cluster validation with instance service account token"""
        # Setup mocks
        mock_client_instance = MagicMock()
        mock_api_client.return_value = mock_client_instance
        
        mock_core_instance = MagicMock()
        mock_core_v1.return_value = mock_core_instance
        
        # Mock list_namespace to return successfully
        mock_namespace_list = MagicMock()
        mock_core_instance.list_namespace.return_value = mock_namespace_list
        
        # Create deployer with instance token
        deployer = DeployerService(service_account_token='instance-token')
        
        # Cluster config without token (should use instance token)
        cluster_config = {
            'host': 'https://test-cluster.example.com',
            'verify_ssl': False
        }
        
        # Validate connectivity
        with patch('app.services.deployer.client.Configuration') as mock_config:
            mock_config_instance = MagicMock()
            mock_config.return_value = mock_config_instance
            
            success, message = deployer.validate_cluster_connectivity(cluster_config)
        
        assert success is True
        assert "Successfully connected" in message
        
        # Verify configuration was set up with instance token
        assert mock_config_instance.host == 'https://test-cluster.example.com'
        assert mock_config_instance.api_key == {"authorization": "Bearer instance-token"}
        assert mock_config_instance.verify_ssl is False
    
    @patch('app.services.deployer.config.load_kube_config')
    @patch('app.services.deployer.client.ApiClient')
    @patch('app.services.deployer.client.CoreV1Api')
    def test_validate_cluster_fallback_to_kubeconfig(
        self, mock_core_v1, mock_api_client, mock_load_kube_config
    ):
        """Test cluster validation falls back to kubeconfig when no token provided"""
        # Setup mocks
        mock_client_instance = MagicMock()
        mock_api_client.return_value = mock_client_instance
        
        mock_core_instance = MagicMock()
        mock_core_v1.return_value = mock_core_instance
        
        # Mock list_namespace to return successfully
        mock_namespace_list = MagicMock()
        mock_core_instance.list_namespace.return_value = mock_namespace_list
        
        # Create deployer without token
        deployer = DeployerService()
        
        # Validate connectivity without cluster config
        success, message = deployer.validate_cluster_connectivity()
        
        assert success is True
        assert "Successfully connected" in message
        
        # Verify kubeconfig was loaded
        mock_load_kube_config.assert_called_once()
    
    def test_deployer_token_priority(self):
        """Test that cluster_config token takes priority over instance token"""
        deployer = DeployerService(service_account_token='instance-token')
        
        cluster_config = {
            'token': 'config-token',
            'host': 'https://test.example.com'
        }
        
        with patch('app.services.deployer.client.Configuration') as mock_config, \
             patch('app.services.deployer.client.ApiClient'), \
             patch('app.services.deployer.client.CoreV1Api') as mock_core_v1:
            
            mock_config_instance = MagicMock()
            mock_config.return_value = mock_config_instance
            
            mock_core_instance = MagicMock()
            mock_core_v1.return_value = mock_core_instance
            mock_core_instance.list_namespace.return_value = MagicMock()
            
            deployer.validate_cluster_connectivity(cluster_config)
            
            # Verify config-token was used, not instance-token
            assert mock_config_instance.api_key == {"authorization": "Bearer config-token"}
    
    def test_deployer_ssl_verification_default(self):
        """Test that SSL verification defaults to True"""
        deployer = DeployerService(service_account_token='test-token')
        
        cluster_config = {
            'host': 'https://test.example.com'
        }
        
        with patch('app.services.deployer.client.Configuration') as mock_config, \
             patch('app.services.deployer.client.ApiClient'), \
             patch('app.services.deployer.client.CoreV1Api') as mock_core_v1:
            
            mock_config_instance = MagicMock()
            mock_config.return_value = mock_config_instance
            
            mock_core_instance = MagicMock()
            mock_core_v1.return_value = mock_core_instance
            mock_core_instance.list_namespace.return_value = MagicMock()
            
            deployer.validate_cluster_connectivity(cluster_config)
            
            # Verify SSL verification is True by default
            assert mock_config_instance.verify_ssl is True
    
    @patch('app.services.deployer.client.ApiClient')
    @patch('app.services.deployer.client.CoreV1Api')
    def test_authentication_failure_with_invalid_token(self, mock_core_v1, mock_api_client):
        """Test that authentication fails with invalid token"""
        from kubernetes.client.rest import ApiException
        
        # Setup mocks
        mock_client_instance = MagicMock()
        mock_api_client.return_value = mock_client_instance
        
        mock_core_instance = MagicMock()
        mock_core_v1.return_value = mock_core_instance
        
        # Mock list_namespace to raise authentication error
        mock_core_instance.list_namespace.side_effect = ApiException(
            status=401,
            reason="Unauthorized"
        )
        
        # Create deployer with invalid token
        deployer = DeployerService(service_account_token='invalid-token')
        
        cluster_config = {
            'host': 'https://test-cluster.example.com'
        }
        
        # Validate connectivity
        with patch('app.services.deployer.client.Configuration') as mock_config:
            mock_config_instance = MagicMock()
            mock_config.return_value = mock_config_instance
            
            success, message = deployer.validate_cluster_connectivity(cluster_config)
        
        assert success is False
        assert "401" in message or "Unauthorized" in message
    
    def test_deployer_preserves_websocket_handler(self):
        """Test that websocket handler is preserved when using service account"""
        mock_websocket = Mock()
        token = "test-token"
        
        deployer = DeployerService(
            websocket_handler=mock_websocket,
            service_account_token=token
        )
        
        assert deployer.websocket_handler == mock_websocket
        assert deployer.service_account_token == token


class TestRBACIntegration:
    """Integration tests for RBAC with real cluster (if available)"""
    
    @pytest.fixture
    def skip_if_no_cluster(self):
        """Skip test if no Kubernetes cluster is available"""
        import subprocess
        try:
            result = subprocess.run(
                ["kubectl", "cluster-info"],
                capture_output=True,
                timeout=5
            )
            if result.returncode != 0:
                pytest.skip("No Kubernetes cluster available")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("kubectl not available or cluster not accessible")
    
    @pytest.fixture
    def deployer_token(self):
        """Get deployer service account token (if available)"""
        import subprocess
        try:
            # Try to get token for deployer service account
            result = subprocess.run(
                [
                    "kubectl", "create", "token",
                    "devops-platform-deployer",
                    "-n", "default",
                    "--duration=1h"
                ],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                pytest.skip("Deployer service account not found")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pytest.skip("Cannot get service account token")
    
    def test_deployer_with_real_token(self, skip_if_no_cluster, deployer_token):
        """Test deployer with real service account token"""
        deployer = DeployerService(service_account_token=deployer_token)
        
        # Try to connect to cluster
        success, message = deployer.validate_cluster_connectivity()
        
        assert success is True, f"Failed to connect: {message}"
        assert deployer.k8s_client is not None
        assert deployer.core_v1 is not None
        assert deployer.apps_v1 is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
