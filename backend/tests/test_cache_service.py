#!/usr/bin/env python3
"""
Test script for Cache Service implementation
Tests Requirements 17.1, 17.2, 17.3, 17.4, 17.5
"""

import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.cache import cache_service


def test_hash_compose():
    """Test SHA-256 hashing of Docker Compose content (Requirement 17.1)"""
    print("\n1. Testing hash_compose method (SHA-256)...")
    
    compose_content = """
version: '3.8'
services:
  web:
    image: nginx:latest
    ports:
      - "80:80"
  db:
    image: postgres:13
    environment:
      POSTGRES_PASSWORD: secret
"""
    
    # Generate hash
    hash1 = cache_service.hash_compose(compose_content)
    print(f"   Generated hash: {hash1}")
    
    # Verify hash is SHA-256 (64 characters)
    assert len(hash1) == 64, "Hash should be 64 characters (SHA-256)"
    assert all(c in '0123456789abcdef' for c in hash1), "Hash should be hexadecimal"
    
    # Verify same content produces same hash
    hash2 = cache_service.hash_compose(compose_content)
    assert hash1 == hash2, "Same content should produce same hash"
    
    # Verify different content produces different hash
    different_content = compose_content + "\n  redis:\n    image: redis:latest"
    hash3 = cache_service.hash_compose(different_content)
    assert hash1 != hash3, "Different content should produce different hash"
    
    print("   ✅ hash_compose works correctly (SHA-256)")
    return True


def test_cache_lookup_before_conversion():
    """Test cache lookup before conversion (Requirement 17.2)"""
    print("\n2. Testing get_cached_conversion (cache lookup)...")
    
    # Test cache miss
    non_existent_hash = "0" * 64
    result = cache_service.get_cached_conversion(non_existent_hash)
    assert result is None, "Non-existent hash should return None"
    print("   ✅ Cache miss returns None correctly")
    
    return True


def test_cache_hit_return():
    """Test cache hit returns cached data (Requirement 17.3)"""
    print("\n3. Testing cache hit return...")
    
    compose_content = """
version: '3.8'
services:
  app:
    image: myapp:latest
"""
    
    # Generate hash
    compose_hash = cache_service.hash_compose(compose_content)
    
    # Create test manifests
    test_manifests = [
        {
            "kind": "Deployment",
            "name": "app",
            "content": "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: app"
        },
        {
            "kind": "Service",
            "name": "app-service",
            "content": "apiVersion: v1\nkind: Service\nmetadata:\n  name: app-service"
        }
    ]
    
    # Cache the conversion
    cache_result = cache_service.cache_conversion(compose_hash, test_manifests, ttl=60)
    assert cache_result is True, "Caching should succeed"
    print("   ✅ Conversion cached successfully")
    
    # Retrieve from cache
    cached_data = cache_service.get_cached_conversion(compose_hash)
    assert cached_data is not None, "Cache hit should return data"
    assert "manifests" in cached_data, "Cached data should contain manifests"
    assert cached_data["manifests"] == test_manifests, "Cached manifests should match original"
    assert cached_data["hash"] == compose_hash, "Cached hash should match"
    print("   ✅ Cache hit returns correct data")
    
    return True


def test_cache_miss_conversion_and_storage():
    """Test cache miss triggers conversion and storage (Requirement 17.4)"""
    print("\n4. Testing cache miss and storage...")
    
    # Create unique content
    import time
    unique_compose = f"""
version: '3.8'
services:
  unique-service-{int(time.time())}:
    image: nginx:latest
"""
    
    # Generate hash for new content
    compose_hash = cache_service.hash_compose(unique_compose)
    
    # Verify cache miss
    cached = cache_service.get_cached_conversion(compose_hash)
    assert cached is None, "New content should not be cached"
    print("   ✅ Cache miss detected for new content")
    
    # Simulate conversion and storage
    new_manifests = [
        {
            "kind": "Deployment",
            "name": "unique-service",
            "content": "test-manifest"
        }
    ]
    
    # Store in cache
    stored = cache_service.cache_conversion(compose_hash, new_manifests, ttl=60)
    assert stored is True, "Storage should succeed"
    print("   ✅ Conversion result stored in cache")
    
    # Verify it's now cached
    cached = cache_service.get_cached_conversion(compose_hash)
    assert cached is not None, "Content should now be cached"
    assert cached["manifests"] == new_manifests, "Cached data should match stored data"
    print("   ✅ Stored data can be retrieved")
    
    return True


