"""
Template management API endpoints for pre-built Docker Compose templates
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
import uuid
import re

from app.database import get_db
from app.auth import get_current_user, get_current_user_optional, TokenData
from app.models import Template
from app.schemas import (
    TemplateResponse,
    TemplateListResponse,
    TemplateLoadRequest,
    TemplateLoadResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("", response_model=TemplateListResponse)
async def list_templates(
    db: Session = Depends(get_db),
    current_user: Optional[TokenData] = Depends(get_current_user_optional)
):
    """
    Get all available templates
    
    Returns all public templates that users can use to quickly deploy
    common application stacks.
    """
    try:
        templates = db.query(Template).filter(
            Template.is_public == True
        ).order_by(Template.category, Template.name).all()
        
        response_templates = [
            TemplateResponse(
                id=str(template.id),
                name=template.name,
                description=template.description,
                category=template.category,
                compose_content=template.compose_content,
                required_params=template.required_params,
                is_public=template.is_public,
                created_at=template.created_at
            )
            for template in templates
        ]
        
        logger.info(f"Retrieved {len(response_templates)} templates")
        return TemplateListResponse(templates=response_templates)
    
    except Exception as e:
        logger.error(f"Failed to retrieve templates: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve templates: {str(e)}"
        )


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: str,
    db: Session = Depends(get_db),
    current_user: Optional[TokenData] = Depends(get_current_user_optional)
):
    """
    Get a specific template by ID
    
    Returns the complete template information including Docker Compose content
    and any required parameters.
    """
    try:
        # Validate UUID format
        try:
            template_uuid = uuid.UUID(template_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid template ID format"
            )
        
        # Find template
        template = db.query(Template).filter(
            Template.id == template_uuid,
            Template.is_public == True
        ).first()
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template with ID '{template_id}' not found"
            )
        
        logger.info(f"Retrieved template: {template.name}")
        
        return TemplateResponse(
            id=str(template.id),
            name=template.name,
            description=template.description,
            category=template.category,
            compose_content=template.compose_content,
            required_params=template.required_params,
            is_public=template.is_public,
            created_at=template.created_at
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve template: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve template: {str(e)}"
        )


@router.post("/{template_id}/load", response_model=TemplateLoadResponse)
async def load_template(
    template_id: str,
    request: TemplateLoadRequest,
    db: Session = Depends(get_db),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Load a template with parameter substitution
    
    If the template has required parameters, this endpoint will substitute
    the provided parameter values into the Docker Compose content.
    """
    try:
        # Validate UUID format
        try:
            template_uuid = uuid.UUID(template_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid template ID format"
            )
        
        # Find template
        template = db.query(Template).filter(
            Template.id == template_uuid,
            Template.is_public == True
        ).first()
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template with ID '{template_id}' not found"
            )
        
        # Get compose content
        compose_content = template.compose_content
        
        # Check if template has required parameters
        if template.required_params:
            required_param_names = template.required_params.get("parameters", [])
            
            if required_param_names:
                # Validate that all required parameters are provided
                provided_params = request.parameters or {}
                missing_params = [
                    param for param in required_param_names 
                    if param not in provided_params
                ]
                
                if missing_params:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Missing required parameters: {', '.join(missing_params)}"
                    )
                
                # Substitute parameters in compose content
                for param_name, param_value in provided_params.items():
                    # Replace placeholders like {{PARAM_NAME}} with actual values
                    placeholder = f"{{{{{param_name}}}}}"
                    compose_content = compose_content.replace(placeholder, param_value)
        
        logger.info(f"Loaded template: {template.name}")
        
        return TemplateLoadResponse(
            template_id=str(template.id),
            name=template.name,
            compose_content=compose_content,
            message=f"Template '{template.name}' loaded successfully"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to load template: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load template: {str(e)}"
        )
