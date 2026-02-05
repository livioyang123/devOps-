"""
LLM Provider Implementations for OpenAI, Anthropic, Google, and Ollama
"""

import httpx
from typing import Optional
import logging
from .llm_router import LLMProvider, ModelParameters

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI API provider (GPT-4, GPT-3.5, etc.)"""
    
    def __init__(self, api_key: str, endpoint: str = "https://api.openai.com/v1"):
        """
        Initialize OpenAI provider
        
        Args:
            api_key: OpenAI API key
            endpoint: API endpoint URL (default: official OpenAI endpoint)
        """
        self.api_key = api_key
        self.endpoint = endpoint
        self.max_tokens_map = {
            'gpt-4': 8192,
            'gpt-4-32k': 32768,
            'gpt-3.5-turbo': 4096,
            'gpt-3.5-turbo-16k': 16384,
        }
    
    def generate(self, prompt: str, parameters: ModelParameters) -> str:
        """
        Generate response using OpenAI API
        
        Args:
            prompt: The prompt to send
            parameters: Generation parameters
            
        Returns:
            Generated text response
            
        Raises:
            Exception: If API call fails
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        messages = []
        if parameters.system_prompt:
            messages.append({"role": "system", "content": parameters.system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": "gpt-4",  # Default model
            "messages": messages,
            "temperature": parameters.temperature,
            "max_tokens": parameters.max_tokens
        }
        
        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    f"{self.endpoint}/chat/completions",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                
                data = response.json()
                return data['choices'][0]['message']['content']
                
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenAI API error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"OpenAI API error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"OpenAI generation failed: {str(e)}")
            raise
    
    def get_max_tokens(self) -> int:
        """Get maximum context window size"""
        return 8192  # Default for GPT-4
    
    def get_provider_name(self) -> str:
        """Get provider name"""
        return "openai"


class AnthropicProvider(LLMProvider):
    """Anthropic API provider (Claude models)"""
    
    def __init__(self, api_key: str, endpoint: str = "https://api.anthropic.com/v1"):
        """
        Initialize Anthropic provider
        
        Args:
            api_key: Anthropic API key
            endpoint: API endpoint URL (default: official Anthropic endpoint)
        """
        self.api_key = api_key
        self.endpoint = endpoint
        self.max_tokens_map = {
            'claude-3-opus': 200000,
            'claude-3-sonnet': 200000,
            'claude-3-haiku': 200000,
            'claude-2.1': 200000,
        }
    
    def generate(self, prompt: str, parameters: ModelParameters) -> str:
        """
        Generate response using Anthropic API
        
        Args:
            prompt: The prompt to send
            parameters: Generation parameters
            
        Returns:
            Generated text response
            
        Raises:
            Exception: If API call fails
        """
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "claude-3-sonnet-20240229",  # Default model
            "max_tokens": parameters.max_tokens,
            "temperature": parameters.temperature,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        if parameters.system_prompt:
            payload["system"] = parameters.system_prompt
        
        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    f"{self.endpoint}/messages",
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                
                data = response.json()
                return data['content'][0]['text']
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Anthropic API error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Anthropic API error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Anthropic generation failed: {str(e)}")
            raise
    
    def get_max_tokens(self) -> int:
        """Get maximum context window size"""
        return 200000  # Claude 3 models
    
    def get_provider_name(self) -> str:
        """Get provider name"""
        return "anthropic"


class GoogleProvider(LLMProvider):
    """Google AI API provider (Gemini models)"""
    
    def __init__(self, api_key: str, endpoint: str = "https://generativelanguage.googleapis.com/v1"):
        """
        Initialize Google AI provider
        
        Args:
            api_key: Google AI API key
            endpoint: API endpoint URL (default: official Google AI endpoint)
        """
        self.api_key = api_key
        self.endpoint = endpoint
        self.max_tokens_map = {
            'gemini-pro': 32768,
            'gemini-1.5-pro': 1000000,
        }
    
    def generate(self, prompt: str, parameters: ModelParameters) -> str:
        """
        Generate response using Google AI API
        
        Args:
            prompt: The prompt to send
            parameters: Generation parameters
            
        Returns:
            Generated text response
            
        Raises:
            Exception: If API call fails
        """
        model_name = "gemini-pro"
        
        # Build the full prompt with system prompt if provided
        full_prompt = prompt
        if parameters.system_prompt:
            full_prompt = f"{parameters.system_prompt}\n\n{prompt}"
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": full_prompt}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": parameters.temperature,
                "maxOutputTokens": parameters.max_tokens,
            }
        }
        
        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    f"{self.endpoint}/models/{model_name}:generateContent?key={self.api_key}",
                    json=payload
                )
                response.raise_for_status()
                
                data = response.json()
                return data['candidates'][0]['content']['parts'][0]['text']
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Google AI API error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Google AI API error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Google AI generation failed: {str(e)}")
            raise
    
    def get_max_tokens(self) -> int:
        """Get maximum context window size"""
        return 32768  # Gemini Pro
    
    def get_provider_name(self) -> str:
        """Get provider name"""
        return "google"


class OllamaProvider(LLMProvider):
    """Ollama local model provider (Llama, Mistral, etc.)"""
    
    def __init__(self, endpoint: str = "http://localhost:11434"):
        """
        Initialize Ollama provider
        
        Args:
            endpoint: Ollama API endpoint URL (default: localhost:11434)
        """
        self.endpoint = endpoint
        self.max_tokens_map = {
            'llama2': 4096,
            'llama3': 8192,
            'mistral': 8192,
            'codellama': 16384,
        }
    
    def generate(self, prompt: str, parameters: ModelParameters) -> str:
        """
        Generate response using Ollama API
        
        Args:
            prompt: The prompt to send
            parameters: Generation parameters
            
        Returns:
            Generated text response
            
        Raises:
            Exception: If API call fails
        """
        model_name = "llama2"  # Default model
        
        # Build the full prompt with system prompt if provided
        full_prompt = prompt
        if parameters.system_prompt:
            full_prompt = f"{parameters.system_prompt}\n\n{prompt}"
        
        payload = {
            "model": model_name,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": parameters.temperature,
                "num_predict": parameters.max_tokens,
            }
        }
        
        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    f"{self.endpoint}/api/generate",
                    json=payload
                )
                response.raise_for_status()
                
                data = response.json()
                return data['response']
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Ollama API error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Ollama API error: {e.response.status_code}")
        except httpx.ConnectError:
            logger.error("Cannot connect to Ollama. Is it running?")
            raise Exception("Cannot connect to Ollama. Please ensure Ollama is running.")
        except Exception as e:
            logger.error(f"Ollama generation failed: {str(e)}")
            raise
    
    def get_max_tokens(self) -> int:
        """Get maximum context window size"""
        return 4096  # Default for Llama2
    
    def get_provider_name(self) -> str:
        """Get provider name"""
        return "ollama"