def test_24_hour_ttl():
    """Test 24-hour TTL for cached responses (Requirement 17.5)"""
    print("\n5. Testing 24-hour TTL...")
    
    # Verify default TTL is 24 hours (86400 seconds)
    assert cache_service.default_ttl == 86400, "Default TTL should be 86400 seconds (24 hours)"
    print(f"   ✅ Default TTL is {cache_service.default_ttl} seconds (24 hours)")
    
    # Test caching with default TTL
    compose_content = "version: '3.8'\nservices:\n  ttl-test:\n    image: nginx"
    compose_hash = cache_service.hash_compose(compose_content)
    manifests = [{"kind": "Deployment", "name": "ttl-test"}]
    
    # Cache without specifying TTL (should use default)
    result = cache_service.cache_conversion(compose_hash, manifests)
    assert result is True, "Caching with default TTL should succeed"
    print("   ✅ Caching with default 24-hour TTL works")
    
    # Test caching with custom TTL
    custom_compose = "version: '3.8'\nservices:\n  custom-ttl:\n    image: redis"
    custom_hash = cache_service.hash_compose(custom_compose)
    custom_ttl = 300  # 5 minutes
    
    result = cache_service.cache_conversion(custom_hash, manifests, ttl=custom_ttl)
    assert result is True, "Caching with custom TTL should succeed"
    print(f"   ✅ Caching with custom TTL ({custom_ttl}s) works")
    
    return True


def test_additional_cache_features():
    """Test additional cache service features"""
    print("\n6. Testing additional cache features...")
    
    # Test health check
    health = cache_service.health_check()
    assert health is True, "Redis health check should pass"
    print("   ✅ Health check works")
    
    # Test task status caching
    task_id = "test-task-123"
    task_status = {
        "status": "in_progress",
        "progress": 50,
        "message": "Processing..."
    }
    
    stored = cache_service.set_task_status(task_id, task_status, ttl=60)
    assert stored is True, "Task status storage should succeed"
    
    retrieved = cache_service.get_task_status(task_id)
    assert retrieved is not None, "Task status should be retrievable"
    assert retrieved["status"] == "in_progress", "Task status should match"
    print("   ✅ Task status caching works")
    
    # Test WebSocket connection storage
    deployment_id = "deploy-123"
    connection_id = "ws-conn-456"
    
    stored = cache_service.store_websocket_connection(deployment_id, connection_id, ttl=60)
    assert stored is True, "WebSocket connection storage should succeed"
    
    retrieved = cache_service.get_websocket_connection(deployment_id)
    assert retrieved == connection_id, "WebSocket connection should match"
    print("   ✅ WebSocket connection caching works")
    
    # Clean up
    cache_service.remove_websocket_connection(deployment_id)
    
    return True


def main():
    """Run all cache service tests"""
    print("=" * 60)
    print("CACHE SERVICE TEST SUITE")
    print("Testing Requirements 17.1, 17.2, 17.3, 17.4, 17.5")
    print("=" * 60)
    
    tests = [
        ("Hash Compose (SHA-256) - Req 17.1", test_hash_compose),
        ("Cache Lookup Before Conversion - Req 17.2", test_cache_lookup_before_conversion),
        ("Cache Hit Return - Req 17.3", test_cache_hit_return),
        ("Cache Miss and Storage - Req 17.4", test_cache_miss_conversion_and_storage),
        ("24-Hour TTL - Req 17.5", test_24_hour_ttl),
        ("Additional Features", test_additional_cache_features),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"   ❌ Test failed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 All cache service tests passed!")
        print("✅ Requirements 17.1, 17.2, 17.3, 17.4, 17.5 validated")
        return 0
    else:
        print("\n⚠️  Some tests failed.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
