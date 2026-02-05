"""
API endpoints for Docker Compose operations.
"""
from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any

from app.schemas import (
    ComposeUploadRequest,
    ComposeParseResponse,
    ComposeStructure,
    ValidationResult,
    ErrorResponse,
)
from app.services import ParserService

router = APIRouter(prefix="/api/compose", tags=["compose"])
parser_service = ParserService()


@router.post("/upload", response_model=ComposeParseResponse)
async def upload_compose(request: ComposeUploadRequest) -> ComposeParseResponse:
    """
    Upload and parse a Docker Compose file.
    
    This endpoint validates the YAML syntax and extracts the structure
    including services, volumes, networks, and dependencies.
    
    Args:
        request: ComposeUploadRequest with YAML content
        
    Returns:
        ComposeParseResponse with parsed structure and validation result
        
    Raises:
        HTTPException: If parsing fails
    """
    try:
        # Validate YAML first
        validation = parser_service.validate_yaml(request.content)
        
        if not validation.valid:
            # Return validation errors without raising exception
            return ComposeParseResponse(
                structure=ComposeStructure(
                    services=[],
                    volumes=[],
                    networks=[],
                ),
                validation=validation,
            )
        
        # Parse the compose file
        structure = parser_service.parse_compose(request.content)
        
        return ComposeParseResponse(
            structure=structure,
            validation=validation,
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse Docker Compose file: {str(e)}",
        )


@router.post("/parse", response_model=ComposeStructure)
async def parse_compose(request: ComposeUploadRequest) -> ComposeStructure:
    """
    Parse a Docker Compose file and return the structure.
    
    This endpoint assumes the YAML is valid and directly returns the parsed structure.
    Use /upload endpoint for validation + parsing.
    
    Args:
        request: ComposeUploadRequest with YAML content
        
    Returns:
        ComposeStructure with extracted components
        
    Raises:
        HTTPException: If parsing fails
    """
    try:
        structure = parser_service.parse_compose(request.content)
        return structure
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse Docker Compose file: {str(e)}",
        )


@router.post("/validate", response_model=ValidationResult)
async def validate_compose(request: ComposeUploadRequest) -> ValidationResult:
    """
    Validate YAML syntax of a Docker Compose file.
    
    Args:
        request: ComposeUploadRequest with YAML content
        
    Returns:
        ValidationResult with validation status and any errors
    """
    try:
        validation = parser_service.validate_yaml(request.content)
        return validation
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate YAML: {str(e)}",
        )
