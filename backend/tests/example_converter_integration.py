"""
Example: How the LLM Router will integrate with the Converter Service

This demonstrates the planned integration between LLM Router and Converter Service
for Docker Compose to Kubernetes conversion.

Note: This is a preview/example. The actual Converter Service will be implemented in Task 6.
"""

from app.services import (
    LLMRouter,
    ModelParameters,
    OpenAIProvider,
    AnthropicProvider
)
from app.config import settings


def example_converter_integration():
    """
    Example showing how Converter Service will use LLM Router
    """
    print("=" * 70)
    print("Example: Converter Service Integration with LLM Router")
    print("=" * 70)
    
    # Step 1: Initialize LLM Router with available providers
    print("\n[Step 1] Initializing LLM Router with providers...")
    providers = {}
    
    if settings.openai_api_key:
        providers['openai'] = OpenAIProvider(api_key=settings.openai_api_key)
        print("  ✓ OpenAI provider configured")
    
    if settings.anthropic_api_key:
        providers['anthropic'] = AnthropicProvider(api_key=settings.anthropic_api_key)
        print("  ✓ Anthropic provider configured")
    
    if not providers:
        print("  ⚠ No providers configured. Set API keys in .env file")
        return
    
    router = LLMRouter(providers=providers)
    print(f"  ✓ Router initialized with {len(providers)} provider(s)")
    
    # Step 2: Sample Docker Compose input
    print("\n[Step 2] Sample Docker Compose configuration...")
    docker_compose = """
version: '3.8'

services:
  web:
    image: nginx:1.21
    ports:
      - "80:80"
      - "443:443"
    environment:
      - NGINX_HOST=example.com
      - NGINX_PORT=80
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - web-data:/var/www/html
    depends_on:
      - api
    restart: unless-stopped

  api:
    image: node:18-alpine
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - DATABASE_URL=postgresql://user:pass@db:5432/myapp
      - REDIS_URL=redis://cache:6379
    volumes:
      - ./app:/usr/src/app
    depends_on:
      - db
      - cache
    restart: unless-stopped

  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=myapp
    volumes:
      - db-data:/var/lib/postgresql/data
    restart: unless-stopped

  cache:
    image: redis:7-alpine
    restart: unless-stopped

volumes:
  web-data:
  db-data:
"""
    
    print(docker_compose)
    
    # Step 3: Configure conversion parameters
    print("\n[Step 3] Configuring conversion parameters...")
    params = ModelParameters(
        temperature=0.3,  # Lower temperature for more deterministic output
        max_tokens=4000,
        system_prompt="""You are a Kubernetes expert specializing in converting 
Docker Compose configurations to production-ready Kubernetes manifests. 

Follow these best practices:
1. Add health checks (liveness and readiness probes)
2. Set resource limits (CPU and memory)
3. Use rolling update strategy
4. Apply security contexts (non-root user, read-only filesystem where possible)
5. Separate sensitive data into Secrets
6. Use ConfigMaps for non-sensitive configuration
7. Create appropriate Services for network exposure
8. Add proper labels and annotations"""
    )
    
    print(f"  ✓ Temperature: {params.temperature}")
    print(f"  ✓ Max tokens: {params.max_tokens}")
    print(f"  ✓ System prompt configured")
    
    # Step 4: Build conversion prompt
    print("\n[Step 4] Building conversion prompt...")
    prompt = f"""Convert the following Docker Compose configuration to Kubernetes manifests.

Docker Compose:
```yaml
{docker_compose}
```

Generate the following Kubernetes manifests:

1. **Deployments** - One for each service (web, api, db, cache)
   - Include health checks (livenessProbe, readinessProbe)
   - Set resource limits (requests and limits for CPU/memory)
   - Use rolling update strategy
   - Apply security contexts

2. **Services** - For network exposure
   - ClusterIP for internal services (api, db, cache)
   - LoadBalancer or NodePort for web service

3. **ConfigMaps** - For non-sensitive environment variables
   - NGINX_HOST, NGINX_PORT
   - NODE_ENV
   - Any other non-sensitive config

4. **Secrets** - For sensitive data
   - DATABASE_URL
   - POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
   - Any other credentials

5. **PersistentVolumeClaims** - For persistent storage
   - web-data volume
   - db-data volume

6. **Ingress** (optional) - If external access is needed
   - Route traffic to web service

Format each manifest as a separate YAML document with '---' separator.
Include comments explaining key configurations.
"""
    
    print("  ✓ Prompt built with detailed instructions")
    
    # Step 5: Generate Kubernetes manifests using LLM Router
    print("\n[Step 5] Generating Kubernetes manifests...")
    print("  (This would call the LLM API - skipped in example)")
    
    # In actual implementation:
    # try:
    #     manifests_yaml = router.generate(
    #         prompt=prompt,
    #         model="gpt-4",  # or user-selected model
    #         parameters=params,
    #         retry_count=3
    #     )
    #     print("  ✓ Manifests generated successfully")
    #     return manifests_yaml
    # except Exception as e:
    #     print(f"  ✗ Generation failed: {e}")
    #     raise
    
    # Step 6: Parse and validate generated manifests
    print("\n[Step 6] Parse and validate manifests (future implementation)...")
    print("  - Split YAML documents by '---' separator")
    print("  - Validate each manifest with Kubernetes schema")
    print("  - Extract manifest types (Deployment, Service, etc.)")
    print("  - Store in database with deployment record")
    
    # Step 7: Cache the result
    print("\n[Step 7] Cache conversion result (future implementation)...")
    print("  - Generate hash of Docker Compose content")
    print("  - Store manifests in Redis with 24-hour TTL")
    print("  - Future requests with same compose will use cache")
    
    print("\n" + "=" * 70)
    print("Integration Example Complete!")
    print("=" * 70)
    print("\nNext Steps:")
    print("  1. Implement Converter Service (Task 6)")
    print("  2. Integrate with Cache Service (Task 5)")
    print("  3. Create API endpoints (Task 7)")
    print("  4. Add frontend integration (Tasks 9-10)")


