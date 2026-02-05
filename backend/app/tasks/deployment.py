"""
Celery tasks for Kubernetes deployment operations
"""

import asyncio
from datetime import datetime
from app.celery_app import celery_app
from app.tasks.base import BaseTask
from celery.utils.log import get_task_logger
from typing import Dict, List, Any, Optional

from app.services.deployer import DeployerService
from app.services.websocket_handler import websocket_handler
from app.schemas import KubernetesManifest, DeploymentStatus, ProgressUpdate
from app.database import SessionLocal
from app.models import Deployment
import uuid

logger = get_task_logger(__name__)


def update_deployment_status(
    deployment_id: str,
    status: str,
    error_message: Optional[str] = None,
    deployed_at: Optional[datetime] = None
):
    """
    Update deployment status in database
    
    Args:
        deployment_id: Deployment identifier
        status: New status value
        error_message: Optional error message
        deployed_at: Optional deployment completion timestamp
    """
    db = SessionLocal()
    try:
        deployment = db.query(Deployment).filter(
            Deployment.id == uuid.UUID(deployment_id)
        ).first()
        
        if deployment:
            deployment.status = status
            deployment.updated_at = datetime.utcnow()
            
            if error_message:
                deployment.error_message = error_message
            
            if deployed_at:
                deployment.deployed_at = deployed_at
            
            db.commit()
            logger.info(f"Updated deployment {deployment_id} status to {status}")
        else:
            logger.warning(f"Deployment {deployment_id} not found in database")
            
    except Exception as e:
        logger.error(f"Error updating deployment status: {str(e)}")
        db.rollback()
    finally:
        db.close()


