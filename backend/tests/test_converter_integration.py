"""
Integration test for ConverterService with real components
"""

from app.services.converter import ConverterService
from app.services.parser import ParserService
from app.services.llm_router import LLMRouter, ModelParameters
from app.services.cache import CacheService


SAMPLE_COMPOSE = """
version: '3.8'

services:
  web:
    image: nginx:latest
    ports:
      - "8080:80"
    environment:
      - ENV=production
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
"""


def test_full_integration():
    """Test full integration without actual LLM calls"""
    print("Testing ConverterService Integration...")
    print()
    
    # Step 1: Parse Docker Compose
    print("1. Parsing Docker Compose...")
    parser = ParserService()
    compose = parser.parse_compose(SAMPLE_COMPOSE)
    print(f"   ✓ Parsed {len(compose.services)} services")
    print(f"   ✓ Parsed {len(compose.volumes)} volumes")
    print()
    
    # Step 2: Initialize services
    print("2. Initializing services...")
    llm_router = LLMRouter({})  # Empty providers for this test
    cache = CacheService()
    converter = ConverterService(llm_router, cache)
    print("   ✓ ConverterService initialized")
    print()
    
    # Step 3: Test prompt generation
    print("3. Testing prompt generation...")
    prompt = converter._build_conversion_prompt(compose, SAMPLE_COMPOSE)
    assert "web" in prompt
    assert "db" in prompt
    assert "nginx:latest" in prompt
    assert "postgres:13" in prompt
    print("   ✓ Prompt generated correctly")
    print()
    
    # Step 4: Test system prompt
    print("4. Testing system prompt...")
    system_prompt = converter._get_system_prompt()
    assert "Kubernetes" in system_prompt
    assert "best practices" in system_prompt
    print("   ✓ System prompt contains required elements")
    print()
    
    # Step 5: Test fallback manifest generation
    print("5. Testing fallback manifest generation...")
    for service in compose.services:
        deployment = converter.generate_deployment(service)
        assert "kind: Deployment" in deployment
        assert f"name: {service.name}" in deployment
        print(f"   ✓ Generated Deployment for {service.name}")
        
        if service.ports:
            k8s_service = converter.generate_service(service)
            assert "kind: Service" in k8s_service
            print(f"   ✓ Generated Service for {service.name}")
    print()
    
    # Step 6: Test LLM response parsing
    print("6. Testing LLM response parsing...")
    sample_response = """
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: default
spec:
  replicas: 1
---
apiVersion: v1
kind: Service
metadata:
  name: web
  namespace: default
spec:
  type: ClusterIP
"""
    manifests = converter._parse_llm_response(sample_response, compose)
    assert len(manifests) == 2
    assert manifests[0].kind == "Deployment"
    assert manifests[1].kind == "Service"
    print(f"   ✓ Parsed {len(manifests)} manifests from response")
    print()
    
    # Step 7: Test manifest enhancement
    print("7. Testing manifest enhancement...")
    basic_deployment = {
        'apiVersion': 'apps/v1',
        'kind': 'Deployment',
        'metadata': {'name': 'test'},
        'spec': {
            'template': {
                'spec': {
                    'containers': [
                        {
                            'name': 'test',
                            'image': 'nginx:latest',
                            'ports': [{'containerPort': 80}]
                        }
                    ]
                }
            }
        }
    }
    
    enhanced = converter._enhance_deployment(basic_deployment, compose)
    container = enhanced['spec']['template']['spec']['containers'][0]
    
    assert 'resources' in container
    assert 'livenessProbe' in container
    assert 'readinessProbe' in container
    assert 'securityContext' in container
    assert 'strategy' in enhanced['spec']
    print("   ✓ Best practices applied to deployment")
    print()
    
    # Step 8: Test caching
    print("8. Testing cache integration...")
    compose_hash = cache.hash_compose(SAMPLE_COMPOSE)
    print(f"   ✓ Generated hash: {compose_hash[:16]}...")
    
    # Clear any existing cache
    cache.clear_cache(f"conversion:{compose_hash}")
    
    # Verify no cache
    cached = cache.get_cached_conversion(compose_hash)
    assert cached is None
    print("   ✓ Cache miss verified")
    
    # Cache a result
    from app.schemas import KubernetesManifest
    test_manifests = [
        KubernetesManifest(
            kind="Deployment",
            name="test",
            content="apiVersion: apps/v1\nkind: Deployment",
            namespace="default"
        )
    ]
    manifest_dicts = [m.model_dump() for m in test_manifests]
    cache.cache_conversion(compose_hash, manifest_dicts)
    
    # Verify cache hit
    cached = cache.get_cached_conversion(compose_hash)
    assert cached is not None
    assert len(cached['manifests']) == 1
    print("   ✓ Cache hit verified")
    print()
    
    print("=" * 60)
    print("All integration tests passed! ✓")
    print("=" * 60)


if __name__ == "__main__":
    test_full_integration()
