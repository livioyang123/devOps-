# ConverterService Quick Start Guide

## Overview

The ConverterService transforms Docker Compose files into Kubernetes manifests using AI. This guide shows you how to use it in 5 minutes.

## Quick Example

```python
from app.services.converter import ConverterService
from app.services.parser import ParserService
from app.services.llm_router import LLMRouter, ModelParameters
from app.services.llm_providers import OpenAIProvider
from app.services.cache import CacheService

# 1. Setup (one-time initialization)
parser = ParserService()
llm_router = LLMRouter({
    'openai': OpenAIProvider(api_key='your-openai-key')
})
cache = CacheService()
converter = ConverterService(llm_router, cache)

# 2. Parse Docker Compose
compose_content = open('docker-compose.yml').read()
compose = parser.parse_compose(compose_content)

# 3. Convert to Kubernetes
manifests, cached, time = converter.convert_to_k8s(
    compose=compose,
    compose_content=compose_content,
    model='gpt-4'
)

# 4. Use the manifests
for manifest in manifests:
    print(f"Generated {manifest.kind}: {manifest.name}")
    # Save to file
    with open(f"{manifest.kind}-{manifest.name}.yaml", 'w') as f:
        f.write(manifest.content)
```

## What You Get

The converter generates production-ready Kubernetes manifests with:

✓ **Deployments** - For your services  
✓ **Services** - For networking  
✓ **ConfigMaps** - For configuration  
✓ **Secrets** - For sensitive data  
✓ **PersistentVolumeClaims** - For storage  
✓ **Ingress** - For external access  

Plus automatic best practices:
- Health checks (liveness & readiness probes)
- Resource limits (CPU & memory)
- Security contexts (non-root users)
- Rolling update strategies

## Configuration Options

### Model Selection

```python
# OpenAI GPT-4 (best quality)
model = 'gpt-4'

# Anthropic Claude (good balance)
model = 'claude-sonnet'

# Google Gemini (fast)
model = 'gemini-pro'

# Local Ollama (free)
model = 'llama2'
```

### Parameters

```python
parameters = ModelParameters(
    temperature=0.3,    # Lower = more consistent
    max_tokens=4000,    # Increase for complex configs
    system_prompt=None  # Use default or customize
)
```

## Common Use Cases

### 1. Simple Web App

```yaml
# docker-compose.yml
version: '3.8'
services:
  web:
    image: nginx:latest
    ports:
      - "80:80"
```

Generates: Deployment + Service

### 2. Web App + Database

```yaml
version: '3.8'
services:
  web:
    image: myapp:latest
    ports:
      - "8080:8080"
    depends_on:
      - db
  db:
    image: postgres:13
    environment:
      - POSTGRES_PASSWORD=secret
    volumes:
      - db_data:/var/lib/postgresql/data
volumes:
  db_data:
```

Generates: 2 Deployments + 2 Services + Secret + PVC

### 3. Microservices

```yaml
version: '3.8'
services:
  frontend:
    image: frontend:latest
    ports:
      - "80:80"
  api:
    image: api:latest
    ports:
      - "8080:8080"
  worker:
    image: worker:latest
  redis:
    image: redis:alpine
```

Generates: 4 Deployments + 3 Services

## Caching

The converter automatically caches results:

```python
# First call: 10-30 seconds (LLM generation)
manifests, cached, time = converter.convert_to_k8s(...)
print(f"Cached: {cached}")  # False
print(f"Time: {time}s")     # ~15s

# Second call with same input: <100ms (cache hit)
manifests, cached, time = converter.convert_to_k8s(...)
print(f"Cached: {cached}")  # True
print(f"Time: {time}s")     # ~0.05s
```

Cache expires after 24 hours.

## Error Handling

```python
try:
    manifests, cached, time = converter.convert_to_k8s(...)
except ValueError as e:
    print(f"Invalid Docker Compose: {e}")
except Exception as e:
    print(f"Conversion failed: {e}")
    # Fallback to manual generation
    manifests = []
    for service in compose.services:
        deployment = converter.generate_deployment(service)
        manifests.append(deployment)
```

## Testing

Run the test suite:

```bash
cd backend
python test_converter_service.py
```

Run integration tests:

```bash
python test_converter_integration.py
```

Verify implementation:

```bash
python verify_converter_implementation.py
```

## Environment Setup

### Required

```bash
# Install dependencies
pip install -r requirements.txt

# Start Redis (for caching)
docker-compose up redis
```

### Optional (for LLM providers)

```bash
# OpenAI
export OPENAI_API_KEY=your-key

# Anthropic
export ANTHROPIC_API_KEY=your-key

# Google
export GOOGLE_API_KEY=your-key

# Ollama (local)
ollama serve
```

## Troubleshooting

### "Provider not configured"

Add the provider to LLM Router:

```python
llm_router = LLMRouter({
    'openai': OpenAIProvider(api_key='your-key')
})
```

### "All retry attempts failed"

Check:
1. API key is valid
2. Network connectivity
3. Provider status

### "Redis cache not available"

Start Redis:

```bash
docker-compose up redis
```

Or continue without cache (slower but works).

## Next Steps

1. **API Integration**: Use in FastAPI endpoints
2. **Async Processing**: Integrate with Celery tasks
3. **Frontend Display**: Show manifests in UI
4. **Deployment**: Apply manifests to cluster

## Full Documentation

See [CONVERTER_SERVICE_IMPLEMENTATION.md](CONVERTER_SERVICE_IMPLEMENTATION.md) for:
- Complete API reference
- Architecture details
- Advanced usage
- Performance tuning
- Security considerations

## Support

- Check test files for examples
- Review documentation
- Check logs for errors
- Refer to design document
