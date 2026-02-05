"""
Unit tests for LLM Router and Providers
"""

import pytest
from unittest.mock import Mock, patch
from app.services.llm_router import LLMRouter, LLMProvider, ModelParameters
from app.services.llm_providers import (
    OpenAIProvider,
    AnthropicProvider,
    GoogleProvider,
    OllamaProvider
)


class MockLLMProvider(LLMProvider):
    """Mock provider for testing"""
    
    def __init__(self, name: str, max_tokens: int = 4096, should_fail: bool = False):
        self.name = name
        self.max_tokens_value = max_tokens
        self.should_fail = should_fail
        self.call_count = 0
    
    def generate(self, prompt: str, parameters: ModelParameters) -> str:
        self.call_count += 1
        if self.should_fail:
            raise Exception(f"Mock provider {self.name} failed")
        return f"Response from {self.name}: {prompt[:50]}"
    
    def get_max_tokens(self) -> int:
        return self.max_tokens_value
    
    def get_provider_name(self) -> str:
        return self.name


class TestLLMRouter:
    """Test LLM Router functionality"""
    
    def test_router_initialization(self):
        """Test router can be initialized with providers"""
        mock_provider = MockLLMProvider("test")
        router = LLMRouter(providers={"test": mock_provider})
        
        assert "test" in router.providers
        assert router.retry_delays == [1, 2, 4]
    
    def test_successful_generation(self):
        """Test successful generation with a provider"""
        mock_provider = MockLLMProvider("openai")
        router = LLMRouter(providers={"openai": mock_provider})
        
        params = ModelParameters(temperature=0.7, max_tokens=100)
        result = router.generate("Test prompt", "gpt-4", params)
        
        assert "Response from openai" in result
        assert mock_provider.call_count == 1
    
    def test_retry_logic_with_exponential_backoff(self):
        """Test retry logic attempts 3 times with exponential backoff"""
        mock_provider = MockLLMProvider("openai", should_fail=True)
        router = LLMRouter(providers={"openai": mock_provider})
        
        params = ModelParameters(temperature=0.7, max_tokens=100)
        
        with pytest.raises(Exception) as exc_info:
            router.generate("Test prompt", "gpt-4", params, retry_count=3)
        
        assert "All 3 retry attempts failed" in str(exc_info.value)
        assert mock_provider.call_count == 3
    
    def test_retry_succeeds_on_second_attempt(self):
        """Test that retry succeeds if provider recovers"""
        mock_provider = MockLLMProvider("openai")
        
        # Fail first attempt, succeed on second
        call_count = [0]
        original_generate = mock_provider.generate
        
        def failing_generate(prompt, params):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("First attempt fails")
            return original_generate(prompt, params)
        
        mock_provider.generate = failing_generate
        router = LLMRouter(providers={"openai": mock_provider})
        
        params = ModelParameters(temperature=0.7, max_tokens=100)
        result = router.generate("Test prompt", "gpt-4", params, retry_count=3)
        
        assert "Response from openai" in result
        assert call_count[0] == 2
    
    def test_context_window_management_no_truncation(self):
        """Test context window management when content fits"""
        router = LLMRouter(providers={})
        
        content = "Short content"
        result = router.manage_context_window(content, max_tokens=1000)
        
        assert result == content
    
    def test_context_window_management_with_truncation(self):
        """Test context window management truncates large content"""
        router = LLMRouter(providers={})
        
        # Create content that exceeds limit
        content = "x" * 50000  # ~12500 tokens
        result = router.manage_context_window(content, max_tokens=1000)
        
        assert len(result) < len(content)
        assert "[Content truncated to fit context window]" in result
    
    def test_provider_extraction_from_model_name(self):
        """Test extracting provider name from model identifier"""
        router = LLMRouter(providers={"openai": MockLLMProvider("openai")})
        
        assert router._get_provider_from_model("gpt-4") == "openai"
        assert router._get_provider_from_model("gpt-3.5-turbo") == "openai"
        assert router._get_provider_from_model("claude-3-sonnet") == "anthropic"
        assert router._get_provider_from_model("claude-opus") == "anthropic"
        assert router._get_provider_from_model("gemini-pro") == "google"
        assert router._get_provider_from_model("llama2") == "ollama"
        assert router._get_provider_from_model("mistral") == "ollama"
    
    def test_provider_not_configured_error(self):
        """Test error when provider is not configured"""
        router = LLMRouter(providers={})
        
        params = ModelParameters(temperature=0.7, max_tokens=100)
        
        with pytest.raises(ValueError) as exc_info:
            router.generate("Test prompt", "gpt-4", params)
        
        assert "Provider 'openai' not configured" in str(exc_info.value)


