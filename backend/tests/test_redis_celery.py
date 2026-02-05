#!/usr/bin/env python3
"""
Test script to verify Redis and Celery setup
"""

import sys
import os
import time
import asyncio

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.redis_client import redis_client
from app.celery_app import celery_app
from app.services.cache import cache_service
from app.tasks.conversion import convert_compose_to_k8s
from app.tasks.deployment import deploy_to_kubernetes
from app.tasks.monitoring import analyze_logs_with_ai


def test_redis_connection():
    """Test Redis connection"""
    print("Testing Redis connection...")
    try:
        result = redis_client.ping()
        if result:
            print("✅ Redis connection successful")
            
            # Test basic operations
            test_key = "test:connection"
            test_value = "redis_working"
            
            redis_client.set(test_key, test_value, ex=60)
            retrieved_value = redis_client.get(test_key)
            
            if retrieved_value == test_value:
                print("✅ Redis read/write operations working")
                redis_client.delete(test_key)
                return True
            else:
                print("❌ Redis read/write operations failed")
                return False
        else:
            print("❌ Redis ping failed")
            return False
    except Exception as e:
        print(f"❌ Redis connection error: {e}")
        return False


def test_cache_service():
    """Test cache service functionality"""
    print("\nTesting cache service...")
    try:
        # Test compose hashing
        test_compose = """
version: '3.8'
services:
  web:
    image: nginx:latest
    ports:
      - "80:80"
"""
        compose_hash = cache_service.hash_compose(test_compose)
        print(f"✅ Compose hash generated: {compose_hash[:16]}...")
        
        # Test caching
        test_manifests = [
            {"kind": "Deployment", "name": "web", "content": "test-manifest"}
        ]
        
        cache_result = cache_service.cache_conversion(compose_hash, test_manifests, ttl=60)
        if cache_result:
            print("✅ Conversion caching successful")
            
            # Test retrieval
            cached_manifests = cache_service.get_cached_conversion(compose_hash)
            if cached_manifests and cached_manifests.get("manifests") == test_manifests:
                print("✅ Conversion retrieval successful")
                return True
            else:
                print("❌ Conversion retrieval failed")
                return False
        else:
            print("❌ Conversion caching failed")
            return False
            
    except Exception as e:
        print(f"❌ Cache service error: {e}")
        return False


def test_celery_tasks():
    """Test Celery task execution"""
    print("\nTesting Celery tasks...")
    try:
        # Test conversion task
        print("Testing conversion task...")
        conversion_task = convert_compose_to_k8s.delay(
            compose_content="version: '3.8'\nservices:\n  web:\n    image: nginx",
            model="gpt-4",
            parameters={"temperature": 0.7}
        )
        
        print(f"✅ Conversion task submitted: {conversion_task.id}")
        
        # Wait for task completion (with timeout)
        timeout = 30
        start_time = time.time()
        
        while not conversion_task.ready() and (time.time() - start_time) < timeout:
            print(f"⏳ Waiting for conversion task... ({int(time.time() - start_time)}s)")
            time.sleep(2)
        
        if conversion_task.ready():
            if conversion_task.successful():
                result = conversion_task.result
                print(f"✅ Conversion task completed successfully")
                print(f"   Status: {result.get('status')}")
                print(f"   Model used: {result.get('model_used')}")
            else:
                print(f"❌ Conversion task failed: {conversion_task.result}")
                return False
        else:
            print("❌ Conversion task timed out")
            return False
        
        # Test deployment task
        print("\nTesting deployment task...")
        deployment_task = deploy_to_kubernetes.delay(
            manifests=[{"kind": "Deployment", "name": "test"}],
            cluster_id="test-cluster",
            deployment_id="test-deployment-123"
        )
        
        print(f"✅ Deployment task submitted: {deployment_task.id}")
        
        # Wait for task completion
        start_time = time.time()
        while not deployment_task.ready() and (time.time() - start_time) < timeout:
            print(f"⏳ Waiting for deployment task... ({int(time.time() - start_time)}s)")
            time.sleep(2)
        
        if deployment_task.ready():
            if deployment_task.successful():
                result = deployment_task.result
                print(f"✅ Deployment task completed successfully")
                print(f"   Status: {result.get('status')}")
                print(f"   Deployment ID: {result.get('deployment_id')}")
            else:
                print(f"❌ Deployment task failed: {deployment_task.result}")
                return False
        else:
            print("❌ Deployment task timed out")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Celery task error: {e}")
        return False


def main():
    """Run all tests"""
    print("🚀 Testing Redis and Celery setup...\n")
    
    tests = [
        ("Redis Connection", test_redis_connection),
        ("Cache Service", test_cache_service),
        ("Celery Tasks", test_celery_tasks)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running {test_name} test...")
        print('='*50)
        
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*50}")
    print("TEST SUMMARY")
    print('='*50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("🎉 All tests passed! Redis and Celery setup is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the setup.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)