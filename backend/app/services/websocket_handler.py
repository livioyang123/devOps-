"""
WebSocket Handler Service for Real-Time Deployment Updates

This service manages WebSocket connections for broadcasting real-time
deployment progress updates to connected clients.

Requirements: 6.3, 6.4, 7.2
"""
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set, Optional
import logging
import json
from datetime import datetime

from app.schemas import ProgressUpdate, DeploymentStatus

logger = logging.getLogger(__name__)


class WebSocketHandler:
    """
    Manages WebSocket connections and broadcasts deployment progress updates.
    
    This handler maintains a registry of active WebSocket connections per
    deployment and provides methods to broadcast progress updates to all
    connected clients.
    """
    
    def __init__(self):
        """Initialize the WebSocket handler with empty connection registry."""
        # Dictionary mapping deployment_id to set of WebSocket connections
        self.connections: Dict[str, Set[WebSocket]] = {}
        logger.info("WebSocketHandler initialized")
    
    async def connect(self, deployment_id: str, websocket: WebSocket) -> None:
        """
        Register a new WebSocket connection for a deployment.
        
        Args:
            deployment_id: Unique identifier for the deployment
            websocket: WebSocket connection to register
            
        Requirements: 6.3
        """
        try:
            # Accept the WebSocket connection
            await websocket.accept()
            
            # Initialize connection set for this deployment if needed
            if deployment_id not in self.connections:
                self.connections[deployment_id] = set()
            
            # Add connection to the set
            self.connections[deployment_id].add(websocket)
            
            logger.info(
                f"WebSocket connected for deployment {deployment_id}. "
                f"Total connections: {len(self.connections[deployment_id])}"
            )
            
            # Send initial connection confirmation
            await websocket.send_json({
                "type": "connection_established",
                "deployment_id": deployment_id,
                "timestamp": datetime.utcnow().isoformat(),
                "message": "WebSocket connection established successfully"
            })
            
        except Exception as e:
            logger.error(
                f"Error connecting WebSocket for deployment {deployment_id}: {str(e)}"
            )
            raise
    
    async def disconnect(self, deployment_id: str, websocket: WebSocket) -> None:
        """
        Unregister a WebSocket connection and clean up resources.
        
        Args:
            deployment_id: Unique identifier for the deployment
            websocket: WebSocket connection to unregister
            
        Requirements: 6.3
        """
        try:
            # Remove connection from the set
            if deployment_id in self.connections:
                self.connections[deployment_id].discard(websocket)
                
                # Clean up empty connection sets
                if not self.connections[deployment_id]:
                    del self.connections[deployment_id]
                    logger.info(
                        f"All WebSocket connections closed for deployment {deployment_id}"
                    )
                else:
                    logger.info(
                        f"WebSocket disconnected for deployment {deployment_id}. "
                        f"Remaining connections: {len(self.connections[deployment_id])}"
                    )
            
        except Exception as e:
            logger.error(
                f"Error disconnecting WebSocket for deployment {deployment_id}: {str(e)}"
            )
    
    async def send_progress(
        self,
        deployment_id: str,
        update: ProgressUpdate
    ) -> None:
        """
        Broadcast a progress update to all connected clients for a deployment.
        
        This method sends the progress update to all WebSocket connections
        registered for the specified deployment. If a connection fails,
        it is automatically removed from the registry.
        
        Args:
            deployment_id: Unique identifier for the deployment
            update: ProgressUpdate containing status, progress, and details
            
        Requirements: 6.4, 7.2
        """
        if deployment_id not in self.connections:
            logger.warning(
                f"No WebSocket connections found for deployment {deployment_id}"
            )
            return
        
        # Get all connections for this deployment
        connections = self.connections[deployment_id].copy()
        
        # Prepare the update message
        message = {
            "type": "progress_update",
            "deployment_id": update.deployment_id,
            "status": update.status.value,
            "progress": update.progress,
            "current_step": update.current_step,
            "applied_manifests": update.applied_manifests,
            "timestamp": update.timestamp.isoformat()
        }
        
        # Track failed connections for cleanup
        failed_connections = set()
        
        # Broadcast to all connections
        for websocket in connections:
            try:
                await websocket.send_json(message)
                logger.debug(
                    f"Progress update sent to WebSocket for deployment {deployment_id}: "
                    f"{update.status.value} - {update.progress}%"
                )
            except WebSocketDisconnect:
                logger.warning(
                    f"WebSocket disconnected during send for deployment {deployment_id}"
                )
                failed_connections.add(websocket)
            except Exception as e:
                logger.error(
                    f"Error sending progress update to WebSocket for deployment "
                    f"{deployment_id}: {str(e)}"
                )
                failed_connections.add(websocket)
        
        # Clean up failed connections
        for websocket in failed_connections:
            await self.disconnect(deployment_id, websocket)
    
    async def send_error(
        self,
        deployment_id: str,
        error_message: str,
        error_details: Optional[Dict] = None
    ) -> None:
        """
        Broadcast an error message to all connected clients for a deployment.
        
        Args:
            deployment_id: Unique identifier for the deployment
            error_message: Human-readable error message
            error_details: Optional dictionary with additional error details
            
        Requirements: 6.8
        """
        if deployment_id not in self.connections:
            logger.warning(
                f"No WebSocket connections found for deployment {deployment_id}"
            )
            return
        
        # Get all connections for this deployment
        connections = self.connections[deployment_id].copy()
        
        # Prepare the error message
        message = {
            "type": "error",
            "deployment_id": deployment_id,
            "error": error_message,
            "details": error_details or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Track failed connections for cleanup
        failed_connections = set()
        
        # Broadcast to all connections
        for websocket in connections:
            try:
                await websocket.send_json(message)
                logger.info(
                    f"Error message sent to WebSocket for deployment {deployment_id}"
                )
            except WebSocketDisconnect:
                logger.warning(
                    f"WebSocket disconnected during error send for deployment {deployment_id}"
                )
                failed_connections.add(websocket)
            except Exception as e:
                logger.error(
                    f"Error sending error message to WebSocket for deployment "
                    f"{deployment_id}: {str(e)}"
                )
                failed_connections.add(websocket)
        
        # Clean up failed connections
        for websocket in failed_connections:
            await self.disconnect(deployment_id, websocket)
    
    async def send_completion(
        self,
        deployment_id: str,
        status: DeploymentStatus,
        message: str,
        details: Optional[Dict] = None
    ) -> None:
        """
        Broadcast a completion message to all connected clients for a deployment.
        
        Args:
            deployment_id: Unique identifier for the deployment
            status: Final deployment status (COMPLETED, FAILED, ROLLED_BACK)
            message: Human-readable completion message
            details: Optional dictionary with additional details
            
        Requirements: 6.5, 7.4
        """
        if deployment_id not in self.connections:
            logger.warning(
                f"No WebSocket connections found for deployment {deployment_id}"
            )
            return
        
        # Get all connections for this deployment
        connections = self.connections[deployment_id].copy()
        
        # Prepare the completion message
        completion_message = {
            "type": "completion",
            "deployment_id": deployment_id,
            "status": status.value,
            "message": message,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Track failed connections for cleanup
        failed_connections = set()
        
        # Broadcast to all connections
        for websocket in connections:
            try:
                await websocket.send_json(completion_message)
                logger.info(
                    f"Completion message sent to WebSocket for deployment {deployment_id}: "
                    f"{status.value}"
                )
            except WebSocketDisconnect:
                logger.warning(
                    f"WebSocket disconnected during completion send for deployment {deployment_id}"
                )
                failed_connections.add(websocket)
            except Exception as e:
                logger.error(
                    f"Error sending completion message to WebSocket for deployment "
                    f"{deployment_id}: {str(e)}"
                )
                failed_connections.add(websocket)
        
        # Clean up failed connections
        for websocket in failed_connections:
            await self.disconnect(deployment_id, websocket)
    
    def get_connection_count(self, deployment_id: str) -> int:
        """
        Get the number of active connections for a deployment.
        
        Args:
            deployment_id: Unique identifier for the deployment
            
        Returns:
            Number of active WebSocket connections
        """
        return len(self.connections.get(deployment_id, set()))
    
    def get_total_connections(self) -> int:
        """
        Get the total number of active connections across all deployments.
        
        Returns:
            Total number of active WebSocket connections
        """
        return sum(len(conns) for conns in self.connections.values())


# Global WebSocket handler instance
websocket_handler = WebSocketHandler()
