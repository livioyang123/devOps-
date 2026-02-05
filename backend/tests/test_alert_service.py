"""
Unit tests for Alert Service
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid

from app.database import Base
from app.models import User, Deployment, Cluster, AlertConfiguration
from app.schemas import (
    AlertConfigCreate,
    PodMetrics,
    NetworkMetrics,
    TriggeredAlert
)
from app.services.alert import AlertService
from app.services.monitor import MonitorService


# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_alert_service.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


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
def mock_monitor_service():
    """Create mock monitor service"""
    mock_service = AsyncMock(spec=MonitorService)
    return mock_service


@pytest.fixture
def alert_service(mock_monitor_service):
    """Create alert service with mocked monitor"""
    return AlertService(monitor_service=mock_monitor_service)


class TestAlertServiceRegistration:
    """Test alert registration functionality"""
    
    def test_register_cpu_threshold_alert(self, test_db, test_user, test_deployment, alert_service):
        """Test registering a CPU threshold alert"""
        alert_config = AlertConfigCreate(
            deployment_id=str(test_deployment.id),
            condition_type="cpu_threshold",
            threshold_value=0.8,
            notification_channel="email",
            notification_config={"recipient": "admin@example.com"}
        )
        
        result = alert_service.register_alert(
            db=test_db,
            alert_config=alert_config,
            user_id=test_user.id
        )
        
        assert result is not None
        assert result.condition_type == "cpu_threshold"
        assert result.threshold_value == 0.8
        assert result.notification_channel == "email"
        assert result.is_active is True
    
    def test_register_memory_threshold_alert(self, test_db, test_user, test_deployment, alert_service):
        """Test registering a memory threshold alert"""
        alert_config = AlertConfigCreate(
            deployment_id=str(test_deployment.id),
            condition_type="memory_threshold",
            threshold_value=1024.0,
            notification_channel="webhook",
            notification_config={"url": "https://example.com/webhook"}
        )
        
        result = alert_service.register_alert(
            db=test_db,
            alert_config=alert_config,
            user_id=test_user.id
        )
        
        assert result is not None
        assert result.condition_type == "memory_threshold"
        assert result.threshold_value == 1024.0
        assert result.notification_channel == "webhook"
    
    def test_register_deployment_failure_alert(self, test_db, test_user, test_deployment, alert_service):
        """Test registering a deployment failure alert"""
        alert_config = AlertConfigCreate(
            deployment_id=str(test_deployment.id),
            condition_type="deployment_failure",
            threshold_value=None,
            notification_channel="in_app",
            notification_config={}
        )
        
        result = alert_service.register_alert(
            db=test_db,
            alert_config=alert_config,
            user_id=test_user.id
        )
        
        assert result is not None
        assert result.condition_type == "deployment_failure"
        assert result.threshold_value is None
    
    def test_register_alert_invalid_condition_type(self, test_db, test_user, test_deployment, alert_service):
        """Test that invalid condition type raises error"""
        alert_config = AlertConfigCreate(
            deployment_id=str(test_deployment.id),
            condition_type="invalid_type",
            threshold_value=1.0,
            notification_channel="email",
            notification_config={"recipient": "admin@example.com"}
        )
        
        with pytest.raises(ValueError, match="Invalid condition_type"):
            alert_service.register_alert(
                db=test_db,
                alert_config=alert_config,
                user_id=test_user.id
            )
    
    def test_register_alert_missing_threshold(self, test_db, test_user, test_deployment, alert_service):
        """Test that missing threshold for threshold-based alert raises error"""
        alert_config = AlertConfigCreate(
            deployment_id=str(test_deployment.id),
            condition_type="cpu_threshold",
            threshold_value=None,
            notification_channel="email",
            notification_config={"recipient": "admin@example.com"}
        )
        
        with pytest.raises(ValueError, match="threshold_value is required"):
            alert_service.register_alert(
                db=test_db,
                alert_config=alert_config,
                user_id=test_user.id
            )
    
    def test_register_alert_invalid_notification_channel(self, test_db, test_user, test_deployment, alert_service):
        """Test that invalid notification channel raises error"""
        alert_config = AlertConfigCreate(
            deployment_id=str(test_deployment.id),
            condition_type="cpu_threshold",
            threshold_value=0.8,
            notification_channel="invalid_channel",
            notification_config={}
        )
        
        with pytest.raises(ValueError, match="Invalid notification_channel"):
            alert_service.register_alert(
                db=test_db,
                alert_config=alert_config,
                user_id=test_user.id
            )


class TestAlertConditionChecking:
    """Test alert condition evaluation"""
    
    @pytest.mark.asyncio
    async def test_check_cpu_threshold_triggered(
        self,
        test_db,
        test_user,
        test_deployment,
        alert_service,
        mock_monitor_service
    ):
        """Test CPU threshold alert is triggered when exceeded"""
        # Create alert
        alert_config = AlertConfigCreate(
            deployment_id=str(test_deployment.id),
            condition_type="cpu_threshold",
            threshold_value=0.5,
            notification_channel="email",
            notification_config={"recipient": "admin@example.com"}
        )
        alert_service.register_alert(test_db, alert_config, test_user.id)
        
        # Mock high CPU usage
        mock_pod_metrics = [
            PodMetrics(
                name="test-pod",
                namespace="default",
                cpu_usage=0.8,  # Exceeds threshold
                memory_usage=1024.0,
                network=NetworkMetrics(rx_bytes=100.0, tx_bytes=200.0),
                timestamp=datetime.utcnow()
            )
        ]
        mock_monitor_service.get_pod_metrics.return_value = mock_pod_metrics
        
        # Check conditions
        triggered = await alert_service.check_conditions(
            db=test_db,
            deployment_id=test_deployment.id,
            namespace="default"
        )
        
        assert len(triggered) == 1
        assert triggered[0].condition_type == "cpu_threshold"
        assert triggered[0].current_value == 0.8
    
    @pytest.mark.asyncio
    async def test_check_memory_threshold_triggered(
        self,
        test_db,
        test_user,
        test_deployment,
        alert_service,
        mock_monitor_service
    ):
        """Test memory threshold alert is triggered when exceeded"""
        # Create alert (threshold in MB)
        alert_config = AlertConfigCreate(
            deployment_id=str(test_deployment.id),
            condition_type="memory_threshold",
            threshold_value=500.0,  # 500 MB
            notification_channel="email",
            notification_config={"recipient": "admin@example.com"}
        )
        alert_service.register_alert(test_db, alert_config, test_user.id)
        
        # Mock high memory usage
        mock_pod_metrics = [
            PodMetrics(
                name="test-pod",
                namespace="default",
                cpu_usage=0.3,
                memory_usage=1024 * 1024 * 1024,  # 1 GB in bytes
                network=NetworkMetrics(rx_bytes=100.0, tx_bytes=200.0),
                timestamp=datetime.utcnow()
            )
        ]
        mock_monitor_service.get_pod_metrics.return_value = mock_pod_metrics
        
        # Check conditions
        triggered = await alert_service.check_conditions(
            db=test_db,
            deployment_id=test_deployment.id,
            namespace="default"
        )
        
        assert len(triggered) == 1
        assert triggered[0].condition_type == "memory_threshold"
        assert triggered[0].current_value > 500.0
    
    @pytest.mark.asyncio
    async def test_check_deployment_failure_triggered(
        self,
        test_db,
        test_user,
        test_cluster,
        alert_service,
        mock_monitor_service
    ):
        """Test deployment failure alert is triggered"""
        # Create failed deployment
        failed_deployment = Deployment(
            id=uuid.uuid4(),
            user_id=test_user.id,
            name="failed-deployment",
            cluster_id=test_cluster.id,
            compose_content="",
            manifests=[],
            status="failed"
        )
        test_db.add(failed_deployment)
        test_db.commit()
        
        # Create alert
        alert_config = AlertConfigCreate(
            deployment_id=str(failed_deployment.id),
            condition_type="deployment_failure",
            threshold_value=None,
            notification_channel="email",
            notification_config={"recipient": "admin@example.com"}
        )
        alert_service.register_alert(test_db, alert_config, test_user.id)
        
        # Mock empty metrics
        mock_monitor_service.get_pod_metrics.return_value = []
        
        # Check conditions
        triggered = await alert_service.check_conditions(
            db=test_db,
            deployment_id=failed_deployment.id,
            namespace="default"
        )
        
        assert len(triggered) == 1
        assert triggered[0].condition_type == "deployment_failure"
    
    @pytest.mark.asyncio
    async def test_check_no_alerts_triggered(
        self,
        test_db,
        test_user,
        test_deployment,
        alert_service,
        mock_monitor_service
    ):
        """Test no alerts triggered when conditions not met"""
        # Create alert
        alert_config = AlertConfigCreate(
            deployment_id=str(test_deployment.id),
            condition_type="cpu_threshold",
            threshold_value=0.9,  # High threshold
            notification_channel="email",
            notification_config={"recipient": "admin@example.com"}
        )
        alert_service.register_alert(test_db, alert_config, test_user.id)
        
        # Mock low CPU usage
        mock_pod_metrics = [
            PodMetrics(
                name="test-pod",
                namespace="default",
                cpu_usage=0.3,  # Below threshold
                memory_usage=1024.0,
                network=NetworkMetrics(rx_bytes=100.0, tx_bytes=200.0),
                timestamp=datetime.utcnow()
            )
        ]
        mock_monitor_service.get_pod_metrics.return_value = mock_pod_metrics
        
        # Check conditions
        triggered = await alert_service.check_conditions(
            db=test_db,
            deployment_id=test_deployment.id,
            namespace="default"
        )
        
        assert len(triggered) == 0


class TestNotificationSending:
    """Test notification sending functionality"""
    
    @pytest.mark.asyncio
    async def test_send_webhook_notification(self, alert_service):
        """Test sending webhook notification"""
        alert_config = AlertConfiguration(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            condition_type="cpu_threshold",
            threshold_value=0.8,
            notification_channel="webhook",
            notification_config={"url": "https://example.com/webhook"}
        )
        
        triggered_alert = TriggeredAlert(
            alert_id=str(alert_config.id),
            condition_type="cpu_threshold",
            threshold_value=0.8,
            current_value=0.9,
            message="CPU threshold exceeded",
            affected_resource="test-pod",
            timestamp=datetime.utcnow()
        )
        
        # Mock HTTP client
        with patch.object(alert_service.http_client, 'post', new_callable=AsyncMock) as mock_post:
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response
            
            result = await alert_service.send_notification(alert_config, triggered_alert)
            
            assert result is True
            mock_post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_in_app_notification(self, alert_service):
        """Test sending in-app notification"""
        alert_config = AlertConfiguration(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            condition_type="memory_threshold",
            threshold_value=1024.0,
            notification_channel="in_app",
            notification_config={}
        )
        
        triggered_alert = TriggeredAlert(
            alert_id=str(alert_config.id),
            condition_type="memory_threshold",
            threshold_value=1024.0,
            current_value=2048.0,
            message="Memory threshold exceeded",
            affected_resource="test-pod",
            timestamp=datetime.utcnow()
        )
        
        result = await alert_service.send_notification(alert_config, triggered_alert)
        
        # In-app notifications currently just log, so should return True
        assert result is True
