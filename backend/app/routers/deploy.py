"""
Deployment API Router

This module provides endpoints for deploying Kubernetes manifests to clusters.

Requirements: 6.1, 6.3, 6.4, 6.5, 6.8, 20.1, 20.2
"""

import uuid
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Deployment, Cluster
from app.schemas import (
    DeploymentRequest,
    DeploymentResponse,
    DeploymentStatus,
    ErrorResponse
)
from app.tasks.deployment import deploy_to_kubernetes
from app.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["deployment"])


@router.post("/deploy", response_model=DeploymentResponse)
async def deploy_manifests(
    request: DeploymentRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
) -> DeploymentResponse:
    """
    Deploy Kubernetes manifests to target cluster
    
    This endpoint:
    1. Validates the cluster exists and is accessible
    2. Creates a deployment record in the database
    3. Initiates an asynchronous Celery task for deployment
    4. Returns deployment ID and WebSocket URL for real-time updates
    
    Args:
        request: DeploymentRequest containing manifests, cluster_id, and namespace
        db: Database session
        current_user: Authenticated user information
        
    Returns:
        DeploymentResponse with deployment_id, status, and websocket_url
        
    Raises:
        HTTPException: If cluster not found or validation fails
        
    Requirements: 6.1, 6.3, 6.4, 6.5, 6.8, 20.1, 20.2
    """
    try:
        user_id = current_user.user_id
        
        # Validate cluster exists and belongs to user
        cluster = db.query(Cluster).filter(
            Cluster.id == uuid.UUID(request.cluster_id),
            Cluster.user_id == uuid.UUID(user_id),
            Cluster.is_active == True
        ).first()
        
        if not cluster:
            logger.warning(
                f"Cluster {request.cluster_id} not found or not accessible for user {user_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cluster {request.cluster_id} not found or not accessible"
            )
        
        # Generate deployment ID
        deployment_id = str(uuid.uuid4())
        
        logger.info(
            f"Creating deployment {deployment_id} for user {user_id} "
            f"on cluster {cluster.name} ({cluster.type})"
        )
        
        # Create deployment record in database
        deployment = Deployment(
            id=uuid.UUID(deployment_id),
            user_id=uuid.UUID(user_id),
            name=f"deployment-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
            cluster_id=cluster.id,
            compose_content="",  # Will be populated if needed
            manifests=[m.model_dump() for m in request.manifests],
            status=DeploymentStatus.PENDING.value,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(deployment)
        db.commit()
        db.refresh(deployment)
        
        logger.info(f"Deployment record created: {deployment_id}")
        
        # Convert manifests to dict format for Celery
        manifest_dicts = [m.model_dump() for m in request.manifests]
        
        # Initiate asynchronous deployment task
        task = deploy_to_kubernetes.apply_async(
            args=[manifest_dicts, request.cluster_id, deployment_id],
            kwargs={"namespace": request.namespace}
        )
        
        logger.info(
            f"Deployment task {task.id} initiated for deployment {deployment_id}"
        )
        
        # Update deployment status to IN_PROGRESS
        deployment.status = DeploymentStatus.IN_PROGRESS.value
        db.commit()
        
        # Construct WebSocket URL
        websocket_url = f"ws://localhost:8000/ws/deployment/{deployment_id}"
        
        return DeploymentResponse(
            deployment_id=deployment_id,
            status=DeploymentStatus.IN_PROGRESS,
            websocket_url=websocket_url
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating deployment: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create deployment: {str(e)}"
        )


@router.get("/deploy/{deployment_id}", response_model=dict)
async def get_deployment_status(
    deployment_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
) -> dict:
    """
    Get deployment status and details
    
    This endpoint allows clients to poll for deployment status if WebSocket
    connection is unavailable.
    
    Args:
        deployment_id: Unique deployment identifier
        db: Database session
        current_user: Authenticated user information
        
    Returns:
        Dict containing deployment status and details
        
    Raises:
        HTTPException: If deployment not found or not accessible
    """
    try:
        user_id = current_user.user_id
        
        # Query deployment
        deployment = db.query(Deployment).filter(
            Deployment.id == uuid.UUID(deployment_id),
            Deployment.user_id == uuid.UUID(user_id)
        ).first()
        
        if not deployment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Deployment {deployment_id} not found"
            )
        
        return {
            "deployment_id": str(deployment.id),
            "name": deployment.name,
            "status": deployment.status,
            "cluster_id": str(deployment.cluster_id),
            "created_at": deployment.created_at.isoformat(),
            "updated_at": deployment.updated_at.isoformat(),
            "deployed_at": deployment.deployed_at.isoformat() if deployment.deployed_at else None,
            "error_message": deployment.error_message,
            "manifest_count": len(deployment.manifests) if deployment.manifests else 0
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving deployment status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve deployment status: {str(e)}"
        )
