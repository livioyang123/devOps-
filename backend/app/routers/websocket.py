"""
WebSocket API endpoints for real-time deployment updates.

This module provides WebSocket endpoints for clients to receive
real-time progress updates during deployment operations.

Requirements: 6.3, 6.4, 7.2
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from typing import Optional
import logging

from app.services.websocket_handler import websocket_handler

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/deployment/{deployment_id}")
async def deployment_websocket(
    websocket: WebSocket,
    deployment_id: str
):
    """
    WebSocket endpoint for real-time deployment progress updates.
    
    Clients connect to this endpoint to receive real-time updates about
    deployment progress, including status changes, applied manifests,
    and completion notifications.
    
    Args:
        websocket: WebSocket connection
        deployment_id: Unique identifier for the deployment to monitor
        
    Message Types Sent to Client:
        - connection_established: Confirmation of successful connection
        - progress_update: Deployment progress update with status and details
        - error: Error message if deployment fails
        - completion: Final deployment status when operation completes
        
    Example Progress Update Message:
        {
            "type": "progress_update",
            "deployment_id": "uuid",
            "status": "in_progress",
            "progress": 50,
            "current_step": "Applying Service manifest",
            "applied_manifests": ["deployment-web", "service-web"],
            "timestamp": "2024-01-01T12:00:00"
        }
        
    Example Completion Message:
        {
            "type": "completion",
            "deployment_id": "uuid",
            "status": "completed",
            "message": "Deployment completed successfully",
            "details": {"pods_healthy": 3, "services_created": 2},
            "timestamp": "2024-01-01T12:05:00"
        }
        
    Requirements: 6.3, 6.4, 7.2
    """
    try:
        # Register the WebSocket connection
        await websocket_handler.connect(deployment_id, websocket)
        
        logger.info(
            f"WebSocket connection established for deployment {deployment_id}"
        )
        
        # Keep the connection alive and handle incoming messages
        # (In this implementation, we primarily send updates to clients,
        # but we need to keep the connection open to receive disconnect events)
        try:
            while True:
                # Wait for any message from client (e.g., ping/pong)
                # This keeps the connection alive and allows us to detect disconnects
                data = await websocket.receive_text()
                
                # Handle client messages if needed (e.g., ping/pong)
                if data == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "deployment_id": deployment_id
                    })
                    
        except WebSocketDisconnect:
            logger.info(
                f"WebSocket client disconnected for deployment {deployment_id}"
            )
        except Exception as e:
            logger.error(
                f"Error in WebSocket connection for deployment {deployment_id}: {str(e)}"
            )
        finally:
            # Unregister the WebSocket connection
            await websocket_handler.disconnect(deployment_id, websocket)
            
    except Exception as e:
        logger.error(
            f"Failed to establish WebSocket connection for deployment "
            f"{deployment_id}: {str(e)}"
        )
        # Try to close the connection gracefully
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except:
            pass


@router.get("/ws/status")
async def websocket_status():
    """
    Get WebSocket handler status and connection statistics.
    
    Returns information about active WebSocket connections for monitoring
    and debugging purposes.
    
    Returns:
        Dictionary with connection statistics
    """
    return {
        "status": "operational",
        "total_connections": websocket_handler.get_total_connections(),
        "active_deployments": len(websocket_handler.connections),
        "deployments": {
            deployment_id: websocket_handler.get_connection_count(deployment_id)
            for deployment_id in websocket_handler.connections.keys()
        }
    }
