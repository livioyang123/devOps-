"""
API endpoints for Docker Compose to Kubernetes conversion.
"""
from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from app.schemas import (
    ConversionRequest,
    ConversionResponse,
    KubernetesManifest,
    ErrorResponse,
)
from app.celery_app import celery_app

router = APIRouter(prefix="/api/convert", tags=["convert"])


@router.post("", response_model=Dict[str, Any])
async def convert_compose(request: ConversionRequest) -> Dict[str, Any]:
    """
    Convert Docker Compose to Kubernetes manifests asynchronously.
    
    This endpoint creates a Celery task for async conversion and returns
    a task ID that can be used to poll for status and results.
    
    Args:
        request: ConversionRequest with compose structure, model, and parameters
        
    Returns:
        Dict with task_id for status polling
        
    Raises:
        HTTPException: If task creation fails
    """
    try:
        # Convert compose structure to dict for serialization
        compose_dict = request.compose_structure.model_dump()
        
        # Reconstruct compose content from structure (simplified)
        # In a real scenario, we'd want to preserve the original content
        compose_content = _reconstruct_compose_yaml(compose_dict)
        
        # Prepare model parameters
        parameters = request.parameters or {}
        
        # Create Celery task
        task = celery_app.send_task(
            'app.celery_app.convert_compose_to_k8s',
            args=[compose_content, request.model, parameters]
        )
        
        return {
            "task_id": task.id,
            "status": "pending",
            "message": "Conversion task created successfully",
            "poll_url": f"/api/convert/status/{task.id}"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create conversion task: {str(e)}",
        )


@router.get("/status/{task_id}", response_model=Dict[str, Any])
async def get_conversion_status(task_id: str) -> Dict[str, Any]:
    """
    Get the status of a conversion task.
    
    Args:
        task_id: The Celery task ID
        
    Returns:
        Dict with task status and result if completed
        
    Raises:
        HTTPException: If task not found or status check fails
    """
    try:
        # Get task result
        task_result = celery_app.AsyncResult(task_id)
        
        response = {
            "task_id": task_id,
            "status": task_result.state,
        }
        
        if task_result.state == 'PENDING':
            response["message"] = "Task is waiting to be processed"
        elif task_result.state == 'STARTED':
            response["message"] = "Task is currently being processed"
        elif task_result.state == 'SUCCESS':
            response["message"] = "Task completed successfully"
            response["result"] = task_result.result
        elif task_result.state == 'FAILURE':
            response["message"] = "Task failed"
            response["error"] = str(task_result.info)
        elif task_result.state == 'RETRY':
            response["message"] = "Task is being retried"
        else:
            response["message"] = f"Task state: {task_result.state}"
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task status: {str(e)}",
        )


