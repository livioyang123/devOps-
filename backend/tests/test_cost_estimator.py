"""
Test suite for CostEstimationService
"""

import pytest
from datetime import datetime

from app.services.cost_estimator import CostEstimationService
from app.schemas import KubernetesManifest, ResourceRequirements


# Sample Kubernetes manifests for testing
SAMPLE_DEPLOYMENT = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-deployment
  namespace: default
spec:
  replicas: 3
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
      - name: nginx
        image: nginx:latest
        resources:
          requests:
            cpu: "500m"
            memory: "512Mi"
          limits:
            cpu: "1"
            memory: "1Gi"
"""

SAMPLE_PVC = """
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data-pvc
  namespace: default
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
"""

SAMPLE_SERVICE = """
apiVersion: v1
kind: Service
metadata:
  name: web-service
  namespace: default
spec:
  selector:
    app: web
  ports:
    - protocol: TCP
      port: 80
      targetPort: 8080
  type: LoadBalancer
"""


def test_cost_estimator_initialization():
    """Test that CostEstimationService can be initialized"""
    service = CostEstimationService()
    
    assert service is not None
    assert "gke" in service.PRICING
    assert "eks" in service.PRICING
    assert "aks" in service.PRICING


def test_parse_cpu_cores():
    """Test CPU parsing from various formats"""
    service = CostEstimationService()
    
    # Test cores
    assert service._parse_cpu("1") == 1.0
    assert service._parse_cpu("0.5") == 0.5
    assert service._parse_cpu("2") == 2.0
    
    # Test millicores
    assert service._parse_cpu("500m") == 0.5
    assert service._parse_cpu("1000m") == 1.0
    assert service._parse_cpu("250m") == 0.25
    
    # Test edge cases
    assert service._parse_cpu("0") == 0.0
    assert service._parse_cpu("") == 0.0


def test_parse_memory_gb():
    """Test memory parsing from various formats"""
    service = CostEstimationService()
    
    # Test Gi (gibibytes)
    assert service._parse_memory("1Gi") == 1.0
    assert service._parse_memory("2Gi") == 2.0
    assert service._parse_memory("0.5Gi") == 0.5
    
    # Test Mi (mebibytes)
    assert service._parse_memory("512Mi") == 0.5
    assert service._parse_memory("1024Mi") == 1.0
    assert service._parse_memory("2048Mi") == 2.0
    
    # Test G (gigabytes)
    assert service._parse_memory("1G") == 1.0
    assert service._parse_memory("2G") == 2.0
    
    # Test M (megabytes)
    assert service._parse_memory("1024M") == 1.0
    
    # Test edge cases
    assert service._parse_memory("0") == 0.0
    assert service._parse_memory("") == 0.0


def test_parse_storage_gb():
    """Test storage parsing (same as memory)"""
    service = CostEstimationService()
    
    assert service._parse_storage("10Gi") == 10.0
    assert service._parse_storage("5Gi") == 5.0
    assert service._parse_storage("1024Mi") == 1.0


def test_extract_deployment_resources():
    """Test extracting resources from a Deployment manifest"""
    service = CostEstimationService()
    
    import yaml
    manifest_dict = yaml.safe_load(SAMPLE_DEPLOYMENT)
    
    cpu, memory, pods = service._extract_deployment_resources(manifest_dict)
    
    # 3 replicas * 0.5 CPU = 1.5 cores
    assert cpu == 1.5
    
    # 3 replicas * 0.5 GB = 1.5 GB
    assert memory == 1.5
    
    # 3 replicas
    assert pods == 3


def test_extract_storage_resources():
    """Test extracting storage from a PVC manifest"""
    service = CostEstimationService()
    
    import yaml
    manifest_dict = yaml.safe_load(SAMPLE_PVC)
    
    storage = service._extract_storage_resources(manifest_dict)
    
    # 10Gi storage
    assert storage == 10.0


def test_calculate_resources_from_manifests():
    """Test calculating total resources from multiple manifests"""
    service = CostEstimationService()
    
    manifests = [
        KubernetesManifest(
            kind="Deployment",
            name="web-deployment",
            content=SAMPLE_DEPLOYMENT,
            namespace="default"
        ),
        KubernetesManifest(
            kind="PersistentVolumeClaim",
            name="data-pvc",
            content=SAMPLE_PVC,
            namespace="default"
        ),
        KubernetesManifest(
            kind="Service",
            name="web-service",
            content=SAMPLE_SERVICE,
            namespace="default"
        )
    ]
    
    resources = service.calculate_resources(manifests)
    
    assert resources.cpu_cores == 1.5  # 3 replicas * 0.5 CPU
    assert resources.memory_gb == 1.5  # 3 replicas * 0.5 GB
    assert resources.storage_gb == 10.0  # 10Gi PVC
    assert resources.pod_count == 3  # 3 replicas


def test_calculate_cost_gke():
    """Test cost calculation for GKE"""
    service = CostEstimationService()
    
    resources = ResourceRequirements(
        cpu_cores=2.0,
        memory_gb=4.0,
        storage_gb=10.0,
        pod_count=2
    )
    
    cost_breakdown = service.calculate_cost(resources, "gke")
    
    # Verify costs are calculated
    assert cost_breakdown.cpu_cost > 0
    assert cost_breakdown.memory_cost > 0
    assert cost_breakdown.storage_cost > 0
    assert cost_breakdown.total_cost == (
        cost_breakdown.cpu_cost + 
        cost_breakdown.memory_cost + 
        cost_breakdown.storage_cost
    )
    
    # Verify approximate values (2 CPU * $33 = $66)
    assert 60 < cost_breakdown.cpu_cost < 70
    
    # Verify approximate values (4 GB * $3.65 = $14.6)
    assert 14 < cost_breakdown.memory_cost < 16
    
    # Verify approximate values (10 GB * $0.17 = $1.7)
    assert 1 < cost_breakdown.storage_cost < 3


def test_calculate_cost_eks():
    """Test cost calculation for EKS"""
    service = CostEstimationService()
    
    resources = ResourceRequirements(
        cpu_cores=1.0,
        memory_gb=2.0,
        storage_gb=5.0,
        pod_count=1
    )
    
    cost_breakdown = service.calculate_cost(resources, "eks")
    
    assert cost_breakdown.cpu_cost > 0
    assert cost_breakdown.memory_cost > 0
    assert cost_breakdown.storage_cost > 0
    assert cost_breakdown.total_cost > 0


def test_calculate_cost_aks():
    """Test cost calculation for AKS"""
    service = CostEstimationService()
    
    resources = ResourceRequirements(
        cpu_cores=1.0,
        memory_gb=2.0,
        storage_gb=5.0,
        pod_count=1
    )
    
    cost_breakdown = service.calculate_cost(resources, "aks")
    
    assert cost_breakdown.cpu_cost > 0
    assert cost_breakdown.memory_cost > 0
    assert cost_breakdown.storage_cost > 0
    assert cost_breakdown.total_cost > 0


def test_calculate_cost_invalid_provider():
    """Test that invalid provider raises ValueError"""
    service = CostEstimationService()
    
    resources = ResourceRequirements(
        cpu_cores=1.0,
        memory_gb=2.0,
        storage_gb=5.0,
        pod_count=1
    )
    
    with pytest.raises(ValueError) as exc_info:
        service.calculate_cost(resources, "invalid_provider")
    
    assert "Unsupported cloud provider" in str(exc_info.value)


def test_estimate_deployment_cost():
    """Test complete deployment cost estimation"""
    service = CostEstimationService()
    
    manifests = [
        KubernetesManifest(
            kind="Deployment",
            name="web-deployment",
            content=SAMPLE_DEPLOYMENT,
            namespace="default"
        ),
        KubernetesManifest(
            kind="PersistentVolumeClaim",
            name="data-pvc",
            content=SAMPLE_PVC,
            namespace="default"
        )
    ]
    
    estimate = service.estimate_deployment_cost(
        deployment_id="test-deployment-123",
        manifests=manifests,
        cloud_provider="gke"
    )
    
    assert estimate.deployment_id == "test-deployment-123"
    assert estimate.cloud_provider == "gke"
    assert estimate.resources.cpu_cores == 1.5
    assert estimate.resources.memory_gb == 1.5
    assert estimate.resources.storage_gb == 10.0
    assert estimate.estimated_monthly_cost > 0
    assert estimate.disclaimer is not None
    assert isinstance(estimate.timestamp, datetime)


def test_empty_manifests():
    """Test handling of empty manifest list"""
    service = CostEstimationService()
    
    resources = service.calculate_resources([])
    
    assert resources.cpu_cores == 0.0
    assert resources.memory_gb == 0.0
    assert resources.storage_gb == 0.0
    assert resources.pod_count == 0


def test_manifests_without_resources():
    """Test handling of manifests without resource specifications"""
    service = CostEstimationService()
    
    deployment_no_resources = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: simple-deployment
spec:
  replicas: 2
  selector:
    matchLabels:
      app: simple
  template:
    metadata:
      labels:
        app: simple
    spec:
      containers:
      - name: app
        image: myapp:latest
"""
    
    manifests = [
        KubernetesManifest(
            kind="Deployment",
            name="simple-deployment",
            content=deployment_no_resources,
            namespace="default"
        )
    ]
    
    resources = service.calculate_resources(manifests)
    
    # Should handle missing resources gracefully
    assert resources.cpu_cores == 0.0
    assert resources.memory_gb == 0.0
    assert resources.pod_count == 2  # Still counts replicas


def test_multiple_deployments():
    """Test calculating resources from multiple deployments"""
    service = CostEstimationService()
    
    deployment2 = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-deployment
spec:
  replicas: 2
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
      - name: api
        image: api:latest
        resources:
          requests:
            cpu: "1"
            memory: "1Gi"
"""
    
    manifests = [
        KubernetesManifest(
            kind="Deployment",
            name="web-deployment",
            content=SAMPLE_DEPLOYMENT,
            namespace="default"
        ),
        KubernetesManifest(
            kind="Deployment",
            name="api-deployment",
            content=deployment2,
            namespace="default"
        )
    ]
    
    resources = service.calculate_resources(manifests)
    
    # web: 3 replicas * 0.5 CPU = 1.5
    # api: 2 replicas * 1 CPU = 2.0
    # total: 3.5 CPU
    assert resources.cpu_cores == 3.5
    
    # web: 3 replicas * 0.5 GB = 1.5
    # api: 2 replicas * 1 GB = 2.0
    # total: 3.5 GB
    assert resources.memory_gb == 3.5
    
    # web: 3 pods, api: 2 pods = 5 total
    assert resources.pod_count == 5
