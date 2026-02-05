"""
Monitoring API Router

This module provides endpoints for collecting metrics and logs from Kubernetes deployments.

Requirements: 8.1, 8.2, 8.3, 8.4, 9.1, 9.3, 9.4, 9.5
"""

import uuid
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Deployment
from app.schemas import (
    PodMetrics,
    LogEntry,
    TimeRange,
    LogFilters,
    ErrorResponse,
    AnalysisRequest,
    AnalysisResult
)
from app.services.monitor import get_monitor_service
from app.services.ai_analyzer import get_ai_analyzer_service
from app.services.llm_router import LLMRouter, ModelParameters
from app.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["monitoring"])


@router.get("/metrics/{deployment_id}", response_model=List[PodMetrics])
async def get_metrics(
    deployment_id: str,
    start_time: Optional[datetime] = Query(None, description="Start time for metrics range"),
    end_time: Optional[datetime] = Query(None, description="End time for metrics range"),
    pod_name: Optional[str] = Query(None, description="Filter by specific pod name"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
) -> List[PodMetrics]:
    """
    Get metrics for a deployment
    
    This endpoint retrieves CPU, memory, and network metrics from Prometheus
    for all pods in a deployment.
    
    Query Parameters:
        - start_time: Optional start time for metrics range (ISO 8601 format)
        - end_time: Optional end time for metrics range (ISO 8601 format)
        - pod_name: Optional filter for specific pod
    
    Args:
        deployment_id: Unique deployment identifier
        start_time: Optional start time for metrics
        end_time: Optional end time for metrics
        pod_name: Optional pod name filter
        db: Database session
        current_user: Authenticated user information
        
    Returns:
        List of PodMetrics containing CPU, memory, and network data
        
    Raises:
        HTTPException: If deployment not found or metrics collection fails
        
    Requirements: 8.1, 8.2, 8.3, 8.4
    """
    try:
        user_id = current_user.user_id
        
        # Validate deployment exists and belongs to user
        deployment = db.query(Deployment).filter(
            Deployment.id == uuid.UUID(deployment_id),
            Deployment.user_id == uuid.UUID(user_id)
        ).first()
        
        if not deployment:
            logger.warning(
                f"Deployment {deployment_id} not found or not accessible for user {user_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Deployment {deployment_id} not found or not accessible"
            )
        
        # Set default time range if not provided (last 5 minutes)
        if not end_time:
            end_time = datetime.utcnow()
        if not start_time:
            start_time = end_time - timedelta(minutes=5)
        
        time_range = TimeRange(start=start_time, end=end_time)
        
        logger.info(
            f"Fetching metrics for deployment {deployment_id}, "
            f"namespace: default, time_range: {start_time} to {end_time}"
        )
        
        # Get monitor service and fetch metrics
        monitor_service = get_monitor_service()
        metrics = await monitor_service.get_pod_metrics(
            namespace="default",
            time_range=time_range,
            pod_name=pod_name
        )
        
        logger.info(f"Retrieved {len(metrics)} pod metrics for deployment {deployment_id}")
        
        return metrics
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching metrics: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch metrics: {str(e)}"
        )


