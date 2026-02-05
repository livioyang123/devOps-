#!/usr/bin/env python3
"""
Test direct task call
"""

from app.celery_app import convert_compose_to_k8s
import time

def test_direct_task():
    print("Testing direct task call...")
    
    # Call task directly using .delay()
    task = convert_compose_to_k8s.delay(
        'version: "3.8"\nservices:\n  web:\n    image: nginx',
        'gpt-4',
        {'temperature': 0.7}
    )
    
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
            print("✅ Task completed successfully!")
            print(f"Status: {result.get('status')}")
            print(f"Model used: {result.get('model_used')}")
            return True
        else:
            print(f"❌ Task failed: {task.result}")
            return False
    else:
        print("❌ Task timed out")
        return False

if __name__ == "__main__":
    success = test_direct_task()
    exit(0 if success else 1)