"""
Tests for cluster management API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import json

from app.main import app
from app.database import Base, get_db
from app.auth import create_access_token
from app.models import User, Cluster
from app.encryption import encrypt_credentials, decrypt_credentials
import uuid

# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
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


@pytest.fixture(scope="module")
def test_user():
    """Create a test user"""
    db = TestingSessionLocal()
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == "test@example.com").first()
    if existing_user:
        yield existing_user
        db.close()
        return
    
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
    db.close()


@pytest.fixture
def auth_headers(test_user):
    """Create authentication headers"""
    token = create_access_token(data={"sub": test_user.email, "user_id": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}


def test_create_cluster_minikube(auth_headers, test_user):
    """Test creating a minikube cluster configuration"""
    cluster_data = {
        "name": "local-minikube",
        "type": "minikube",
        "config": {
            "kubeconfig": "/path/to/kubeconfig",
            "context": "minikube"
        }
    }
    
    response = client.post(
        "/api/clusters",
        json=cluster_data,
        headers=auth_headers
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "local-minikube"
    assert data["type"] == "minikube"
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_create_cluster_gke(auth_headers, test_user):
    """Test creating a GKE cluster configuration"""
    cluster_data = {
        "name": "production-gke",
        "type": "gke",
        "config": {
            "project_id": "my-project",
            "cluster_name": "prod-cluster",
            "zone": "us-central1-a",
            "credentials": "service-account-key-json"
        }
    }
    
    response = client.post(
        "/api/clusters",
        json=cluster_data,
        headers=auth_headers
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "production-gke"
    assert data["type"] == "gke"


def test_create_cluster_eks(auth_headers, test_user):
    """Test creating an EKS cluster configuration"""
    cluster_data = {
        "name": "production-eks",
        "type": "eks",
        "config": {
            "cluster_name": "prod-cluster",
            "region": "us-east-1",
            "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
            "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        }
    }
    
    response = client.post(
        "/api/clusters",
        json=cluster_data,
        headers=auth_headers
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "production-eks"
    assert data["type"] == "eks"


def test_create_cluster_aks(auth_headers, test_user):
    """Test creating an AKS cluster configuration"""
    cluster_data = {
        "name": "production-aks",
        "type": "aks",
        "config": {
            "subscription_id": "12345678-1234-1234-1234-123456789012",
            "resource_group": "my-resource-group",
            "cluster_name": "prod-cluster",
            "credentials": "azure-credentials-json"
        }
    }
    
    response = client.post(
        "/api/clusters",
        json=cluster_data,
        headers=auth_headers
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "production-aks"
    assert data["type"] == "aks"


def test_create_cluster_kind(auth_headers, test_user):
    """Test creating a kind cluster configuration"""
    cluster_data = {
        "name": "local-kind",
        "type": "kind",
        "config": {
            "kubeconfig": "/path/to/kind/kubeconfig",
            "context": "kind-kind"
        }
    }
    
    response = client.post(
        "/api/clusters",
        json=cluster_data,
        headers=auth_headers
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "local-kind"
    assert data["type"] == "kind"


def test_create_cluster_invalid_type(auth_headers, test_user):
    """Test creating a cluster with invalid type"""
    cluster_data = {
        "name": "invalid-cluster",
        "type": "invalid-type",
        "config": {"key": "value"}
    }
    
    response = client.post(
        "/api/clusters",
        json=cluster_data,
        headers=auth_headers
    )
    
    assert response.status_code == 400
    assert "Invalid cluster type" in response.json()["detail"]


def test_create_cluster_empty_name(auth_headers, test_user):
    """Test creating a cluster with empty name"""
    cluster_data = {
        "name": "",
        "type": "minikube",
        "config": {"key": "value"}
    }
    
    response = client.post(
        "/api/clusters",
        json=cluster_data,
        headers=auth_headers
    )
    
    assert response.status_code == 400
    assert "cannot be empty" in response.json()["detail"]


def test_create_cluster_duplicate_name(auth_headers, test_user):
    """Test creating a cluster with duplicate name"""
    cluster_data = {
        "name": "duplicate-cluster",
        "type": "minikube",
        "config": {"key": "value"}
    }
    
    # Create first cluster
    response1 = client.post(
        "/api/clusters",
        json=cluster_data,
        headers=auth_headers
    )
    assert response1.status_code == 201
    
    # Try to create duplicate
    response2 = client.post(
        "/api/clusters",
        json=cluster_data,
        headers=auth_headers
    )
    assert response2.status_code == 409
    assert "already exists" in response2.json()["detail"]


def test_list_clusters_empty(auth_headers, test_user):
    """Test listing clusters when none exist"""
    response = client.get(
        "/api/clusters",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "clusters" in data
    assert len(data["clusters"]) == 0


def test_list_clusters_multiple(auth_headers, test_user):
    """Test listing multiple clusters"""
    # Create multiple clusters
    clusters = [
        {"name": "cluster-1", "type": "minikube", "config": {"key": "value1"}},
        {"name": "cluster-2", "type": "kind", "config": {"key": "value2"}},
        {"name": "cluster-3", "type": "gke", "config": {"key": "value3"}},
    ]
    
    for cluster_data in clusters:
        response = client.post(
            "/api/clusters",
            json=cluster_data,
            headers=auth_headers
        )
        assert response.status_code == 201
    
    # List all clusters
    response = client.get(
        "/api/clusters",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["clusters"]) == 3
    
    # Verify clusters are ordered by created_at desc (newest first)
    cluster_names = [c["name"] for c in data["clusters"]]
    assert cluster_names == ["cluster-3", "cluster-2", "cluster-1"]


def test_delete_cluster(auth_headers, test_user):
    """Test deleting a cluster"""
    # Create a cluster
    cluster_data = {
        "name": "cluster-to-delete",
        "type": "minikube",
        "config": {"key": "value"}
    }
    
    create_response = client.post(
        "/api/clusters",
        json=cluster_data,
        headers=auth_headers
    )
    assert create_response.status_code == 201
    cluster_id = create_response.json()["id"]
    
    # Delete the cluster
    delete_response = client.delete(
        f"/api/clusters/{cluster_id}",
        headers=auth_headers
    )
    assert delete_response.status_code == 204
    
    # Verify cluster is deleted
    list_response = client.get(
        "/api/clusters",
        headers=auth_headers
    )
    assert list_response.status_code == 200
    assert len(list_response.json()["clusters"]) == 0


def test_delete_cluster_not_found(auth_headers, test_user):
    """Test deleting a non-existent cluster"""
    fake_id = str(uuid.uuid4())
    
    response = client.delete(
        f"/api/clusters/{fake_id}",
        headers=auth_headers
    )
    
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_delete_cluster_invalid_id(auth_headers, test_user):
    """Test deleting a cluster with invalid ID format"""
    response = client.delete(
        "/api/clusters/invalid-id",
        headers=auth_headers
    )
    
    assert response.status_code == 400
    assert "Invalid cluster ID format" in response.json()["detail"]


def test_cluster_credentials_encrypted(auth_headers, test_user):
    """Test that cluster credentials are encrypted in database"""
    cluster_data = {
        "name": "secure-cluster",
        "type": "gke",
        "config": {
            "sensitive_key": "super-secret-value",
            "api_token": "secret-token-12345"
        }
    }
    
    # Create cluster
    response = client.post(
        "/api/clusters",
        json=cluster_data,
        headers=auth_headers
    )
    assert response.status_code == 201
    cluster_id = response.json()["id"]
    
    # Check database directly
    db = TestingSessionLocal()
    cluster = db.query(Cluster).filter(Cluster.id == uuid.UUID(cluster_id)).first()
    
    # Verify config is encrypted (stored in 'encrypted' key)
    assert "encrypted" in cluster.config
    encrypted_config = cluster.config["encrypted"]
    
    # Verify we can decrypt it
    decrypted_json = decrypt_credentials(encrypted_config)
    decrypted_config = json.loads(decrypted_json)
    
    assert decrypted_config["sensitive_key"] == "super-secret-value"
    assert decrypted_config["api_token"] == "secret-token-12345"
    
    db.close()


def test_create_cluster_without_auth(test_user):
    """Test creating a cluster without authentication"""
    cluster_data = {
        "name": "unauthorized-cluster",
        "type": "minikube",
        "config": {"key": "value"}
    }
    
    response = client.post(
        "/api/clusters",
        json=cluster_data
    )
    
    # Should fail with 401 or 403
    assert response.status_code in [401, 403]


def test_list_clusters_without_auth(test_user):
    """Test listing clusters without authentication"""
    response = client.get("/api/clusters")
    
    # Should fail with 401 or 403
    assert response.status_code in [401, 403]


def test_delete_cluster_without_auth(test_user):
    """Test deleting a cluster without authentication"""
    fake_id = str(uuid.uuid4())
    response = client.delete(f"/api/clusters/{fake_id}")
    
    # Should fail with 401 or 403
    assert response.status_code in [401, 403]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