class TestOpenAIProvider:
    """Test OpenAI provider"""
    
    def test_provider_initialization(self):
        """Test OpenAI provider can be initialized"""
        provider = OpenAIProvider(api_key="test-key")
        
        assert provider.api_key == "test-key"
        assert provider.get_provider_name() == "openai"
        assert provider.get_max_tokens() == 8192
    
    @patch('httpx.Client')
    def test_successful_generation(self, mock_client):
        """Test successful generation with OpenAI API"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'choices': [
                {'message': {'content': 'Generated response'}}
            ]
        }
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response
        
        provider = OpenAIProvider(api_key="test-key")
        params = ModelParameters(temperature=0.7, max_tokens=100)
        
        result = provider.generate("Test prompt", params)
        
        assert result == "Generated response"
    
    @patch('httpx.Client')
    def test_api_error_handling(self, mock_client):
        """Test error handling for API failures"""
        mock_client.return_value.__enter__.return_value.post.side_effect = Exception("API Error")
        
        provider = OpenAIProvider(api_key="test-key")
        params = ModelParameters(temperature=0.7, max_tokens=100)
        
        with pytest.raises(Exception):
            provider.generate("Test prompt", params)


class TestAnthropicProvider:
    """Test Anthropic provider"""
    
    def test_provider_initialization(self):
        """Test Anthropic provider can be initialized"""
        provider = AnthropicProvider(api_key="test-key")
        
        assert provider.api_key == "test-key"
        assert provider.get_provider_name() == "anthropic"
        assert provider.get_max_tokens() == 200000
    
    @patch('httpx.Client')
    def test_successful_generation(self, mock_client):
        """Test successful generation with Anthropic API"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'content': [
                {'text': 'Generated response'}
            ]
        }
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response
        
        provider = AnthropicProvider(api_key="test-key")
        params = ModelParameters(temperature=0.7, max_tokens=100)
        
        result = provider.generate("Test prompt", params)
        
        assert result == "Generated response"


class TestGoogleProvider:
    """Test Google AI provider"""
    
    def test_provider_initialization(self):
        """Test Google provider can be initialized"""
        provider = GoogleProvider(api_key="test-key")
        
        assert provider.api_key == "test-key"
        assert provider.get_provider_name() == "google"
        assert provider.get_max_tokens() == 32768
    
    @patch('httpx.Client')
    def test_successful_generation(self, mock_client):
        """Test successful generation with Google AI API"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'candidates': [
                {
                    'content': {
                        'parts': [
                            {'text': 'Generated response'}
                        ]
                    }
                }
            ]
        }
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response
        
        provider = GoogleProvider(api_key="test-key")
        params = ModelParameters(temperature=0.7, max_tokens=100)
        
        result = provider.generate("Test prompt", params)
        
        assert result == "Generated response"


class TestOllamaProvider:
    """Test Ollama provider"""
    
    def test_provider_initialization(self):
        """Test Ollama provider can be initialized"""
        provider = OllamaProvider(endpoint="http://localhost:11434")
        
        assert provider.endpoint == "http://localhost:11434"
        assert provider.get_provider_name() == "ollama"
        assert provider.get_max_tokens() == 4096
    
    @patch('httpx.Client')
    def test_successful_generation(self, mock_client):
        """Test successful generation with Ollama API"""
        mock_response = Mock()
        mock_response.json.return_value = {
            'response': 'Generated response'
        }
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response
        
        provider = OllamaProvider()
        params = ModelParameters(temperature=0.7, max_tokens=100)
        
        result = provider.generate("Test prompt", params)
        
        assert result == "Generated response"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
