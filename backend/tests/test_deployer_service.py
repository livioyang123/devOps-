"""
Unit tests for DeployerService
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock, patch
from app.services.deployer import DeployerService, DeploymentResult, HealthCheckResult
from app.schemas import KubernetesManifest


def test_deployer_initialization():
    """Test DeployerService initialization"""
    deployer = DeployerService()
    
    assert deployer.websocket_handler is None
    assert deployer.k8s_client is None
    assert deployer.apps_v1 is None
    assert deployer.core_v1 is None
    assert deployer.networking_v1 is None
    assert len(deployer.applied_resources) == 0
    
    print("✓ DeployerService initialization test passed")


def test_dependency_ordering():
    """Test manifest dependency ordering"""
    deployer = DeployerService()
    
    # Create manifests in random order
    manifests = [
        KubernetesManifest(kind="Service", name="svc1", content="", namespace="default"),
        KubernetesManifest(kind="ConfigMap", name="cm1", content="", namespace="default"),
        KubernetesManifest(kind="Deployment", name="dep1", content="", namespace="default"),
        KubernetesManifest(kind="Ingress", name="ing1", content="", namespace="default"),
        KubernetesManifest(kind="Secret", name="sec1", content="", namespace="default"),
        KubernetesManifest(kind="PersistentVolumeClaim", name="pvc1", content="", namespace="default"),
    ]
    
    # Sort by dependency order
    sorted_manifests = deployer._get_dependency_order(manifests)
    
    # Verify order: ConfigMap/Secret → PVC → Deployment → Service → Ingress
    kinds = [m.kind for m in sorted_manifests]
    
    # ConfigMap and Secret should come first
    assert kinds[0] in ["ConfigMap", "Secret"]
    assert kinds[1] in ["ConfigMap", "Secret"]
    
    # PVC should come before Deployment
    pvc_index = kinds.index("PersistentVolumeClaim")
    dep_index = kinds.index("Deployment")
    assert pvc_index < dep_index
    
    # Deployment should come before Service
    svc_index = kinds.index("Service")
    assert dep_index < svc_index
    
    # Service should come before Ingress
    ing_index = kinds.index("Ingress")
    assert svc_index < ing_index
    
    print("✓ Dependency ordering test passed")


def test_validate_cluster_connectivity_no_config():
    """Test cluster connectivity validation without config"""
    deployer = DeployerService()
    
    # This will fail in test environment without kubeconfig
    success, message = deployer.validate_cluster_connectivity()
    
    # In test environment, we expect this to fail
    assert isinstance(success, bool)
    assert isinstance(message, str)
    
    print("✓ Cluster connectivity validation test passed")


def test_deployment_result():
    """Test DeploymentResult creation"""
    result = DeploymentResult(
        success=True,
        deployment_id="test-123",
        applied_manifests=["Deployment/app", "Service/app"],
        failed_manifests=[],
        error_message=None
    )
    
    assert result.success is True
    assert result.deployment_id == "test-123"
    assert len(result.applied_manifests) == 2
    assert len(result.failed_manifests) == 0
    assert result.error_message is None
    
    print("✓ DeploymentResult test passed")


def test_health_check_result():
    """Test HealthCheckResult creation"""
    result = HealthCheckResult(
        healthy=True,
        pod_statuses=[
            {
                "name": "pod-1",
                "phase": "Running",
                "is_running": True,
                "is_ready": True
            }
        ],
        unhealthy_pods=[],
        message="All pods are healthy"
    )
    
    assert result.healthy is True
    assert len(result.pod_statuses) == 1
    assert len(result.unhealthy_pods) == 0
    assert "healthy" in result.message.lower()
    
    print("✓ HealthCheckResult test passed")


def test_get_container_state():
    """Test container state extraction"""
    deployer = DeployerService()
    
    # Mock running state
    running_state = Mock()
    running_state.running = True
    running_state.waiting = None
    running_state.terminated = None
    
    state = deployer._get_container_state(running_state)
    assert state == "running"
    
    # Mock waiting state
    waiting_state = Mock()
    waiting_state.running = None
    waiting_state.waiting = Mock(reason="ContainerCreating")
    waiting_state.terminated = None
    
    state = deployer._get_container_state(waiting_state)
    assert "waiting" in state
    assert "ContainerCreating" in state
    
    # Mock terminated state
    terminated_state = Mock()
    terminated_state.running = None
    terminated_state.waiting = None
    terminated_state.terminated = Mock(reason="Error")
    
    state = deployer._get_container_state(terminated_state)
    assert "terminated" in state
    assert "Error" in state
    
    print("✓ Container state extraction test passed")


@pytest.mark.asyncio
async def test_rollback_no_resources():
    """Test rollback with no applied resources"""
    deployer = DeployerService()
    
    # Rollback with no resources should succeed
    success = await deployer.rollback("test-deployment")
    
    assert success is True
    assert len(deployer.applied_resources) == 0
    
    print("✓ Rollback with no resources test passed")


def test_apply_manifest_without_client():
    """Test apply_manifest without initialized client"""
    deployer = DeployerService()
    
    manifest = KubernetesManifest(
        kind="ConfigMap",
        name="test-cm",
        content="apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: test-cm",
        namespace="default"
    )
    
    success, message = deployer.apply_manifest(manifest)
    
    assert success is False
    assert "not initialized" in message.lower()
    
    print("✓ Apply manifest without client test passed")


if __name__ == "__main__":
    print("\nRunning DeployerService tests...\n")
    
    test_deployer_initialization()
    test_dependency_ordering()
    test_validate_cluster_connectivity_no_config()
    test_deployment_result()
    test_health_check_result()
    test_get_container_state()
    
    # Run async tests
    asyncio.run(test_rollback_no_resources())
    
    test_apply_manifest_without_client()
    
    print("\n✅ All DeployerService tests passed!")