@router.post("/sync", response_model=ConversionResponse)
async def convert_compose_sync(request: ConversionRequest) -> ConversionResponse:
    """
    Convert Docker Compose to Kubernetes manifests synchronously.
    
    This endpoint performs the conversion immediately and waits for the result.
    Use this for testing or when immediate results are needed.
    For production, use the async endpoint (/api/convert) instead.
    
    Args:
        request: ConversionRequest with compose structure, model, and parameters
        
    Returns:
        ConversionResponse with generated manifests
        
    Raises:
        HTTPException: If conversion fails
    """
    try:
        from app.services.parser import ParserService
        from app.services.converter import ConverterService
        from app.services.llm_router import LLMRouter, ModelParameters
        from app.services.llm_providers import OpenAIProvider, AnthropicProvider, GoogleProvider, OllamaProvider
        from app.services.cache import cache_service
        from app.config import settings

        # Build providers dict from configured API keys
        providers = {}
        if settings.openai_api_key:
            providers["openai"] = OpenAIProvider(api_key=settings.openai_api_key)
        if settings.anthropic_api_key:
            providers["anthropic"] = AnthropicProvider(api_key=settings.anthropic_api_key)
        if settings.google_api_key:
            providers["google"] = GoogleProvider(api_key=settings.google_api_key)
        if settings.ollama_endpoint:
            providers["ollama"] = OllamaProvider(endpoint=settings.ollama_endpoint)

        # Detect missing provider before attempting conversion
        if not providers:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No LLM provider is configured. Set OPENAI_API_KEY, ANTHROPIC_API_KEY, or configure Ollama.",
            )

        # Initialize services
        parser = ParserService()
        llm_router = LLMRouter(providers=providers)
        converter = ConverterService(llm_router, cache_service)
        
        # Reconstruct compose content from structure
        compose_dict = request.compose_structure.model_dump()
        compose_content = _reconstruct_compose_yaml(compose_dict)
        
        # Convert model parameters
        model_params = ModelParameters(**request.parameters) if request.parameters else ModelParameters()
        
        # Convert to Kubernetes manifests
        manifests, cached, conversion_time = converter.convert_to_k8s(
            compose=request.compose_structure,
            compose_content=compose_content,
            model=request.model,
            parameters=model_params
        )
        
        return ConversionResponse(
            manifests=manifests,
            cached=cached,
            conversion_time=conversion_time
        )

    except HTTPException:
        # Re-raise HTTPExceptions unchanged (e.g., the 503 raised above)
        raise
    except ValueError as e:
        error_msg = str(e)
        # Provider-configuration errors (e.g., "Provider 'X' not configured") → 503
        if "not configured" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=error_msg,
            )
        # Request-payload validation errors (e.g., invalid model name format) → 400
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        )
    except Exception as e:
        error_msg = str(e)
        # LLMRouter exhausted all retries → 503 (service unavailable, not a client error)
        if "retry attempts failed" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=error_msg,
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to convert Docker Compose: {error_msg}",
        )


def _reconstruct_compose_yaml(compose_dict: Dict[str, Any]) -> str:
    """
    Reconstruct Docker Compose YAML from parsed structure.
    
    This is a simplified reconstruction. In production, we should
    preserve the original YAML content from the upload.
    
    Args:
        compose_dict: Parsed compose structure as dict
        
    Returns:
        YAML string
    """
    import yaml
    
    # Build compose structure
    compose = {}
    
    if compose_dict.get('version'):
        compose['version'] = compose_dict['version']
    
    # Reconstruct services
    if compose_dict.get('services'):
        compose['services'] = {}
        for service in compose_dict['services']:
            service_name = service['name']
            service_config = {}
            
            if service.get('image'):
                service_config['image'] = service['image']
            
            if service.get('build'):
                service_config['build'] = service['build']
            
            if service.get('ports'):
                service_config['ports'] = [
                    f"{p['host']}:{p['container']}" if p.get('host') else p['container']
                    for p in service['ports']
                ]
            
            if service.get('environment'):
                service_config['environment'] = service['environment']
            
            if service.get('volumes'):
                service_config['volumes'] = service['volumes']
            
            if service.get('depends_on'):
                service_config['depends_on'] = service['depends_on']
            
            if service.get('command'):
                service_config['command'] = service['command']
            
            if service.get('networks'):
                service_config['networks'] = service['networks']
            
            compose['services'][service_name] = service_config
    
    # Reconstruct volumes
    if compose_dict.get('volumes'):
        compose['volumes'] = {}
        for volume in compose_dict['volumes']:
            volume_name = volume['name']
            volume_config = {}
            
            if volume.get('driver'):
                volume_config['driver'] = volume['driver']
            
            if volume.get('driver_opts'):
                volume_config['driver_opts'] = volume['driver_opts']
            
            if volume.get('external'):
                volume_config['external'] = volume['external']
            
            compose['volumes'][volume_name] = volume_config if volume_config else None
    
    # Reconstruct networks
    if compose_dict.get('networks'):
        compose['networks'] = {}
        for network in compose_dict['networks']:
            network_name = network['name']
            network_config = {}
            
            if network.get('driver'):
                network_config['driver'] = network['driver']
            
            if network.get('external'):
                network_config['external'] = network['external']
            
            if network.get('ipam'):
                network_config['ipam'] = network['ipam']
            
            compose['networks'][network_name] = network_config if network_config else None
    
    return yaml.dump(compose, default_flow_style=False, sort_keys=False)
