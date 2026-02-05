"""
Test suite for ConverterService
"""

import pytest
from app.services.converter import ConverterService
from app.services.llm_router import LLMRouter, ModelParameters
from app.services.llm_providers import OpenAIProvider
from app.services.cache import CacheService
from app.services.parser import ParserService
from app.schemas import ComposeStructure, ServiceDefinition, PortMapping


# Sample Docker Compose content for testing
SAMPLE_COMPOSE = """
version: '3.8'

services:
  web:
    image: nginx:latest
    ports:
      - "8080:80"
    environment:
      - ENV=production
      - DEBUG=false
    depends_on:
      - db
  
  db:
    image: postgres:13
    environment:
      - POSTGRES_PASSWORD=secret
      - POSTGRES_USER=admin
    volumes:
      - db_data:/var/lib/postgresql/data

volumes:
  db_data:

networks:
  default:
    driver: bridge
"""


def test_converter_service_initialization():
    """Test that ConverterService can be initialized"""
    # Create mock LLM router
    providers = {}
    llm_router = LLMRouter(providers)
    cache = CacheService()
    
    converter = ConverterService(llm_router, cache)
    
    assert converter is not None
    assert converter.llm_router == llm_router
    assert converter.cache == cache


def test_system_prompt_generation():
    """Test that system prompt is properly formatted"""
    providers = {}
    llm_router = LLMRouter(providers)
    cache = CacheService()
    converter = ConverterService(llm_router, cache)
    
    system_prompt = converter._get_system_prompt()
    
    assert "Kubernetes" in system_prompt
    assert "best practices" in system_prompt
    assert "Deployment" in system_prompt
    assert "Service" in system_prompt
    assert "ConfigMap" in system_prompt
    assert "Secret" in system_prompt


def test_conversion_prompt_building():
    """Test that conversion prompt includes all necessary information"""
    providers = {}
    llm_router = LLMRouter(providers)
    cache = CacheService()
    converter = ConverterService(llm_router, cache)
    
    # Parse sample compose
    parser = ParserService()
    compose = parser.parse_compose(SAMPLE_COMPOSE)
    
    prompt = converter._build_conversion_prompt(compose, SAMPLE_COMPOSE)
    
    # Verify prompt contains key information
    assert "web" in prompt
    assert "db" in prompt
    assert "nginx:latest" in prompt
    assert "postgres:13" in prompt
    assert "8080:80" in prompt
    assert "Deployment" in prompt
    assert "Service" in prompt
    assert "ConfigMap" in prompt or "environment variables" in prompt


def test_parse_llm_response():
    """Test parsing LLM response into manifests"""
    providers = {}
    llm_router = LLMRouter(providers)
    cache = CacheService()
    converter = ConverterService(llm_router, cache)
    
    # Sample LLM response with multiple manifests
    llm_response = """
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: web
  template:
    metadata:
      labels:
        app: web
    spec:
      containers:
      - name: web
        image: nginx:latest
        ports:
        - containerPort: 80
---
apiVersion: v1
kind: Service
metadata:
  name: web
  namespace: default
spec:
  selector:
    app: web
  ports:
  - port: 8080
    targetPort: 80
  type: ClusterIP
"""
    
    parser = ParserService()
    compose = parser.parse_compose(SAMPLE_COMPOSE)
    
    manifests = converter._parse_llm_response(llm_response, compose)
    
    assert len(manifests) == 2
    assert manifests[0].kind == "Deployment"
    assert manifests[0].name == "web"
    assert manifests[1].kind == "Service"
    assert manifests[1].name == "web"


def test_generate_deployment_fallback():
    """Test fallback deployment generation"""
    providers = {}
    llm_router = LLMRouter(providers)
    cache = CacheService()
    converter = ConverterService(llm_router, cache)
    
    service = ServiceDefinition(
        name="test-service",
        image="nginx:latest",
        ports=[PortMapping(host="8080", container="80")],
        environment={"ENV": "test"}
    )
    
    deployment_yaml = converter.generate_deployment(service)
    
    assert "kind: Deployment" in deployment_yaml
    assert "name: test-service" in deployment_yaml
    assert "image: nginx:latest" in deployment_yaml
    assert "containerPort: 80" in deployment_yaml


def test_generate_service_fallback():
    """Test fallback service generation"""
    providers = {}
    llm_router = LLMRouter(providers)
    cache = CacheService()
    converter = ConverterService(llm_router, cache)
    
    service = ServiceDefinition(
        name="test-service",
        image="nginx:latest",
        ports=[PortMapping(host="8080", container="80")]
    )
    
    service_yaml = converter.generate_service(service)
    
    assert "kind: Service" in service_yaml
    assert "name: test-service" in service_yaml
    assert "port: 8080" in service_yaml
    assert "targetPort: 80" in service_yaml


def test_enhance_deployment():
    """Test deployment enhancement with best practices"""
    providers = {}
    llm_router = LLMRouter(providers)
    cache = CacheService()
    converter = ConverterService(llm_router, cache)
    
    parser = ParserService()
    compose = parser.parse_compose(SAMPLE_COMPOSE)
    
    # Basic deployment without best practices
    deployment = {
        'apiVersion': 'apps/v1',
        'kind': 'Deployment',
        'metadata': {'name': 'web'},
        'spec': {
            'template': {
                'spec': {
                    'containers': [
                        {
                            'name': 'web',
                            'image': 'nginx:latest',
                            'ports': [{'containerPort': 80}]
                        }
                    ]
                }
            }
        }
    }
    
    enhanced = converter._enhance_deployment(deployment, compose)
    
    # Verify best practices are applied
    container = enhanced['spec']['template']['spec']['containers'][0]
    
    # Check resource limits
    assert 'resources' in container
    assert 'requests' in container['resources']
    assert 'limits' in container['resources']
    
    # Check health probes
    assert 'livenessProbe' in container
    assert 'readinessProbe' in container
    
    # Check security context
    assert 'securityContext' in container
    assert container['securityContext']['runAsNonRoot'] == True
    
    # Check rolling update strategy
    assert 'strategy' in enhanced['spec']
    assert enhanced['spec']['strategy']['type'] == 'RollingUpdate'


def test_cache_integration():
    """Test that caching works correctly"""
    providers = {}
    llm_router = LLMRouter(providers)
    cache = CacheService()
    converter = ConverterService(llm_router, cache)
    
    # Clear cache first
    cache.clear_cache("conversion:*")
    
    # Generate hash
    compose_hash = cache.hash_compose(SAMPLE_COMPOSE)
    
    # Verify no cached result initially
    cached = cache.get_cached_conversion(compose_hash)
    assert cached is None
    
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
    
    # Verify cached result is retrieved
    cached = cache.get_cached_conversion(compose_hash)
    assert cached is not None
    assert len(cached['manifests']) == 1
    assert cached['manifests'][0]['kind'] == "Deployment"


if __name__ == "__main__":
    # Run basic tests
    print("Running ConverterService tests...")
    
    test_converter_service_initialization()
    print("✓ Initialization test passed")
    
    test_system_prompt_generation()
    print("✓ System prompt test passed")
    
    test_conversion_prompt_building()
    print("✓ Conversion prompt test passed")
    
    test_parse_llm_response()
    print("✓ LLM response parsing test passed")
    
    test_generate_deployment_fallback()
    print("✓ Deployment generation test passed")
    
    test_generate_service_fallback()
    print("✓ Service generation test passed")
    
    test_enhance_deployment()
    print("✓ Deployment enhancement test passed")
    
    test_cache_integration()
    print("✓ Cache integration test passed")
    
    print("\nAll tests passed! ✓")
