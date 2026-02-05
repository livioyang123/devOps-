"""
Alert Service for monitoring conditions and triggering notifications.

This service monitors deployment metrics and triggers alerts when configured
conditions are met.
"""

import logging
import smtplib
import httpx
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session
from app.models import AlertConfiguration, Deployment
from app.schemas import (
    AlertConfigCreate,
    AlertConfigResponse,
    TriggeredAlert,
    PodMetrics
)
from app.services.monitor import MonitorService
from app.config import settings

logger = logging.getLogger(__name__)


class AlertService:
    """
    Service for managing alert configurations and monitoring conditions.
    
    Supports alert types:
    - CPU threshold exceeded
    - Memory threshold exceeded
    - Pod restart count
    - Deployment failure
    
    Notification channels:
    - Email
    - Webhook
    - In-app notifications
    """
    
    def __init__(
        self,
        monitor_service: Optional[MonitorService] = None
    ):
        """
        Initialize AlertService.
        
        Args:
            monitor_service: MonitorService instance for metrics collection
        """
        self.monitor_service = monitor_service or MonitorService()
        self.http_client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """Close HTTP client connections."""
        await self.http_client.aclose()
        if self.monitor_service:
            await self.monitor_service.close()
    
    def register_alert(
        self,
        db: Session,
        alert_config: AlertConfigCreate,
        user_id: UUID
    ) -> AlertConfiguration:
        """
        Register a new alert configuration.
        
        Args:
            db: Database session
            alert_config: Alert configuration data
            user_id: User ID creating the alert
        
        Returns:
            Created AlertConfiguration
        
        Raises:
            ValueError: If configuration is invalid
        """
        try:
            # Validate alert configuration
            self._validate_alert_config(alert_config)
            
            # Convert deployment_id from string to UUID if provided
            deployment_uuid = None
            if alert_config.deployment_id:
                try:
                    deployment_uuid = UUID(alert_config.deployment_id)
                except (ValueError, AttributeError):
                    raise ValueError(f"Invalid deployment_id format: {alert_config.deployment_id}")
            
            # Create alert configuration
            db_alert = AlertConfiguration(
                user_id=user_id,
                deployment_id=deployment_uuid,
                condition_type=alert_config.condition_type,
                threshold_value=alert_config.threshold_value,
                notification_channel=alert_config.notification_channel,
                notification_config=alert_config.notification_config,
                is_active=True
            )
            
            db.add(db_alert)
            db.commit()
            db.refresh(db_alert)
            
            logger.info(
                f"Registered alert {db_alert.id} for user {user_id}",
                extra={
                    "alert_id": str(db_alert.id),
                    "user_id": str(user_id),
                    "condition_type": alert_config.condition_type
                }
            )
            
            return db_alert
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to register alert: {e}")
            raise
    
    def _validate_alert_config(self, alert_config: AlertConfigCreate) -> None:
        """
        Validate alert configuration.
        
        Args:
            alert_config: Alert configuration to validate
        
        Raises:
            ValueError: If configuration is invalid
        """
        # Validate condition type
        valid_condition_types = [
            "cpu_threshold",
            "memory_threshold",
            "pod_restart_count",
            "deployment_failure"
        ]
        if alert_config.condition_type not in valid_condition_types:
            raise ValueError(
                f"Invalid condition_type: {alert_config.condition_type}. "
                f"Must be one of: {', '.join(valid_condition_types)}"
            )
        
        # Validate threshold value for threshold-based alerts
        if alert_config.condition_type in ["cpu_threshold", "memory_threshold", "pod_restart_count"]:
            if alert_config.threshold_value is None:
                raise ValueError(
                    f"threshold_value is required for {alert_config.condition_type}"
                )
            if alert_config.threshold_value <= 0:
                raise ValueError("threshold_value must be positive")
        
        # Validate notification channel
        valid_channels = ["email", "webhook", "in_app"]
        if alert_config.notification_channel not in valid_channels:
            raise ValueError(
                f"Invalid notification_channel: {alert_config.notification_channel}. "
                f"Must be one of: {', '.join(valid_channels)}"
            )
        
        # Validate notification config based on channel
        if alert_config.notification_channel == "email":
            if "recipient" not in alert_config.notification_config:
                raise ValueError("notification_config must contain 'recipient' for email channel")
        elif alert_config.notification_channel == "webhook":
            if "url" not in alert_config.notification_config:
                raise ValueError("notification_config must contain 'url' for webhook channel")
    
    async def check_conditions(
        self,
        db: Session,
        deployment_id: UUID,
        namespace: str = "default"
    ) -> List[TriggeredAlert]:
        """
        Evaluate all alert conditions for a deployment.
        
        Args:
            db: Database session
            deployment_id: Deployment ID to check
            namespace: Kubernetes namespace
        
        Returns:
            List of triggered alerts
        """
        try:
            # Get active alerts for this deployment
            alerts = db.query(AlertConfiguration).filter(
                AlertConfiguration.deployment_id == deployment_id,
                AlertConfiguration.is_active == True
            ).all()
            
            if not alerts:
                logger.debug(f"No active alerts for deployment {deployment_id}")
                return []
            
            # Get deployment info
            deployment = db.query(Deployment).filter(
                Deployment.id == deployment_id
            ).first()
            
            if not deployment:
                logger.warning(f"Deployment {deployment_id} not found")
                return []
            
            # Collect current metrics
            pod_metrics = await self.monitor_service.get_pod_metrics(namespace)
            
            # Check each alert condition
            triggered_alerts = []
            for alert in alerts:
                triggered = await self._evaluate_condition(
                    alert,
                    deployment,
                    pod_metrics
                )
                if triggered:
                    triggered_alerts.append(triggered)
            
            logger.info(
                f"Checked {len(alerts)} alerts for deployment {deployment_id}, "
                f"{len(triggered_alerts)} triggered"
            )
            
            return triggered_alerts
            
        except Exception as e:
            logger.error(f"Failed to check alert conditions: {e}")
            raise
    
    async def _evaluate_condition(
        self,
        alert: AlertConfiguration,
        deployment: Deployment,
        pod_metrics: List[PodMetrics]
    ) -> Optional[TriggeredAlert]:
        """
        Evaluate a single alert condition.
        
        Args:
            alert: Alert configuration
            deployment: Deployment being monitored
            pod_metrics: Current pod metrics
        
        Returns:
            TriggeredAlert if condition is met, None otherwise
        """
        try:
            condition_type = alert.condition_type
            threshold = alert.threshold_value
            
            # CPU threshold check
            if condition_type == "cpu_threshold":
                for pod in pod_metrics:
                    if pod.cpu_usage > threshold:
                        return TriggeredAlert(
                            alert_id=str(alert.id),
                            condition_type=condition_type,
                            threshold_value=threshold,
                            current_value=pod.cpu_usage,
                            message=f"CPU usage {pod.cpu_usage:.2f} cores exceeds threshold {threshold} cores for pod {pod.name}",
                            affected_resource=pod.name,
                            timestamp=datetime.utcnow()
                        )
            
            # Memory threshold check
            elif condition_type == "memory_threshold":
                for pod in pod_metrics:
                    # Convert bytes to MB for comparison
                    memory_mb = pod.memory_usage / (1024 * 1024)
                    if memory_mb > threshold:
                        return TriggeredAlert(
                            alert_id=str(alert.id),
                            condition_type=condition_type,
                            threshold_value=threshold,
                            current_value=memory_mb,
                            message=f"Memory usage {memory_mb:.2f} MB exceeds threshold {threshold} MB for pod {pod.name}",
                            affected_resource=pod.name,
                            timestamp=datetime.utcnow()
                        )
            
            # Pod restart count check
            elif condition_type == "pod_restart_count":
                # This would require querying Kubernetes API for restart counts
                # For now, we'll log that this check is not yet implemented
                logger.debug(f"Pod restart count check not yet implemented for alert {alert.id}")
            
            # Deployment failure check
            elif condition_type == "deployment_failure":
                if deployment.status == "failed" or deployment.status == "rolled_back":
                    return TriggeredAlert(
                        alert_id=str(alert.id),
                        condition_type=condition_type,
                        threshold_value=None,
                        current_value=None,
                        message=f"Deployment {deployment.name} failed with status: {deployment.status}",
                        affected_resource=deployment.name,
                        timestamp=datetime.utcnow()
                    )
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to evaluate condition for alert {alert.id}: {e}")
            return None
    
    async def send_notification(
        self,
        alert_config: AlertConfiguration,
        triggered_alert: TriggeredAlert
    ) -> bool:
        """
        Send notification through configured channel.
        
        Args:
            alert_config: Alert configuration with notification settings
            triggered_alert: Triggered alert details
        
        Returns:
            True if notification sent successfully, False otherwise
        """
        try:
            channel = alert_config.notification_channel
            
            if channel == "email":
                return await self._send_email_notification(
                    alert_config.notification_config,
                    triggered_alert
                )
            elif channel == "webhook":
                return await self._send_webhook_notification(
                    alert_config.notification_config,
                    triggered_alert
                )
            elif channel == "in_app":
                return await self._send_in_app_notification(
                    alert_config.notification_config,
                    triggered_alert
                )
            else:
                logger.error(f"Unknown notification channel: {channel}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False
    
    async def _send_email_notification(
        self,
        config: Dict[str, Any],
        triggered_alert: TriggeredAlert
    ) -> bool:
        """
        Send email notification.
        
        Args:
            config: Email configuration (recipient, etc.)
            triggered_alert: Triggered alert details
        
        Returns:
            True if email sent successfully
        """
        try:
            recipient = config.get("recipient")
            if not recipient:
                logger.error("No recipient specified in email config")
                return False
            
            # Create email message
            msg = MIMEMultipart()
            msg["From"] = settings.smtp_from_email
            msg["To"] = recipient
            msg["Subject"] = f"Alert: {triggered_alert.condition_type}"
            
            # Email body
            body = f"""
Alert Triggered

Condition: {triggered_alert.condition_type}
Message: {triggered_alert.message}
Affected Resource: {triggered_alert.affected_resource}
Timestamp: {triggered_alert.timestamp}

"""
            if triggered_alert.threshold_value is not None:
                body += f"Threshold: {triggered_alert.threshold_value}\n"
            if triggered_alert.current_value is not None:
                body += f"Current Value: {triggered_alert.current_value}\n"
            
            msg.attach(MIMEText(body, "plain"))
            
            # Send email
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                if settings.smtp_use_tls:
                    server.starttls()
                if settings.smtp_username and settings.smtp_password:
                    server.login(settings.smtp_username, settings.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email notification sent to {recipient}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False
    
    async def _send_webhook_notification(
        self,
        config: Dict[str, Any],
        triggered_alert: TriggeredAlert
    ) -> bool:
        """
        Send webhook notification.
        
        Args:
            config: Webhook configuration (url, headers, etc.)
            triggered_alert: Triggered alert details
        
        Returns:
            True if webhook called successfully
        """
        try:
            url = config.get("url")
            if not url:
                logger.error("No URL specified in webhook config")
                return False
            
            # Prepare payload
            payload = {
                "alert_id": triggered_alert.alert_id,
                "condition_type": triggered_alert.condition_type,
                "message": triggered_alert.message,
                "affected_resource": triggered_alert.affected_resource,
                "timestamp": triggered_alert.timestamp.isoformat(),
                "threshold_value": triggered_alert.threshold_value,
                "current_value": triggered_alert.current_value
            }
            
            # Get custom headers if provided
            headers = config.get("headers", {})
            headers["Content-Type"] = "application/json"
            
            # Send webhook
            response = await self.http_client.post(
                url,
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            
            logger.info(f"Webhook notification sent to {url}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")
            return False
    
    async def _send_in_app_notification(
        self,
        config: Dict[str, Any],
        triggered_alert: TriggeredAlert
    ) -> bool:
        """
        Send in-app notification.
        
        Args:
            config: In-app notification configuration
            triggered_alert: Triggered alert details
        
        Returns:
            True if notification stored successfully
        """
        try:
            # In-app notifications would typically be stored in a database
            # or sent via WebSocket to connected clients
            # For now, we'll just log the notification
            logger.info(
                f"In-app notification: {triggered_alert.message}",
                extra={
                    "alert_id": triggered_alert.alert_id,
                    "condition_type": triggered_alert.condition_type,
                    "affected_resource": triggered_alert.affected_resource
                }
            )
            
            # TODO: Implement actual in-app notification storage/delivery
            # This could involve:
            # 1. Storing notification in database
            # 2. Broadcasting via WebSocket to connected users
            # 3. Updating notification count in user session
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send in-app notification: {e}")
            return False


# Singleton instance
_alert_service: Optional[AlertService] = None


def get_alert_service() -> AlertService:
    """
    Get or create AlertService singleton instance.
    
    Returns:
        AlertService instance
    """
    global _alert_service
    if _alert_service is None:
        _alert_service = AlertService()
    return _alert_service
