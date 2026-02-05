"""
Tests for Manifest Export API

Requirements: 13.2, 13.3, 13.4
"""

import pytest
import uuid
import zipfile
import io
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models import Deployment, Cluster, User
from app.auth import create_access_token

# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(scope="function")
def setup_database():
    """Create tables before each test and drop after"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_user(setup_database):
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
    
    # Create access token
    token = create_access_token({"sub": str(user.id)})
    
    yield {"user": user, "token": token}
    db.close()


@pytest.fixture
def test_cluster(setup_database, test_user):
    """Create a test cluster"""
    db = TestingSessionLocal()
    cluster = Cluster(
        id=uuid.uuid4(),
        user_id=test_user["user"].id,
        name="test-cluster",
        type="minikube",
        config={"kubeconfig": "test-config"},
        is_active=True
    )
    db.add(cluster)
    db.commit()
    db.refresh(cluster)
    yield cluster
    db.close()


@pytest.fixture
def test_deployment(setup_database, test_user, test_cluster):
    """Create a test deployment with manifests"""
    db = TestingSessionLocal()
    
    # Sample manifests
    manifests = [
        {
            "kind": "Deployment",
            "name": "web-deployment",
            "content": """apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-deployment
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
      - name: web
        image: nginx:latest
        ports:
        - containerPort: 80
""",
            "namespace": "default"
        },
        {
            "kind": "Service",
            "name": "web-service",
            "content": """apiVersion: v1
kind: Service
metadata:
  name: web-service
spec:
  selector:
    app: web
  ports:
  - port: 80
    targetPort: 80
  type: LoadBalancer
""",
            "namespace": "default"
        },
        {
            "kind": "ConfigMap",
            "name": "app-config",
            "content": """apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
data:
  config.json: |
    {"key": "value"}
