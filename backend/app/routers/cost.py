"""
Cost Estimation API endpoints.

Provides endpoints for estimating cloud costs based on Kubernetes deployments.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models import Deployment
from app.schemas import CostEstimateResponse, KubernetesManifest
from app.services.cost_estimator import CostEstimationService
from app.auth import get_current_user, TokenData

router = APIRouter(prefix="/api", tags=["cost-estimation"])


@router.get(
    "/cost-estimate/{deployment_id}",
    response_model=CostEstimateResponse,
    summary="Get cost estimate for deployment",
    description="Calculate estimated monthly cloud costs for a deployment based on resource requirements"
)
async def get_cost_estimate(
    deployment_id: str,
    cloud_provider: str = Query(
        default="gke",
        description="Cloud provider for pricing: gke, eks, aks"
    ),
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get cost estimate for a deployment.
    
    Calculates estimated monthly costs based on:
    - CPU requests from Deployments/StatefulSets
    - Memory requests from Deployments/StatefulSets
    - Storage requests from PersistentVolumeClaims
    - Selected cloud provider pricing model
    
    Args:
        deployment_id: UUID of the deployment
        cloud_provider: Cloud provider (gke, eks, aks)
        db: Database session
        current_user: Authenticated user
        
    Returns:
        CostEstimateResponse with resource breakdown and estimated costs
        
    Raises:
        HTTPException: If deployment not found or provider not supported
    """
    # Fetch deployment from database
    deployment = db.query(Deployment).filter(
        Deployment.id == deployment_id,
        Deployment.user_id == current_user.user_id
    ).first()
    
    if not deployment:
        raise HTTPException(
            status_code=404,
            detail=f"Deployment {deployment_id} not found"
        )
    
    # Convert stored manifests to KubernetesManifest objects
    manifests = []
    for manifest_data in deployment.manifests:
        manifests.append(
            KubernetesManifest(
                kind=manifest_data.get("kind", ""),
                name=manifest_data.get("name", ""),
                content=manifest_data.get("content", ""),
                namespace=manifest_data.get("namespace", "default")
            )
        )
    
    # Validate cloud provider
    valid_providers = ["gke", "eks", "aks"]
    if cloud_provider.lower() not in valid_providers:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid cloud provider. Supported providers: {', '.join(valid_providers)}"
        )
    
    # Calculate cost estimate
    try:
        cost_service = CostEstimationService()
        estimate = cost_service.estimate_deployment_cost(
            deployment_id=deployment_id,
            manifests=manifests,
            cloud_provider=cloud_provider.lower()
        )
        
        return estimate
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error calculating cost estimate: {str(e)}"
        )
