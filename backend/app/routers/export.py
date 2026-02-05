"""
Manifest Export API Router

This module provides endpoints for exporting Kubernetes manifests as ZIP archives.

Requirements: 13.2, 13.3, 13.4
"""

import uuid
import logging
import io
import zipfile
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Deployment
from app.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["export"])


def organize_manifests_by_type(manifests: List[Dict]) -> Dict[str, List[Dict]]:
    """
    Organize manifests into folders by type.
    
    Args:
        manifests: List of manifest dictionaries with 'kind', 'name', 'content'
        
    Returns:
        Dictionary mapping folder names to lists of manifests
    """
    organized = {}
    
    for manifest in manifests:
        kind = manifest.get("kind", "unknown").lower()
        
        # Map kinds to folder names (pluralized)
        folder_map = {
            "deployment": "deployments",
            "service": "services",
            "configmap": "configmaps",
            "secret": "secrets",
            "persistentvolumeclaim": "persistentvolumeclaims",
            "ingress": "ingresses",
            "statefulset": "statefulsets",
            "daemonset": "daemonsets",
            "job": "jobs",
            "cronjob": "cronjobs",
            "namespace": "namespaces",
            "serviceaccount": "serviceaccounts",
            "role": "roles",
            "rolebinding": "rolebindings",
            "clusterrole": "clusterroles",
            "clusterrolebinding": "clusterrolebindings",
        }
        
        folder_name = folder_map.get(kind, "other")
        
        if folder_name not in organized:
            organized[folder_name] = []
        
        organized[folder_name].append(manifest)
    
    return organized


def create_zip_archive(manifests: List[Dict]) -> io.BytesIO:
    """
    Create a ZIP archive containing all manifests organized by type.
    
    Args:
        manifests: List of manifest dictionaries
        
    Returns:
        BytesIO object containing the ZIP archive
    """
    # Create in-memory ZIP file
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Organize manifests by type
        organized = organize_manifests_by_type(manifests)
        
        # Add manifests to ZIP, organized in folders
        for folder_name, folder_manifests in organized.items():
            for manifest in folder_manifests:
                # Get manifest details
                name = manifest.get("name", "unnamed")
                content = manifest.get("content", "")
                
                # Create file path: folder/name.yaml
                file_path = f"{folder_name}/{name}.yaml"
                
                # Add to ZIP
                zip_file.writestr(file_path, content)
                
                logger.debug(f"Added manifest to ZIP: {file_path}")
        
        # Add a README file
        readme_content = """# Kubernetes Manifests Export

This archive contains Kubernetes manifests organized by resource type.

## Directory Structure

- deployments/: Deployment resources
- services/: Service resources
- configmaps/: ConfigMap resources
- secrets/: Secret resources
- persistentvolumeclaims/: PersistentVolumeClaim resources
- ingresses/: Ingress resources
- other/: Other resource types

## Usage

To apply all manifests to your cluster:

```bash
kubectl apply -f deployments/
kubectl apply -f services/
kubectl apply -f configmaps/
kubectl apply -f secrets/
kubectl apply -f persistentvolumeclaims/
kubectl apply -f ingresses/
```

Or apply all at once:

```bash
kubectl apply -R -f .
```

## Notes

- Review and modify manifests as needed before applying
- Ensure your kubectl context is set to the correct cluster
- Some resources may have dependencies on others (apply in order)
"""
        zip_file.writestr("README.md", readme_content)
    
    # Reset buffer position to beginning
    zip_buffer.seek(0)
    
    return zip_buffer


@router.get("/export/{deployment_id}")
async def export_manifests(
    deployment_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
) -> StreamingResponse:
    """
    Export Kubernetes manifests as a ZIP archive.
    
    This endpoint:
    1. Retrieves the deployment record from the database
    2. Organizes manifests by type into folders
    3. Creates a ZIP archive with all manifests
    4. Returns the ZIP file for download
    
    Args:
        deployment_id: Unique deployment identifier
        db: Database session
        current_user: Authenticated user information
        
    Returns:
        StreamingResponse containing the ZIP file
        
    Raises:
        HTTPException: If deployment not found or not accessible
        
    Requirements: 13.2, 13.3, 13.4
    """
    try:
        user_id = current_user.user_id
        
        logger.info(
            f"Export request for deployment {deployment_id} by user {user_id}"
        )
        
        # Query deployment
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
        
        # Check if deployment has manifests
        if not deployment.manifests or len(deployment.manifests) == 0:
            logger.warning(
                f"Deployment {deployment_id} has no manifests to export"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Deployment has no manifests to export"
            )
        
        logger.info(
            f"Creating ZIP archive for deployment {deployment_id} "
            f"with {len(deployment.manifests)} manifests"
        )
        
        # Create ZIP archive
        zip_buffer = create_zip_archive(deployment.manifests)
        
        # Generate filename
        filename = f"k8s-manifests-{deployment.name}-{deployment_id[:8]}.zip"
        
        logger.info(
            f"ZIP archive created successfully for deployment {deployment_id}: {filename}"
        )
        
        # Return as streaming response
        return StreamingResponse(
            zip_buffer,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error exporting manifests for deployment {deployment_id}: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export manifests: {str(e)}"
        )
