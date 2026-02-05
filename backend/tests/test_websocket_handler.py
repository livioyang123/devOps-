"""
Unit tests for WebSocket Handler Service

Tests the WebSocket handler's ability to manage connections and broadcast
progress updates for deployment operations.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.websocket_handler import WebSocketHandler
from app.schemas import ProgressUpdate, DeploymentStatus


@pytest.fixture
def handler():
    """Create a fresh WebSocket handler for each test."""
    return WebSocketHandler()


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket connection."""
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    ws.receive_text = AsyncMock()
    return ws


@pytest.mark.asyncio
async def test_connect_registers_websocket(handler, mock_websocket):
    """Test that connect() registers a WebSocket connection."""
    deployment_id = "test-deployment-123"
    
    await handler.connect(deployment_id, mock_websocket)
    
    # Verify WebSocket was accepted
    mock_websocket.accept.assert_called_once()
    
    # Verify connection was registered
    assert deployment_id in handler.connections
    assert mock_websocket in handler.connections[deployment_id]
    assert handler.get_connection_count(deployment_id) == 1
    
    # Verify confirmation message was sent
    mock_websocket.send_json.assert_called_once()
    call_args = mock_websocket.send_json.call_args[0][0]
    assert call_args["type"] == "connection_established"
    assert call_args["deployment_id"] == deployment_id


@pytest.mark.asyncio
async def test_connect_multiple_websockets(handler, mock_websocket):
    """Test that multiple WebSockets can connect to the same deployment."""
    deployment_id = "test-deployment-123"
    ws1 = mock_websocket
    ws2 = AsyncMock()
    ws2.accept = AsyncMock()
    ws2.send_json = AsyncMock()
    
    await handler.connect(deployment_id, ws1)
    await handler.connect(deployment_id, ws2)
    
    # Verify both connections are registered
    assert handler.get_connection_count(deployment_id) == 2
    assert ws1 in handler.connections[deployment_id]
    assert ws2 in handler.connections[deployment_id]


@pytest.mark.asyncio
async def test_disconnect_removes_websocket(handler, mock_websocket):
    """Test that disconnect() removes a WebSocket connection."""
    deployment_id = "test-deployment-123"
    
    # First connect
    await handler.connect(deployment_id, mock_websocket)
    assert handler.get_connection_count(deployment_id) == 1
    
    # Then disconnect
    await handler.disconnect(deployment_id, mock_websocket)
    
    # Verify connection was removed
    assert deployment_id not in handler.connections


@pytest.mark.asyncio
async def test_disconnect_cleans_up_empty_sets(handler):
    """Test that disconnect() removes empty connection sets."""
    deployment_id = "test-deployment-123"
    ws1 = AsyncMock()
    ws1.accept = AsyncMock()
    ws1.send_json = AsyncMock()
    ws2 = AsyncMock()
    ws2.accept = AsyncMock()
    ws2.send_json = AsyncMock()
    
    # Connect two WebSockets
    await handler.connect(deployment_id, ws1)
    await handler.connect(deployment_id, ws2)
    assert handler.get_connection_count(deployment_id) == 2
    
    # Disconnect first WebSocket
    await handler.disconnect(deployment_id, ws1)
    assert handler.get_connection_count(deployment_id) == 1
    assert deployment_id in handler.connections
    
    # Disconnect second WebSocket
    await handler.disconnect(deployment_id, ws2)
    assert handler.get_connection_count(deployment_id) == 0
    assert deployment_id not in handler.connections


@pytest.mark.asyncio
async def test_send_progress_broadcasts_to_all_connections(handler):
    """Test that send_progress() broadcasts to all connected WebSockets."""
    deployment_id = "test-deployment-123"
    ws1 = AsyncMock()
    ws1.accept = AsyncMock()
    ws1.send_json = AsyncMock()
    ws2 = AsyncMock()
    ws2.accept = AsyncMock()
    ws2.send_json = AsyncMock()
    
    # Connect two WebSockets
    await handler.connect(deployment_id, ws1)
    await handler.connect(deployment_id, ws2)
    
    # Reset mock call counts after connection
    ws1.send_json.reset_mock()
    ws2.send_json.reset_mock()
    
    # Create progress update
    update = ProgressUpdate(
        deployment_id=deployment_id,
        status=DeploymentStatus.IN_PROGRESS,
        progress=50,
        current_step="Applying Service manifest",
        applied_manifests=["deployment-web"],
        timestamp=datetime.utcnow()
    )
    
    # Send progress update
    await handler.send_progress(deployment_id, update)
    
    # Verify both WebSockets received the update
    assert ws1.send_json.call_count == 1
    assert ws2.send_json.call_count == 1
    
    # Verify message content
    call_args = ws1.send_json.call_args[0][0]
    assert call_args["type"] == "progress_update"
    assert call_args["deployment_id"] == deployment_id
    assert call_args["status"] == "in_progress"
    assert call_args["progress"] == 50
    assert call_args["current_step"] == "Applying Service manifest"


