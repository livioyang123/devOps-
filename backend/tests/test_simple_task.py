#!/usr/bin/env python3
"""
Simple test for Celery task execution
"""

import time
from app.tasks.conversion import convert_compose_to_k8s

def test_simple_task():
    print("Testing simple Celery task...")
    
    # Submit task
    task = convert_compose_to_k8s.delay(
        compose_content='version: "3.8"\nservices:\n  web:\n    image: nginx',
        model='gpt-4',
        parameters={'temperature': 0.7}
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
    success = test_simple_task()
    exit(0 if success else 1)