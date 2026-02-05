# Converter Service Implementation

## Overview

The ConverterService is responsible for transforming Docker Compose configurations into production-ready Kubernetes manifests using Large Language Models (LLMs). It integrates with the LLM Router for AI-powered conversion and the Cache Service for performance optimization.

## Architecture

```
┌─────────────────┐
│ Docker Compose  │
│   YAML File     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ ParserService   │ ◄── Validates and extracts structure
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ ConverterService│
│                 │
│  ┌───────────┐  │
│  │ Cache     │  │ ◄── Check for cached conversion
│  │ Check     │  │
│  └─────┬─────┘  │
│        │        │
│        ▼        │
│  ┌───────────┐  │
│  │ LLM       │  │ ◄── Generate manifests using AI
│  │ Router    │  │
│  └─────┬─────┘  │
│        │        │
│        ▼        │
│  ┌───────────┐  │
│  │ Best      │  │ ◄── Apply Kubernetes best practices
│  │ Practices │  │
│  └─────┬─────┘  │
│        │        │
│        ▼        │
│  ┌───────────┐  │
│  │ Cache     │  │ ◄── Store result for future use
│  │ Store     │  │
│  └───────────┘  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Kubernetes     │
│   Manifests     │
└─────────────────┘
```

## Key Features

### 1. AI-Powered Conversion

The service uses LLMs to intelligently convert Docker Compose to Kubernetes:

- **Context-Aware**: Understands service relationships and dependencies
- **Best Practices**: Automatically applies Kubernetes best practices
- **Complete Coverage**: Generates all necessary manifest types
- **Production-Ready**: Includes health checks, resource limits, and security contexts

### 2. Caching System

Implements intelligent caching to reduce API costs and improve performance:

- **Hash-Based**: Uses SHA-256 hash of Docker Compose content
- **24-Hour TTL**: Cached results expire after 24 hours
- **Automatic Lookup**: Checks cache before calling LLM
- **Transparent**: Returns cached flag to indicate cache hit/miss

### 3. Manifest Types Generated

The service generates all required Kubernetes resource types:

- **Deployment**: For stateless services
- **StatefulSet**: For stateful services (databases)
- **Service**: For network exposure
- **ConfigMap**: For non-sensitive configuration
- **Secret**: For sensitive data (passwords, API keys)
- **PersistentVolumeClaim**: For persistent storage
- **Ingress**: For external HTTP/HTTPS access

### 4. Best Practices Applied

Automatically enhances manifests with production best practices:

#### Health Checks
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 80
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /ready
    port: 80
  initialDelaySeconds: 5
  periodSeconds: 5
```

#### Resource Limits
```yaml
resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 512Mi
```

#### Security Context
```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: false
```

#### Rolling Update Strategy
```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1
    maxUnavailable: 0
```

## Usage

### Basic Usage

```python
from app.services.converter import ConverterService
from app.services.parser import ParserService
from app.services.llm_router import LLMRouter, ModelParameters
from app.services.llm_providers import OpenAIProvider
from app.services.cache import CacheService

# Initialize services
parser = ParserService()
llm_router = LLMRouter({
    'openai': OpenAIProvider(api_key='your-api-key')
})
cache = CacheService()
converter = ConverterService(llm_router, cache)

# Parse Docker Compose
compose_content = """
version: '3.8'
services:
  web:
    image: nginx:latest
    ports:
      - "8080:80"
"""

compose = parser.parse_compose(compose_content)

# Convert to Kubernetes
manifests, cached, conversion_time = converter.convert_to_k8s(
    compose=compose,
    compose_content=compose_content,
    model='gpt-4',
    parameters=ModelParameters(temperature=0.3, max_tokens=4000)
)

# Use the manifests
for manifest in manifests:
    print(f"{manifest.kind}: {manifest.name}")
    print(manifest.content)
```

### With Custom Parameters

```python
# Custom model parameters
parameters = ModelParameters(
    temperature=0.2,  # Lower for more consistent output
    max_tokens=6000,  # Higher for complex configurations
    system_prompt="Custom system prompt..."  # Override default
)

