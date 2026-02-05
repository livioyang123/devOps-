"""
Test suite for Cost Estimation API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import uuid

from app.main import app
from app.database import Base, get_db
from app.models import Deployment, Cluster, User
from app.auth import create_access_token

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_cost_api.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


# Sample manifests for testing
SAMPLE_MANIFESTS = [
    {
        "kind": "Deployment",
        "name": "web-deployment",
        "namespace": "default",
        "content": """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-deployment
spec:
  replicas: 2
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
"""
    },
    {
        "kind": "PersistentVolumeClaim",
        "name": "data-pvc",
        "namespace": "default",
        "content": """
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: data-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
"""
    }
]


@pytest.fixture
def test_user():
    """Create a test user"""
    db = TestingSessionLocal()
    
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        hashed_password="hashed_password",
        full_name="Test User",
        is_active=True
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    yield user
    
    db.delete(user)
    db.commit()
    db.close()


@pytest.fixture
def test_cluster(test_user):
    """Create a test cluster"""
    db = TestingSessionLocal()
    
    cluster = Cluster(
        id=uuid.uuid4(),
        user_id=test_user.id,
        name="test-cluster",
        type="minikube",
        config={"kubeconfig": "test-config"},
        is_active=True
    )
    
    db.add(cluster)
    db.commit()
    db.refresh(cluster)
    
    yield cluster
    
    db.delete(cluster)
    db.commit()
    db.close()


@pytest.fixture
def test_deployment(test_user, test_cluster):
    """Create a test deployment"""
    db = TestingSessionLocal()
    
    deployment = Deployment(
        id=uuid.uuid4(),
        user_id=test_user.id,
        name="test-deployment",
        cluster_id=test_cluster.id,
        compose_content="version: '3.8'\nservices:\n  web:\n    image: nginx",
        manifests=SAMPLE_MANIFESTS,
        status="completed",
        deployed_at=datetime.utcnow()
    )
    
    db.add(deployment)
    db.commit()
    db.refresh(deployment)
    
    yield deployment
    
    db.delete(deployment)
    db.commit()
    db.close()


@pytest.fixture
def auth_headers(test_user):
    """Create authentication headers"""
    token = create_access_token({"sub": str(test_user.id), "user_id": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}


def test_get_cost_estimate_success(test_deployment, auth_headers):
    """Test successful cost estimation"""
    response = client.get(
        f"/api/cost-estimate/{test_deployment.id}",
        params={"cloud_provider": "gke"},
        headers=auth_headers
    )
    
    assert response.status_code == 200
    
    data = response.json()
    assert data["deployment_id"] == str(test_deployment.id)
    assert data["cloud_provider"] == "gke"
    assert "resources" in data
    assert "cost_breakdown" in data
    assert "estimated_monthly_cost" in data
    assert "disclaimer" in data
    
    # Verify resources
    resources = data["resources"]
    assert resources["cpu_cores"] == 1.0  # 2 replicas * 0.5 CPU
    assert resources["memory_gb"] == 1.0  # 2 replicas * 0.5 GB
    assert resources["storage_gb"] == 10.0  # 10Gi PVC
    assert resources["pod_count"] == 2
    
    # Verify cost breakdown
    cost_breakdown = data["cost_breakdown"]
    assert cost_breakdown["cpu_cost"] > 0
    assert cost_breakdown["memory_cost"] > 0
    assert cost_breakdown["storage_cost"] > 0
    assert cost_breakdown["total_cost"] > 0
    
    # Verify total matches breakdown
    assert cost_breakdown["total_cost"] == (
        cost_breakdown["cpu_cost"] + 
        cost_breakdown["memory_cost"] + 
        cost_breakdown["storage_cost"]
    )


def test_get_cost_estimate_eks(test_deployment, auth_headers):
    """Test cost estimation with EKS provider"""
    response = client.get(
        f"/api/cost-estimate/{test_deployment.id}",
        params={"cloud_provider": "eks"},
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["cloud_provider"] == "eks"
    assert data["estimated_monthly_cost"] > 0


def test_get_cost_estimate_aks(test_deployment, auth_headers):
    """Test cost estimation with AKS provider"""
    response = client.get(
        f"/api/cost-estimate/{test_deployment.id}",
        params={"cloud_provider": "aks"},
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["cloud_provider"] == "aks"
    assert data["estimated_monthly_cost"] > 0


def test_get_cost_estimate_default_provider(test_deployment, auth_headers):
    """Test cost estimation with default provider (GKE)"""
    response = client.get(
        f"/api/cost-estimate/{test_deployment.id}",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["cloud_provider"] == "gke"  # Default


def test_get_cost_estimate_invalid_provider(test_deployment, auth_headers):
    """Test cost estimation with invalid provider"""
    response = client.get(
        f"/api/cost-estimate/{test_deployment.id}",
        params={"cloud_provider": "invalid"},
        headers=auth_headers
    )
    
    assert response.status_code == 400
    assert "Invalid cloud provider" in response.json()["detail"]


def test_get_cost_estimate_deployment_not_found(auth_headers):
    """Test cost estimation for non-existent deployment"""
    fake_id = str(uuid.uuid4())
    response = client.get(
        f"/api/cost-estimate/{fake_id}",
        headers=auth_headers
    )
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_get_cost_estimate_unauthorized():
    """Test cost estimation without authentication"""
    fake_id = str(uuid.uuid4())
    response = client.get(f"/api/cost-estimate/{fake_id}")
    
    # Should be rejected by authentication middleware
    assert response.status_code in [401, 403]


def test_cost_estimate_disclaimer_present(test_deployment, auth_headers):
    """Test that disclaimer is included in response"""
    response = client.get(
        f"/api/cost-estimate/{test_deployment.id}",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "disclaimer" in data
    assert "approximate" in data["disclaimer"].lower()


def test_cost_estimate_timestamp_present(test_deployment, auth_headers):
    """Test that timestamp is included in response"""
    response = client.get(
        f"/api/cost-estimate/{test_deployment.id}",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "timestamp" in data
    # Verify it's a valid datetime string
    from datetime import datetime
    datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
