"""
Unit tests for Monitoring API endpoints
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.models import User, Deployment
from app.schemas import PodMetrics, NetworkMetrics, LogEntry, TimeRange
from app.auth import TokenData, get_current_user
import uuid


# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_monitor_api.db"
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
def mock_current_user(test_user):
    """Mock current user authentication"""
    return TokenData(user_id=str(test_user.id), email=test_user.email)


@pytest.fixture
def client(mock_current_user):
    """Create test client with auth override."""
    def override_get_current_user():
        return mock_current_user
    
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    client = TestClient(app)
    yield client
    
    # Clean up overrides
    app.dependency_overrides.clear()


@pytest.fixture
def mock_deployment(test_db, test_user):
    """Create mock deployment."""
    deployment = Deployment(
        id=uuid.uuid4(),
        user_id=test_user.id,
        name="test-deployment",
        cluster_id=uuid.uuid4(),
        compose_content="",
        manifests=[],
        status="completed"
    )
    test_db.add(deployment)
    test_db.commit()
    test_db.refresh(deployment)
    return deployment


@pytest.fixture
def mock_pod_metrics():
    """Create mock pod metrics."""
    timestamp = datetime.now()
    return [
        PodMetrics(
            name="test-pod-1",
            namespace="default",
            cpu_usage=0.5,
            memory_usage=1073741824,
            network=NetworkMetrics(rx_bytes=1000000, tx_bytes=2000000),
            timestamp=timestamp
        ),
        PodMetrics(
            name="test-pod-2",
            namespace="default",
            cpu_usage=0.3,
            memory_usage=536870912,
            network=NetworkMetrics(rx_bytes=500000, tx_bytes=1000000),
            timestamp=timestamp
        )
    ]


@pytest.fixture
def mock_log_entries():
    """Create mock log entries."""
    timestamp = datetime.now()
    return [
        LogEntry(
            timestamp=timestamp,
            pod_name="test-pod-1",
            container_name="app",
            message="Application started",
            level="info"
        ),
        LogEntry(
            timestamp=timestamp + timedelta(seconds=1),
            pod_name="test-pod-1",
            container_name="app",
            message="Processing request",
            level="info"
        ),
        LogEntry(
            timestamp=timestamp + timedelta(seconds=2),
            pod_name="test-pod-1",
            container_name="app",
            message="ERROR: Connection failed",
            level="error"
        )
    ]


def test_get_metrics_success(client, test_db, mock_deployment, mock_pod_metrics):
    """Test successful metrics retrieval."""
    deployment_id = str(mock_deployment.id)
    
    with patch('app.routers.monitor.get_monitor_service') as mock_get_service:
        mock_service = MagicMock()
        mock_service.get_pod_metrics = AsyncMock(return_value=mock_pod_metrics)
        mock_get_service.return_value = mock_service
        
        # Make request
        response = client.get(f"/api/metrics/{deployment_id}")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["name"] == "test-pod-1"
        assert data[0]["cpu_usage"] == 0.5
        assert data[1]["name"] == "test-pod-2"
        assert data[1]["cpu_usage"] == 0.3


def test_get_metrics_with_time_range(client, test_db, mock_deployment, mock_pod_metrics):
    """Test metrics retrieval with time range parameters."""
    deployment_id = str(mock_deployment.id)
    start_time = datetime.now() - timedelta(hours=1)
    end_time = datetime.now()
    
    with patch('app.routers.monitor.get_monitor_service') as mock_get_service:
        mock_service = MagicMock()
        mock_service.get_pod_metrics = AsyncMock(return_value=mock_pod_metrics)
        mock_get_service.return_value = mock_service
        
        # Make request with time range
        response = client.get(
            f"/api/metrics/{deployment_id}",
            params={
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            }
        )
        
        # Verify response
        assert response.status_code == 200
        
        # Verify service was called with time range
        mock_service.get_pod_metrics.assert_called_once()
        call_kwargs = mock_service.get_pod_metrics.call_args[1]
        assert "time_range" in call_kwargs
        assert isinstance(call_kwargs["time_range"], TimeRange)


def test_get_metrics_with_pod_filter(client, test_db, mock_deployment, mock_pod_metrics):
    """Test metrics retrieval with pod name filter."""
    deployment_id = str(mock_deployment.id)
    
    with patch('app.routers.monitor.get_monitor_service') as mock_get_service:
        mock_service = MagicMock()
        mock_service.get_pod_metrics = AsyncMock(return_value=[mock_pod_metrics[0]])
        mock_get_service.return_value = mock_service
        
        # Make request with pod filter
        response = client.get(
            f"/api/metrics/{deployment_id}",
            params={"pod_name": "test-pod-1"}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "test-pod-1"


def test_get_metrics_deployment_not_found(client, test_db):
    """Test metrics retrieval with non-existent deployment."""
    deployment_id = str(uuid.uuid4())
    
    # Make request
    response = client.get(f"/api/metrics/{deployment_id}")
    
    # Verify response
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_logs_success(client, test_db, mock_deployment, mock_log_entries):
    """Test successful log retrieval."""
    deployment_id = str(mock_deployment.id)
    
    with patch('app.routers.monitor.get_monitor_service') as mock_get_service:
        # Create async iterator for log streaming
        async def mock_stream_logs(*args, **kwargs):
            for entry in mock_log_entries:
                yield entry
        
        mock_service = MagicMock()
        mock_service.stream_logs = mock_stream_logs
        mock_get_service.return_value = mock_service
        
        # Make request
        response = client.get(f"/api/logs/{deployment_id}")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert data[0]["pod_name"] == "test-pod-1"
        assert data[0]["message"] == "Application started"
        assert data[2]["level"] == "error"


def test_get_logs_with_filters(client, test_db, mock_deployment, mock_log_entries):
    """Test log retrieval with filters."""
    deployment_id = str(mock_deployment.id)
    
    with patch('app.routers.monitor.get_monitor_service') as mock_get_service:
        # Create async iterator for log streaming
        async def mock_stream_logs(*args, **kwargs):
            # Return only error logs
            for entry in mock_log_entries:
                if entry.level == "error":
                    yield entry
        
        mock_service = MagicMock()
        mock_service.stream_logs = mock_stream_logs
        mock_get_service.return_value = mock_service
        
        # Make request with filters
        response = client.get(
            f"/api/logs/{deployment_id}",
            params={
                "pod_name": "test-pod-1",
                "level": "error",
                "search": "Connection"
            }
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["level"] == "error"


def test_get_logs_with_limit(client, test_db, mock_deployment, mock_log_entries):
    """Test log retrieval respects limit parameter."""
    deployment_id = str(mock_deployment.id)
    
    with patch('app.routers.monitor.get_monitor_service') as mock_get_service:
        # Create async iterator for log streaming
        async def mock_stream_logs(*args, **kwargs):
            for entry in mock_log_entries:
                yield entry
        
        mock_service = MagicMock()
        mock_service.stream_logs = mock_stream_logs
        mock_get_service.return_value = mock_service
        
        # Make request with limit
        response = client.get(
            f"/api/logs/{deployment_id}",
            params={"limit": 2}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2  # Should respect limit


def test_get_logs_deployment_not_found(client, test_db):
    """Test log retrieval with non-existent deployment."""
    deployment_id = str(uuid.uuid4())
    
    # Make request
    response = client.get(f"/api/logs/{deployment_id}")
    
    # Verify response
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_stream_logs_endpoint_exists(client, test_db, mock_deployment):
    """Test that stream logs endpoint exists and returns proper response."""
    deployment_id = str(mock_deployment.id)
    
    with patch('app.routers.monitor.get_monitor_service') as mock_get_service:
        # Create async iterator for log streaming
        async def mock_stream_logs(*args, **kwargs):
            yield LogEntry(
                timestamp=datetime.now(),
                pod_name="test-pod",
                container_name="app",
                message="Test log",
                level="info"
            )
        
        mock_service = MagicMock()
        mock_service.stream_logs = mock_stream_logs
        mock_get_service.return_value = mock_service
        
        # Make request
        response = client.get(f"/api/logs/{deployment_id}/stream")
        
        # Verify response
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/event-stream; charset=utf-8"


def test_get_metrics_handles_service_error(client, test_db, mock_deployment):
    """Test metrics endpoint handles service errors gracefully."""
    deployment_id = str(mock_deployment.id)
    
    with patch('app.routers.monitor.get_monitor_service') as mock_get_service:
        mock_service = MagicMock()
        mock_service.get_pod_metrics = AsyncMock(side_effect=Exception("Prometheus unavailable"))
        mock_get_service.return_value = mock_service
        
        # Make request
        response = client.get(f"/api/metrics/{deployment_id}")
        
        # Verify response
        assert response.status_code == 500
        assert "Failed to fetch metrics" in response.json()["detail"]


def test_get_logs_handles_service_error(client, test_db, mock_deployment):
    """Test logs endpoint handles service errors gracefully."""
    deployment_id = str(mock_deployment.id)
    
    with patch('app.routers.monitor.get_monitor_service') as mock_get_service:
        # Create async iterator that raises error
        async def mock_stream_logs(*args, **kwargs):
            raise Exception("Loki unavailable")
            yield  # Never reached
        
        mock_service = MagicMock()
        mock_service.stream_logs = mock_stream_logs
        mock_get_service.return_value = mock_service
        
        # Make request
        response = client.get(f"/api/logs/{deployment_id}")
        
        # Verify response
        assert response.status_code == 500
        assert "Failed to fetch logs" in response.json()["detail"]
