#!/usr/bin/env python3
"""
Test Celery configuration
"""

from app.config import settings
from app.celery_app import celery_app

def test_celery_config():
    print("Testing Celery configuration...")
    print(f"Settings broker URL: {settings.celery_broker_url}")
    print(f"Settings result backend: {settings.celery_result_backend}")
    print(f"Celery broker URL: {celery_app.conf.broker_url}")
    print(f"Celery result backend: {celery_app.conf.result_backend}")
    
    # Test broker connection
    try:
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        if stats:
            print(f"✅ Connected to broker, found {len(stats)} workers")
            return True
        else:
            print("❌ No workers found")
            return False
    except Exception as e:
        print(f"❌ Broker connection failed: {e}")
        return False

if __name__ == "__main__":
    success = test_celery_config()
    exit(0 if success else 1)