"""
Integration tests for WebSocket endpoint

Tests the WebSocket endpoint's ability to handle connections and
receive real-time deployment updates.
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime

from app.main import app
from app.services.websocket_handler import websocket_handler
from app.schemas import ProgressUpdate, DeploymentStatus


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


def test_websocket_connection_establishment(client):
    """Test that WebSocket connection can be established."""
    deployment_id = "test-deployment-123"
    
    with client.websocket_connect(f"/ws/deployment/{deployment_id}") as websocket:
        # Receive connection confirmation
        data = websocket.receive_json()
        
        assert data["type"] == "connection_established"
        assert data["deployment_id"] == deployment_id
        assert "timestamp" in data
        assert data["message"] == "WebSocket connection established successfully"


def test_websocket_ping_pong(client):
    """Test that WebSocket responds to ping messages."""
    deployment_id = "test-deployment-123"
    
    with client.websocket_connect(f"/ws/deployment/{deployment_id}") as websocket:
        # Receive connection confirmation
        websocket.receive_json()
        
        # Send ping
        websocket.send_text("ping")
        
        # Receive pong
        data = websocket.receive_json()
        assert data["type"] == "pong"
        assert data["deployment_id"] == deployment_id


@pytest.mark.asyncio
async def test_websocket_receives_progress_updates(client):
    """Test that WebSocket receives progress updates."""
    deployment_id = "test-deployment-456"
    
    with client.websocket_connect(f"/ws/deployment/{deployment_id}") as websocket:
        # Receive connection confirmation
        websocket.receive_json()
        
        # Send a progress update through the handler
        update = ProgressUpdate(
            deployment_id=deployment_id,
            status=DeploymentStatus.IN_PROGRESS,
            progress=50,
            current_step="Applying Service manifest",
            applied_manifests=["deployment-web"],
            timestamp=datetime.utcnow()
        )
        
        # Use the global handler to send progress
        await websocket_handler.send_progress(deployment_id, update)
        
        # Receive the progress update
        data = websocket.receive_json()
        
        assert data["type"] == "progress_update"
        assert data["deployment_id"] == deployment_id
        assert data["status"] == "in_progress"
        assert data["progress"] == 50
        assert data["current_step"] == "Applying Service manifest"
        assert data["applied_manifests"] == ["deployment-web"]


@pytest.mark.asyncio
async def test_websocket_receives_error_messages(client):
    """Test that WebSocket receives error messages."""
    deployment_id = "test-deployment-789"
    
    with client.websocket_connect(f"/ws/deployment/{deployment_id}") as websocket:
        # Receive connection confirmation
        websocket.receive_json()
        
        # Send an error message through the handler
        error_message = "Deployment failed"
        error_details = {"reason": "Invalid manifest"}
        
        await websocket_handler.send_error(deployment_id, error_message, error_details)
        
        # Receive the error message
        data = websocket.receive_json()
        
        assert data["type"] == "error"
        assert data["deployment_id"] == deployment_id
        assert data["error"] == error_message
        assert data["details"] == error_details


@pytest.mark.asyncio
async def test_websocket_receives_completion_messages(client):
    """Test that WebSocket receives completion messages."""
    deployment_id = "test-deployment-101"
    
    with client.websocket_connect(f"/ws/deployment/{deployment_id}") as websocket:
        # Receive connection confirmation
        websocket.receive_json()
        
        # Send a completion message through the handler
        status = DeploymentStatus.COMPLETED
        message = "Deployment completed successfully"
        details = {"pods_healthy": 3}
        
        await websocket_handler.send_completion(deployment_id, status, message, details)
        
        # Receive the completion message
        data = websocket.receive_json()
        
        assert data["type"] == "completion"
        assert data["deployment_id"] == deployment_id
        assert data["status"] == "completed"
        assert data["message"] == message
        assert data["details"] == details


def test_websocket_status_endpoint(client):
    """Test that WebSocket status endpoint returns connection statistics."""
    response = client.get("/ws/status")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "operational"
    assert "total_connections" in data
    assert "active_deployments" in data
    assert "deployments" in data
    assert isinstance(data["total_connections"], int)
    assert isinstance(data["active_deployments"], int)
    assert isinstance(data["deployments"], dict)


@pytest.mark.asyncio
async def test_multiple_websocket_connections_same_deployment(client):
    """Test that multiple clients can connect to the same deployment."""
    deployment_id = "test-deployment-multi"
    
    with client.websocket_connect(f"/ws/deployment/{deployment_id}") as ws1:
        # Receive connection confirmation for ws1
        ws1.receive_json()
        
        with client.websocket_connect(f"/ws/deployment/{deployment_id}") as ws2:
            # Receive connection confirmation for ws2
            ws2.receive_json()
            
            # Send a progress update
            update = ProgressUpdate(
                deployment_id=deployment_id,
                status=DeploymentStatus.IN_PROGRESS,
                progress=75,
                current_step="Applying Ingress manifest",
                applied_manifests=["deployment-web", "service-web"],
                timestamp=datetime.utcnow()
            )
            
            await websocket_handler.send_progress(deployment_id, update)
            
            # Both WebSockets should receive the update
            data1 = ws1.receive_json()
            data2 = ws2.receive_json()
            
            assert data1["type"] == "progress_update"
            assert data1["progress"] == 75
            assert data2["type"] == "progress_update"
            assert data2["progress"] == 75
