"""
Unit tests for Deployment API endpoint

Tests the POST /api/deploy endpoint and integration with Celery tasks.

Requirements: 6.1, 6.3, 6.4, 6.5, 6.8, 20.1, 20.2
"""

import pytest
import uuid
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.models import User, Cluster, Deployment
from app.schemas import DeploymentRequest, KubernetesManifest, DeploymentStatus
from app.auth import TokenData

# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_deploy.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# Override dependencies
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(scope="function")
def test_db():
    """Create test database and tables"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    yield db
    db.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_user(test_db):
    """Create a test user"""
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        hashed_password="hashed_password",
        full_name="Test User",
        is_active=True
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def test_cluster(test_db, test_user):
    """Create a test cluster"""
    cluster = Cluster(
        id=uuid.uuid4(),
        user_id=test_user.id,
        name="test-cluster",
        type="minikube",
        config={"kubeconfig": "test-config"},
        is_active=True
    )
    test_db.add(cluster)
    test_db.commit()
    test_db.refresh(cluster)
    return cluster


@pytest.fixture
def mock_current_user(test_user):
    """Mock current user authentication"""
    return TokenData(user_id=str(test_user.id), email=test_user.email)


@pytest.fixture
def sample_manifests():
    """Sample Kubernetes manifests for testing"""
    return [
        KubernetesManifest(
            kind="Deployment",
            name="test-deployment",
            content="""
apiVersion: apps/v1
kind: Deployment
metadata:
  name: test-deployment
spec:
  replicas: 1
  selector:
    matchLabels:
      app: test
  template:
    metadata:
      labels:
        app: test
    spec:
      containers:
      - name: test
        image: nginx:latest
""",
            namespace="default"
        ),
        KubernetesManifest(
            kind="Service",
            name="test-service",
            content="""
apiVersion: v1
kind: Service
metadata:
  name: test-service
spec:
  selector:
    app: test
  ports:
  - port: 80
    targetPort: 80