manifests, cached, conversion_time = converter.convert_to_k8s(
    compose=compose,
    compose_content=compose_content,
    model='claude-sonnet',
    parameters=parameters
)
```

### Checking Cache

```python
# Check if conversion is cached
compose_hash = cache.hash_compose(compose_content)
cached_result = cache.get_cached_conversion(compose_hash)

if cached_result:
    print("Using cached conversion")
else:
    print("Will generate new conversion")
```

## API Reference

### ConverterService

#### `__init__(llm_router: LLMRouter, cache: CacheService)`

Initialize the converter service.

**Parameters:**
- `llm_router`: LLM Router instance for AI generation
- `cache`: Cache service instance for result caching

#### `convert_to_k8s(compose, compose_content, model, parameters=None)`

Convert Docker Compose to Kubernetes manifests.

**Parameters:**
- `compose`: Parsed ComposeStructure object
- `compose_content`: Original Docker Compose YAML string
- `model`: LLM model identifier (e.g., 'gpt-4', 'claude-sonnet')
- `parameters`: Optional ModelParameters for generation

**Returns:**
- Tuple of `(manifests, cached, conversion_time)`
  - `manifests`: List of KubernetesManifest objects
  - `cached`: Boolean indicating if result was cached
  - `conversion_time`: Float of seconds taken

**Raises:**
- `Exception`: If conversion fails

#### `generate_deployment(service: ServiceDefinition) -> str`

Generate Deployment manifest for a service (fallback method).

**Parameters:**
- `service`: ServiceDefinition from Docker Compose

**Returns:**
- YAML string for Deployment manifest

#### `generate_service(service: ServiceDefinition) -> str`

Generate Service manifest for network exposure (fallback method).

**Parameters:**
- `service`: ServiceDefinition from Docker Compose

**Returns:**
- YAML string for Service manifest

## Prompt Engineering

### System Prompt

The service uses a carefully crafted system prompt to guide the LLM:

```
You are an expert Kubernetes architect and DevOps engineer. Your task is to 
convert Docker Compose configurations into production-ready Kubernetes manifests.

Follow these guidelines:
1. Generate separate YAML manifests for each Kubernetes resource type
2. Apply Kubernetes best practices including:
   - Health checks (liveness and readiness probes)
   - Resource limits and requests (CPU and memory)
   - Rolling update strategies
   - Security contexts (non-root users, read-only filesystems where possible)
3. Use appropriate Kubernetes resource types:
   - Deployment for stateless services
   - StatefulSet for stateful services (databases)
   - Service for network exposure
   - ConfigMap for non-sensitive configuration
   - Secret for sensitive data
   - PersistentVolumeClaim for persistent storage
   - Ingress for external HTTP/HTTPS access
4. Maintain service dependencies and relationships
5. Use meaningful labels and selectors
6. Set appropriate namespace (default if not specified)