@router.get("/logs/{deployment_id}", response_model=List[LogEntry])
async def get_logs(
    deployment_id: str,
    start_time: Optional[datetime] = Query(None, description="Start time for log range"),
    end_time: Optional[datetime] = Query(None, description="End time for log range"),
    pod_name: Optional[str] = Query(None, description="Filter by specific pod name"),
    container_name: Optional[str] = Query(None, description="Filter by specific container name"),
    level: Optional[str] = Query(None, description="Filter by log level (info, warning, error, debug)"),
    search: Optional[str] = Query(None, description="Search query for full-text log search"),
    limit: Optional[int] = Query(1000, description="Maximum number of log entries to return", ge=1, le=5000),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
) -> List[LogEntry]:
    """
    Get logs for a deployment
    
    This endpoint retrieves logs from Loki for all pods in a deployment
    with support for filtering by pod, container, level, time range, and search query.
    
    Query Parameters:
        - start_time: Optional start time for log range (ISO 8601 format)
        - end_time: Optional end time for log range (ISO 8601 format)
        - pod_name: Optional filter for specific pod
        - container_name: Optional filter for specific container
        - level: Optional filter for log level (info, warning, error, debug)
        - search: Optional search query for full-text search
        - limit: Maximum number of log entries to return (default: 1000, max: 5000)
    
    Args:
        deployment_id: Unique deployment identifier
        start_time: Optional start time for logs
        end_time: Optional end time for logs
        pod_name: Optional pod name filter
        container_name: Optional container name filter
        level: Optional log level filter
        search: Optional search query
        limit: Maximum number of entries
        db: Database session
        current_user: Authenticated user information
        
    Returns:
        List of LogEntry objects
        
    Raises:
        HTTPException: If deployment not found or log retrieval fails
        
    Requirements: 9.1, 9.3, 9.4, 9.5
    """
    try:
        user_id = current_user.user_id
        
        # Validate deployment exists and belongs to user
        deployment = db.query(Deployment).filter(
            Deployment.id == uuid.UUID(deployment_id),
            Deployment.user_id == uuid.UUID(user_id)
        ).first()
        
        if not deployment:
            logger.warning(
                f"Deployment {deployment_id} not found or not accessible for user {user_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Deployment {deployment_id} not found or not accessible"
            )
        
        # Set default time range if not provided (last 1 hour)
        if not end_time:
            end_time = datetime.utcnow()
        if not start_time:
            start_time = end_time - timedelta(hours=1)
        
        time_range = TimeRange(start=start_time, end=end_time)
        
        # Build log filters
        filters = LogFilters(
            pod_name=pod_name,
            container_name=container_name,
            level=level,
            search_query=search
        )
        
        logger.info(
            f"Fetching logs for deployment {deployment_id}, "
            f"namespace: default, filters: {filters.model_dump()}"
        )
        
        # Get monitor service and fetch logs
        monitor_service = get_monitor_service()
        
        # Collect logs from async iterator
        logs = []
        async for log_entry in monitor_service.stream_logs(
            namespace="default",
            pod_name=pod_name,
            filters=filters,
            time_range=time_range
        ):
            logs.append(log_entry)
            if len(logs) >= limit:
                break
        
        logger.info(f"Retrieved {len(logs)} log entries for deployment {deployment_id}")
        
        return logs
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching logs: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch logs: {str(e)}"
        )


