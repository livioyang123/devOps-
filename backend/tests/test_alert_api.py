"""
Unit tests for Alert API endpoints
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid

from app.main import app
from app.database import Base, get_db
from app.models import User, Deployment, Cluster, AlertConfiguration
from app.auth import get_current_user
from app.services.alert import get_alert_service, AlertService


# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_alert_api.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


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
        config={"kubeconfig": "test"},
        is_active=True
    )
    test_db.add(cluster)
    test_db.commit()
    test_db.refresh(cluster)
    return cluster


@pytest.fixture
def test_deployment(test_db, test_user, test_cluster):
    """Create a test deployment"""
    deployment = Deployment(
        id=uuid.uuid4(),
        user_id=test_user.id,
        name="test-deployment",
        cluster_id=test_cluster.id,
        compose_content="version: '3'\nservices:\n  web:\n    image: nginx",
        manifests=[],
        status="completed"
    )
    test_db.add(deployment)
    test_db.commit()
    test_db.refresh(deployment)
    return deployment


@pytest.fixture
def client(test_user):
    """Create test client with auth override"""
    def override_get_current_user():
        return test_user
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    client = TestClient(app)
    yield client
    
    # Clean up overrides
    app.dependency_overrides.clear()


class TestCreateAlert:
    """Test POST /api/alerts endpoint"""
    
    def test_create_cpu_threshold_alert(self, client, test_deployment):
        """Test creating a CPU threshold alert"""
        alert_data = {
            "deployment_id": str(test_deployment.id),
            "condition_type": "cpu_threshold",
            "threshold_value": 0.8,
            "notification_channel": "email",
            "notification_config": {
                "recipient": "admin@example.com"
            }
        }
        
        response = client.post("/api/alerts", json=alert_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["condition_type"] == "cpu_threshold"
        assert data["threshold_value"] == 0.8
        assert data["notification_channel"] == "email"
        assert data["is_active"] is True
        assert "id" in data
        assert "created_at" in data
    
    def test_create_memory_threshold_alert(self, client, test_deployment):
        """Test creating a memory threshold alert"""
        alert_data = {
            "deployment_id": str(test_deployment.id),
            "condition_type": "memory_threshold",
            "threshold_value": 1024.0,
            "notification_channel": "webhook",
            "notification_config": {
                "url": "https://example.com/webhook"
            }
        }
        
        response = client.post("/api/alerts", json=alert_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["condition_type"] == "memory_threshold"
        assert data["threshold_value"] == 1024.0
        assert data["notification_channel"] == "webhook"
    
    def test_create_deployment_failure_alert(self, client, test_deployment):
        """Test creating a deployment failure alert"""
        alert_data = {
            "deployment_id": str(test_deployment.id),
            "condition_type": "deployment_failure",
            "notification_channel": "in_app",
            "notification_config": {}
        }
        
        response = client.post("/api/alerts", json=alert_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["condition_type"] == "deployment_failure"
        assert data["threshold_value"] is None
    
    def test_create_alert_invalid_condition_type(self, client, test_deployment):
        """Test creating alert with invalid condition type"""
        alert_data = {
            "deployment_id": str(test_deployment.id),
            "condition_type": "invalid_type",
            "threshold_value": 1.0,
            "notification_channel": "email",
            "notification_config": {
                "recipient": "admin@example.com"
            }
        }
        
        response = client.post("/api/alerts", json=alert_data)
        
        assert response.status_code == 400
        assert "Invalid condition_type" in response.json()["detail"]
    
    def test_create_alert_missing_threshold(self, client, test_deployment):
        """Test creating threshold alert without threshold value"""
        alert_data = {
            "deployment_id": str(test_deployment.id),
            "condition_type": "cpu_threshold",
            "notification_channel": "email",
            "notification_config": {
                "recipient": "admin@example.com"
            }
        }
        
        response = client.post("/api/alerts", json=alert_data)
        
        assert response.status_code == 400
        assert "threshold_value is required" in response.json()["detail"]
    
    def test_create_alert_invalid_notification_channel(self, client, test_deployment):
        """Test creating alert with invalid notification channel"""
        alert_data = {
            "deployment_id": str(test_deployment.id),
            "condition_type": "cpu_threshold",
            "threshold_value": 0.8,
            "notification_channel": "invalid_channel",
            "notification_config": {}
        }
        
        response = client.post("/api/alerts", json=alert_data)
        
        assert response.status_code == 400
        assert "Invalid notification_channel" in response.json()["detail"]


class TestListAlerts:
    """Test GET /api/alerts endpoint"""
    
    def test_list_alerts_empty(self, client):
        """Test listing alerts when none exist"""
        response = client.get("/api/alerts")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0
    
    def test_list_alerts_with_data(self, client, test_deployment, test_db, test_user):
        """Test listing alerts with existing data"""
        # Create some alerts
        alert1 = AlertConfiguration(
            id=uuid.uuid4(),
            user_id=test_user.id,
            deployment_id=test_deployment.id,
            condition_type="cpu_threshold",
            threshold_value=0.8,
            notification_channel="email",
            notification_config={"recipient": "admin@example.com"},
            is_active=True
        )
        alert2 = AlertConfiguration(
            id=uuid.uuid4(),
            user_id=test_user.id,
            deployment_id=test_deployment.id,
            condition_type="memory_threshold",
            threshold_value=1024.0,
            notification_channel="webhook",
            notification_config={"url": "https://example.com/webhook"},
            is_active=True
        )
        test_db.add(alert1)
        test_db.add(alert2)
        test_db.commit()
        
        response = client.get("/api/alerts")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert any(a["condition_type"] == "cpu_threshold" for a in data)
        assert any(a["condition_type"] == "memory_threshold" for a in data)
    
    def test_list_alerts_filtered_by_deployment(
        self,
        client,
        test_deployment,
        test_cluster,
        test_db,
        test_user
    ):
        """Test listing alerts filtered by deployment ID"""
        # Create another deployment
        deployment2 = Deployment(
            id=uuid.uuid4(),
            user_id=test_user.id,
            name="test-deployment-2",
            cluster_id=test_cluster.id,
            compose_content="",
            manifests=[],
            status="completed"
        )
        test_db.add(deployment2)
        test_db.commit()
        
        # Create alerts for different deployments
        alert1 = AlertConfiguration(
            id=uuid.uuid4(),
            user_id=test_user.id,
            deployment_id=test_deployment.id,
            condition_type="cpu_threshold",
            threshold_value=0.8,
            notification_channel="email",
            notification_config={"recipient": "admin@example.com"},
            is_active=True
        )
        alert2 = AlertConfiguration(
            id=uuid.uuid4(),
            user_id=test_user.id,
            deployment_id=deployment2.id,
            condition_type="memory_threshold",
            threshold_value=1024.0,
            notification_channel="email",
            notification_config={"recipient": "admin@example.com"},
            is_active=True
        )
        test_db.add(alert1)
        test_db.add(alert2)
        test_db.commit()
        
        # Filter by first deployment
        response = client.get(f"/api/alerts?deployment_id={test_deployment.id}")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["deployment_id"] == str(test_deployment.id)


class TestDeleteAlert:
    """Test DELETE /api/alerts/{alert_id} endpoint"""
    
    def test_delete_alert_success(self, client, test_deployment, test_db, test_user):
        """Test successfully deleting an alert"""
        # Create alert
        alert = AlertConfiguration(
            id=uuid.uuid4(),
            user_id=test_user.id,
            deployment_id=test_deployment.id,
            condition_type="cpu_threshold",
            threshold_value=0.8,
            notification_channel="email",
            notification_config={"recipient": "admin@example.com"},
            is_active=True
        )
        test_db.add(alert)
        test_db.commit()
        
        response = client.delete(f"/api/alerts/{alert.id}")
        
        assert response.status_code == 204
        
        # Verify alert is deleted
        deleted_alert = test_db.query(AlertConfiguration).filter(
            AlertConfiguration.id == alert.id
        ).first()
        assert deleted_alert is None
    
    def test_delete_alert_not_found(self, client):
        """Test deleting non-existent alert"""
        fake_id = uuid.uuid4()
        response = client.delete(f"/api/alerts/{fake_id}")
        
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    def test_delete_alert_invalid_id(self, client):
        """Test deleting alert with invalid ID format"""
        response = client.delete("/api/alerts/invalid-id")
        
        assert response.status_code == 400
        assert "Invalid alert_id format" in response.json()["detail"]
