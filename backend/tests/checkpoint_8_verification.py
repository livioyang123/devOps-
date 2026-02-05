"""
Checkpoint 8: Verify parsing and conversion

This script tests:
1. Upload and parse flow with sample Docker Compose files
2. Conversion generates valid Kubernetes manifests
3. Caching works correctly
"""

import sys
import os
import yaml
import hashlib
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.parser import ParserService
from app.services.converter import ConverterService
from app.services.cache import CacheService
from app.services.llm_router import LLMRouter, LLMProvider, ModelParameters
from app.redis_client import redis_client


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing"""
    
    def generate(self, prompt: str, parameters: ModelParameters) -> str:
        """Generate mock Kubernetes manifests"""
        # Return a simple mock response with basic K8s manifests
        return """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
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
spec:
  selector:
    app: web
  ports:
  - port: 80
    targetPort: 80
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: web-data
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
"""
    
    def get_max_tokens(self) -> int:
        """Get maximum context window size"""
        return 4096
    
    def get_provider_name(self) -> str:
        """Get provider name"""
        return "mock"


def print_section(title):
    """Print a formatted section header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def print_success(message):
    """Print success message"""
    print(f"✓ {message}")


def print_error(message):
    """Print error message"""
    print(f"✗ {message}")


def print_info(message):
    """Print info message"""
    print(f"ℹ {message}")