""",
            "namespace": "default"
        }
    ]
    
    deployment = Deployment(
        id=uuid.uuid4(),
        user_id=test_user["user"].id,
        name="test-deployment",
        cluster_id=test_cluster.id,
        compose_content="version: '3'",
        manifests=manifests,
        status="completed",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(deployment)
    db.commit()
    db.refresh(deployment)
    yield deployment
    db.close()


def test_export_manifests_success(test_deployment, test_user):
    """
    Test successful manifest export
    
    Requirements: 13.2, 13.3, 13.4
    """
    # Make request
    response = client.get(
        f"/api/export/{test_deployment.id}",
        headers={"Authorization": f"Bearer {test_user['token']}"}
    )
    
    # Verify response
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert "attachment" in response.headers["content-disposition"]
    
    # Verify ZIP content
    zip_buffer = io.BytesIO(response.content)
    with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
        # Check file list
        file_list = zip_file.namelist()
        
        # Should have README
        assert "README.md" in file_list
        
        # Should have manifests organized by type
        assert "deployments/web-deployment.yaml" in file_list
        assert "services/web-service.yaml" in file_list
        assert "configmaps/app-config.yaml" in file_list
        
        # Verify content of one manifest
        deployment_content = zip_file.read("deployments/web-deployment.yaml").decode()
        assert "kind: Deployment" in deployment_content
        assert "name: web-deployment" in deployment_content


def test_export_manifests_not_found(test_user):
    """
    Test export with non-existent deployment
    
    Requirements: 13.2
    """
    fake_id = str(uuid.uuid4())
    response = client.get(
        f"/api/export/{fake_id}",
        headers={"Authorization": f"Bearer {test_user['token']}"}
    )
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_export_manifests_no_manifests(test_user, test_cluster):
    """
    Test export with deployment that has no manifests
    
    Requirements: 13.2
    """
    db = TestingSessionLocal()
    
    # Create deployment without manifests
    deployment = Deployment(
        id=uuid.uuid4(),
        user_id=test_user["user"].id,
        name="empty-deployment",
        cluster_id=test_cluster.id,
        compose_content="version: '3'",
        manifests=[],
        status="pending",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(deployment)
    db.commit()
    db.refresh(deployment)
    
    response = client.get(
        f"/api/export/{deployment.id}",
        headers={"Authorization": f"Bearer {test_user['token']}"}
    )
    
    assert response.status_code == 400
    assert "no manifests" in response.json()["detail"].lower()
    
    db.close()


def test_export_manifests_unauthorized(test_deployment):
    """
    Test export without authentication
    
    Requirements: 13.2
    """
    response = client.get(f"/api/export/{test_deployment.id}")
    
    # Should fail due to missing authentication
    assert response.status_code in [401, 403]


def test_export_manifests_different_user(test_deployment, setup_database):
    """
    Test export with different user (should not have access)
    
    Requirements: 13.2
    """
    db = TestingSessionLocal()
    
    # Create another user
    other_user = User(
        id=uuid.uuid4(),
        email="other@example.com",
        hashed_password="hashed_password",
        full_name="Other User",
        is_active=True
    )
    db.add(other_user)
    db.commit()
    db.refresh(other_user)
    
    # Create token for other user
    other_token = create_access_token({"sub": str(other_user.id)})
    
    response = client.get(
        f"/api/export/{test_deployment.id}",
        headers={"Authorization": f"Bearer {other_token}"}
    )
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
    
    db.close()


def test_export_manifest_organization(test_deployment, test_user):
    """
    Test that manifests are properly organized by type in folders
    
    Requirements: 13.3, 13.4
    """
    response = client.get(
        f"/api/export/{test_deployment.id}",
        headers={"Authorization": f"Bearer {test_user['token']}"}
    )
    
    assert response.status_code == 200
    
    # Parse ZIP
    zip_buffer = io.BytesIO(response.content)
    with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
        file_list = zip_file.namelist()
        
        # Check folder structure
        folders = set()
        for file_path in file_list:
            if "/" in file_path:
                folder = file_path.split("/")[0]
                folders.add(folder)
        
        # Should have proper folders
        assert "deployments" in folders
        assert "services" in folders
        assert "configmaps" in folders
        
        # Each manifest should be in correct folder
        for file_path in file_list:
            if file_path.endswith(".yaml"):
                content = zip_file.read(file_path).decode()
                
                if "deployments/" in file_path:
                    assert "kind: Deployment" in content
                elif "services/" in file_path:
                    assert "kind: Service" in content
                elif "configmaps/" in file_path:
                    assert "kind: ConfigMap" in content


def test_export_multiple_manifest_types(test_user, test_cluster):
    """
    Test export with various manifest types
    
    Requirements: 13.3, 13.4
    """
    db = TestingSessionLocal()
    
    # Create deployment with various manifest types
    manifests = [
        {"kind": "Deployment", "name": "app", "content": "kind: Deployment\nmetadata:\n  name: app", "namespace": "default"},
        {"kind": "Service", "name": "app-svc", "content": "kind: Service\nmetadata:\n  name: app-svc", "namespace": "default"},
        {"kind": "ConfigMap", "name": "config", "content": "kind: ConfigMap\nmetadata:\n  name: config", "namespace": "default"},
        {"kind": "Secret", "name": "secret", "content": "kind: Secret\nmetadata:\n  name: secret", "namespace": "default"},
        {"kind": "PersistentVolumeClaim", "name": "pvc", "content": "kind: PersistentVolumeClaim\nmetadata:\n  name: pvc", "namespace": "default"},
        {"kind": "Ingress", "name": "ingress", "content": "kind: Ingress\nmetadata:\n  name: ingress", "namespace": "default"},
    ]
    
    deployment = Deployment(
        id=uuid.uuid4(),
        user_id=test_user["user"].id,
        name="multi-type-deployment",
        cluster_id=test_cluster.id,
        compose_content="version: '3'",
        manifests=manifests,
        status="completed",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(deployment)
    db.commit()
    db.refresh(deployment)
    
    response = client.get(
        f"/api/export/{deployment.id}",
        headers={"Authorization": f"Bearer {test_user['token']}"}
    )
    
    assert response.status_code == 200
    
    # Verify all types are present
    zip_buffer = io.BytesIO(response.content)
    with zipfile.ZipFile(zip_buffer, 'r') as zip_file:
        file_list = zip_file.namelist()
        
        assert "deployments/app.yaml" in file_list
        assert "services/app-svc.yaml" in file_list
        assert "configmaps/config.yaml" in file_list
        assert "secrets/secret.yaml" in file_list
        assert "persistentvolumeclaims/pvc.yaml" in file_list
        assert "ingresses/ingress.yaml" in file_list
    
    db.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