""",
            namespace="default"
        )
    ]


def test_deploy_endpoint_creates_deployment_record(test_db, test_cluster, mock_current_user, sample_manifests):
    """Test that POST /api/deploy creates a deployment record in database"""
    
    # Mock authentication
    with patch("app.routers.deploy.get_current_user", return_value=mock_current_user):
        # Mock Celery task
        with patch("app.routers.deploy.deploy_to_kubernetes.apply_async") as mock_task:
            mock_task.return_value = Mock(id="test-task-id")
            
            # Create request
            request = DeploymentRequest(
                manifests=sample_manifests,
                cluster_id=str(test_cluster.id),
                namespace="default"
            )
            
            # Make request with authorization header
            response = client.post(
                "/api/deploy",
                json=request.model_dump(),
                headers={"Authorization": "Bearer test-token"}
            )
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            
            assert "deployment_id" in data
            assert data["status"] == "in_progress"
            assert "websocket_url" in data
            assert f"/ws/deployment/{data['deployment_id']}" in data["websocket_url"]
            
            # Verify deployment record created in database
            deployment = test_db.query(Deployment).filter(
                Deployment.id == uuid.UUID(data["deployment_id"])
            ).first()
            
            assert deployment is not None
            assert deployment.cluster_id == test_cluster.id
            assert deployment.status == DeploymentStatus.IN_PROGRESS.value
            assert len(deployment.manifests) == 2
            
            print("✓ Deployment endpoint creates deployment record")


def test_deploy_endpoint_initiates_celery_task(test_db, test_cluster, mock_current_user, sample_manifests):
    """Test that POST /api/deploy initiates a Celery task"""
    
    with patch("app.routers.deploy.get_current_user", return_value=mock_current_user):
        with patch("app.routers.deploy.deploy_to_kubernetes.apply_async") as mock_task:
            mock_task.return_value = Mock(id="test-task-id")
            
            request = DeploymentRequest(
                manifests=sample_manifests,
                cluster_id=str(test_cluster.id),
                namespace="default"
            )
            
            response = client.post(
                "/api/deploy",
                json=request.model_dump(),
                headers={"Authorization": "Bearer test-token"}
            )
            
            assert response.status_code == 200
            
            # Verify Celery task was called
            mock_task.assert_called_once()
            call_args = mock_task.call_args
            
            # Verify task arguments
            assert len(call_args[1]["args"]) == 3  # manifests, cluster_id, deployment_id
            assert call_args[1]["args"][1] == str(test_cluster.id)
            assert call_args[1]["kwargs"]["namespace"] == "default"
            
            print("✓ Deployment endpoint initiates Celery task")


def test_deploy_endpoint_validates_cluster_exists(test_db, mock_current_user, sample_manifests):
    """Test that POST /api/deploy validates cluster exists"""
    
    with patch("app.routers.deploy.get_current_user", return_value=mock_current_user):
        # Use non-existent cluster ID
        request = DeploymentRequest(
            manifests=sample_manifests,
            cluster_id=str(uuid.uuid4()),
            namespace="default"
        )
        
        response = client.post(
            "/api/deploy",
            json=request.model_dump(),
            headers={"Authorization": "Bearer test-token"}
        )
        
        # Should return 404
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
        
        print("✓ Deployment endpoint validates cluster exists")


def test_deploy_endpoint_requires_authentication(test_db, test_cluster, sample_manifests):
    """Test that POST /api/deploy requires authentication"""
    
    request = DeploymentRequest(
        manifests=sample_manifests,
        cluster_id=str(test_cluster.id),
        namespace="default"
    )
    
    # Make request without authorization header
    response = client.post("/api/deploy", json=request.model_dump())
    
    # Should return 401
    assert response.status_code == 401
    
    print("✓ Deployment endpoint requires authentication")


def test_get_deployment_status_endpoint(test_db, test_user, test_cluster, mock_current_user):
    """Test GET /api/deploy/{deployment_id} endpoint"""
    
    # Create a deployment record
    deployment = Deployment(
        id=uuid.uuid4(),
        user_id=test_user.id,
        name="test-deployment",
        cluster_id=test_cluster.id,
        compose_content="",
        manifests=[{"kind": "Deployment", "name": "test"}],
        status=DeploymentStatus.COMPLETED.value,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        deployed_at=datetime.utcnow()
    )
    test_db.add(deployment)
    test_db.commit()
    
    with patch("app.routers.deploy.get_current_user", return_value=mock_current_user):
        response = client.get(
            f"/api/deploy/{deployment.id}",
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["deployment_id"] == str(deployment.id)
        assert data["status"] == DeploymentStatus.COMPLETED.value
        assert data["cluster_id"] == str(test_cluster.id)
        assert data["manifest_count"] == 1
        
        print("✓ Get deployment status endpoint works")


def test_get_deployment_status_not_found(test_db, mock_current_user):
    """Test GET /api/deploy/{deployment_id} with non-existent deployment"""
    
    with patch("app.routers.deploy.get_current_user", return_value=mock_current_user):
        response = client.get(
            f"/api/deploy/{uuid.uuid4()}",
            headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
        
        print("✓ Get deployment status returns 404 for non-existent deployment")


if __name__ == "__main__":
    print("\nRunning Deployment API tests...\n")
    
    # Create test database
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    
    try:
        # Create test fixtures
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
        
        cluster = Cluster(
            id=uuid.uuid4(),
            user_id=user.id,
            name="test-cluster",
            type="minikube",
            config={"kubeconfig": "test-config"},
            is_active=True
        )
        db.add(cluster)
        db.commit()
        db.refresh(cluster)
        
        mock_user = TokenData(user_id=str(user.id), email=user.email)
        
        manifests = [
            KubernetesManifest(
                kind="Deployment",
                name="test-deployment",
                content="apiVersion: apps/v1\nkind: Deployment",
                namespace="default"
            )
        ]
        
        # Run tests
        test_deploy_endpoint_creates_deployment_record(db, cluster, mock_user, manifests)
        test_deploy_endpoint_initiates_celery_task(db, cluster, mock_user, manifests)
        test_deploy_endpoint_validates_cluster_exists(db, mock_user, manifests)
        test_get_deployment_status_endpoint(db, user, cluster, mock_user)
        test_get_deployment_status_not_found(db, mock_user)
        
        print("\n✅ All Deployment API tests passed!\n")
        
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