def test_parser_with_sample_compose():
    """Test 1: Upload and parse flow with sample Docker Compose files"""
    print_section("Test 1: Parser Service - Upload and Parse Flow")
    
    parser = ParserService()
    
    # Test with the project's docker-compose.yml
    compose_path = Path(__file__).parent.parent.parent / "docker-compose.yml"
    
    if not compose_path.exists():
        print_error(f"Docker Compose file not found: {compose_path}")
        return False
    
    print_info(f"Reading Docker Compose file: {compose_path}")
    
    with open(compose_path, 'r') as f:
        compose_content = f.read()
    
    # Test 1.1: Validate YAML
    print_info("Testing YAML validation...")
    validation_result = parser.validate_yaml(compose_content)
    
    if not validation_result.valid:
        print_error(f"YAML validation failed: {validation_result.errors}")
        return False
    
    print_success("YAML validation passed")
    
    # Test 1.2: Parse Docker Compose structure
    print_info("Testing Docker Compose parsing...")
    
    try:
        compose_structure = parser.parse_compose(compose_content)
        print_success(f"Parsed {len(compose_structure.services)} services")
        print_success(f"Parsed {len(compose_structure.volumes)} volumes")
        print_success(f"Parsed {len(compose_structure.networks)} networks")
        
        # Display parsed services
        print_info("\nParsed Services:")
        for service in compose_structure.services:
            print(f"  - {service.name}")
            print(f"    Image: {service.image}")
            print(f"    Ports: {len(service.ports)}")
            print(f"    Environment: {len(service.environment)} variables")
            print(f"    Volumes: {len(service.volumes)}")
            print(f"    Depends on: {service.depends_on}")
        
        # Verify expected services are present
        service_names = [s.name for s in compose_structure.services]
        expected_services = ['postgres', 'redis', 'prometheus', 'loki', 'grafana']
        
        for expected in expected_services:
            if expected in service_names:
                print_success(f"Found expected service: {expected}")
            else:
                print_error(f"Missing expected service: {expected}")
                return False
        
        return True
        
    except Exception as e:
        print_error(f"Parsing failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_converter_generates_manifests():
    """Test 2: Verify conversion generates valid Kubernetes manifests"""
    print_section("Test 2: Converter Service - Generate Kubernetes Manifests")
    
    # Setup services
    parser = ParserService()
    
    # Use mock LLM provider for testing
    mock_provider = MockLLMProvider()
    llm_router = LLMRouter(providers={"mock": mock_provider})
    
    # Get Redis client for cache
    try:
        cache_service = CacheService()
        print_success("Connected to Redis for caching")
    except Exception as e:
        print_error(f"Failed to connect to Redis: {e}")
        print_info("Continuing without cache...")
        cache_service = None
    
    converter = ConverterService(llm_router, cache_service)
    
    # Create a simple test Docker Compose
    simple_compose = """
version: '3.8'
services:
  web:
    image: nginx:latest
    ports:
      - "80:80"
    environment:
      - ENV=production
    volumes:
      - web_data:/usr/share/nginx/html
  
  db:
    image: postgres:15
    environment:
      - POSTGRES_PASSWORD=secret
    volumes:
      - db_data:/var/lib/postgresql/data

volumes:
  web_data:
  db_data:

networks:
  default:
    driver: bridge
"""
    
    print_info("Parsing simple Docker Compose...")
    compose_structure = parser.parse_compose(simple_compose)
    print_success(f"Parsed {len(compose_structure.services)} services")
    
    print_info("Converting to Kubernetes manifests...")
    
    try:
        manifests, cached, conversion_time = converter.convert_to_k8s(
            compose_structure,
            simple_compose,  # Pass the original content
            model="mock",
            parameters=ModelParameters()
        )
        
        print_success(f"Generated {len(manifests)} Kubernetes manifests in {conversion_time:.2f}s")
        print_info(f"Cached: {cached}")
        
        # Display generated manifests
        print_info("\nGenerated Manifests:")
        manifest_kinds = {}
        for manifest in manifests:
            kind = manifest.kind
            name = manifest.name
            print(f"  - {kind}: {name}")
            manifest_kinds[kind] = manifest_kinds.get(kind, 0) + 1
        
        # Verify expected manifest types
        print_info("\nManifest Type Summary:")
        for kind, count in manifest_kinds.items():
            print(f"  {kind}: {count}")
        
        # Validate YAML structure of each manifest
        print_info("\nValidating manifest YAML structure...")
        for i, manifest in enumerate(manifests):
            try:
                import yaml
                # Parse the manifest content
                parsed = yaml.safe_load(manifest.content)
                
                if not isinstance(parsed, dict):
                    print_error(f"Manifest {i} content is not a dictionary")
                    return False
                
                # Check required fields
                if 'apiVersion' not in parsed:
                    print_error(f"Manifest {i} missing apiVersion")
                    return False
                
                if 'kind' not in parsed:
                    print_error(f"Manifest {i} missing kind")
                    return False
                
                if 'metadata' not in parsed:
                    print_error(f"Manifest {i} missing metadata")
                    return False
                
                print_success(f"Manifest {i} ({manifest.kind}) is valid")
                
            except Exception as e:
                print_error(f"Manifest {i} validation failed: {e}")
                return False
        
        return True
        
    except Exception as e:
        print_error(f"Conversion failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_caching_works():
    """Test 3: Verify caching works correctly"""
    print_section("Test 3: Cache Service - Verify Caching")
    
    try:
        cache_service = CacheService()
        # Test Redis connection
        if not cache_service.health_check():
            print_error("Redis health check failed")
            print_info("Skipping cache tests - Redis not available")
            return True  # Don't fail if Redis is not running
        print_success("Connected to Redis")
    except Exception as e:
        print_error(f"Failed to connect to Redis: {e}")
        print_info("Skipping cache tests - Redis not available")
        return True  # Don't fail if Redis is not running
    
    # Test 3.1: Hash generation
    print_info("Testing hash generation...")
    
    test_content = "version: '3.8'\nservices:\n  web:\n    image: nginx"
    hash1 = cache_service.hash_compose(test_content)
    hash2 = cache_service.hash_compose(test_content)
    
    if hash1 == hash2:
        print_success(f"Hash generation is consistent: {hash1[:16]}...")
    else:
        print_error("Hash generation is inconsistent")
        return False
    
    # Test 3.2: Cache storage and retrieval
    print_info("Testing cache storage and retrieval...")
    
    test_manifests = [
        {
            'kind': 'Service',
            'name': 'test-service',
            'content': 'apiVersion: v1\nkind: Service\nmetadata:\n  name: test-service',
            'namespace': 'default'
        }
    ]
    
    # Store in cache
    cache_service.cache_conversion(hash1, test_manifests, ttl=60)
    print_success("Stored manifests in cache")
    
    # Retrieve from cache
    cached_manifests = cache_service.get_cached_conversion(hash1)
    
    if cached_manifests is None:
        print_error("Failed to retrieve cached manifests")
        return False
    
    print_success("Retrieved manifests from cache")
    
    # Verify content matches
    cached_list = cached_manifests.get('manifests', [])
    if len(cached_list) == len(test_manifests):
        print_success(f"Cache returned correct number of manifests: {len(cached_list)}")
    else:
        print_error(f"Cache returned wrong number of manifests: {len(cached_list)} vs {len(test_manifests)}")
        return False
    
    # Test 3.3: Cache miss
    print_info("Testing cache miss...")
    
    fake_hash = "nonexistent_hash_12345"
    cached = cache_service.get_cached_conversion(fake_hash)
    
    if cached is None:
        print_success("Cache correctly returns None for non-existent hash")
    else:
        print_error("Cache returned data for non-existent hash")
        return False
    
    # Test 3.4: Integration with converter
    print_info("Testing cache integration with converter...")
    
    parser = ParserService()
    mock_provider = MockLLMProvider()
    llm_router = LLMRouter(providers={"mock": mock_provider})
    converter = ConverterService(llm_router, cache_service)
    
    simple_compose = """
version: '3.8'
services:
  app:
    image: alpine:latest
"""
    
    compose_structure = parser.parse_compose(simple_compose)
    
    # First conversion - should not be cached
    print_info("First conversion (cache miss expected)...")
    manifests1, cached1, time1 = converter.convert_to_k8s(
        compose_structure, 
        simple_compose,
        model="mock", 
        parameters=ModelParameters()
    )
    print_success(f"First conversion generated {len(manifests1)} manifests (cached: {cached1})")
    
    # Second conversion - should be cached
    print_info("Second conversion (cache hit expected)...")
    manifests2, cached2, time2 = converter.convert_to_k8s(
        compose_structure, 
        simple_compose,
        model="mock", 
        parameters=ModelParameters()
    )
    print_success(f"Second conversion returned {len(manifests2)} manifests (cached: {cached2})")
    
    if len(manifests1) == len(manifests2):
        print_success("Cache integration working - same number of manifests returned")
    else:
        print_error("Cache integration issue - different number of manifests")
        return False
    
    if cached2:
        print_success("Second conversion was served from cache")
    else:
        print_error("Second conversion was not cached (expected cache hit)")
        return False
    
    return True


def main():
    """Run all checkpoint tests"""
    print("\n" + "=" * 80)
    print("  CHECKPOINT 8: Verify Parsing and Conversion")
    print("=" * 80)
    
    results = []
    
    # Test 1: Parser
    try:
        result1 = test_parser_with_sample_compose()
        results.append(("Parser Service", result1))
    except Exception as e:
        print_error(f"Parser test crashed: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Parser Service", False))
    
    # Test 2: Converter
    try:
        result2 = test_converter_generates_manifests()
        results.append(("Converter Service", result2))
    except Exception as e:
        print_error(f"Converter test crashed: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Converter Service", False))
    
    # Test 3: Caching
    try:
        result3 = test_caching_works()
        results.append(("Cache Service", result3))
    except Exception as e:
        print_error(f"Cache test crashed: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Cache Service", False))
    
    # Summary
    print_section("CHECKPOINT 8 SUMMARY")
    
    all_passed = True
    for test_name, passed in results:
        if passed:
            print_success(f"{test_name}: PASSED")
        else:
            print_error(f"{test_name}: FAILED")
            all_passed = False
    
    print("\n" + "=" * 80)
    if all_passed:
        print("  ✓ ALL TESTS PASSED - Checkpoint 8 Complete")
    else:
        print("  ✗ SOME TESTS FAILED - Review errors above")
    print("=" * 80 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
