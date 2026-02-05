"""
Configuration API endpoints for LLM providers and model settings
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import logging
import uuid
from datetime import datetime

from app.database import get_db
from app.auth import get_current_user
from app.models import User, LLMConfiguration
from app.schemas import (
    LLMProviderConfig,
    LLMProviderConfigResponse,
    LLMConfigListResponse,
    ModelInfo,
    ModelsListResponse,
    ModelSelectionRequest,
    ModelSelectionResponse,
    ModelParametersRequest,
    ModelParametersResponse,
    ModelParameters,
)
from app.encryption import encrypt_api_key, decrypt_api_key, mask_api_key
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/config", tags=["configuration"])


# Available models configuration
AVAILABLE_MODELS = [
    ModelInfo(
        id="gpt-4",
        name="GPT-4",
        provider="openai",
        description="OpenAI's most capable model, great for complex tasks",
        max_tokens=8192
    ),
    ModelInfo(
        id="gpt-3.5-turbo",
        name="GPT-3.5 Turbo",
        provider="openai",
        description="Fast and efficient model for most tasks",
        max_tokens=4096
    ),
    ModelInfo(
        id="claude-sonnet-3.5",
        name="Claude Sonnet 3.5",
        provider="anthropic",
        description="Anthropic's balanced model for general use",
        max_tokens=200000
    ),
    ModelInfo(
        id="claude-opus-3",
        name="Claude Opus 3",
        provider="anthropic",
        description="Anthropic's most powerful model",
        max_tokens=200000
    ),
    ModelInfo(
        id="gemini-pro",
        name="Gemini Pro",
        provider="google",
        description="Google's advanced AI model",
        max_tokens=32000
    ),
    ModelInfo(
        id="llama-3-70b",
        name="Llama 3 70B",
        provider="ollama",
        description="Meta's open-source large language model",
        max_tokens=8192
    ),
]


@router.post("/llm", response_model=LLMProviderConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_llm_config(
    config: LLMProviderConfig,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Create or update LLM provider configuration
    
    Encrypts API keys before storage using AES-256 encryption.
    """
    try:
        # Validate provider
        valid_providers = ["openai", "anthropic", "google", "ollama"]
        if config.provider not in valid_providers:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid provider. Must be one of: {', '.join(valid_providers)}"
            )
        
        # Encrypt API key
        encrypted_key = encrypt_api_key(config.api_key)
        
        # Check if configuration already exists for this provider
        existing_config = db.query(LLMConfiguration).filter(
            LLMConfiguration.user_id == current_user.id,
            LLMConfiguration.provider == config.provider
        ).first()
        
        if existing_config:
            # Update existing configuration
            existing_config.api_key_encrypted = encrypted_key.encode()
            existing_config.endpoint = config.endpoint
            existing_config.is_active = True
            existing_config.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing_config)
            
            logger.info(f"Updated LLM configuration for provider: {config.provider}")
            
            return LLMProviderConfigResponse(
                id=str(existing_config.id),
                provider=existing_config.provider,
                api_key_masked=mask_api_key(config.api_key),
                endpoint=existing_config.endpoint,
                is_active=existing_config.is_active,
                created_at=existing_config.created_at,
                updated_at=existing_config.updated_at
            )
        else:
            # Create new configuration
            new_config = LLMConfiguration(
                id=uuid.uuid4(),
                user_id=current_user.id,
                provider=config.provider,
                api_key_encrypted=encrypted_key.encode(),
                endpoint=config.endpoint,
                is_active=True
            )
            
            db.add(new_config)
            db.commit()
            db.refresh(new_config)
            
            logger.info(f"Created LLM configuration for provider: {config.provider}")
            
            return LLMProviderConfigResponse(
                id=str(new_config.id),
                provider=new_config.provider,
                api_key_masked=mask_api_key(config.api_key),
                endpoint=new_config.endpoint,
                is_active=new_config.is_active,
                created_at=new_config.created_at,
                updated_at=new_config.updated_at
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save LLM configuration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save configuration: {str(e)}"
        )


@router.get("/llm", response_model=LLMConfigListResponse)
async def get_llm_configs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get all LLM provider configurations for the current user
    
    Returns configurations with masked API keys for security.
    """
    try:
        configs = db.query(LLMConfiguration).filter(
            LLMConfiguration.user_id == current_user.id
        ).all()
        
        response_configs = []
        for config in configs:
            # Decrypt API key to mask it properly
            try:
                decrypted_key = decrypt_api_key(config.api_key_encrypted.decode())
                masked_key = mask_api_key(decrypted_key)
            except Exception as e:
                logger.warning(f"Failed to decrypt API key for config {config.id}: {str(e)}")
                masked_key = "****"
            
            response_configs.append(
                LLMProviderConfigResponse(
                    id=str(config.id),
                    provider=config.provider,
                    api_key_masked=masked_key,
                    endpoint=config.endpoint,
                    is_active=config.is_active,
                    created_at=config.created_at,
                    updated_at=config.updated_at
                )
            )
        
        logger.info(f"Retrieved {len(response_configs)} LLM configurations")
        return LLMConfigListResponse(configurations=response_configs)
    
    except Exception as e:
        logger.error(f"Failed to retrieve LLM configurations: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve configurations: {str(e)}"
        )


@router.get("/models", response_model=ModelsListResponse)
async def get_available_models(
    current_user: User = Depends(get_current_user)
):
    """
    Get list of available AI models
    
    Returns all supported models across different providers.
    """
    logger.info("Retrieved available models list")
    return ModelsListResponse(models=AVAILABLE_MODELS)


@router.post("/model", response_model=ModelSelectionResponse)
async def select_model(
    request: ModelSelectionRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Select the AI model to use for operations
    
    The selected model will be used for conversion and analysis tasks.
    Note: In this implementation, model selection is stored in user session/preferences.
    For production, consider storing in database or user settings.
    """
    try:
        # Validate model exists
        valid_models = [model.id for model in AVAILABLE_MODELS]
        if request.model not in valid_models:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid model. Must be one of: {', '.join(valid_models)}"
            )
        
        # In a production system, you would store this in the database
        # For now, we'll just validate and return success
        # The model selection would be passed with each request
        
        logger.info(f"Model selected: {request.model}")
        return ModelSelectionResponse(
            model=request.model,
            message=f"Model '{request.model}' selected successfully. Use this model ID in conversion and analysis requests."
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to select model: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to select model: {str(e)}"
        )


@router.post("/parameters", response_model=ModelParametersResponse)
async def update_model_parameters(
    request: ModelParametersRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Update advanced model parameters
    
    Configure temperature, max tokens, and system prompt for AI operations.
    Note: In this implementation, parameters are returned for use in requests.
    For production, consider storing in database or user settings.
    """
    try:
        # Validate parameters
        params = request.parameters
        
        if params.temperature < 0.0 or params.temperature > 2.0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Temperature must be between 0.0 and 2.0"
            )
        
        if params.max_tokens < 1 or params.max_tokens > 32000:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Max tokens must be between 1 and 32000"
            )
        
        # In a production system, you would store these in the database
        # For now, we'll just validate and return the parameters
        
        logger.info(f"Model parameters updated: temperature={params.temperature}, max_tokens={params.max_tokens}")
        return ModelParametersResponse(
            parameters=params,
            message="Model parameters updated successfully. Use these parameters in conversion and analysis requests."
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update model parameters: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update parameters: {str(e)}"
        )
