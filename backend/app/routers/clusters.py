"""
Cluster management API endpoints for Kubernetes cluster configurations
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging
import uuid
import json
from datetime import datetime

from app.database import get_db
from app.auth import get_current_user, TokenData
from app.models import User, Cluster
from app.schemas import (
    ClusterConfig,
    ClusterResponse,
    ClusterListResponse,
)
from app.encryption import encrypt_credentials, decrypt_credentials

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/clusters", tags=["clusters"])


@router.post("", response_model=ClusterResponse, status_code=status.HTTP_201_CREATED)
async def create_cluster(
    cluster_config: ClusterConfig,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Create a new Kubernetes cluster configuration
    
    Encrypts cluster credentials before storage using AES-256 encryption.
    Supports cluster types: minikube, kind, GKE, EKS, AKS.
    """
    try:
        # Validate cluster type
        valid_types = ["minikube", "kind", "gke", "eks", "aks"]
        if cluster_config.type not in valid_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid cluster type. Must be one of: {', '.join(valid_types)}"
            )
        
        # Validate cluster name is not empty
        if not cluster_config.name or not cluster_config.name.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cluster name cannot be empty"
            )
        
        # Check if cluster with same name already exists for this user
        user_uuid = uuid.UUID(current_user.user_id)
        existing_cluster = db.query(Cluster).filter(
            Cluster.user_id == user_uuid,
            Cluster.name == cluster_config.name
        ).first()
        
        if existing_cluster:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cluster with name '{cluster_config.name}' already exists"
            )
        
        # Encrypt cluster configuration (contains sensitive credentials)
        config_json = json.dumps(cluster_config.config)
        encrypted_config = encrypt_credentials(config_json)
        
        # Create new cluster
        user_uuid = uuid.UUID(current_user.user_id)
        new_cluster = Cluster(
            id=uuid.uuid4(),
            user_id=user_uuid,
            name=cluster_config.name,
            type=cluster_config.type,
            config={"encrypted": encrypted_config},  # Store encrypted config
            is_active=True
        )
        
        db.add(new_cluster)
        db.commit()
        db.refresh(new_cluster)
        
        logger.info(f"Created cluster configuration: {cluster_config.name} (type: {cluster_config.type})")
        
        return ClusterResponse(
            id=str(new_cluster.id),
            name=new_cluster.name,
            type=new_cluster.type,
            is_active=new_cluster.is_active,
            created_at=new_cluster.created_at,
            updated_at=new_cluster.updated_at
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create cluster configuration: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create cluster configuration: {str(e)}"
        )


@router.get("", response_model=ClusterListResponse)
async def list_clusters(
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get all cluster configurations for the current user
    
    Returns cluster information without exposing sensitive credentials.
    """
    try:
        user_uuid = uuid.UUID(current_user.user_id)
        clusters = db.query(Cluster).filter(
            Cluster.user_id == user_uuid
        ).order_by(Cluster.created_at.desc()).all()
        
        response_clusters = [
            ClusterResponse(
                id=str(cluster.id),
                name=cluster.name,
                type=cluster.type,
                is_active=cluster.is_active,
                created_at=cluster.created_at,
                updated_at=cluster.updated_at
            )
            for cluster in clusters
        ]
        
        logger.info(f"Retrieved {len(response_clusters)} cluster configurations")
        return ClusterListResponse(clusters=response_clusters)
    
    except Exception as e:
        logger.error(f"Failed to retrieve cluster configurations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve cluster configurations: {str(e)}"
        )


@router.delete("/{cluster_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cluster(
    cluster_id: str,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Delete a cluster configuration
    
    Removes the cluster configuration from the database.
    """
    try:
        # Validate UUID format
        try:
            cluster_uuid = uuid.UUID(cluster_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid cluster ID format"
            )
        
        # Find cluster
        user_uuid = uuid.UUID(current_user.user_id)
        cluster = db.query(Cluster).filter(
            Cluster.id == cluster_uuid,
            Cluster.user_id == user_uuid
        ).first()
        
        if not cluster:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cluster with ID '{cluster_id}' not found"
            )
        
        # Check if cluster has active deployments
        if cluster.deployments:
            active_deployments = [d for d in cluster.deployments if d.status in ['pending', 'in_progress']]
            if active_deployments:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot delete cluster with active deployments. Please wait for deployments to complete or fail."
                )
        
        cluster_name = cluster.name
        db.delete(cluster)
        db.commit()
        
        logger.info(f"Deleted cluster configuration: {cluster_name}")
        return None
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete cluster configuration: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete cluster configuration: {str(e)}"
        )
