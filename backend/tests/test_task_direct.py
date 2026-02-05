#!/usr/bin/env python3
"""
Test task execution directly through Celery app
"""

from app.celery_app import celery_app
import time

def test_task_direct():
    print("Testing task execution through Celery app...")
    
    try:
        # Send task directly through celery app
        task = celery_app.send_task(
            'app.tasks.conversion.convert_compose_to_k8s',
            args=['version: "3.8"\nservices:\n  web:\n    image: nginx', 'gpt-4', {'temperature': 0.7}]
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
                print(f"Result: {result}")
                return True
            else:
                print(f"❌ Task failed: {task.result}")
                return False
        else:
            print("❌ Task timed out")
            return False
            
    except Exception as e:
        print(f"❌ Task execution failed: {e}")
        return False

if __name__ == "__main__":
    success = test_task_direct()
    exit(0 if success else 1)