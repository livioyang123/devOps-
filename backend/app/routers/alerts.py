"""
Alert configuration API endpoints.

Provides endpoints for creating, listing, and deleting alert configurations.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from uuid import UUID
import logging

from app.database import get_db
from app.auth import get_current_user
from app.models import User, AlertConfiguration
from app.schemas import (
    AlertConfigCreate,
    AlertConfigResponse,
    ErrorResponse
)
from app.services.alert import get_alert_service, AlertService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/alerts",
    tags=["alerts"]
)


@router.post(
    "",
    response_model=AlertConfigResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def create_alert(
    alert_config: AlertConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    alert_service: AlertService = Depends(get_alert_service)
) -> AlertConfigResponse:
    """
    Create a new alert configuration.
    
    Creates an alert that monitors specified conditions and sends notifications
    when conditions are met.
    
    **Supported condition types:**
    - `cpu_threshold`: Alert when CPU usage exceeds threshold (in cores)
    - `memory_threshold`: Alert when memory usage exceeds threshold (in MB)
    - `pod_restart_count`: Alert when pod restart count exceeds threshold
    - `deployment_failure`: Alert when deployment fails
    
    **Supported notification channels:**
    - `email`: Send email notification (requires `recipient` in notification_config)
    - `webhook`: Call webhook URL (requires `url` in notification_config)
    - `in_app`: Show in-app notification
    
    **Example request:**
    ```json
    {
        "deployment_id": "123e4567-e89b-12d3-a456-426614174000",
        "condition_type": "cpu_threshold",
        "threshold_value": 0.8,
        "notification_channel": "email",
        "notification_config": {
            "recipient": "admin@example.com"
        }
    }
    ```
    
    Args:
        alert_config: Alert configuration data
        db: Database session
        current_user: Authenticated user
        alert_service: Alert service instance
    
    Returns:
        Created alert configuration
    
    Raises:
        HTTPException: If validation fails or creation fails
    """
    try:
        # Register alert
        db_alert = alert_service.register_alert(
            db=db,
            alert_config=alert_config,
            user_id=current_user.id
        )
        
        # Convert to response model
        return AlertConfigResponse(
            id=str(db_alert.id),
            user_id=str(db_alert.user_id),
            deployment_id=str(db_alert.deployment_id) if db_alert.deployment_id else None,
            condition_type=db_alert.condition_type,
            threshold_value=db_alert.threshold_value,
            notification_channel=db_alert.notification_channel,
            notification_config=db_alert.notification_config,
            is_active=db_alert.is_active,
            created_at=db_alert.created_at
        )
        
    except ValueError as e:
        logger.warning(f"Invalid alert configuration: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Failed to create alert: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create alert configuration"
        )


@router.get(
    "",
    response_model=List[AlertConfigResponse],
    responses={
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def list_alerts(
    deployment_id: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[AlertConfigResponse]:
    """
    List all alert configurations for the current user.
    
    Optionally filter by deployment_id to get alerts for a specific deployment.
    
    **Query parameters:**
    - `deployment_id` (optional): Filter alerts by deployment ID
    
    Args:
        deployment_id: Optional deployment ID filter
        db: Database session
        current_user: Authenticated user
    
    Returns:
        List of alert configurations
    
    Raises:
        HTTPException: If query fails
    """
    try:
        # Build query
        query = db.query(AlertConfiguration).filter(
            AlertConfiguration.user_id == current_user.id
        )
        
        # Apply deployment filter if provided
        if deployment_id:
            try:
                deployment_uuid = UUID(deployment_id)
                query = query.filter(AlertConfiguration.deployment_id == deployment_uuid)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid deployment_id format"
                )
        
        # Execute query
        alerts = query.order_by(AlertConfiguration.created_at.desc()).all()
        
        # Convert to response models
        return [
            AlertConfigResponse(
                id=str(alert.id),
                user_id=str(alert.user_id),
                deployment_id=str(alert.deployment_id) if alert.deployment_id else None,
                condition_type=alert.condition_type,
                threshold_value=alert.threshold_value,
                notification_channel=alert.notification_channel,
                notification_config=alert.notification_config,
                is_active=alert.is_active,
                created_at=alert.created_at
            )
            for alert in alerts
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list alerts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve alert configurations"
        )


@router.delete(
    "/{alert_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def delete_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> None:
    """
    Delete an alert configuration.
    
    Only the user who created the alert can delete it.
    
    Args:
        alert_id: Alert configuration ID
        db: Database session
        current_user: Authenticated user
    
    Raises:
        HTTPException: If alert not found or deletion fails
    """
    try:
        # Parse alert ID
        try:
            alert_uuid = UUID(alert_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid alert_id format"
            )
        
        # Find alert
        alert = db.query(AlertConfiguration).filter(
            AlertConfiguration.id == alert_uuid,
            AlertConfiguration.user_id == current_user.id
        ).first()
        
        if not alert:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Alert configuration not found"
            )
        
        # Delete alert
        db.delete(alert)
        db.commit()
        
        logger.info(
            f"Deleted alert {alert_id}",
            extra={
                "alert_id": alert_id,
                "user_id": str(current_user.id)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete alert: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete alert configuration"
        )
