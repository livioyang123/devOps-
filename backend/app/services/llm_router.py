"""
LLM Router Service - Abstraction layer for multiple LLM providers
"""

import time
import asyncio
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from pydantic import BaseModel
import logging

logger = logging.getLogger(__name__)


class ModelParameters(BaseModel):
    """Parameters for LLM generation"""
    temperature: float = 0.7
    max_tokens: int = 4000
    system_prompt: Optional[str] = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    def generate(self, prompt: str, parameters: ModelParameters) -> str:
        """
        Generate response from LLM
        
        Args:
            prompt: The prompt to send to the LLM
            parameters: Generation parameters
            
        Returns:
            Generated text response
            
        Raises:
            Exception: If generation fails
        """
        pass
    
    @abstractmethod
    def get_max_tokens(self) -> int:
        """
        Get maximum context window size for this provider
        
        Returns:
            Maximum number of tokens
        """
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """
        Get the name of this provider
        
        Returns:
            Provider name (e.g., 'openai', 'anthropic')
        """
        pass


class LLMRouter:
    """
    Router for managing multiple LLM providers with retry logic and context management
    """
    
    def __init__(self, providers: Dict[str, LLMProvider]):
        """
        Initialize LLM Router
        
        Args:
            providers: Dictionary mapping provider names to LLMProvider instances
        """
        self.providers = providers
        self.retry_delays = [1, 2, 4]  # Exponential backoff: 1s, 2s, 4s
    
    def generate(
        self,
        prompt: str,
        model: str,
        parameters: ModelParameters,
        retry_count: int = 3
    ) -> str:
        """
        Generate response from specified model with retry logic
        
        Args:
            prompt: The prompt to send to the LLM
            model: Model identifier (e.g., 'gpt-4', 'claude-sonnet')
            parameters: Generation parameters
            retry_count: Number of retry attempts (default: 3)
            
        Returns:
            Generated text response
            
        Raises:
            ValueError: If provider not found
            Exception: If all retries fail
        """
        # Extract provider from model name
        provider_name = self._get_provider_from_model(model)
        
        if provider_name not in self.providers:
            raise ValueError(f"Provider '{provider_name}' not configured")
        
        provider = self.providers[provider_name]
        
        # Manage context window
        max_tokens = provider.get_max_tokens()
        managed_prompt = self.manage_context_window(prompt, max_tokens)
        
        # Retry logic with exponential backoff
        last_exception = None
        for attempt in range(retry_count):
            try:
                logger.info(
                    f"Attempting LLM generation with {provider_name} "
                    f"(attempt {attempt + 1}/{retry_count})"
                )
                response = provider.generate(managed_prompt, parameters)
                logger.info(f"Successfully generated response from {provider_name}")
                return response
                
            except Exception as e:
                last_exception = e
                logger.warning(
                    f"LLM generation failed on attempt {attempt + 1}/{retry_count}: {str(e)}"
                )
                
                # Don't sleep after the last attempt
                if attempt < retry_count - 1:
                    delay = self.retry_delays[attempt]
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
        
        # All retries failed
        error_msg = f"All {retry_count} retry attempts failed for provider '{provider_name}'"
        logger.error(f"{error_msg}. Last error: {str(last_exception)}")
        raise Exception(f"{error_msg}. Provider is unavailable. Last error: {str(last_exception)}")
    
    def manage_context_window(self, content: str, max_tokens: int) -> str:
        """
        Manage context window by truncating or summarizing content
        
        Args:
            content: The content to manage
            max_tokens: Maximum number of tokens allowed
            
        Returns:
            Managed content that fits within context window
        """
        # Rough estimation: 1 token ≈ 4 characters
        estimated_tokens = len(content) // 4
        
        if estimated_tokens <= max_tokens:
            return content
        
        # Truncate to fit within context window
        # Reserve some tokens for the response
        max_chars = (max_tokens - 1000) * 4
        
        if len(content) > max_chars:
            logger.warning(
                f"Content exceeds context window ({estimated_tokens} tokens). "
                f"Truncating to {max_tokens - 1000} tokens."
            )
            truncated = content[:max_chars]
            truncated += "\n\n[Content truncated to fit context window]"
            return truncated
        
        return content
    
    def _get_provider_from_model(self, model: str) -> str:
        """
        Extract provider name from model identifier
        
        Args:
            model: Model identifier (e.g., 'gpt-4', 'claude-sonnet-3.5')
            
        Returns:
            Provider name (e.g., 'openai', 'anthropic')
        """
        model_lower = model.lower()
        
        if 'gpt' in model_lower:
            return 'openai'
        elif 'claude' in model_lower:
            return 'anthropic'
        elif 'gemini' in model_lower:
            return 'google'
        elif 'llama' in model_lower or 'mistral' in model_lower:
            return 'ollama'
        else:
            # Default to first available provider
            if self.providers:
                return list(self.providers.keys())[0]
            raise ValueError(f"Cannot determine provider for model: {model}")