@router.get("/logs/{deployment_id}/stream")
async def stream_logs(
    deployment_id: str,
    pod_name: Optional[str] = Query(None, description="Filter by specific pod name"),
    container_name: Optional[str] = Query(None, description="Filter by specific container name"),
    level: Optional[str] = Query(None, description="Filter by log level (info, warning, error, debug)"),
    search: Optional[str] = Query(None, description="Search query for full-text log search"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Stream logs for a deployment in real-time
    
    This endpoint provides Server-Sent Events (SSE) streaming of logs from Loki.
    Clients can connect and receive log entries as they are generated.
    
    Query Parameters:
        - pod_name: Optional filter for specific pod
        - container_name: Optional filter for specific container
        - level: Optional filter for log level (info, warning, error, debug)
        - search: Optional search query for full-text search
    
    Args:
        deployment_id: Unique deployment identifier
        pod_name: Optional pod name filter
        container_name: Optional container name filter
        level: Optional log level filter
        search: Optional search query
        db: Database session
        current_user: Authenticated user information
        
    Returns:
        StreamingResponse with Server-Sent Events
        
    Raises:
        HTTPException: If deployment not found or streaming fails
        
    Requirements: 9.1
    """
    try:
        user_id = current_user.user_id
        
        # Validate deployment exists and belongs to user
        deployment = db.query(Deployment).filter(
            Deployment.id == uuid.UUID(deployment_id),
            Deployment.user_id == uuid.UUID(user_id)
        ).first()
        
        if not deployment:
            logger.warning(
                f"Deployment {deployment_id} not found or not accessible for user {user_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Deployment {deployment_id} not found or not accessible"
            )
        
        # Build log filters
        filters = LogFilters(
            pod_name=pod_name,
            container_name=container_name,
            level=level,
            search_query=search
        )
        
        logger.info(
            f"Starting log stream for deployment {deployment_id}, "
            f"namespace: default, filters: {filters.model_dump()}"
        )
        
        # Get monitor service
        monitor_service = get_monitor_service()
        
        # Create async generator for streaming
        async def log_generator():
            """Generate Server-Sent Events for log streaming."""
            try:
                # Stream logs from last 5 minutes and continue
                end_time = datetime.utcnow()
                start_time = end_time - timedelta(minutes=5)
                time_range = TimeRange(start=start_time, end=end_time)
                
                async for log_entry in monitor_service.stream_logs(
                    namespace="default",
                    pod_name=pod_name,
                    filters=filters,
                    time_range=time_range
                ):
                    # Format as Server-Sent Event
                    log_json = log_entry.model_dump_json()
                    yield f"data: {log_json}\n\n"
                    
            except Exception as e:
                logger.error(f"Error in log stream: {str(e)}", exc_info=True)
                error_msg = f'{{"error": "Stream error: {str(e)}"}}'
                yield f"data: {error_msg}\n\n"
        
        return StreamingResponse(
            log_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Disable nginx buffering
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting log stream: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start log stream: {str(e)}"
        )



@router.post("/analyze-logs", response_model=AnalysisResult)
async def analyze_logs(
    request: AnalysisRequest,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
) -> AnalysisResult:
    """
    Analyze logs using AI to detect issues and provide recommendations
    
    This endpoint uses LLMs to perform intelligent analysis of Kubernetes logs,
    including:
    - Anomaly detection
    - Common error identification (OOMKilled, CrashLoopBackOff, ImagePullBackOff)
    - Severity classification
    - Actionable recommendations
    
    Request Body:
        - deployment_id: Unique deployment identifier
        - namespace: Kubernetes namespace (default: "default")
        - time_range: Optional time range for log analysis
        - model: LLM model to use (default: "gpt-4")
    
    Args:
        request: AnalysisRequest with deployment_id, namespace, time_range, and model
        db: Database session
        current_user: Authenticated user information
        
    Returns:
        AnalysisResult with summary, anomalies, errors, and recommendations
        
    Raises:
        HTTPException: If deployment not found or analysis fails
        
    Requirements: 10.1, 10.2, 10.3, 10.4
    """
    try:
        user_id = current_user.user_id
        
        # Validate deployment exists and belongs to user
        deployment = db.query(Deployment).filter(
            Deployment.id == uuid.UUID(request.deployment_id),
            Deployment.user_id == uuid.UUID(user_id)
        ).first()
        
        if not deployment:
            logger.warning(
                f"Deployment {request.deployment_id} not found or not accessible for user {user_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Deployment {request.deployment_id} not found or not accessible"
            )
        
        # Set default time range if not provided (last 1 hour)
        if request.time_range:
            time_range = request.time_range
        else:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=1)
            time_range = TimeRange(start=start_time, end=end_time)
        
        logger.info(
            f"Starting log analysis for deployment {request.deployment_id}, "
            f"namespace: {request.namespace}, model: {request.model}"
        )
        
        # Get monitor service and fetch logs
        monitor_service = get_monitor_service()
        
        # Collect logs for analysis (limit to 500 most recent entries)
        logs = []
        async for log_entry in monitor_service.stream_logs(
            namespace=request.namespace,
            pod_name=None,
            filters=None,
            time_range=time_range
        ):
            logs.append(log_entry)
            if len(logs) >= 500:
                break
        
        if not logs:
            logger.warning(f"No logs found for deployment {request.deployment_id}")
            return AnalysisResult(
                summary="No logs available for analysis in the specified time range.",
                anomalies=[],
                common_errors=[],
                recommendations=["Verify that pods are running and generating logs."],
                severity="info"
            )
        
        logger.info(f"Collected {len(logs)} log entries for analysis")
        
        # Get LLM router from config
        from app.config import settings
        from app.services.llm_providers import (
            OpenAIProvider,
            AnthropicProvider,
            GoogleProvider,
            OllamaProvider
        )
        
        # Initialize LLM providers (in production, these would come from user config)
        providers = {}
        
        if settings.openai_api_key:
            providers["openai"] = OpenAIProvider(api_key=settings.openai_api_key)
        if settings.anthropic_api_key:
            providers["anthropic"] = AnthropicProvider(api_key=settings.anthropic_api_key)
        if settings.google_api_key:
            providers["google"] = GoogleProvider(api_key=settings.google_api_key)
        if settings.ollama_endpoint:
            providers["ollama"] = OllamaProvider(endpoint=settings.ollama_endpoint)
        
        if not providers:
            logger.error("No LLM providers configured")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No LLM providers configured. Please configure API keys in settings."
            )
        
        llm_router = LLMRouter(providers=providers)
        
        # Get AI analyzer service and perform analysis
        ai_analyzer = get_ai_analyzer_service(llm_router)
        
        # Set model parameters for analysis
        parameters = ModelParameters(
            temperature=0.3,  # Lower temperature for focused analysis
            max_tokens=2000
        )
        
        analysis_result = ai_analyzer.analyze_logs(
            logs=logs,
            model=request.model,
            parameters=parameters
        )
        
        logger.info(
            f"Analysis complete for deployment {request.deployment_id}. "
            f"Severity: {analysis_result.severity}, "
            f"Errors: {len(analysis_result.common_errors)}, "
            f"Anomalies: {len(analysis_result.anomalies)}"
        )
        
        return analysis_result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing logs: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze logs: {str(e)}"
        )