def example_with_retry_scenario():
    """
    Example showing retry logic in action
    """
    print("\n" + "=" * 70)
    print("Example: Retry Logic in Converter Service")
    print("=" * 70)
    
    providers = {}
    if settings.openai_api_key:
        providers['openai'] = OpenAIProvider(api_key=settings.openai_api_key)
    
    if not providers:
        print("⚠ No providers configured")
        return
    
    router = LLMRouter(providers=providers)
    
    print("\nScenario: LLM API is temporarily unavailable")
    print("\nRouter behavior:")
    print("  1. Attempt 1: Immediate request → Fails")
    print("  2. Wait 1 second...")
    print("  3. Attempt 2: Retry → Fails")
    print("  4. Wait 2 seconds...")
    print("  5. Attempt 3: Retry → Succeeds!")
    print("\n✓ Conversion completes successfully despite temporary failures")
    print("\nThis ensures robust operation even with intermittent API issues.")


def example_context_window_scenario():
    """
    Example showing context window management
    """
    print("\n" + "=" * 70)
    print("Example: Context Window Management")
    print("=" * 70)
    
    providers = {}
    if settings.openai_api_key:
        providers['openai'] = OpenAIProvider(api_key=settings.openai_api_key)
    
    if not providers:
        print("⚠ No providers configured")
        return
    
    router = LLMRouter(providers=providers)
    
    print("\nScenario: Very large Docker Compose file (>10,000 lines)")
    print("\nRouter behavior:")
    print("  1. Estimate token count: ~15,000 tokens")
    print("  2. Check model limit: 8,192 tokens (GPT-4)")
    print("  3. Truncate content to fit: ~7,000 tokens")
    print("  4. Add truncation notice")
    print("  5. Send to LLM")
    print("\n✓ Large files are handled gracefully without errors")
    print("\nAlternative: Use Claude 3 (200K context) for very large files")


if __name__ == "__main__":
    # Run examples
    example_converter_integration()
    example_with_retry_scenario()
    example_context_window_scenario()
    
    print("\n" + "=" * 70)
    print("All Integration Examples Complete!")
    print("=" * 70)