Format your response as separate YAML documents separated by '---'.
Each document should be a complete, valid Kubernetes manifest.
```

### Conversion Prompt

The conversion prompt includes:

1. **Docker Compose Content**: Full YAML configuration
2. **Requirements**: Specific manifest types to generate
3. **Service Details**: Summary of each service with key attributes
4. **Network Information**: Networks and their configurations
5. **Best Practices Reminder**: Explicit request for production-ready output

## Error Handling

### LLM Provider Errors

The service handles LLM provider errors through the LLM Router:

- **Retry Logic**: 3 attempts with exponential backoff (1s, 2s, 4s)
- **Provider Fallback**: Can switch to alternative providers
- **Context Management**: Automatically truncates large files

### Parsing Errors

If LLM response cannot be parsed:

- **Graceful Degradation**: Skips invalid YAML documents
- **Logging**: Warns about parsing failures
- **Partial Results**: Returns successfully parsed manifests

### Cache Errors

If cache operations fail:

- **Non-Blocking**: Continues without caching
- **Logging**: Logs cache errors for debugging
- **Fallback**: Always generates fresh conversion if cache fails

## Performance Considerations

### Caching Strategy

- **First Request**: 10-30 seconds (LLM generation)
- **Cached Request**: <100ms (Redis lookup)
- **Cache Hit Rate**: Typically 60-80% in production

### Optimization Tips

1. **Use Lower Temperature**: 0.2-0.3 for more consistent output
2. **Batch Conversions**: Convert multiple services together
3. **Cache Warming**: Pre-generate common configurations
4. **Model Selection**: Use faster models for simple conversions

## Testing

### Unit Tests

Run the test suite:

```bash
cd backend
python test_converter_service.py
```

Tests cover:
- Service initialization
- Prompt generation
- LLM response parsing
- Manifest enhancement
- Cache integration
- Fallback methods

### Integration Tests

Test with real LLM providers:

```bash
cd backend
export OPENAI_API_KEY=your-key
python example_converter_usage.py
```

## Troubleshooting

### Common Issues

#### 1. "Provider not configured"

**Cause**: LLM provider not initialized in LLM Router

**Solution**: 
```python
providers = {
    'openai': OpenAIProvider(api_key='your-key')
}
llm_router = LLMRouter(providers)
```

#### 2. "All retry attempts failed"

**Cause**: LLM provider unavailable or API key invalid

**Solution**:
- Check API key is valid
- Verify network connectivity
- Check provider status page
- Try alternative provider

#### 3. "Failed to parse YAML document"

**Cause**: LLM generated invalid YAML

**Solution**:
- Lower temperature for more consistent output
- Use more specific prompts
- Try different model
- Check LLM response in logs

#### 4. "Redis cache not available"

**Cause**: Redis not running or not accessible

**Solution**:
- Start Redis: `docker-compose up redis`
- Check Redis connection in config
- Service continues without cache

## Best Practices

### 1. Model Selection

- **GPT-4**: Best quality, slower, more expensive
- **Claude Sonnet**: Good balance of quality and speed
- **Gemini Pro**: Fast, good for simple conversions
- **Llama (Ollama)**: Free, local, good for development

### 2. Parameter Tuning

```python
# For production conversions
parameters = ModelParameters(
    temperature=0.2,      # Consistent output
    max_tokens=4000,      # Sufficient for most cases
    system_prompt=None    # Use default
)

# For experimental conversions
parameters = ModelParameters(
    temperature=0.7,      # More creative
    max_tokens=6000,      # Handle complex cases
    system_prompt="..."   # Custom instructions
)
```

### 3. Cache Management

```python
# Clear old cache entries
cache.clear_cache("conversion:*")

# Set custom TTL for specific conversions
cache.cache_conversion(
    compose_hash=hash,
    manifests=manifests,
    ttl=3600  # 1 hour instead of 24
)
```

### 4. Error Recovery

```python
try:
    manifests, cached, time = converter.convert_to_k8s(...)
except Exception as e:
    logger.error(f"Conversion failed: {e}")
    # Fallback to manual generation
    manifests = [
        converter.generate_deployment(service)
        for service in compose.services
    ]
```

## Future Enhancements

### Planned Features

1. **Multi-Cluster Support**: Generate manifests for different cluster types
2. **Custom Templates**: User-defined manifest templates
3. **Validation**: Pre-deployment manifest validation
4. **Optimization**: Automatic resource sizing based on workload
5. **Migration**: Support for Docker Swarm and other formats

### Extensibility

The service is designed for easy extension:

```python
class CustomConverterService(ConverterService):
    def _enhance_deployment(self, deployment, compose):
        # Add custom enhancements
        deployment = super()._enhance_deployment(deployment, compose)
        # Your custom logic here
        return deployment
```

## Related Documentation

- [LLM Router Implementation](LLM_ROUTER_IMPLEMENTATION.md)
- [Cache Service Implementation](CACHE_SERVICE_IMPLEMENTATION.md)
- [Parser Service Documentation](backend/app/services/parser.py)
- [Requirements Document](.kiro/specs/devops-k8s-platform/requirements.md)
- [Design Document](.kiro/specs/devops-k8s-platform/design.md)

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the test suite for examples
3. Check logs for detailed error messages
4. Refer to the design document for architecture details
