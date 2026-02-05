# LLM Router Service

The LLM Router provides a unified interface for interacting with multiple Large Language Model (LLM) providers, including OpenAI, Anthropic, Google AI, and local Ollama models.

## Features

- **Multi-Provider Support**: Seamlessly switch between OpenAI, Anthropic, Google AI, and Ollama
- **Automatic Retry Logic**: Exponential backoff retry mechanism (1s, 2s, 4s) for failed requests
- **Context Window Management**: Automatic truncation of content that exceeds provider limits
- **Provider Abstraction**: Consistent interface across all providers
- **Error Handling**: Comprehensive error handling with detailed logging

## Architecture

```
LLMRouter
├── LLMProvider (Abstract Base Class)
│   ├── OpenAIProvider
│   ├── AnthropicProvider
│   ├── GoogleProvider
│   └── OllamaProvider
```

## Installation

Required dependencies (already in requirements.txt):
```
httpx>=0.25.2
pydantic>=2.5.0
```

## Configuration

Set up API keys in your `.env` file:

```env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
```

For Ollama (local models), ensure Ollama is running:
```bash
ollama serve
```

## Usage

### Basic Usage

```python
from app.services import (
    LLMRouter,
    ModelParameters,
    OpenAIProvider
)

# Initialize provider
provider = OpenAIProvider(api_key="your-api-key")

# Create router
router = LLMRouter(providers={"openai": provider})

# Set parameters
params = ModelParameters(
    temperature=0.7,
    max_tokens=1000,
    system_prompt="You are a helpful assistant."
)

# Generate response
response = router.generate(
    prompt="Explain Kubernetes in simple terms",
    model="gpt-4",
    parameters=params
)

print(response)
```

### Multiple Providers

```python
from app.services import (
    LLMRouter,
    OpenAIProvider,
    AnthropicProvider,
    GoogleProvider,
    OllamaProvider
)

# Initialize all providers
providers = {
    "openai": OpenAIProvider(api_key="..."),
    "anthropic": AnthropicProvider(api_key="..."),
    "google": GoogleProvider(api_key="..."),
    "ollama": OllamaProvider(endpoint="http://localhost:11434")
}

router = LLMRouter(providers=providers)

# Use different models
response1 = router.generate("Hello", "gpt-4", params)
response2 = router.generate("Hello", "claude-3-sonnet", params)
response3 = router.generate("Hello", "gemini-pro", params)
response4 = router.generate("Hello", "llama2", params)
```

### Custom Retry Configuration

```python
# Retry up to 5 times instead of default 3
response = router.generate(
    prompt="Your prompt",
    model="gpt-4",
    parameters=params,
    retry_count=5
)
```

### Context Window Management

The router automatically manages context windows:

```python
# Large content will be automatically truncated
large_prompt = "x" * 100000  # Very large prompt

response = router.generate(
    prompt=large_prompt,
    model="gpt-4",
    parameters=params
)
# Content is automatically truncated to fit within the model's context window
```

## Supported Models

### OpenAI
- `gpt-4` (8K context)
- `gpt-4-32k` (32K context)
- `gpt-3.5-turbo` (4K context)
- `gpt-3.5-turbo-16k` (16K context)

### Anthropic
- `claude-3-opus` (200K context)
- `claude-3-sonnet` (200K context)
- `claude-3-haiku` (200K context)
- `claude-2.1` (200K context)

### Google AI
- `gemini-pro` (32K context)
- `gemini-1.5-pro` (1M context)

### Ollama (Local)
- `llama2` (4K context)
- `llama3` (8K context)
- `mistral` (8K context)
- `codellama` (16K context)

## Model Parameters

```python
class ModelParameters:
    temperature: float = 0.7      # Randomness (0.0 - 1.0)
    max_tokens: int = 4000        # Maximum response length
    system_prompt: Optional[str]  # System/instruction prompt
```

## Error Handling

The router handles various error scenarios:

```python
try:
    response = router.generate(prompt, model, params)
except ValueError as e:
    # Provider not configured
    print(f"Configuration error: {e}")
except Exception as e:
    # All retries failed
    print(f"Generation failed: {e}")
```

## Retry Logic

The router implements exponential backoff:

1. **First attempt**: Immediate
2. **Second attempt**: After 1 second
3. **Third attempt**: After 2 seconds
4. **Fourth attempt**: After 4 seconds

If all attempts fail, an exception is raised with details.

## Provider-Specific Notes

### OpenAI
- Requires valid API key from OpenAI
- Uses chat completions API
- Supports system prompts

### Anthropic
- Requires valid API key from Anthropic
- Uses messages API
- Supports system prompts

### Google AI
- Requires valid API key from Google AI Studio
- Uses generateContent API
- System prompt is prepended to user prompt

### Ollama
- Requires Ollama running locally
- No API key needed
- Supports local models (Llama, Mistral, etc.)
- System prompt is prepended to user prompt

## Testing

Run the test suite:

```bash
cd backend
python -m pytest test_llm_router.py -v
```

Run examples:

```bash
cd backend
python example_llm_usage.py
```

## Integration with Converter Service

The LLM Router is designed to be used by the Converter Service for Docker Compose to Kubernetes conversion:

```python
from app.services import LLMRouter, ConverterService

# Initialize router with providers
router = LLMRouter(providers=providers)

# Create converter service
converter = ConverterService(llm_router=router, cache=cache_service)

# Convert Docker Compose to Kubernetes
manifests = converter.convert_to_k8s(
    compose=compose_structure,
    model="gpt-4",
    parameters=params
)
```

## Logging

The router logs important events:

- Provider initialization
- Generation attempts
- Retry attempts with delays
- Failures and errors
- Context window truncation

Configure logging in your application:

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app.services.llm_router")
```

## Best Practices

1. **Use appropriate temperature**: Lower (0.1-0.3) for deterministic tasks, higher (0.7-0.9) for creative tasks
2. **Set reasonable max_tokens**: Balance between response completeness and cost
3. **Provide clear system prompts**: Guide the model's behavior and output format
4. **Handle errors gracefully**: Always wrap generation calls in try-except blocks
5. **Monitor API usage**: Track costs and rate limits for each provider
6. **Use caching**: Implement caching layer to avoid redundant API calls

## Requirements Validation

This implementation satisfies the following requirements:

- **Requirement 16.1**: OpenAI API support ✓
- **Requirement 16.2**: Anthropic API support ✓
- **Requirement 16.3**: Google AI API support ✓
- **Requirement 16.4**: Local Ollama support ✓
- **Requirement 16.5**: Retry logic with exponential backoff ✓
- **Requirement 16.6**: Error handling for provider unavailability ✓
- **Requirement 16.7**: Context window management ✓

## Future Enhancements

Potential improvements:

- Async/await support for concurrent requests
- Streaming responses for real-time output
- Token usage tracking and cost estimation
- Provider health monitoring
- Automatic provider selection based on availability
- Response caching at router level
- Rate limiting per provider
