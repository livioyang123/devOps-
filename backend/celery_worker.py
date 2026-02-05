#!/usr/bin/env python3
"""
Celery worker entry point
Run with: celery -A celery_worker worker --loglevel=info
"""

import os
import sys

# Add the app directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.celery_app import celery_app

if __name__ == "__main__":
    celery_app.start()