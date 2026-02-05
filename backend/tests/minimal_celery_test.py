#!/usr/bin/env python3
"""
Minimal Celery test to isolate the issue
"""

from celery import Celery
import time

# Create minimal celery app
app = Celery('minimal_celery_test', broker='redis://localhost:6379/0', backend='redis://localhost:6379/0')

@app.task
def add(x, y):
    print(f"Adding {x} + {y}")
    return x + y

def test_minimal():
    print("Testing minimal Celery setup...")
    
    # Test task
    task = add.delay(4, 4)
    print(f"Task ID: {task.id}")
    
    # Wait for result
    timeout = 10
    start_time = time.time()
    
    while not task.ready() and (time.time() - start_time) < timeout:
        print(f"Waiting... ({int(time.time() - start_time)}s)")
        time.sleep(1)
    
    if task.ready():
        if task.successful():
            print(f"✅ Result: {task.result}")
            return True
        else:
            print(f"❌ Failed: {task.result}")
            return False
    else:
        print("❌ Timeout")
        return False

if __name__ == "__main__":
    success = test_minimal()
    exit(0 if success else 1)