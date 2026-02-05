"""
Base task class with common functionality
"""

from celery import Task
from celery.utils.log import get_task_logger
from typing import Any, Dict, Optional
import traceback
import time
from datetime import datetime

logger = get_task_logger(__name__)


class BaseTask(Task):
    """Base task class with common functionality for all Celery tasks"""
    
    def __init__(self):
        self.start_time: Optional[float] = None
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Called when task is retried"""
        logger.warning(
            f"Task {self.name} [{task_id}] retry {self.request.retries + 1}/{self.max_retries}: {exc}"
        )
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Called when task fails"""
        execution_time = time.time() - self.start_time if self.start_time else 0
        logger.error(
            f"Task {self.name} [{task_id}] failed after {execution_time:.2f}s: {exc}\n"
            f"Traceback: {einfo.traceback}"
        )
        
        # Store failure details for retrieval
        self.update_task_status(
            task_id=task_id,
            status="FAILURE",
            result={
                "error": str(exc),
                "traceback": einfo.traceback,
                "execution_time": execution_time,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    def on_success(self, retval, task_id, args, kwargs):
        """Called when task succeeds"""
        execution_time = time.time() - self.start_time if self.start_time else 0
        logger.info(f"Task {self.name} [{task_id}] completed successfully in {execution_time:.2f}s")
        
        # Update task status with success details
        if isinstance(retval, dict):
            retval["execution_time"] = execution_time
            retval["timestamp"] = datetime.utcnow().isoformat()
        
        self.update_task_status(
            task_id=task_id,
            status="SUCCESS",
            result=retval
        )
    
    def __call__(self, *args, **kwargs):
        """Override call to track execution time"""
        self.start_time = time.time()
        logger.info(f"Starting task {self.name} [{self.request.id}]")
        return super().__call__(*args, **kwargs)
    
    def update_task_status(self, task_id: str, status: str, result: Any = None):
        """Update task status in result backend"""
        try:
            self.update_state(
                task_id=task_id,
                state=status,
                meta=result
            )
        except Exception as e:
            logger.error(f"Failed to update task status: {e}")
    
    def send_progress_update(self, task_id: str, progress: int, message: str, **kwargs):
        """Send progress update for long-running tasks"""
        try:
            self.update_state(
                task_id=task_id,
                state="PROGRESS",
                meta={
                    "progress": progress,
                    "message": message,
                    "timestamp": datetime.utcnow().isoformat(),
                    **kwargs
                }
            )
            logger.info(f"Task {task_id} progress: {progress}% - {message}")
        except Exception as e:
            logger.error(f"Failed to send progress update: {e}")
    
    def validate_input(self, **kwargs) -> Dict[str, Any]:
        """Validate task input parameters - override in subclasses"""
        return kwargs
    
    def cleanup(self):
        """Cleanup resources - override in subclasses"""
        pass