@celery_app.task(base=BaseTask, bind=True)
def deploy_to_kubernetes(
    self,
    manifests: List[Dict[str, Any]],
    cluster_id: str,
    deployment_id: str,
    namespace: Optional[str] = None
) -> Dict[str, Any]:
    """
    Deploy Kubernetes manifests to target cluster
    
    This task integrates DeployerService and WebSocketHandler to:
    - Apply manifests to the Kubernetes cluster
    - Send real-time progress updates via WebSocket
    - Perform post-deployment health checks
    - Trigger rollback on failure
    - Store deployment record in database
    
    Args:
        manifests: List of Kubernetes manifest dictionaries
        cluster_id: Target cluster identifier
        deployment_id: Unique deployment identifier
        namespace: Optional namespace override
    
    Returns:
        Dict containing deployment results and status
        
    Requirements: 6.1, 6.3, 6.4, 6.5, 6.8, 20.1, 20.2
    """
    try:
        # Validate input
        validated_input = self.validate_input(
            manifests=manifests,
            cluster_id=cluster_id,
            deployment_id=deployment_id
        )
        
        # Convert manifest dicts to KubernetesManifest objects
        manifest_objects = [
            KubernetesManifest(**m) for m in manifests
        ]
        
        # Initialize DeployerService with WebSocket handler
        deployer = DeployerService(websocket_handler=websocket_handler)
        
        # Send initial progress update
        asyncio.run(
            websocket_handler.send_progress(
                deployment_id,
                ProgressUpdate(
                    deployment_id=deployment_id,
                    status=DeploymentStatus.IN_PROGRESS,
                    progress=5,
                    current_step="Initializing deployment",
                    applied_manifests=[],
                    timestamp=datetime.utcnow()
                )
            )
        )
        
        # Deploy manifests
        logger.info(f"Starting deployment {deployment_id} with {len(manifest_objects)} manifests")
        deployment_result = asyncio.run(
            deployer.deploy(
                manifests=manifest_objects,
                cluster_id=cluster_id,
                deployment_id=deployment_id,
                namespace=namespace
            )
        )
        
        if not deployment_result.success:
            # Deployment failed, update database
            update_deployment_status(
                deployment_id,
                DeploymentStatus.FAILED.value,
                error_message=deployment_result.error_message
            )
            
            # Send error notification
            logger.error(f"Deployment {deployment_id} failed: {deployment_result.error_message}")
            
            asyncio.run(
                websocket_handler.send_error(
                    deployment_id,
                    deployment_result.error_message or "Deployment failed",
                    {
                        "applied_manifests": deployment_result.applied_manifests,
                        "failed_manifests": deployment_result.failed_manifests
                    }
                )
            )
            
            asyncio.run(
                websocket_handler.send_completion(
                    deployment_id,
                    DeploymentStatus.FAILED,
                    f"Deployment failed: {deployment_result.error_message}",
                    {
                        "applied_manifests": deployment_result.applied_manifests,
                        "failed_manifests": deployment_result.failed_manifests,
                        "rollback_performed": True
                    }
                )
            )
            
            return {
                "deployment_id": deployment_id,
                "status": "failed",
                "applied_manifests": deployment_result.applied_manifests,
                "failed_manifests": deployment_result.failed_manifests,
                "error_message": deployment_result.error_message,
                "rollback_performed": True
            }
        
        # Deployment successful, perform health checks
        logger.info(f"Deployment {deployment_id} completed, performing health checks")
        
        asyncio.run(
            websocket_handler.send_progress(
                deployment_id,
                ProgressUpdate(
                    deployment_id=deployment_id,
                    status=DeploymentStatus.IN_PROGRESS,
                    progress=95,
                    current_step="Performing post-deployment health checks",
                    applied_manifests=deployment_result.applied_manifests,
                    timestamp=datetime.utcnow()
                )
            )
        )
        
        # Perform health check
        health_result = asyncio.run(
            deployer.health_check(
                namespace=namespace or "default",
                deployment_id=deployment_id,
                wait_seconds=30
            )
        )
        
        # Update database with completion
        update_deployment_status(
            deployment_id,
            DeploymentStatus.COMPLETED.value,
            deployed_at=datetime.utcnow()
        )
        
        # Send completion notification
        if health_result.healthy:
            logger.info(f"Deployment {deployment_id} completed successfully with healthy pods")
            
            asyncio.run(
                websocket_handler.send_completion(
                    deployment_id,
                    DeploymentStatus.COMPLETED,
                    "Deployment completed successfully",
                    {
                        "applied_manifests": deployment_result.applied_manifests,
                        "health_check": {
                            "healthy": True,
                            "message": health_result.message,
                            "pod_count": len(health_result.pod_statuses)
                        }
                    }
                )
            )
            
            return {
                "deployment_id": deployment_id,
                "status": "completed",
                "applied_manifests": deployment_result.applied_manifests,
                "cluster_id": cluster_id,
                "health_check_passed": True,
                "health_check_message": health_result.message,
                "pod_statuses": health_result.pod_statuses,
                "rollback_performed": False
            }
        else:
            logger.warning(f"Deployment {deployment_id} completed but health checks failed")
            
            asyncio.run(
                websocket_handler.send_completion(
                    deployment_id,
                    DeploymentStatus.COMPLETED,
                    "Deployment completed with health check warnings",
                    {
                        "applied_manifests": deployment_result.applied_manifests,
                        "health_check": {
                            "healthy": False,
                            "message": health_result.message,
                            "unhealthy_pods": health_result.unhealthy_pods
                        }
                    }
                )
            )
            
            return {
                "deployment_id": deployment_id,
                "status": "completed",
                "applied_manifests": deployment_result.applied_manifests,
                "cluster_id": cluster_id,
                "health_check_passed": False,
                "health_check_message": health_result.message,
                "unhealthy_pods": health_result.unhealthy_pods,
                "rollback_performed": False
            }
        
    except Exception as e:
        logger.error(f"Deployment task failed with exception: {e}", exc_info=True)
        
        # Update database with failure
        update_deployment_status(
            deployment_id,
            DeploymentStatus.FAILED.value,
            error_message=str(e)
        )
        
        # Send error notification
        asyncio.run(
            websocket_handler.send_error(
                deployment_id,
                f"Deployment failed with error: {str(e)}",
                {"error_type": type(e).__name__}
            )
        )
        
        asyncio.run(
            websocket_handler.send_completion(
                deployment_id,
                DeploymentStatus.FAILED,
                f"Deployment failed: {str(e)}",
                {"error_type": type(e).__name__}
            )
        )
        
        raise
    finally:
        self.cleanup()
    
    def validate_input(self, **kwargs) -> Dict[str, Any]:
        """Validate deployment task input"""
        manifests = kwargs.get("manifests")
        cluster_id = kwargs.get("cluster_id")
        deployment_id = kwargs.get("deployment_id")
        
        if not manifests or not isinstance(manifests, list):
            raise ValueError("manifests must be a non-empty list")
        
        if not cluster_id or not isinstance(cluster_id, str):
            raise ValueError("cluster_id must be a non-empty string")
        
        if not deployment_id or not isinstance(deployment_id, str):
            raise ValueError("deployment_id must be a non-empty string")
        
        return kwargs