@pytest.mark.asyncio
async def test_send_progress_handles_disconnected_websocket(handler):
    """Test that send_progress() handles disconnected WebSockets gracefully."""
    deployment_id = "test-deployment-123"
    ws1 = AsyncMock()
    ws1.accept = AsyncMock()
    ws1.send_json = AsyncMock()
    ws2 = AsyncMock()
    ws2.accept = AsyncMock()
    ws2.send_json = AsyncMock()
    
    # Connect two WebSockets
    await handler.connect(deployment_id, ws1)
    await handler.connect(deployment_id, ws2)
    
    # Reset mock call counts
    ws1.send_json.reset_mock()
    
    # Now simulate ws2 being disconnected when sending
    ws2.send_json = AsyncMock(side_effect=Exception("Connection closed"))
    
    # Create progress update
    update = ProgressUpdate(
        deployment_id=deployment_id,
        status=DeploymentStatus.IN_PROGRESS,
        progress=50,
        current_step="Applying Service manifest",
        applied_manifests=["deployment-web"],
        timestamp=datetime.utcnow()
    )
    
    # Send progress update
    await handler.send_progress(deployment_id, update)
    
    # Verify ws1 received the update
    assert ws1.send_json.call_count == 1
    
    # Verify ws2 was removed from connections after failure
    assert ws2 not in handler.connections[deployment_id]
    assert handler.get_connection_count(deployment_id) == 1


@pytest.mark.asyncio
async def test_send_error_broadcasts_error_message(handler):
    """Test that send_error() broadcasts error messages to all connections."""
    deployment_id = "test-deployment-123"
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    
    # Connect WebSocket
    await handler.connect(deployment_id, ws)
    ws.send_json.reset_mock()
    
    # Send error message
    error_message = "Deployment failed"
    error_details = {"reason": "Invalid manifest"}
    await handler.send_error(deployment_id, error_message, error_details)
    
    # Verify error message was sent
    assert ws.send_json.call_count == 1
    call_args = ws.send_json.call_args[0][0]
    assert call_args["type"] == "error"
    assert call_args["deployment_id"] == deployment_id
    assert call_args["error"] == error_message
    assert call_args["details"] == error_details


@pytest.mark.asyncio
async def test_send_completion_broadcasts_completion_message(handler):
    """Test that send_completion() broadcasts completion messages."""
    deployment_id = "test-deployment-123"
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    
    # Connect WebSocket
    await handler.connect(deployment_id, ws)
    ws.send_json.reset_mock()
    
    # Send completion message
    status = DeploymentStatus.COMPLETED
    message = "Deployment completed successfully"
    details = {"pods_healthy": 3}
    await handler.send_completion(deployment_id, status, message, details)
    
    # Verify completion message was sent
    assert ws.send_json.call_count == 1
    call_args = ws.send_json.call_args[0][0]
    assert call_args["type"] == "completion"
    assert call_args["deployment_id"] == deployment_id
    assert call_args["status"] == "completed"
    assert call_args["message"] == message
    assert call_args["details"] == details


@pytest.mark.asyncio
async def test_get_total_connections(handler):
    """Test that get_total_connections() returns correct count."""
    ws1 = AsyncMock()
    ws1.accept = AsyncMock()
    ws1.send_json = AsyncMock()
    ws2 = AsyncMock()
    ws2.accept = AsyncMock()
    ws2.send_json = AsyncMock()
    ws3 = AsyncMock()
    ws3.accept = AsyncMock()
    ws3.send_json = AsyncMock()
    
    # Connect to different deployments
    await handler.connect("deployment-1", ws1)
    await handler.connect("deployment-1", ws2)
    await handler.connect("deployment-2", ws3)
    
    # Verify total connection count
    assert handler.get_total_connections() == 3


@pytest.mark.asyncio
async def test_send_progress_no_connections(handler):
    """Test that send_progress() handles no connections gracefully."""
    deployment_id = "test-deployment-123"
    
    # Create progress update
    update = ProgressUpdate(
        deployment_id=deployment_id,
        status=DeploymentStatus.IN_PROGRESS,
        progress=50,
        current_step="Applying Service manifest",
        applied_manifests=["deployment-web"],
        timestamp=datetime.utcnow()
    )
    
    # Send progress update (should not raise exception)
    await handler.send_progress(deployment_id, update)
    
    # Verify no connections exist
    assert handler.get_connection_count(deployment_id) == 0
