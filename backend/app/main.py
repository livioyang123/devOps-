"""
DevOps K8s Platform - FastAPI Backend
Main application entry point
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import logging

# Import Celery app and services
from app.celery_app import celery_app
from app.redis_client import redis_client
from app.services.cache import cache_service

# Import middleware
from app.middleware import (
    RateLimitMiddleware,
    InputSanitizationMiddleware,
    AuthenticationMiddleware
)

# Import routers
from app.routers import auth, compose, convert, websocket, deploy, monitor, alerts, config, clusters, export

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="DevOps K8s Platform API",
    description="API for converting Docker Compose to Kubernetes and managing deployments",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Security middleware - order matters!
# 1. Trusted host check
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

# 2. CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Rate limiting (before authentication to prevent auth brute force)
app.add_middleware(RateLimitMiddleware, requests_per_minute=60)

# 4. Input sanitization
app.add_middleware(InputSanitizationMiddleware)

# 5. Authentication check (validates token presence, not validity)
# Note: Actual token validation happens in endpoint dependencies
app.add_middleware(AuthenticationMiddleware)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return JSONResponse(
        content={"status": "healthy", "service": "devops-k8s-platform-api"}
    )

# Detailed health check with dependencies
@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check including Redis and Celery status"""
    health_status = {
        "service": "devops-k8s-platform-api",
        "status": "healthy",
        "components": {}
    }
    
    # Check Redis connection
    try:
        redis_healthy = redis_client.ping()
        health_status["components"]["redis"] = {
            "status": "healthy" if redis_healthy else "unhealthy",
            "message": "Connected" if redis_healthy else "Connection failed"
        }
    except Exception as e:
        health_status["components"]["redis"] = {
            "status": "unhealthy",
            "message": f"Error: {str(e)}"
        }
        health_status["status"] = "degraded"
    
    # Check Celery workers
    try:
        # Get active workers
        inspect = celery_app.control.inspect()
        active_workers = inspect.active()
        
        if active_workers:
            health_status["components"]["celery"] = {
                "status": "healthy",
                "message": f"Active workers: {len(active_workers)}",
                "workers": list(active_workers.keys())
            }
        else:
            health_status["components"]["celery"] = {
                "status": "unhealthy",
                "message": "No active workers found"
            }
            health_status["status"] = "degraded"
            
    except Exception as e:
        health_status["components"]["celery"] = {
            "status": "unhealthy",
            "message": f"Error: {str(e)}"
        }
        health_status["status"] = "degraded"
    
    # Check cache service
    try:
        cache_healthy = cache_service.health_check()
        health_status["components"]["cache"] = {
            "status": "healthy" if cache_healthy else "unhealthy",
            "message": "Cache service operational" if cache_healthy else "Cache service unavailable"
        }
    except Exception as e:
        health_status["components"]["cache"] = {
            "status": "unhealthy",
            "message": f"Error: {str(e)}"
        }
        health_status["status"] = "degraded"
    
    return JSONResponse(content=health_status)

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return JSONResponse(
        content={
            "message": "DevOps K8s Platform API",
            "version": "1.0.0",
            "docs": "/api/docs",
        }
    )

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(compose.router)
app.include_router(convert.router)
app.include_router(websocket.router)
app.include_router(deploy.router)
app.include_router(monitor.router)
app.include_router(alerts.router)
app.include_router(config.router)
app.include_router(clusters.router)
app.include_router(export.router)

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )