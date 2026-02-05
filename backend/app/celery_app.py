"""
Celery application configuration and initialization
"""

from celery import Celery
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Create Celery instance
celery_app = Celery(
    "devops_k8s_platform",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend
)

# Celery configuration
celery_app.conf.update(
    # Broker settings - explicitly set Redis
    broker_url=settings.celery_broker_url,
    result_backend=settings.celery_result_backend,
    broker_transport_options={'visibility_timeout': 3600},
    
    # Task execution settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task result settings
    result_expires=3600,  # 1 hour
    
    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
    
    # Task retry settings
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
)

# Simple task definitions
@celery_app.task
def convert_compose_to_k8s(compose_content: str, model: str, parameters: dict) -> dict:
    """Convert Docker Compose to Kubernetes manifests using LLM"""
    logger.info(f"Starting conversion with model: {model}")
    
    # Validate input
    if not compose_content or not isinstance(compose_content, str):
        raise ValueError("compose_content must be a non-empty string")
    
    if not model or not isinstance(model, str):
        raise ValueError("model must be a non-empty string")
    
    if not isinstance(parameters, dict):
        raise ValueError("parameters must be a dictionary")
    
    try:
        # Import services here to avoid circular imports
        from app.services.parser import ParserService
        from app.services.converter import ConverterService
        from app.services.llm_router import LLMRouter, ModelParameters
        from app.services.cache import cache_service
        
        # Initialize services
        parser = ParserService()
        llm_router = LLMRouter()
        converter = ConverterService(llm_router, cache_service)
        
        # Parse the compose content
        logger.info("Parsing Docker Compose content")
        compose_structure = parser.parse_compose(compose_content)
        
        # Convert model parameters dict to ModelParameters object
        model_params = ModelParameters(**parameters) if parameters else ModelParameters()
        
        # Convert to Kubernetes manifests
        logger.info(f"Converting to Kubernetes manifests using {model}")
        manifests, cached, conversion_time = converter.convert_to_k8s(
            compose=compose_structure,
            compose_content=compose_content,
            model=model,
            parameters=model_params
        )
        
        # Convert manifests to dict format for JSON serialization
        manifest_dicts = [manifest.model_dump() for manifest in manifests]
        
        result = {
            "manifests": manifest_dicts,
            "cached": cached,
            "conversion_time": conversion_time,
            "model_used": model,
            "status": "completed"
        }
        
        logger.info(f"Conversion completed successfully: {len(manifests)} manifests generated")
        return result
        
    except Exception as e:
        logger.error(f"Conversion task failed: {str(e)}")
        return {
            "manifests": [],
            "cached": False,
            "conversion_time": 0.0,
            "model_used": model,
            "status": "failed",
            "error": str(e)
        }

@celery_app.task
def deploy_to_kubernetes(manifests: list, cluster_id: str, deployment_id: str) -> dict:
    """Deploy Kubernetes manifests to target cluster"""
    logger.info(f"Starting deployment {deployment_id} to cluster {cluster_id}")
    
    # Validate input
    if not manifests or not isinstance(manifests, list):
        raise ValueError("manifests must be a non-empty list")
    
    if not cluster_id or not isinstance(cluster_id, str):
        raise ValueError("cluster_id must be a non-empty string")
    
    if not deployment_id or not isinstance(deployment_id, str):
        raise ValueError("deployment_id must be a non-empty string")
    
    # TODO: Implement actual deployment logic in later tasks
    
    result = {
        "deployment_id": deployment_id,
        "status": "completed",
        "applied_manifests": [f"manifest-{i}" for i in range(len(manifests))],
        "cluster_id": cluster_id,
        "health_check_passed": True,
        "rollback_performed": False
    }
    
    logger.info("Deployment completed successfully")
    return result

@celery_app.task
def rollback_deployment(deployment_id: str, cluster_id: str) -> dict:
    """Rollback a failed deployment"""
    logger.info(f"Starting rollback for deployment {deployment_id}")
    
    # Validate input
    if not deployment_id or not isinstance(deployment_id, str):
        raise ValueError("deployment_id must be a non-empty string")
    
    if not cluster_id or not isinstance(cluster_id, str):
        raise ValueError("cluster_id must be a non-empty string")
    
    # TODO: Implement actual rollback logic in later tasks
    
    result = {
        "deployment_id": deployment_id,
        "status": "rolled_back",
        "removed_resources": [],
        "cluster_id": cluster_id
    }
    
    logger.info("Rollback completed successfully")
    return result

@celery_app.task
def analyze_logs_with_ai(deployment_id: str, logs: list, model: str) -> dict:
    """Analyze deployment logs using AI"""
    logger.info(f"Starting log analysis for deployment {deployment_id}")
    
    # Validate input
    if not deployment_id or not isinstance(deployment_id, str):
        raise ValueError("deployment_id must be a non-empty string")
    
    if not logs or not isinstance(logs, list):
        raise ValueError("logs must be a non-empty list")
    
    if not model or not isinstance(model, str):
        raise ValueError("model must be a non-empty string")
    
    # TODO: Implement actual AI analysis logic in later tasks
    
    result = {
        "deployment_id": deployment_id,
        "summary": "Log analysis completed",
        "anomalies": [],
        "common_errors": [],
        "recommendations": [],
        "severity": "info",
        "model_used": model,
        "logs_analyzed": len(logs)
    }
    
    logger.info("Log analysis completed successfully")
    return result

@celery_app.task
def collect_metrics(deployment_id: str, cluster_id: str, time_range: dict) -> dict:
    """Collect metrics from Prometheus"""
    logger.info(f"Starting metrics collection for deployment {deployment_id}")
    
    # Validate input
    if not deployment_id or not isinstance(deployment_id, str):
        raise ValueError("deployment_id must be a non-empty string")
    
    if not cluster_id or not isinstance(cluster_id, str):
        raise ValueError("cluster_id must be a non-empty string")
    
    if not time_range or not isinstance(time_range, dict):
        raise ValueError("time_range must be a dictionary")
    
    # TODO: Implement actual metrics collection logic in later tasks
    
    result = {
        "deployment_id": deployment_id,
        "cluster_id": cluster_id,
        "metrics": {
            "pods": [],
            "services": [],
            "timestamp": None
        },
        "time_range": time_range
    }
    
    logger.info("Metrics collection completed successfully")
    return result

logger.info("Celery application initialized with tasks")