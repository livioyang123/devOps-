#!/usr/bin/env python3
"""
Simple Celery test without complex imports
"""

from celery import Celery
from app.config import settings
import time

# Create simple celery app
app = Celery(
    'simple_test',
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend
)

@app.task
def simple_add(x, y):
    """Simple addition task"""
    print(f"Adding {x} + {y}")
    time.sleep(1)  # Simulate work
    result = x + y
    print(f"Result: {result}")
    return result

def test_simple_task():
    print("Testing simple Celery task...")
    
    # Submit task
    task = simple_add.delay(4, 4)
    print(f"Task submitted with ID: {task.id}")
    
    # Wait for completion
    timeout = 10
    start_time = time.time()
    
    while not task.ready() and (time.time() - start_time) < timeout:
        print(f"Waiting... ({int(time.time() - start_time)}s)")
        time.sleep(1)
    
    if task.ready():
        if task.successful():
            result = task.result
            print(f"✅ Task completed successfully! Result: {result}")
            return True
        else:
            print(f"❌ Task failed: {task.result}")
            return False
    else:
        print("❌ Task timed out")
        return False

if __name__ == "__main__":
    success = test_simple_task()
    exit(0 if success else 1)