"""
Celery tasks for Docker Compose to Kubernetes conversion
"""

from app.tasks.base import BaseTask
from celery.utils.log import get_task_logger
from typing import Dict, List, Any

logger = get_task_logger(__name__)


def convert_compose_to_k8s(compose_content: str, model: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert Docker Compose to Kubernetes manifests using LLM
    
    This function is now implemented in app.celery_app.convert_compose_to_k8s
    and is kept here for reference and potential future use.
    
    Args:
        compose_content: Docker Compose YAML content
        model: LLM model to use for conversion
        parameters: Model parameters (temperature, max_tokens, etc.)
    
    Returns:
        Dict containing generated manifests and metadata
    """
    try:
        # Validate input
        if not compose_content or not isinstance(compose_content, str):
            raise ValueError("compose_content must be a non-empty string")
        
        if not model or not isinstance(model, str):
            raise ValueError("model must be a non-empty string")
        
        if not isinstance(parameters, dict):
            raise ValueError("parameters must be a dictionary")
        
        logger.info(f"Starting conversion with model: {model}")
        
        # Import services
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